import pytest

from brownie import chain


def test_revoke_strategy_from_vault(
    chain, token, vault, strategy, amount, user, gov, RELATIVE_APPROX_LOSSY
):
    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_LOSSY) == amount

    vault.revokeStrategy(strategy.address, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert vault.strategies(strategy).dict()["debtRatio"] == 0
    assert vault.strategies(strategy).dict()["totalDebt"] == 0
    assert pytest.approx(token.balanceOf(vault.address), rel=RELATIVE_APPROX_LOSSY) == amount


def test_revoke_strategy_from_strategy(
    chain, token, vault, strategy, amount, user, gov, RELATIVE_APPROX_LOSSY
):
    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_LOSSY) == amount

    strategy.setEmergencyExit({"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert vault.strategies(strategy).dict()["debtRatio"] == 0
    assert vault.strategies(strategy).dict()["totalDebt"] == 0
    assert pytest.approx(token.balanceOf(vault.address), rel=RELATIVE_APPROX_LOSSY) == amount


def test_revoke_with_profit(
    token, dai, vault, strategy, token_whale, gov, borrow_token, borrow_whale, Contract, steth_whale, steth
):
    token.approve(vault, 2 ** 256 - 1, {"from": token_whale})
    toadd = 2000 * (10 ** token.decimals())
    vault.deposit(toadd, {"from": token_whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})

    vault.setPerformanceFee(0, {"from":gov})

    assert vault.strategies(strategy).dict()["totalGain"] == 0
    assert vault.strategies(strategy).dict()["debtRatio"] == 10_000
    assert vault.strategies(strategy).dict()["totalDebt"] == toadd

    #Create profits
    days = 14
    #send some steth to simulate profit. 10% apr
    rewards_amount = toadd/10/365*days
    steth.transfer(strategy, rewards_amount*2, {'from': steth_whale})

    chain.sleep(1)

    vault.revokeStrategy(strategy, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})

    assert vault.strategies(strategy).dict()["totalGain"] > 0
    assert vault.strategies(strategy).dict()["debtRatio"] == 0
    assert vault.strategies(strategy).dict()["totalDebt"] == 0
