// SPDX-License-Identifier: agpl-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/math/Math.sol";

import "../../interfaces/maker/IMaker.sol";
import "../../interfaces/GUNI/GUniPool.sol";

import {
    SafeERC20,
    SafeMath,
    IERC20,
    Address
} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

import "../../interfaces/aave/ILendingPool.sol";
import "../../interfaces/aave/IProtocolDataProvider.sol";
import "../../interfaces/aave/IPriceOracle.sol";

//OSM
import "../../interfaces/yearn/IOSMedianizer.sol";

interface PSMLike {
    function gemJoin() external view returns (address);
    function sellGem(address usr, uint256 gemAmt) external;
    function buyGem(address usr, uint256 gemAmt) external;
}

interface IERC3156FlashLender {
    function maxFlashLoan(
        address token
    ) external view returns (uint256);
    function flashFee(
        address token,
        uint256 amount
    ) external view returns (uint256);
    function flashLoan(
        //IERC3156FlashBorrower receiver,
        address receiver,
        address token,
        uint256 amount,
        bytes calldata data
    ) external returns (bool);
}

interface IERC3156FlashBorrower {
    function onFlashLoan(
        address initiator,
        address token,
        uint256 amount,
        uint256 fee,
        bytes calldata data
    ) external returns (bytes32);
}

library MakerDaiDelegateLib {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;
    enum Action {WIND, UNWIND}

    //Strategy specific addresses:
    IERC20 internal constant want = IERC20(0x6B175474E89094C44Da98b954EedeAC495271d0F); //dai
    IERC20 internal constant otherToken = IERC20(0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48); //usdc
    uint256 public constant otherTokenTo18Conversion = 10 ** 12;
    
    //GUNIDAIUSDC2 - Gelato Uniswap DAI/USDC2 LP 2 - 0.01% fee
    GUniPool internal constant yieldBearing = GUniPool(0x50379f632ca68D36E50cfBC8F78fe16bd1499d1e);
    //DAI borrowToken:
    IERC20 internal constant borrowToken = IERC20(0x6B175474E89094C44Da98b954EedeAC495271d0F);

    //AAVEV2 lending pool:
    //ILendingPool private constant lendingPool = ILendingPool(0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9);
    //IProtocolDataProvider private constant protocolDataProvider = IProtocolDataProvider(0x057835Ad21a177dbdd3090bB1CAE03EaCF78Fc6d);
    //AAVEV2 AMM lending pool:
    ILendingPool private constant lendingPool = ILendingPool(0x7937D4799803FbBe595ed57278Bc4cA21f3bFfCB);
    IProtocolDataProvider private constant protocolDataProvider = IProtocolDataProvider(0xc443AD9DDE3cecfB9dfC5736578f447aFE3590ba);

    IPriceOracle private constant priceOracle = IPriceOracle(0xA50ba011c48153De246E5192C8f9258A2ba79Ca9);
    uint16 private constant referral = 7; // Yearn's aave referral code

    //MAKER Flashmint:
    IERC3156FlashLender public constant flashmint = IERC3156FlashLender(0x1EB4CF3A948E7D72A198fe073cCb8C7a948cD853);
    //MAKER PSM:
    PSMLike public constant psm = PSMLike(0x89B78CfA322F6C5dE0aBcEecab66Aee45393cC5A) ;

    // Decimal Units 
    uint256 internal constant WAD = 10**18;
    uint256 internal constant RAY = 10**27;
    uint256 internal constant LTV_BPS_TO_CZR = 10**22;

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
        uint256 flashloanMaximum = flashmint.maxFlashLoan(address(borrowToken));
        //Cap flashloan only up to maximum allowed:
        flashloanAmount = Math.min(flashloanAmount, flashloanMaximum);
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
        uint256 flashloanMaximum = flashmint.maxFlashLoan(address(borrowToken));
        //Paying off the full debt it's common to experience Vat/dust reverts: we circumvent this with add 1 Wei to the amount to be paid
        //flashloan only up to maximum allowed:
        uint256 flashloanAmount = Math.min(_debtForCdp(debtToken), flashloanMaximum);
        bytes memory data = abi.encode(Action.UNWIND, wantAmountRequested, flashloanAmount, targetCollateralizationRatio);
        //Always flashloan entire debt to pay off entire debt:
        _initFlashLoan(data, flashloanAmount);
    }

    function _wind(uint256 flashloanRepayAmount, uint256 wantAmountInitial, uint256) external {
        //repayAmount includes any fees
        uint256 yieldBearingAmountToLock = _swapWantToYieldBearing(balanceOfWant());
        //Lock collateral and borrow dai to repay flashmint
        _depositCollateral(yieldBearingAmountToLock);
        _borrowBorrowToken(flashloanRepayAmount);
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
        //mint dai to repay flashmint
        _borrowBorrowToken(borrowTokenAmountToBorrow);
    }

    //get amount of Want in Wei that is received for 1 yieldBearing
    function getWantPerYieldBearing() internal view returns (uint256){
        (uint256 wantUnderlyingBalance, uint256 otherTokenUnderlyingBalance) = yieldBearing.getUnderlyingBalances();
        return (wantUnderlyingBalance.mul(WAD).add(otherTokenUnderlyingBalance.mul(WAD).mul(WAD).div(1e6))).div(yieldBearing.totalSupply());
    }

    function balanceOfWant() internal view returns (uint256) {
        return want.balanceOf(address(this));
    }

    function balanceOfYieldBearing() internal view returns (uint256) {
        return yieldBearing.balanceOf(address(this));
    }

    function balanceOfOtherToken() internal view returns (uint256) {
        return otherToken.balanceOf(address(this));
    }

    // ----------------- INTERNAL FUNCTIONS -----------------

    function _initFlashLoan(bytes memory data, uint256 amount) internal {
        //Flashmint implementation:
        _checkAllowance(address(flashmint), address(borrowToken), amount);
        flashmint.flashLoan(address(this), address(borrowToken), amount, data);
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
        (uint256 wantRatio, uint256 otherTokenRatio) = yieldBearing.getUnderlyingBalances();
        wantRatio = wantRatio.mul(WAD).div(yieldBearing.totalSupply());
        otherTokenRatio = otherTokenRatio.mul(WAD).mul(otherTokenTo18Conversion).div(yieldBearing.totalSupply());
        uint256 wantAmountForMint = _amount.mul(wantRatio).div(wantRatio + otherTokenRatio);
        uint256 wantAmountToSwapToOtherTokenForMint = _amount.mul(otherTokenRatio).div(wantRatio + otherTokenRatio);
        //Swap through PSM wantAmountToSwapToOtherTokenForMint --> otherToken
        _checkAllowance(address(psm), address(want), wantAmountToSwapToOtherTokenForMint);
        psm.buyGem(address(this), wantAmountToSwapToOtherTokenForMint.div(otherTokenTo18Conversion));
        
        //Mint yieldBearing:
        wantAmountForMint = Math.min(wantAmountForMint, balanceOfWant());
        uint256 otherTokenBalance = balanceOfOtherToken();
        _checkAllowance(address(yieldBearing), address(want), wantAmountForMint);
        _checkAllowance(address(yieldBearing), address(otherToken), otherTokenBalance);      
        (,,uint256 mintAmount) = yieldBearing.getMintAmounts(wantAmountForMint, otherTokenBalance); 
        yieldBearing.mint(mintAmount, address(this));
        return balanceOfYieldBearing();
    }

    function _swapYieldBearingToWant(uint256 _amount) internal {
        if (_amount == 0) {
            return;
        }
        //Burn the yieldBearing token to unlock DAI and USDC:
        yieldBearing.burn(Math.min(_amount, balanceOfYieldBearing()), address(this));
        
        //Amount of otherToken after burning:
        uint256 otherTokenBalance = balanceOfOtherToken();

        //Swap through PSM otherToken ---> Want:
        address psmGemJoin = psm.gemJoin();
        _checkAllowance(psmGemJoin, address(otherToken), otherTokenBalance);
        psm.sellGem(address(this), otherTokenBalance);
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
        lendingPool.deposit(address(yieldBearing), _amount, address(this), referral);
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
        lendingPool.borrow(address(borrowToken), amount, 2, referral, address(this));
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
