import pytest

from brownie import chain, ZERO_ADDRESS


def test_direct_transfer_increments_estimated_total_assets(
    strategy, token, token_whale
):
    initial = strategy.estimatedTotalAssets()
    amount = 10 * (10 ** token.decimals())
    token.transfer(strategy, amount, {"from": token_whale})
    assert strategy.estimatedTotalAssets() == initial + amount


def test_direct_transfer_increments_profits(
    vault, strategy, token, token_whale, gov, RELATIVE_APPROX_LOSSY
):
    initialProfit = vault.strategies(strategy).dict()["totalGain"]
    assert initialProfit == 0

    token.approve(vault.address, 2 ** 256 - 1, {"from": token_whale})
    vault.deposit(1000 * (10 ** token.decimals()), {"from": token_whale})
    chain.sleep(1)
    harvest_tx = strategy.harvest({"from": gov})

    amount = 50 * (10 ** token.decimals())
    token.transfer(strategy, amount, {"from": token_whale})



    #chain.sleep(1)
    strategy.harvest({"from": gov})
    assert (vault.strategies(strategy).dict()["totalGain"] > initialProfit)


def test_borrow_token_transfer_invests(
    vault, strategy, token, token_whale, borrow_token, borrow_whale, gov, Contract,
):
    token.approve(vault, 2 ** 256 - 1, {"from": token_whale})
    vault.deposit(1000 * (10 ** token.decimals()), {"from": token_whale})

    chain.sleep(1)
    strategy.harvest({"from": gov})

    amount = 4_000 * (10 ** borrow_token.decimals())
    borrow_token.transfer(strategy, amount, {"from": borrow_whale})
    chain.sleep(1)
    with pytest.reverts("!healthcheck"):
        strategy.harvest({"from": gov})
    strategy.setHealthCheck(ZERO_ADDRESS, {"from": gov})
    strategy.harvest({"from": gov})
    assert borrow_token.balanceOf(strategy) < 10**token.decimals()


def test_borrow_token_transfer_increments_profits(
    vault, test_strategy, token, token_whale, borrow_token, borrow_whale, gov
):
    token.approve(vault, 2 ** 256 - 1, {"from": token_whale})
    vault.deposit(1000 * (10 ** token.decimals()), {"from": token_whale})

    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    amount = 5_000 * (10 ** borrow_token.decimals())
    borrow_token.transfer(test_strategy, amount, {"from": borrow_whale})

    chain.sleep(1)
    with pytest.reverts("!healthcheck"):
        test_strategy.harvest({"from": gov})
    test_strategy.setHealthCheck(ZERO_ADDRESS, {"from": gov})
    test_strategy.setHealthCheck(ZERO_ADDRESS, {"from": gov})
    test_strategy.harvest({"from": gov})

    token_price = test_strategy._getYieldBearingPrice()
    transferInWant = amount / token_price

    chain.sleep(60)  # wait a minute!
    chain.mine(1)

    test_strategy.harvest({"from": gov})
    # account for fees and slippage - our profit should be at least 95% of the transfer in want
    assert vault.strategies(test_strategy).dict()["totalGain"] > transferInWant * 0.95


def test_deposit_should_not_increment_profits(vault, strategy, token, token_whale, gov):
    initialProfit = vault.strategies(strategy).dict()["totalGain"]
    assert initialProfit == 0

    token.approve(vault, 2 ** 256 - 1, {"from": token_whale})
    vault.deposit(1000 * (10 ** token.decimals()), {"from": token_whale})

    chain.sleep(1)
    strategy.harvest({"from": gov})

    assert vault.strategies(strategy).dict()["totalGain"] == initialProfit


def test_direct_transfer_with_actual_profits_100k(
    vault, token, token_whale, borrow_token, borrow_whale, gov, test_strategy, Contract, steth_whale, steth
):
    strategy = test_strategy
    initialProfit = vault.strategies(strategy).dict()["totalGain"]
    assert initialProfit == 0

    token.approve(vault, 2 ** 256 - 1, {"from": token_whale})
    deposit_tx = vault.deposit(1e3 * (10 ** token.decimals()), {"from": token_whale})

    chain.sleep(1)
    harvest_tx = strategy.harvest({"from": gov})
    assert strategy.estimatedTotalAssets()/1e18 > 980 

    #Create profits
    days = 14
    #send some steth to simulate profit. 10% apr
    rewards_amount = 1e3* (10 ** token.decimals())/10/365*days
    steth.transfer(strategy, rewards_amount*2, {'from': steth_whale})
    chain.sleep(1)

    # sleep for a day
    chain.sleep(24 * 3600)
    chain.mine(1)

    # receive a direct transfer
    airdropAmount = 50 * (10 ** token.decimals())
    token.transfer(strategy, airdropAmount, {"from": token_whale})

    # sleep for another day
    chain.sleep(24 * 3600)
    chain.mine(1)

    strategy.harvest({"from": gov})
    assert (
        vault.strategies(strategy).dict()["totalGain"] > initialProfit + airdropAmount*0.9
    )



def test_direct_transfer_with_actual_profits_1000(
    vault, token, token_whale, borrow_token, borrow_whale, gov, test_strategy, Contract, steth_whale, steth
):
    strategy = test_strategy
    initialProfit = vault.strategies(strategy).dict()["totalGain"]
    assert initialProfit == 0

    token.approve(vault, 2 ** 256 - 1, {"from": token_whale})
    deposit_tx = vault.deposit(1000 * (10 ** token.decimals()), {"from": token_whale})

    chain.sleep(1)
    harvest_tx = strategy.harvest({"from": gov})
    assert strategy.estimatedTotalAssets()/1e18 > 99

    #Create profits
    days = 14
    #send some steth to simulate profit. 10% apr
    rewards_amount = 1000* (10 ** token.decimals())/10/365*days
    steth.transfer(strategy, rewards_amount*2, {'from': steth_whale})
    chain.sleep(1)
    chain.sleep(1)
    # sleep for a day
    chain.sleep(24 * 3600)
    chain.mine(1)

    # receive a direct transfer
    airdropAmount = 5 * (10 ** token.decimals())
    token.transfer(strategy, airdropAmount, {"from": token_whale})

    # sleep for another day
    chain.sleep(24 * 3600)
    chain.mine(1)

    strategy.harvest({"from": gov})
    assert (
        vault.strategies(strategy).dict()["totalGain"] > initialProfit + airdropAmount*0.9
    )
