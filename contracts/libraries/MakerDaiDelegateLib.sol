// SPDX-License-Identifier: agpl-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/math/Math.sol";

import {
    SafeERC20,
    SafeMath,
    IERC20,
    Address
} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

import "../../interfaces/aave/ILendingPool.sol";
import "../../interfaces/aave/IProtocolDataProvider.sol";
import "../../interfaces/aave/IPriceOracle.sol";

import "../../interfaces/chainlink/AggregatorInterface.sol";

import "../../interfaces/UniswapInterfaces/IWETH.sol";

import "../../interfaces/lido/ISteth.sol";
import "../../interfaces/curve/Curve.sol";

interface IBalancer {
    function flashLoan(
        address recipient,
        address[] memory tokens,
        uint256[] memory amounts,
        bytes memory userData
    ) external;
}

library MakerDaiDelegateLib {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;
    enum Action {WIND, UNWIND}

    //Strategy specific addresses:
    //IERC20 internal constant want = IERC20(0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2); //weth
    IWETH internal constant want = IWETH(0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2);

    //stETH is yieldBearing:
    ISteth internal constant yieldBearing =  ISteth(0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84);
    //WETH is borrowToken:
    IERC20 internal constant borrowToken = IERC20(0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2);
    
    //Curve:
    ICurveFi internal constant curve = ICurveFi(0xDC24316b9AE028F1497c275EB9192a3Ea0f67022);

    //Chainlink Oracle:
    AggregatorInterface internal constant chainlinkYieldBearingToETHPriceFeed = AggregatorInterface(0x86392dC19c0b719886221c78AB11eb8Cf5c52812);

    //AAVEV2 lending pool:
    ILendingPool private constant lendingPool = ILendingPool(0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9);
    IProtocolDataProvider private constant protocolDataProvider = IProtocolDataProvider(0x057835Ad21a177dbdd3090bB1CAE03EaCF78Fc6d);
    
    IPriceOracle private constant priceOracle = IPriceOracle(0xA50ba011c48153De246E5192C8f9258A2ba79Ca9);
    uint16 private constant aaveReferral = 7; // Yearn's aave referral code
    address private constant lidoReferral = 0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7; //stratms. for recycling and redepositing

    //Balancer Flashloan:
    IBalancer constant balancer = IBalancer(0xBA12222222228d8Ba445958a75a0704d566BF2C8);

    // Decimal Units 
    uint256 internal constant WAD = 10**18;
    uint256 internal constant RAY = 10**27;
    uint256 internal constant LTV_BPS_TO_CZR = 10**22;

    uint256 public constant DENOMINATOR = 10_000;

    // Do not attempt to mint DAI if there are less than MIN_MINTABLE available. Used to be 500kDAI --> reduced to 50kDAI
    uint256 internal constant MIN_MINTABLE = 50000 * WAD;

    // ----------------- PUBLIC FUNCTIONS -----------------

    // Liquidation ratio for the given ilk returned in [ray]
    function getLiquidationRatio() public view returns (uint256) {
        (, , uint256 liquidationRatio, , , , , , , ) = protocolDataProvider.getReserveConfigurationData(address(yieldBearing));
        // convert ltv value in bps to collateralization ratio in wad
        return LTV_BPS_TO_CZR.div(liquidationRatio);
    }

    function wind(
        uint256 wantAmountInitial,
        uint256 targetCollateralizationRatio,
        address debtToken
    ) public {
        wantAmountInitial = Math.min(wantAmountInitial, balanceOfWant());
        //Calculate how much borrowToken to mint to leverage up to targetCollateralizationRatio:
        uint256 flashloanAmount = wantAmountInitial.mul(RAY).div(targetCollateralizationRatio.mul(1e9).sub(RAY));
        //Retrieve upper max limit of flashloan:
        //uint256 flashloanMaximum = flashmint.maxFlashLoan(address(borrowToken));
        //Cap flashloan only up to maximum allowed:
        //flashloanAmount = Math.min(flashloanAmount, flashloanMaximum);
        uint256 currentDebt = _debtForCdp(debtToken);
        bytes memory data = abi.encode(Action.WIND, wantAmountInitial, flashloanAmount, targetCollateralizationRatio); 
        _initFlashLoan(data, flashloanAmount);
    }
    
    function unwind(
        uint256 wantAmountRequested,
        uint256 targetCollateralizationRatio,
        address aToken,
        address debtToken
    ) public {
        if (_balanceOfCdp(aToken) == 0){
            return;
        }
        //Retrieve for upper max limit of flashloan:
        //uint256 flashloanMaximum = flashmint.maxFlashLoan(address(borrowToken));
        //flashloan only up to maximum allowed:
        //uint256 flashloanAmount = Math.min(_debtForCdp(debtToken), flashloanMaximum);
        uint256 flashloanAmount = _debtForCdp(debtToken);
        bytes memory data = abi.encode(Action.UNWIND, wantAmountRequested, flashloanAmount, targetCollateralizationRatio);
        //Always flashloan entire debt to pay off entire debt:
        _initFlashLoan(data, flashloanAmount);
    }

    function _wind(uint256 flashloanRepayAmount, uint256 wantAmountInitial, uint256) external {
        //repayAmount includes any fees
        uint256 yieldBearingAmountToLock = _swapWantToYieldBearing(balanceOfWant());
        //Lock collateral and borrow borrowToken to repay flashloan
        _depositCollateral(yieldBearingAmountToLock);
        _borrowBorrowToken(flashloanRepayAmount);
        
        //repay flashloan:
        borrowToken.transfer(address(balancer), flashloanRepayAmount);
    }

    function _unwind(uint256 flashloanAmount, uint256 flashloanRepayAmount, uint256 wantAmountRequested, uint256 targetCollateralizationRatio, address aToken, address debtToken) external {
        //Calculate leverage+1 to know how much totalRequestedInYieldBearing to swap for borrowToken
        uint256 leveragePlusOne = (RAY.mul(WAD).div((targetCollateralizationRatio.mul(1e9).sub(RAY)))).add(WAD);
        uint256 totalRequestedInYieldBearing = wantAmountRequested.mul(leveragePlusOne).div(getWantPerYieldBearing());
        uint256 collateralBalance = _balanceOfCdp(aToken);
        //Maximum of all collateral can be requested
        totalRequestedInYieldBearing = Math.min(totalRequestedInYieldBearing, collateralBalance);
        //Check allowance for repaying borrowToken Debt
        _repayBorrowToken(flashloanAmount);
        _withdrawCollateral(totalRequestedInYieldBearing);
        //Desired collateral amount unlocked --> swap to want
        _swapYieldBearingToWant(totalRequestedInYieldBearing);
        //----> Want amount requested now in wallet

        //Now mint dai to repay flashloan: Rest of collateral is already locked, borrow dai equivalent to amount given by targetCollateralizationRatio:
        collateralBalance = _balanceOfCdp(aToken);
        //In case not all debt was paid down, the remainingDebt is not 0
        uint256 remainingDebt = _debtForCdp(debtToken); //necessarily less in value than collateralBalance due to overcollateralization of cdp
        //Calculate how much more borrowToken to borrow to attain desired targetCollateralizationRatio:
        uint256 borrowTokenAmountToBorrow = collateralBalance.mul(getWantPerYieldBearing()).div(targetCollateralizationRatio).sub(remainingDebt);

        //Make sure to always mint enough to repay the flashloan
        uint256 wantBalance = balanceOfWant();
        if (flashloanRepayAmount > wantBalance){
            borrowTokenAmountToBorrow = Math.max(borrowTokenAmountToBorrow, flashloanRepayAmount.sub(wantBalance));
        }        
        //borrow borrowToken to repay flashloan
        _borrowBorrowToken(borrowTokenAmountToBorrow);

        //repay flashloan:
        borrowToken.transfer(address(balancer), flashloanRepayAmount);
    }

    //get amount of Want in Wei that is received for 1 yieldBearing
    function getWantPerYieldBearing() internal view returns (uint256){
        return uint256(chainlinkYieldBearingToETHPriceFeed.latestAnswer());
    }

    function balanceOfWant() internal view returns (uint256) {
        return want.balanceOf(address(this));
    }

    function balanceOfYieldBearing() internal view returns (uint256) {
        return yieldBearing.balanceOf(address(this));
    }

    // ----------------- INTERNAL FUNCTIONS -----------------

    function _initFlashLoan(bytes memory data, uint256 amount)
        public
    {
        address[] memory tokens = new address[](1);
        tokens[0] = address(borrowToken);
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = amount;
        //address[] memory tokens; 
        //tokens[0] = address(borrowToken);
        //uint256[] memory amounts; 
        //amounts[0] = amount; 
        balancer.flashLoan(address(this), tokens, amounts, data);
    }

    function _checkAllowance(
        address _contract,
        address _token,
        uint256 _amount
    ) internal {
        if (IERC20(_token).allowance(address(this), _contract) < _amount) {
            //IERC20(_token).safeApprove(_contract, 0);
            IERC20(_token).safeApprove(_contract, type(uint256).max);
        }
    }

    function _swapWantToYieldBearing(uint256 _amount) internal returns (uint256) {
        if (_amount == 0) {
            return 0;
        }
        _amount = Math.min(_amount, balanceOfWant());
        //---WETH (ethwrapping withdraw) --> ETH --- Unwrap WETH to ETH (to be used in Curve or Lido)
        want.withdraw(_amount);  
        _amount = address(this).balance;        
        //---ETH test if mint on Lido or buy on Curve --> STETH --- 
        if (curve.get_dy(0, 1, _amount) <= _amount){
            //Lido mint: 
            yieldBearing.submit{value: _amount}(lidoReferral);
        }else{ 
            //approve Curve ETH/stETH StableSwap & exchange eth to steth
            _checkAllowance(address(curve), address(yieldBearing), _amount);       
            curve.exchange{value: _amount}(0, 1, _amount, _amount); //at minimum get 1:1 for weth
        }
        return balanceOfYieldBearing();
    }

    function _swapYieldBearingToWant(uint256 _amount) internal {
    //function _swapYieldBearingToWant(uint256 _amount, uint256 _slippageProtection) internal {
        if (_amount == 0) {
            return;
        }
        _amount = Math.min(_amount, balanceOfYieldBearing());
        //---STEHT --> ETH
        uint256 slippageAllowance = _amount.mul(DENOMINATOR.sub(200)).div(DENOMINATOR);
        _checkAllowance(address(curve), address(yieldBearing), _amount);
        curve.exchange(1, 0, _amount, slippageAllowance);
        //Re-Wrap it back up: ETH to WETH
        want.deposit{value: address(this).balance}();
    }

    function swapYieldBearingToWant(uint256 _amount) external {
        _swapYieldBearingToWant(_amount);
    }

///////////////////////////////////////////
//////////////////////////// A   A   V   E
///////////////////////////////////////////

    function _balanceOfCdp(address _aToken) internal view returns (uint256) {
        return IERC20(_aToken).balanceOf(address(this));
    }

    function _debtForCdp(address _debtToken) internal view returns (uint256) {
        return IERC20(_debtToken).balanceOf(address(this));
    }

    function _depositCollateral(uint256 _amount) internal {
        if (_amount == 0) return;
        _checkAllowance(address(lendingPool), address(yieldBearing), _amount);
        lendingPool.deposit(address(yieldBearing), _amount, address(this), aaveReferral);
    }

    function _withdrawCollateral(uint256 _amount) internal {
        if (_amount == 0) return;
        lendingPool.withdraw(address(yieldBearing), _amount, address(this));
    }

    function _repayBorrowToken(uint256 amount) internal returns (uint256) {
        if (amount == 0) return 0;
        _checkAllowance(address(lendingPool), address(borrowToken), amount);
        return lendingPool.repay(address(borrowToken), amount, 2, address(this));
    }

    function _borrowBorrowToken(uint256 amount) internal returns (uint256) {
        if (amount == 0) return 0;
        lendingPool.borrow(address(borrowToken), amount, 2, aaveReferral, address(this));
        return amount;
    }

    function depositCollateral(uint256 _amount) external {
        _depositCollateral(_amount);
    }

    function withdrawCollateral(uint256 _amount) external {
        _withdrawCollateral(_amount);
    }

    function borrowBorrowToken(uint256 _amount) external {
        _borrowBorrowToken(_amount);
    }

    function repayBorrowToken(uint256 _amount) external {
        _repayBorrowToken(_amount);
    }

}
