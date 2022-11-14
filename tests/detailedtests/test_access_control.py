from brownie import chain, reverts, Contract


def test_set_collateralization_ratio_acl(
    strategy, gov, strategist, management, guardian, user
):
    strategy.setCollateralizationRatio(200 * 1e18, {"from": gov})
    assert strategy.collateralizationRatio() == 200 * 1e18

    with reverts("!authorized"):
        strategy.setCollateralizationRatio(201 * 1e18, {"from": strategist})
        assert strategy.collateralizationRatio() == 201 * 1e18

    strategy.setCollateralizationRatio(202 * 1e18, {"from": management})
    assert strategy.collateralizationRatio() == 202 * 1e18

    with reverts("!authorized"):
        strategy.setCollateralizationRatio(203 * 1e18, {"from": guardian})

    with reverts("!authorized"):
        strategy.setCollateralizationRatio(200 * 1e18, {"from": user})


def test_set_rebalance_tolerance_acl(
    strategy, gov, strategist, management, guardian, user
):
    strategy.setRebalanceTolerance(5, 5, {"from": gov})
    assert strategy.lowerRebalanceTolerance() == 5
    assert strategy.upperRebalanceTolerance() == 5

    with reverts("!authorized"):
        strategy.setRebalanceTolerance(4, 5, {"from": strategist})
    
    strategy.setRebalanceTolerance(3, 4, {"from": management})
    assert strategy.lowerRebalanceTolerance() == 3
    assert strategy.upperRebalanceTolerance() == 4

    with reverts("!authorized"):
        strategy.setRebalanceTolerance(2, 3, {"from": guardian})
    
    with reverts("!authorized"):
        strategy.setRebalanceTolerance(5, 4, {"from": user})




def test_shift_cdp_acl(strategy, gov, strategist, management, guardian, user):
    # cdp-not-allowed should be the revert msg when allowed / we are shifting to a random cdp
    with reverts("cdp-not-allowed"):
        strategy.shiftToCdp(123, {"from": gov})

    with reverts("!authorized"):
        strategy.shiftToCdp(123, {"from": strategist})

    with reverts("!authorized"):
        strategy.shiftToCdp(123, {"from": management})

    with reverts("!authorized"):
        strategy.shiftToCdp(123, {"from": guardian})

    with reverts("!authorized"):
        strategy.shiftToCdp(123, {"from": user})


def test_allow_managing_cdp_acl(strategy, gov, strategist, management, guardian, user):
    cdpManager = Contract("0x5ef30b9986345249bc32d8928B7ee64DE9435E39")
    cdp = strategy.cdpId()

    with reverts("!authorized"):
        strategy.grantCdpManagingRightsToUser(user, True, {"from": strategist})

    with reverts("!authorized"):
        strategy.grantCdpManagingRightsToUser(user, True, {"from": management})

    with reverts("!authorized"):
        strategy.grantCdpManagingRightsToUser(user, True, {"from": guardian})

    with reverts("!authorized"):
        strategy.grantCdpManagingRightsToUser(user, True, {"from": user})

    strategy.grantCdpManagingRightsToUser(user, True, {"from": gov})
    cdpManager.cdpAllow(cdp, guardian, 1, {"from": user})

    strategy.grantCdpManagingRightsToUser(user, False, {"from": gov})

    with reverts("cdp-not-allowed"):
        cdpManager.cdpAllow(cdp, guardian, 1, {"from": user})



def test_emergency_debt_repayment_acl(
    strategy, gov, strategist, management, guardian, user
):
    strategy.emergencyDebtRepayment(strategy.estimatedTotalAssets(), {"from": gov})
    assert strategy.balanceOfDebt() == 0

    strategy.emergencyDebtRepayment(strategy.estimatedTotalAssets(), {"from": management})
    assert strategy.balanceOfDebt() == 0

    with reverts("!authorized"):
        strategy.emergencyDebtRepayment(strategy.estimatedTotalAssets(), {"from": strategist})

    with reverts("!authorized"):
        strategy.emergencyDebtRepayment(strategy.estimatedTotalAssets(), {"from": guardian})

    with reverts("!authorized"):
        strategy.emergencyDebtRepayment(strategy.estimatedTotalAssets(), {"from": user})


def DISABLED_repay_debt_acl(
    vault,
    strategy,
    token,
    amount,
    dai,
    dai_whale,
    gov,
    strategist,
    management,
    guardian,
    keeper,
    user,
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": gov})

    dai.transfer(strategy, 1000 * 1e18, {"from": dai_whale})
    debt_balance = strategy.balanceOfDebt()

    strategy.repayDebtWithDaiBalance(1, {"from": gov})
    assert strategy.balanceOfDebt() == (debt_balance - 1)

    strategy.repayDebtWithDaiBalance(2, {"from": management})
    assert strategy.balanceOfDebt() == (debt_balance - 3)

    with reverts("!authorized"):
        strategy.repayDebtWithDaiBalance(3, {"from": strategist})

    with reverts("!authorized"):
        strategy.repayDebtWithDaiBalance(4, {"from": guardian})

    with reverts("!authorized"):
        strategy.repayDebtWithDaiBalance(5, {"from": keeper})

    with reverts("!authorized"):
        strategy.repayDebtWithDaiBalance(6, {"from": user})
