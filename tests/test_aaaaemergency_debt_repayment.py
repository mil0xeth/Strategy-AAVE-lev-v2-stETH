import pytest
from brownie import chain, reverts, Wei, Contract


def test_repay_all_debt(
    vault, strategy, token, token_whale, user, gov, dai, dai_whale, RELATIVE_APPROX, yieldBearing, partnerToken, amount
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})

    decimals = token.decimals()
    # Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert strategy.balanceOfDebt() > 0
    assets_before = strategy.estimatedTotalAssets()

    aboveLiquidationRatio = 1020000001000000000
    for x in range(0,1000):
        if (strategy.balanceOfDebt() == 0):
            break
        strategy.emergencyDebtRepayment(strategy.balanceOfMakerVault()-(strategy.balanceOfMakerVault()/strategy.getCurrentMakerVaultRatio()*aboveLiquidationRatio), {"from": gov})

    assert pytest.approx(strategy.estimatedTotalAssets() == assets_before, rel=RELATIVE_APPROX)
    assert pytest.approx(strategy.estimatedTotalAssets() == strategy.balanceOfWant(), rel=RELATIVE_APPROX)
