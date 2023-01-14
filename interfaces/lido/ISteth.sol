// SPDX-License-Identifier: MIT

pragma solidity 0.6.12;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface ISteth is IERC20 {
    //function getPooledEthByShares(uint256 _sharesAmount) external view returns (uint256);
    //function getSharesByPooledEth(uint256 _pooledEthAmount) external view returns (uint256);
    event Submitted(address sender, uint256 amount, address referral);
    function submit(address) external payable returns (uint256);
    function isStakingPaused() external returns (bool);
}
