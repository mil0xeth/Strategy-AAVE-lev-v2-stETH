import pytest

from brownie import reverts


def test_operation(chain, token, vault, strategy, user, amount, gov, RELATIVE_APPROX_LOSSY, token_whale):
    # Deposit to the vault
    user_balance_before = token.balanceOf(user)
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount

    # harvest
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_LOSSY) == amount

    # tend()
    # strategy.tend({"from": gov})

    # withdrawal
    vault.withdraw(vault.balanceOf(user), user, 100, {"from": user})
    assert (pytest.approx(token.balanceOf(user), rel=RELATIVE_APPROX_LOSSY) == user_balance_before)

def test_emergency_exit(
    dai, chain, token, vault, strategy, user, amount, gov, RELATIVE_APPROX_LOSSY
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_LOSSY) == amount

    # set emergency and exit
    strategy.setEmergencyExit({"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert strategy.estimatedTotalAssets() < amount


def disabled_profitable_harvest(
    chain,
    token,
    vault,
    yvDAI,
    dai,
    dai_whale,
    strategy,
    user,
    amount,
    gov,
    RELATIVE_APPROX_LOSSY,
):

    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount

    # Harvest 1: Send funds through the strategy
    chain.sleep(1)
    firstharvest = strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_LOSSY) == amount

    # Sleep for 60 days
    chain.sleep(60 * 24 * 3600)
    chain.mine(1)

    # Simulate profit in yVault
    before_pps = vault.pricePerShare()
    percentage = 0.1
    #percentage = 1 # = 100%
    dai.approve(yvDAI.address, yvDAI.totalAssets() * percentage, {"from": dai_whale})
    dai.transfer(yvDAI, yvDAI.totalAssets() * percentage, {"from": dai_whale})

    # Harvest 2: Realize profit
    strategy.harvest({"from": gov})

    chain.sleep(3600 * 6)  # 6 hrs needed for profits to unlock
    chain.mine(1)
    profit = token.balanceOf(vault.address)  # Profits go to vault

    assert strategy.estimatedTotalAssets() + profit > amount
    assert vault.pricePerShare() > before_pps
    assert vault.totalAssets() > amount



def disabled_profitable_harvest_SMALL(
    chain,
    token,
    vault,
    yvDAI,
    dai,
    dai_whale,
    strategy,
    user,
    amount,
    gov,
    RELATIVE_APPROX_LOSSY,
    #new_full_dai_yvault
):

    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount

    # Harvest 1: Send funds through the strategy
    chain.sleep(1)
    firstharvest = strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_LOSSY) == amount

    # Sleep for 60 days
    chain.sleep(60 * 24 * 3600)
    chain.mine(1)

    # Simulate profit in yVault
    before_pps = vault.pricePerShare()
    percentage = 0.001
    #percentage = 1 # = 100%
    dai.approve(yvDAI.address, yvDAI.totalAssets() * percentage, {"from": dai_whale})
    dai.transfer(yvDAI, yvDAI.totalAssets() * percentage, {"from": dai_whale})

    # Harvest 2: Realize profit
    strategy.harvest({"from": gov})

    chain.sleep(3600 * 6)  # 6 hrs needed for profits to unlock
    chain.mine(1)
    profit = token.balanceOf(vault.address)  # Profits go to vault
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets() + profit, rel=RELATIVE_APPROX_LOSSY) == amount
    assert vault.pricePerShare() >= before_pps
    assert vault.totalAssets() >= amount

def disabled_profitable_harvest_BIG(
    chain,
    token,
    vault,
    yvDAI,
    dai,
    dai_whale,
    strategy,
    user,
    amount,
    gov,
    RELATIVE_APPROX_LOSSY,
    healthCheck
):
    healthCheck.setProfitLimitRatio(5000, {"from": gov})  #default 100, # 1%
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount

    # Harvest 1: Send funds through the strategy
    chain.sleep(1)
    firstharvest = strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_LOSSY) == amount

    # Sleep for 60 days
    chain.sleep(60 * 24 * 3600)
    chain.mine(1)

    before_pps = vault.pricePerShare()
    percentage = 1
    #percentage = 1 # = 100%
    dai.approve(yvDAI.address, yvDAI.totalAssets() * percentage, {"from": dai_whale})
    dai.transfer(yvDAI, yvDAI.totalAssets() * percentage, {"from": dai_whale})

    # Harvest 2: Realize profit
    strategy.harvest({"from": gov})

    chain.sleep(3600 * 6)  # 6 hrs needed for profits to unlock
    chain.mine(1)
    profit = token.balanceOf(vault.address)  # Profits go to vault

    assert strategy.estimatedTotalAssets() + profit > amount
    assert vault.pricePerShare() > before_pps
    assert vault.totalAssets() > amount


def disabled_change_debt(token_whale, yieldBearing,  chain, gov, token, vault, strategy, user, amount, RELATIVE_APPROX_LOSSY):
    # Deposit to the vault and harvest
    assert vault.totalAssets() == 0
    assert token.balanceOf(vault) == 0
    assert token.balanceOf(strategy) == 0
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert vault.totalAssets() == 50e18
    vault.updateStrategyDebtRatio(strategy.address, 5_000, {"from": gov})
    assert vault.totalAssets() == 50e18
    chain.sleep(1)
    assert vault.totalAssets() == 50e18
    firstharvest = strategy.harvest({"from": gov})
    assert vault.totalAssets() == 50e18
    half = int(amount / 2)

    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_LOSSY) == half

    vault.updateStrategyDebtRatio(strategy.address, 10_000, {"from": gov})
    chain.sleep(1)
    secondharvest = strategy.harvest({"from": gov})
    assert vault.totalAssets() >= 50e18 
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_LOSSY) == amount

    vault.updateStrategyDebtRatio(strategy.address, 5_000, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_LOSSY) == half


def test_sweep(
    gov, vault, strategy, token, user, amount, weth, weth_amount, yvDAI, dai
):
    # Strategy want token doesn't work
    token.transfer(strategy, amount, {"from": user})
    assert token.address == strategy.want()
    assert token.balanceOf(strategy) > 0
    with reverts("!want"):
        strategy.sweep(token, {"from": gov})

    # Vault share token doesn't work
    with reverts("!shares"):
        strategy.sweep(vault.address, {"from": gov})


def test_triggers(chain, gov, vault, strategy, token, amount, user):
    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    vault.updateStrategyDebtRatio(strategy.address, 5_000, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})

    strategy.harvestTrigger(0)
    strategy.tendTrigger(0)
