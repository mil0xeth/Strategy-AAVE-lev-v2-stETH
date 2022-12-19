# TODO: Add tests that show proper operation of this strategy through "emergencyExit"
#       Make sure to demonstrate the "worst case losses" as well as the time it takes

from brownie import ZERO_ADDRESS
import pytest


def test_vault_shutdown_can_withdraw(
    gov, token_whale, chain, token, vault, strategy, user, amount, RELATIVE_APPROX
):
    ## Deposit in Vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount

    if token.balanceOf(user) > 0:
        #token.transfer(ZERO_ADDRESS, token.balanceOf(user), {"from": user})
        token.transfer(token_whale, token.balanceOf(user), {"from": user})

    # Harvest 1: Send funds through the 
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(3600 * 7)
    chain.mine(1)
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    ## Set Emergency
    vault.setEmergencyShutdown(True)

    ## Withdraw (does it work, do you get what you expect)
    vault.withdraw(vault.balanceOf(user), user, 1000,{"from": user})

    assert pytest.approx(token.balanceOf(user), rel=RELATIVE_APPROX) == amount


def test_basic_shutdown(
    gov,chain, token, vault, strategy, user, strategist, amount, RELATIVE_APPROX
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount

    # Harvest 1: Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.mine(100)
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    ## Earn interest
    #chain.sleep(3600 * 24 * 1)  ## Sleep 1 day
    chain.mine(1)

    # Harvest 2: Realize profit
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(3600 * 6)  # 6 hrs needed for profits to unlock
    chain.mine(1)

    ## Set emergency
    strategy.setEmergencyExit({"from": strategist})

    strategy.harvest({"from": gov})  ## Remove funds from strategy

    assert token.balanceOf(strategy) == 0
    assert pytest.approx(token.balanceOf(vault), rel=RELATIVE_APPROX) == amount  ## The vault has all funds
    ## NOTE: May want to tweak this based on potential loss during migration
