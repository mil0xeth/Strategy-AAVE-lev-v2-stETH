import pytest

from brownie import Wei, Contract


def test_liquidates_all_if_exact_same_want_balance(test_strategy, token, token_whale):
    amount = Wei("100 ether")
    token.approve(test_strategy, amount, {"from": token_whale})
    token.transfer(test_strategy, amount, {"from": token_whale})

    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(amount).return_value
    assert _liquidatedAmount == amount
    assert _loss == 0


def test_liquidates_all_if_has_more_want_balance(test_strategy, token, token_whale):
    amount = Wei("50 ether")
    token.approve(test_strategy, amount, {"from": token_whale})
    token.transfer(test_strategy, amount, {"from": token_whale})

    amountToLiquidate = amount * 0.5
    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(
        amountToLiquidate
    ).return_value
    assert _liquidatedAmount == amountToLiquidate
    assert _loss == 0


def test_liquidate_more_than_we_have_should_report_loss(
    test_strategy, token, token_whale, gov
):
    amount = Wei("50 ether")
    token.approve(test_strategy, amount, {"from": token_whale})
    token.transfer(test_strategy, amount, {"from": token_whale})

    amountToLiquidate = amount * 1.5
    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(
        amountToLiquidate
    ).return_value
    assert _liquidatedAmount == amount
    assert _loss == (amountToLiquidate - amount)


# In this test we attempt to liquidate the whole position a week after the deposit.
# We do not simulate any gains, so there will not be enough money
# to unlock the whole collateral without a loss.
# If leaveDebtBehind is false (default) then the strategy will need to unlock a bit
# of collateral and sell it for DAI in order to pay back the debt.
def test_liquidate_position_without_enough_profit_by_selling_want(
    chain, token, vault, test_strategy, user, amount, token_whale, gov
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # sleep 7 days
    chain.sleep(24 * 60 * 60 * 7)
    chain.mine(1)

    # Harvest so all the collateral is locked in the CDP
    test_strategy.harvest({"from": gov})

    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(amount).return_value
    assert _liquidatedAmount + _loss == amount
    assert _loss > 0
    assert token.balanceOf(test_strategy) < amount




# In this test the strategy has enough profit to close the whole position
def test_happy_liquidation(
    chain, token, vault, test_strategy, token_whale, steth_whale, dai, dai_whale, user, amount, gov, steth
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # Harvest so all the collateral is locked in the CDP
    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    # sleep 7 days
    chain.sleep(24 * 60 * 60 * 7)
    chain.mine(1)

    #Create profits
    days = 14
    #send some steth to simulate profit. 10% apr
    rewards_amount = amount/10/365*days
    steth.transfer(test_strategy, rewards_amount*2, {'from': steth_whale})
    chain.sleep(1)


    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(test_strategy.estimatedTotalAssets()).return_value
    ## everything in want now:
    assert _loss < 1e18
    assert _liquidatedAmount > amount-1e18
    assert test_strategy.estimatedTotalAssets() > 10
    assert test_strategy.balanceOfDebt() == 0
    assert test_strategy.balanceOfCollateral() < 10

    #take back to vault:
    vault.updateStrategyDebtRatio(test_strategy, 0, {"from": gov})
    test_strategy.harvest({"from": gov})
    assert test_strategy.estimatedTotalAssets() < 10
