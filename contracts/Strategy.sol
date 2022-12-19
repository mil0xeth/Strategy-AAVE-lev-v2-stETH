// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import {BaseStrategy,StrategyParams} from "@yearnvaults/contracts/BaseStrategy.sol";
import "@openzeppelin/contracts/math/Math.sol";
import {IERC20,Address} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "./libraries/MakerDaiDelegateLib.sol";
import "../interfaces/yearn/IBaseFee.sol";
import "../interfaces/yearn/IVault.sol";

import "../interfaces/lido/ISteth.sol";
import "../interfaces/curve/Curve.sol";
import "../interfaces/chainlink/AggregatorInterface.sol";

import "../interfaces/aave/ILendingPool.sol";
import "../interfaces/aave/IProtocolDataProvider.sol";
import "../../interfaces/aave/IPriceOracle.sol";
import "../interfaces/aave/IAToken.sol";
import "../interfaces/aave/IVariableDebtToken.sol";


contract Strategy is BaseStrategy {
    using Address for address;
    enum Action {WIND, UNWIND}

    //stETH is yieldBearing:
    ISteth internal constant yieldBearing =  ISteth(0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84);
    //WETH is borrowToken:
    IERC20 internal constant borrowToken = IERC20(0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2);

    // Use Chainlink oracle to obtain latest want/ETH price
    AggregatorInterface public chainlinkYieldBearingToETHPriceFeed;

    //AAVEV2 lending pool:
    ILendingPool private constant lendingPool = ILendingPool(0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9);
    IProtocolDataProvider private constant protocolDataProvider = IProtocolDataProvider(0x057835Ad21a177dbdd3090bB1CAE03EaCF78Fc6d);

    IPriceOracle private constant priceOracle = IPriceOracle(0xA50ba011c48153De246E5192C8f9258A2ba79Ca9);
    uint16 private constant referral = 7; // Yearn's aave referral code

    // Supply and borrow tokens
    IAToken public aToken;
    IVariableDebtToken public debtToken;

    //Balancer Flashloan:
    address internal constant balancer = 0xBA12222222228d8Ba445958a75a0704d566BF2C8;

    //----------- MAKER INIT    
    // Units used in Maker contracts
    uint256 internal constant WAD = 10**18;
    uint256 internal constant RAY = 10**27;

    //Desired collaterization ratio
    //Directly affects the leverage multiplier for every investment to leverage up the Maker vault with yieldBearing: 
    //Off-chain calculation geometric converging series: sum(1/1.02^n)-1 for n=0-->infinity --> for 102% collateralization ratio = 50x leverage.
    uint256 public collateralizationRatio;

    // Allow the collateralization ratio to drift a bit in order to avoid cycles
    uint256 public lowerRebalanceTolerance;
    uint256 public upperRebalanceTolerance;

    bool internal forceHarvestTriggerOnce; // only set this to true when we want to trigger our keepers to harvest for us
    uint256 public creditThreshold; // amount of credit in underlying tokens that will automatically trigger a harvest  

    // Maximum Single Trade possible
    uint256 public maxSingleTrade;
    // Minimum Single Trade & Minimum Profit to be taken:
    uint256 public minSingleTrade;

    //Expected flashloan fee:
    uint256 public expectedFlashloanFee;

    // Name of the strategy
    string internal strategyName;

    // ----------------- INIT FUNCTIONS TO SUPPORT CLONING -----------------

    constructor(
        address _vault,
        string memory _strategyName
    ) public BaseStrategy(_vault) {
        _initializeThis(
            _strategyName
        );
    }

    function initialize(
        address _vault,
        string memory _strategyName
    ) public {
        address sender = msg.sender;
        // Initialize BaseStrategy
        _initialize(_vault, sender, sender, sender);
        // Initialize cloned instance
        _initializeThis(
            _strategyName
        );
    }

    function _initializeThis(
        string memory _strategyName
    ) internal {
        strategyName = _strategyName;

        //chainlinkYieldBearingToETHPriceFeed = AggregatorInterface(_chainlinkYieldBearingToETHPriceFeed);
        chainlinkYieldBearingToETHPriceFeed = AggregatorInterface(0x86392dC19c0b719886221c78AB11eb8Cf5c52812);

        //10M$ dai or usdc maximum trade
        maxSingleTrade = 5_000 * 1e18;
        //10M$ dai or usdc maximum trade
        //minSingleTrade = 1 * 1e17;
        minSingleTrade = 1 * 1e10;

        creditThreshold = 1e3 * 1e18;
        maxReportDelay = 21 days; // 21 days in seconds, if we hit this then harvestTrigger = True

        // Set health check to health.ychad.eth
        healthCheck = 0xDDCea799fF1699e98EDF118e0629A974Df7DF012;

        // Current ratio can drift
        // Allow additional 20 BPS = 0.002 = 0.2% in any direction by default ==> 102.5% upper, 102.1% lower
        upperRebalanceTolerance = (500 * WAD) / 10000;
        lowerRebalanceTolerance = (500 * WAD) / 10000;

        // Minimum collateralization ratio for GUNIV3DAIUSDC is 102.3% == 10230 BPS
        //collateralizationRatio = (10230 * WAD) / 10000;
        collateralizationRatio = (20000 * WAD) / 10000;

        // Set aave tokens
        (address _aToken, , ) = protocolDataProvider.getReserveTokensAddresses(address(yieldBearing));
        ( , , address _debtToken) = protocolDataProvider.getReserveTokensAddresses(address(borrowToken));
        aToken = IAToken(_aToken);
        debtToken = IVariableDebtToken(_debtToken);

        // Let collateral targets
        //(uint256 ltv, uint256 liquidationThreshold) = getProtocolCollatRatios(address(want));
        //targetCollatRatio = liquidationThreshold.sub(DEFAULT_COLLAT_TARGET_MARGIN);
        //maxCollatRatio = liquidationThreshold.sub(DEFAULT_COLLAT_MAX_MARGIN);
        //maxBorrowCollatRatio = ltv.sub(DEFAULT_COLLAT_MAX_MARGIN);
        //(uint256 daiLtv, ) = getProtocolCollatRatios(dai);
        //daiBorrowCollatRatio = daiLtv.sub(DEFAULT_COLLAT_MAX_MARGIN);
        //DECIMALS = 10**vault.decimals();

    }


    // ----------------- SETTERS & MIGRATION -----------------

    /////////////////// Manual harvest through keepers using KP3R instead of ETH:
    function setForceHarvestTriggerOnce(bool _forceHarvestTriggerOnce)
        external
        onlyVaultManagers
    {
        forceHarvestTriggerOnce = _forceHarvestTriggerOnce;
    }

    function setCreditThreshold(uint256 _creditThreshold)
        external
        onlyVaultManagers
    {
        creditThreshold = _creditThreshold;
    }

    function setMinMaxSingleTrade(uint256 _minSingleTrade, uint256 _maxSingleTrade) external onlyVaultManagers {
        minSingleTrade = _minSingleTrade;
        maxSingleTrade = _maxSingleTrade;
    }

    function setExpectedFlashloanFee(uint256 _expectedFlashloanFee) external onlyVaultManagers {
        expectedFlashloanFee = _expectedFlashloanFee;
    }

    // Target collateralization ratio to maintain within bounds
    function setCollateralizationRatio(uint256 _collateralizationRatio)
        external
        onlyVaultManagers
    {
        require(_collateralizationRatio.sub(lowerRebalanceTolerance) > MakerDaiDelegateLib.getLiquidationRatio().mul(WAD).div(RAY)); // dev: desired collateralization ratio is too low
        collateralizationRatio = _collateralizationRatio;
    }

    // Rebalancing bands (collat ratio - tolerance, collat_ratio plus tolerance)
    function setRebalanceTolerance(uint256 _lowerRebalanceTolerance, uint256 _upperRebalanceTolerance)
        external
        onlyVaultManagers
    {
        require(collateralizationRatio.sub(_lowerRebalanceTolerance) > MakerDaiDelegateLib.getLiquidationRatio().mul(WAD).div(RAY)); // dev: desired rebalance tolerance makes allowed ratio too low
        lowerRebalanceTolerance = _lowerRebalanceTolerance;
        upperRebalanceTolerance = _upperRebalanceTolerance;
    }

    // Allow external debt repayment & direct repayment of debt with collateral (price oracle independent)
    function emergencyDebtRepayment(uint256 repayAmountOfCollateral)
        external
        onlyVaultManagers
    {
        uint256 wantBalance = balanceOfWant();
        wantBalance = Math.min(wantBalance, balanceOfDebt());
        repayAmountOfCollateral = Math.min(repayAmountOfCollateral, balanceOfCollateral());
        //free collateral and pay down debt with free want:
        MakerDaiDelegateLib.repayBorrowToken(wantBalance);
        MakerDaiDelegateLib.withdrawCollateral(repayAmountOfCollateral);
        //Desired collateral amount unlocked --> swap to want
        MakerDaiDelegateLib.swapYieldBearingToWant(repayAmountOfCollateral);
        //Pay down debt with freed collateral that was swapped to want:
        wantBalance = balanceOfWant();
        wantBalance = Math.min(wantBalance, balanceOfDebt());
        MakerDaiDelegateLib.repayBorrowToken(wantBalance);
        //If all debt is paid down, free all collateral and swap to want:
        if (balanceOfDebt() == 0){
            MakerDaiDelegateLib.withdrawCollateral(balanceOfCollateral());
            MakerDaiDelegateLib.swapYieldBearingToWant(balanceOfYieldBearing());
        }
    }

    function emergencyUnwind(uint256 repayAmountOfWant)
        external
        onlyVaultManagers
    {
        MakerDaiDelegateLib.unwind(repayAmountOfWant, getCurrentCollRatio(), address(aToken), address(debtToken));
    }

    // ******** OVERRIDEN METHODS FROM BASE CONTRACT ************

    function name() external view override returns (string memory) {
        return strategyName;
    }

    function estimatedTotalAssets() public view override returns (uint256) {  //measured in WANT
        return  
                balanceOfWant() //free WANT balance in wallet
                .add(balanceOfYieldBearing().add(balanceOfCollateral()).mul(getWantPerYieldBearing()).div(WAD))
                .sub(balanceOfDebt());
    }

    function prepareReturn(uint256 _debtOutstanding)
        internal
        override
        returns (
            uint256 _profit,
            uint256 _loss,
            uint256 _debtPayment
        )
    {
        uint256 totalDebt = vault.strategies(address(this)).totalDebt;
        uint256 totalAssetsAfterProfit = estimatedTotalAssets();
        //Here minSingleTrade represents the minimum profit of want that should be given back to the vault
        _profit = totalAssetsAfterProfit > ( totalDebt + minSingleTrade ) 
            ? totalAssetsAfterProfit.sub(totalDebt)
            : 0;
        uint256 _amountFreed;
        (_amountFreed, _loss) = liquidatePosition(_debtOutstanding.add(_profit));
        _debtPayment = Math.min(_debtOutstanding, _amountFreed);
        //Net profit and loss calculation
        if (_loss > _profit) {
            _loss = _loss.sub(_profit);
            _profit = 0;
        } else {
            _profit = _profit.sub(_loss);
            _loss = 0;
        }

        // we're done harvesting, so reset our trigger if we used it
        forceHarvestTriggerOnce = false;
    }

    function adjustPosition(uint256 _debtOutstanding) internal override {
        // If we have enough want to convert and deposit more into aave, we do it
        // Here minSingleTrade represents the minimum investment of want that makes it worth it to loop 
        if (balanceOfWant() > _debtOutstanding.add(minSingleTrade) ) {
            MakerDaiDelegateLib.wind(Math.min(maxSingleTrade, balanceOfWant().sub(_debtOutstanding)), collateralizationRatio, address(debtToken));
        } else {
            //Check if collateralizationRatio needs adjusting
            // Allow the ratio to move a bit in either direction to avoid cycles
            uint256 currentRatio = getCurrentCollRatio();
            if (currentRatio < collateralizationRatio.sub(lowerRebalanceTolerance)) { //if current ratio is BELOW goal ratio:
                uint256 currentCollateral = balanceOfCollateral();
                uint256 yieldBearingToRepay = currentCollateral.sub( currentCollateral.mul(currentRatio).div(collateralizationRatio)  );
                uint256 wantAmountToRepay = yieldBearingToRepay.mul(getWantPerYieldBearing()).div(WAD);
                MakerDaiDelegateLib.unwind(Math.min(wantAmountToRepay, maxSingleTrade), collateralizationRatio, address(aToken), address(debtToken));
            } else if (currentRatio > collateralizationRatio.add(upperRebalanceTolerance)) { //if current ratio is ABOVE goal ratio:
                // Borrow the maximum borrowToken amount possible for the deposited collateral            
                _depositCollateralAndBorrow(0, _borrowTokenAmountToBorrow(balanceOfCollateral()).sub(balanceOfDebt()));
                MakerDaiDelegateLib.wind(Math.min(maxSingleTrade, balanceOfWant().sub(_debtOutstanding)), collateralizationRatio, address(debtToken));
            }
        }
        //Check safety of collateralization ratio after all actions:
        if (balanceOfDebt() > 0) {
            require(getCurrentCollRatio() > collateralizationRatio.sub(lowerRebalanceTolerance), "unsafe coll. ratio (adjPos)");
        }

    }

    function liquidatePosition(uint256 _wantAmountNeeded)
        internal
        override
        returns (uint256 _liquidatedAmount, uint256 _loss)
    {
        //Maximum liquidation per tx is of size maxSingleTrade:
        _wantAmountNeeded = Math.min(_wantAmountNeeded, maxSingleTrade);
        uint256 wantBalance = balanceOfWant();
        //Check if we can handle it without swapping free yieldBearing or freeing collateral yieldBearing
        if (wantBalance >= _wantAmountNeeded) {
            return (_wantAmountNeeded, 0);
        }
        //Not enough want to pay _wantAmountNeeded --> unwind position
        MakerDaiDelegateLib.unwind(_wantAmountNeeded.sub(wantBalance), collateralizationRatio, address(aToken), address(debtToken));

        //update free want after liquidating
        wantBalance = balanceOfWant();
        //loss calculation and returning liquidated amount
        if (_wantAmountNeeded > wantBalance) {
            _liquidatedAmount = wantBalance;
            _loss = _wantAmountNeeded.sub(wantBalance);
        } else {
            _liquidatedAmount = _wantAmountNeeded;
            _loss = 0;
        } 
        //Check safety of collateralization ratio after all actions:
        if (balanceOfDebt() > 0) {
            require(getCurrentCollRatio() > collateralizationRatio.sub(lowerRebalanceTolerance), "unsafe coll. ratio (liqPos)");
        }
    }

    function liquidateAllPositions()
        internal
        override
        returns (uint256 _amountFreed)
    {
        (_amountFreed, ) = liquidatePosition(estimatedTotalAssets());
    }

    function harvestTrigger(uint256 callCostInWei)
        public
        view
        override
        returns (bool)
    {
        // Should not trigger if strategy is not active (no assets and no debtRatio). This means we don't need to adjust keeper job.
        if (!isActive()) {
            return false;
        }

        // check if the base fee gas price is higher than we allow. if it is, block harvests.
        if (!isBaseFeeAcceptable()) {
            return false;
        }

        // trigger if we want to manually harvest, but only if our gas price is acceptable
        if (forceHarvestTriggerOnce) {
            return true;
        }

        StrategyParams memory params = vault.strategies(address(this));
        // harvest once we reach our maxDelay if our gas price is okay
        if (block.timestamp.sub(params.lastReport) > maxReportDelay) {
            return true;
        }

        // harvest our credit if it's above our threshold
        if (vault.creditAvailable() > creditThreshold) {
            return true;
        }

        // otherwise, we don't harvest
        return false;
    }

    function tendTrigger(uint256 callCostInWei)
        public
        view
        override
        returns (bool)
    {
        // Nothing to adjust if there is no collateral locked
        if (balanceOfCollateral() == 0) {
            return false;
        }

        uint256 currentRatio = getCurrentCollRatio();
        // If we need to repay debt and are outside the tolerance bands,
        // we do it regardless of the call cost
        if (currentRatio < collateralizationRatio.sub(lowerRebalanceTolerance)) {
            return true;
        }

        // Mint more DAI if possible
        return
            currentRatio > collateralizationRatio.add(upperRebalanceTolerance) &&
            balanceOfDebt() > 0 &&
            isBaseFeeAcceptable();
    }

    function prepareMigration(address _newStrategy) internal override 
    {}

    function protectedTokens()
        internal
        view
        override
        returns (address[] memory)
    {}

    // we don't need this anymore since we don't use baseStrategy harvestTrigger
    function ethToWant(uint256 _amtInWei)
        public
        view
        virtual
        override
        returns (uint256)
    {}


    // ----------------- FLASHLOAN CALLBACK -----------------
    //Flashloan Callback:
    function receiveFlashLoan(
        IERC20[] calldata tokens,
        uint256[] calldata amounts,
        uint256[] calldata fees,
        bytes calldata data
    ) external {
        require(msg.sender == balancer);
        //require(initiator == address(this));
        uint256 fee = fees[0];
        require(fee <= expectedFlashloanFee, "fee > expectedFlashloanFee");
        (Action action, uint256 _wantAmountInitialOrRequested, uint256 flashloanAmount, uint256 _collateralizationRatio) = abi.decode(data, (Action, uint256, uint256, uint256));
        uint256 amount = amounts[0];
        _checkAllowance(balancer, address(borrowToken), amount.add(fee));
        if (action == Action.WIND) {
            MakerDaiDelegateLib._wind(amount.add(fee), _wantAmountInitialOrRequested, _collateralizationRatio);
        } else if (action == Action.UNWIND) {
            //amount = flashloanAmount, amount.add(fee) = flashloanAmount+fee for flashloan (usually 0)
            MakerDaiDelegateLib._unwind(amount, amount.add(fee), _wantAmountInitialOrRequested, _collateralizationRatio, address(aToken), address(debtToken));
        }
    }

    // ----------------- INTERNAL FUNCTIONS SUPPORT -----------------

    function _borrowTokenAmountToBorrow(uint256 _amount) internal returns (uint256) {
        return _amount.mul(getWantPerYieldBearing()).mul(WAD).div(collateralizationRatio).div(WAD);
    }

    function _checkAllowance(
        address _contract,
        address _token,
        uint256 _amount
    ) internal {
        if (IERC20(_token).allowance(address(this), _contract) < _amount) {
            IERC20(_token).safeApprove(_contract, 0);
            IERC20(_token).safeApprove(_contract, type(uint256).max);
        }
    }


    // ----------------- PUBLIC BALANCES AND CALCS -----------------
    function balanceOfWant() public view returns (uint256) {
        return want.balanceOf(address(this));
    }

    function balanceOfYieldBearing() public view returns (uint256) {
        return yieldBearing.balanceOf(address(this));
    }

    //get amount of Want in Wei that is received for 1 yieldBearing
    function getWantPerYieldBearing() public view returns (uint256){
        return uint256(chainlinkYieldBearingToETHPriceFeed.latestAnswer());
    }

    function balanceOfDebt() public view returns (uint256) {
        return debtToken.balanceOf(address(this));
    }

    // Returns collateral balance in the vault
    function balanceOfCollateral() public view returns (uint256) {
        return aToken.balanceOf(address(this));
    }

    // Effective collateralization ratio of the vault
    function getCurrentCollRatio() public view returns (uint256) {
        return _getCurrentPessimisticRatio(getWantPerYieldBearing());
    }

    // check if the current baseFee is below our external target
    function isBaseFeeAcceptable() internal view returns (bool) {
        return IBaseFee(0xb5e1CAcB567d98faaDB60a1fD4820720141f064F).isCurrentBaseFeeAcceptable();
    }


    // ----------------- AAVE INTERNAL CALCS -----------------

    function _depositCollateralAndBorrow(
        uint256 collateralAmount,
        uint256 borrowAmount
    ) internal {
        MakerDaiDelegateLib.depositCollateral(collateralAmount);
        MakerDaiDelegateLib.borrowBorrowToken(borrowAmount);
    }

    function _getTokenPriceInETH(address _token) internal view returns (uint256){
        return WAD.mul(WAD).div(priceOracle.getAssetPrice(_token));
    }

    function _getCurrentPessimisticRatio(uint256 price) internal view returns (uint256) {
        // Use pessimistic price to determine the worst ratio possible
        //uint256 externalPrice = WAD.mul(_getTokenPriceInETH(address(borrowToken))).div(_getTokenPriceInETH(address(yieldBearing)));
        //price = Math.min(price, externalPrice);
        require(price > 0); // dev: invalid price

        uint256 totalCollateralValue = balanceOfCollateral().mul(price);
        uint256 totalDebt = balanceOfDebt();

        // If for some reason we do not have debt (e.g: deposits under dust)
        // make sure the operation does not revert
        if (totalDebt == 0) {
            totalDebt = 1;
        }
        return totalCollateralValue.div(totalDebt);
    }

    //make strategy payable to be able to wrap and unwrap weth
    receive() external payable {}

}
