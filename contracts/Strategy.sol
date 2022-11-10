// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import {BaseStrategy,StrategyParams} from "@yearnvaults/contracts/BaseStrategy.sol";
import "@openzeppelin/contracts/math/Math.sol";
import {IERC20,Address} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "./libraries/MakerDaiDelegateLib.sol";
import "../interfaces/yearn/IBaseFee.sol";
import "../interfaces/yearn/IVault.sol";
import "../interfaces/GUNI/GUniPool.sol";

contract Strategy is BaseStrategy {
    using Address for address;

    //event Debug(uint256 _number, uint _value);

    enum Action {WIND, UNWIND}

    //GUNIDAIUSDC1 - Gelato Uniswap DAI/USDC LP - 0.05% fee
    //GUniPool internal constant yieldBearing = GUniPool(0xAbDDAfB225e10B90D798bB8A886238Fb835e2053);
    //bytes32 internal constant ilk_yieldBearing = 0x47554e49563344414955534443312d4100000000000000000000000000000000;
    //address internal constant gemJoinAdapter = 0xbFD445A97e7459b0eBb34cfbd3245750Dba4d7a4;
    
    //GUNIDAIUSDC2 - Gelato Uniswap DAI/USDC2 LP 2 - 0.01% fee
    GUniPool internal constant yieldBearing = GUniPool(0x50379f632ca68D36E50cfBC8F78fe16bd1499d1e);
    bytes32 internal constant ilk_yieldBearing = 0x47554e49563344414955534443322d4100000000000000000000000000000000;
    address internal constant gemJoinAdapter = 0xA7e4dDde3cBcEf122851A7C8F7A55f23c0Daf335;

    //Flashmint:
    address internal constant flashmint = 0x1EB4CF3A948E7D72A198fe073cCb8C7a948cD853;

    IERC20 internal constant borrowToken = IERC20(0x6B175474E89094C44Da98b954EedeAC495271d0F);

    //----------- MAKER INIT    
    // Units used in Maker contracts
    uint256 internal constant WAD = 10**18;
    uint256 internal constant RAY = 10**27;

    // maker vault identifier
    uint256 public cdpId;

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

        //10M$ dai or usdc maximum trade
        maxSingleTrade = 5_000_000 * 1e18;
        //10M$ dai or usdc maximum trade
        minSingleTrade = 1 * 1e17;

        creditThreshold = 1e6 * 1e18;
        maxReportDelay = 21 days; // 21 days in seconds, if we hit this then harvestTrigger = True

        // Set health check to health.ychad.eth
        healthCheck = 0xDDCea799fF1699e98EDF118e0629A974Df7DF012;

        cdpId = MakerDaiDelegateLib.openCdp(ilk_yieldBearing);
        require(cdpId > 0); // dev: error opening cdp

        // Current ratio can drift
        // Allow additional 0.002 = 0.2% in any direction by default ==> 102.5% upper, 102.1% lower
        upperRebalanceTolerance = (20 * WAD) / 10000;
        lowerRebalanceTolerance = (20 * WAD) / 10000;

        // Minimum collateralization ratio for GUNIV3DAIUSDC is 102.3% == 10230
        collateralizationRatio = (10230 * WAD) / 10000;

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

    // Target collateralization ratio to maintain within bounds
    function setCollateralizationRatio(uint256 _collateralizationRatio)
        external
        onlyEmergencyAuthorized
    {
        require(_collateralizationRatio.sub(lowerRebalanceTolerance) > MakerDaiDelegateLib.getLiquidationRatio(ilk_yieldBearing).mul(WAD).div(RAY)); // dev: desired collateralization ratio is too low
        collateralizationRatio = _collateralizationRatio;
    }

    // Rebalancing bands (collat ratio - tolerance, collat_ratio plus tolerance)
    function setRebalanceTolerance(uint256 _lowerRebalanceTolerance, uint256 _upperRebalanceTolerance)
        external
        onlyEmergencyAuthorized
    {
        require(collateralizationRatio.sub(_lowerRebalanceTolerance) > MakerDaiDelegateLib.getLiquidationRatio(ilk_yieldBearing).mul(WAD).div(RAY)); // dev: desired rebalance tolerance makes allowed ratio too low
        lowerRebalanceTolerance = _lowerRebalanceTolerance;
        upperRebalanceTolerance = _upperRebalanceTolerance;
    }

    // Required to move funds to a new cdp and use a different cdpId after migration
    // Should only be called by governance as it will move funds
    function shiftToCdp(uint256 newCdpId) external onlyGovernance {
        MakerDaiDelegateLib.shiftCdp(cdpId, newCdpId);
        cdpId = newCdpId;
    }

    // Allow address to manage Maker's CDP
    function grantCdpManagingRightsToUser(address user, bool allow)
        external
        onlyGovernance
    {
        MakerDaiDelegateLib.allowManagingCdp(cdpId, user, allow);
    }

    // Allow external debt repayment
    // Attempt to take currentRatio to target c-ratio
    function emergencyDebtRepayment(uint256 repayAmountOfWant)
        external
        onlyVaultManagers
    {
        MakerDaiDelegateLib.unwind(repayAmountOfWant, getCurrentMakerVaultRatio(), cdpId);
    }



    // ******** OVERRIDEN METHODS FROM BASE CONTRACT ************

    function name() external view override returns (string memory) {
        return strategyName;
    }

    function estimatedTotalAssets() public view override returns (uint256) {  //measured in WANT
        return  
                balanceOfWant() //free WANT balance in wallet
                .add(balanceOfYieldBearing().add(balanceOfMakerVault()).mul(getWantPerYieldBearing()).div(WAD))
                .sub(balanceOfDebt());
                //want=usdc:
                //.add(_convertBorrowTokenAmountToWant(balanceOfBorrowToken()))  // free DAI balance in wallet --> WANT
                //.sub(_convertBorrowTokenAmountToWant(balanceOfDebt()));  //DAI debt of maker --> WANT
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
        // Update accumulated stability fees,  Update the debt ceiling using DSS Auto Line
        MakerDaiDelegateLib.keepBasicMakerHygiene(ilk_yieldBearing);
        // If we have enough want to convert and deposit more into the maker vault, we do it
        //Here minSingleTrade represents the minimum investment of want that makes it worth it to loop 
        if (balanceOfWant() > _debtOutstanding.add(minSingleTrade) ) {
            MakerDaiDelegateLib.wind(Math.min(maxSingleTrade, balanceOfWant().sub(_debtOutstanding)), collateralizationRatio, cdpId);
        } else {
            //Check if collateralizationRatio needs adjusting
            // Allow the ratio to move a bit in either direction to avoid cycles
            uint256 currentRatio = getCurrentMakerVaultRatio();
            if (currentRatio < collateralizationRatio.sub(lowerRebalanceTolerance)) { //if current ratio is BELOW goal ratio:
                uint256 currentCollateral = balanceOfMakerVault();
                uint256 yieldBearingToRepay = currentCollateral.sub( currentCollateral.mul(currentRatio).div(collateralizationRatio)  );
                uint256 wantAmountToRepay = yieldBearingToRepay.mul(getWantPerYieldBearing()).div(WAD);
                MakerDaiDelegateLib.unwind(Math.min(wantAmountToRepay, maxSingleTrade), collateralizationRatio, cdpId);
            } else if (currentRatio > collateralizationRatio.add(upperRebalanceTolerance)) { //if current ratio is ABOVE goal ratio:
                // Mint the maximum DAI possible for the locked collateral            
                _lockCollateralAndMintDai(0, _borrowTokenAmountToMint(balanceOfMakerVault()).sub(balanceOfDebt()));
                MakerDaiDelegateLib.wind(Math.min(maxSingleTrade, balanceOfWant().sub(_debtOutstanding)), collateralizationRatio, cdpId);
            }
        }
        //Check safety of collateralization ratio after all actions:
        if (balanceOfMakerVault() > 0) {
            require(getCurrentMakerVaultRatio() > collateralizationRatio.sub(lowerRebalanceTolerance), "unsafe collateralization");
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
        MakerDaiDelegateLib.unwind(_wantAmountNeeded.sub(wantBalance), collateralizationRatio, cdpId);

        //update free want after liquidating
        uint256 looseWant = balanceOfWant();
        //loss calculation and returning liquidated amount
        if (_wantAmountNeeded > looseWant) {
            _liquidatedAmount = looseWant;
            _loss = _wantAmountNeeded.sub(looseWant);
        } else {
            _liquidatedAmount = _wantAmountNeeded;
            _loss = 0;
        } 
        //Check safety of collateralization ratio after all actions:
        if (balanceOfMakerVault() > 0) {
            require(getCurrentMakerVaultRatio() > collateralizationRatio.sub(lowerRebalanceTolerance), "unsafe collateralization");
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
        if (balanceOfMakerVault() == 0) {
            return false;
        }

        uint256 currentRatio = getCurrentMakerVaultRatio();
        // If we need to repay debt and are outside the tolerance bands,
        // we do it regardless of the call cost
        if (currentRatio < collateralizationRatio.sub(lowerRebalanceTolerance)) {
            return true;
        }

        // Mint more DAI if possible
        return
            currentRatio > collateralizationRatio.add(upperRebalanceTolerance) &&
            balanceOfDebt() > 0 &&
            isBaseFeeAcceptable() &&
            MakerDaiDelegateLib.isDaiAvailableToMint(ilk_yieldBearing);
    }

    function prepareMigration(address _newStrategy) internal override {
        // Transfer Maker Vault ownership to the new startegy
        MakerDaiDelegateLib.transferCdp(cdpId, _newStrategy);
    }

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
    //Flashmint Callback:
    function onFlashLoan(
        address initiator,
        address,
        uint256 amount,
        uint256 fee,
        bytes calldata data
    ) external returns (bytes32) {
        require(msg.sender == flashmint);
        require(initiator == address(this));
        (Action action, uint256 _cdpId, uint256 _wantAmountInitialOrRequested, uint256 flashloanAmount, uint256 _collateralizationRatio) = abi.decode(data, (Action, uint256, uint256, uint256, uint256));
        _checkAllowance(address(flashmint), address(borrowToken), amount.add(fee));
        if (action == Action.WIND) {
            MakerDaiDelegateLib._wind(_cdpId, amount, _wantAmountInitialOrRequested, _collateralizationRatio);
        } else if (action == Action.UNWIND) {
            //amount = flashloanAmount, amount.add(fee) = flashloanAmount+fee for flashloan (usually 0)
            MakerDaiDelegateLib._unwind(_cdpId, amount, amount.add(fee), _wantAmountInitialOrRequested, _collateralizationRatio);
        }
        return keccak256("ERC3156FlashBorrower.onFlashLoan");
    }

    // ----------------- INTERNAL FUNCTIONS SUPPORT -----------------

    function _borrowTokenAmountToMint(uint256 _amount) internal returns (uint256) {
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
        //The returned tuple contains (DAI amount, USDC amount) - for want=dai:
        (uint256 wantUnderlyingBalance, uint256 otherTokenUnderlyingBalance) = yieldBearing.getUnderlyingBalances();
        return wantUnderlyingBalance.add(otherTokenUnderlyingBalance.mul(1e12)).mul(WAD).div(yieldBearing.totalSupply());
    }

    function balanceOfDebt() public view returns (uint256) {
        return MakerDaiDelegateLib.debtForCdp(cdpId, ilk_yieldBearing);
    }

    // Returns collateral balance in the vault
    function balanceOfMakerVault() public view returns (uint256) {
        return MakerDaiDelegateLib.balanceOfCdp(cdpId, ilk_yieldBearing);
    }

    function balanceOfDaiAvailableToMint() public view returns (uint256) {
        return MakerDaiDelegateLib.balanceOfDaiAvailableToMint(ilk_yieldBearing);
    }

    // Effective collateralization ratio of the vault
    function getCurrentMakerVaultRatio() public view returns (uint256) {
        return MakerDaiDelegateLib.getPessimisticRatioOfCdpWithExternalPrice(cdpId,ilk_yieldBearing,getWantPerYieldBearing(),WAD);
    }

    function getHypotheticalMakerVaultRatioWithMultiplier(uint256 _wantMultiplier, uint256 _otherTokenMultiplier) public view returns (uint256) {
        //The Multipliers are basispoints 100.01 = +0.01% increase of DAI price. Multipliers of 10000 are returning the CurrentMakerVaultRatio()
        //The returned tuple contains (DAI amount, USDC amount) - for want=dai:
        (uint256 wantUnderlyingBalance, uint256 otherTokenUnderlyingBalance) = yieldBearing.getUnderlyingBalances();
        uint256 hypotheticalWantPerYieldBearing = wantUnderlyingBalance.mul(_wantMultiplier).div(10000).add(otherTokenUnderlyingBalance.mul(_otherTokenMultiplier).div(10000).mul(1e12)).mul(WAD).div(yieldBearing.totalSupply());
        return balanceOfMakerVault().mul(hypotheticalWantPerYieldBearing).div(balanceOfDebt().mul(_wantMultiplier));
    }

    // check if the current baseFee is below our external target
    function isBaseFeeAcceptable() internal view returns (bool) {
        return IBaseFee(0xb5e1CAcB567d98faaDB60a1fD4820720141f064F).isCurrentBaseFeeAcceptable();
    }


    // ----------------- INTERNAL CALCS -----------------

    function _lockCollateralAndMintDai(
        uint256 collateralAmount,
        uint256 daiToMint
    ) internal {
        MakerDaiDelegateLib.lockGemAndDraw(
            gemJoinAdapter,
            cdpId,
            collateralAmount,
            daiToMint,
            balanceOfDebt()
        );
    }

}
