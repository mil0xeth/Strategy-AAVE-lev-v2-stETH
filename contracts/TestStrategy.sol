// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "./Strategy.sol";
//import "../interfaces/yearn/IOSMedianizer.sol";

// The purpose of this wrapper contract is to expose internal functions
// that may contain application logic and therefore need to be unit tested.
contract TestStrategy is Strategy {
    constructor(
        address _vault,
        string memory _strategyName
//        bytes32 _ilk_want,
//        bytes32 _ilk_yieldBearing,
//        address _gemJoin
//        address _wantToUSDOSMProxy
//        address _yieldBearingToUSDOSMProxy
//        address _chainlinkWantToETHPriceFeed
    )
        public
        Strategy(
            _vault,
            _strategyName
//            _ilk_want,
//            _ilk_yieldBearing,
//            _gemJoin
//            _wantToUSDOSMProxy
//            _yieldBearingToUSDOSMProxy
//            _chainlinkWantToETHPriceFeed
        )
    {}

    function _liquidatePosition(uint256 _amountNeeded)
        public
        returns (uint256 _liquidatedAmount, uint256 _loss)
    {
        (_liquidatedAmount, _loss) = liquidatePosition(_amountNeeded);
    }

    function _getWantPrice() public view returns (uint256) {
        return getWantPerYieldBearing();
    }

    function _getYieldBearingPrice() public view returns (uint256) {
        return getWantPerYieldBearing();
    }

    function freeCollateral(uint256 collateralAmount, uint256 daiAmount) public {
        _checkAllowance(
            MakerDaiDelegateLib.daiJoinAddress(),
            address(borrowToken),
            daiAmount
        );
        return MakerDaiDelegateLib.wipeAndFreeGem(gemJoinAdapter, cdpId, collateralAmount, daiAmount);
    }
/*
    function repayDebt(uint256 _amount) public {
        return _repayDebt(_amount);
    }

    function setCustomWantOSM(IOSMedianizer _wantToUSDOSMProxy) public {
        wantToUSDOSMProxy = _wantToUSDOSMProxy;
    }

    //Test Function
    function setCustomOSM(IOSMedianizer _yieldBearingToUSDOSMProxy) public {
        yieldBearingToUSDOSMProxy = address(_yieldBearingToUSDOSMProxy);
    }
*/

}
