import pytest
from brownie import chain, reverts, Wei

def test_tend_trigger_conditions(
    vault, strategy, token, token_whale, amount, user, gov, chain, basefeeChecker, RELATIVE_APPROX
):
    # Initial ratio is 0 because there is no collateral locked
    assert strategy.tendTrigger(1) == False
    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    chain.sleep(1)
    strategy.harvest({"from": gov})

    #orig_target = strategy.collateralizationRatio()
    assert ( pytest.approx(strategy.getCurrentMakerVaultRatio(), rel=RELATIVE_APPROX) == strategy.collateralizationRatio())
    orig_target = strategy.getCurrentMakerVaultRatio()
    rebalance_tolerance = strategy.lowerRebalanceTolerance()

    # Make sure we are in equilibrium
    assert strategy.tendTrigger(1) == False

    # Going under the rebalancing band should need to adjust position
    # regardless of the max acceptable base fee
    strategy.setCollateralizationRatio(orig_target + rebalance_tolerance * 1.001, {"from": gov})

    #### Basefee:
    basefeeChecker.setMaxAcceptableBaseFee(0, {"from": strategy.strategist()})
    assert strategy.tendTrigger(1) == True

    basefeeChecker.setMaxAcceptableBaseFee(1001 * 1e9, {"from": strategy.strategist()})
    assert strategy.tendTrigger(1) == True

    # Going over the target ratio but inside rebalancing band should not adjust position
    strategy.setCollateralizationRatio(orig_target + rebalance_tolerance * 0.999, {"from": gov})
    assert strategy.tendTrigger(1) == False

    # Going over the rebalancing band should need to adjust position
    # but only if block's base fee is deemed to be acceptable
    strategy.setCollateralizationRatio(orig_target + rebalance_tolerance * 1.001, {"from": gov})

    basefeeChecker.setMaxAcceptableBaseFee(1001 * 1e9, {"from": strategy.strategist()})
    assert strategy.tendTrigger(1) == True

    # Going over the target ratio but inside rebalancing band should not adjust position
    strategy.setCollateralizationRatio(orig_target + rebalance_tolerance * 0.999, {"from": gov})
    basefeeChecker.setMaxAcceptableBaseFee(1001 * 1e9, {"from": strategy.strategist()})
    assert strategy.tendTrigger(1) == False
