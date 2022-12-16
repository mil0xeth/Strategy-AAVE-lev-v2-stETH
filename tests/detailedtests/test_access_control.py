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

