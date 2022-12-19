import pytest, time

from brownie import reverts, chain, Contract, Wei, history, ZERO_ADDRESS
from eth_abi import encode_single


def test_prod(yieldBearing, token, weth, gov, token_whale, Strategy, strategy, productionVault, vault, amount, RELATIVE_APPROX, RELATIVE_APPROX_LOSSY):
    # Deposit to the vault
    user_balance_before = token.balanceOf(token_whale)
    token.approve(vault.address, amount, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})
    assert token.balanceOf(vault.address) == amount

    # harvest
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_LOSSY) == amount
    
    # withdrawal
    vault.withdraw(vault.balanceOf(token_whale), token_whale, 1000, {"from": token_whale})
    assert ( pytest.approx(token.balanceOf(token_whale), rel=RELATIVE_APPROX_LOSSY) == user_balance_before )

def test_profitable_harvest(strategy,vault, steth, token, token_whale, gov, steth_whale, weth):

    token.approve(vault, 2 ** 256 - 1, {"from": token_whale} )
    whalebefore = token.balanceOf(token_whale)
    whale_deposit  = 100 *1e18
    vault.deposit(whale_deposit, {"from": token_whale})
    strategy.setDoHealthCheck(False, {"from": gov})
    strategy.harvest({'from': gov})
    assert weth.balanceOf(strategy) == 0

    days = 14
    chain.sleep(days*24*60*60)
    chain.mine(1)

    #send some steth to simulate profit. 10% apr
    rewards_amount = whale_deposit/10/365*days
    steth.transfer(strategy, rewards_amount, {'from': steth_whale})

    strategy.harvest({'from': gov})

    assert strategy.balance() == 0

    vault.updateStrategyDebtRatio(strategy, 0, {'from': gov})

    strategy.harvest({'from': gov})

    assert strategy.balance() == 0
    
    vault.withdraw(vault.balanceOf(token_whale), token_whale, 1000, {"from": token_whale})
    whale_profit = (token.balanceOf(token_whale) - whalebefore)/1e18
    print("Whale profit: ", whale_profit)
    assert whale_profit > 0
