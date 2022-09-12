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
    token, dai, vault, strategy, token_whale, gov, borrow_token, borrow_whale, partnerToken, Contract
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

    #Create profits for UNIV3 DAI<->USDC
    uniswapv3 = Contract("0xE592427A0AEce92De3Edee1F18E0157C05861564")
    #token --> partnerToken
    uniswapAmount = token.balanceOf(token_whale)*0.1
    token.approve(uniswapv3, uniswapAmount, {"from": token_whale})
    uniswapv3.exactInputSingle((token, partnerToken, 100, token_whale, 1856589943, uniswapAmount, 0, 0), {"from": token_whale})
    chain.sleep(1)

    vault.revokeStrategy(strategy, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})

    assert vault.strategies(strategy).dict()["totalGain"] > 0
    assert vault.strategies(strategy).dict()["debtRatio"] == 0
    assert vault.strategies(strategy).dict()["totalDebt"] == 0
