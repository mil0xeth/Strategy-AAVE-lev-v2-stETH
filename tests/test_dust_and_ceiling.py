import pytest, time

from brownie import chain, reverts, Wei, Contract


def test_small_deposit_does_not_generate_debt_under_floor(
    vault, test_strategy, token, token_whale_BIG,borrow_token, gov, RELATIVE_APPROX_ROUGH, yieldBearing
):
    #price = test_strategy._getYieldBearingPrice()
    #floor = Wei("15_000 ether")  # assume a price floor of 15k
    # Amount in want that generates 'floor' debt minus a treshold
    #token_floor = ((test_strategy.collateralizationRatio() * floor / 1e18) / price) * ( 10 ** token.decimals())
    token_floor = 200*10**token.decimals()

    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, token_floor, {"from": token_whale_BIG})

    vault.deposit(token_floor, {"from": token_whale_BIG})
    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    # with a lower deposit amount
    assert (pytest.approx(test_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_ROUGH) == token_floor)
    assert test_strategy.balanceOfDebt() == 0
    # everything is left in want
    assert test_strategy.balanceOfMakerVault() == 0
    assert token.balanceOf(test_strategy) > token_floor*0.8
    assert yieldBearing.balanceOf(test_strategy) < 0.1*10**token.decimals()

def test_deposit_after_passing_debt_floor_generates_debt(
    vault, test_strategy, token, token_whale_BIG, borrow_token, gov, RELATIVE_APPROX, RELATIVE_APPROX_ROUGH, yieldBearing
):
    #price = test_strategy._getYieldBearingPrice()
    #floor = Wei("14_000 ether")  # assume a price floor of 5k as in ETH-C
    token_floor = 300*10**token.decimals()
    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, 2 ** 256 - 1, {"from": token_whale_BIG})
    vault.deposit(token_floor, {"from": token_whale_BIG})
    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    # Debt floor is 10k for YFI-A, so the strategy should not take any debt
    # with a lower deposit amount
    assert test_strategy.balanceOfDebt() == 0
    assert test_strategy.balanceOfMakerVault() == 0
    assert token.balanceOf(test_strategy) > token_floor*0.8
    assert (pytest.approx(test_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_ROUGH) == token_floor)

    # Deposit enough want token to go over the dust
    additional_deposit = 300*10**token.decimals()

    vault.deposit(additional_deposit, {"from": token_whale_BIG})
    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    assert test_strategy.balanceOfDebt() > 0    
    assert test_strategy.balanceOfMakerVault() > 0
    assert (pytest.approx(test_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_ROUGH) == token_floor + additional_deposit)
    # Check if collateralization ratio is correct:
    assert (pytest.approx(test_strategy.getCurrentMakerVaultRatio(), rel=RELATIVE_APPROX) == test_strategy.collateralizationRatio())

def test_withdraw_does_not_leave_debt_under_floor(
    vault, test_strategy, token, token_whale_BIG, dai, dai_whale, gov, RELATIVE_APPROX_ROUGH, partnerToken, token_whale
):
    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, 2 ** 256 - 1, {"from": token_whale_BIG})
    vault.deposit(1000*10**token.decimals(), {"from": token_whale_BIG})
    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    #PROFITS:
    #Create profits for UNIV3 DAI<->USDC
    uniswapv3 = Contract("0xE592427A0AEce92De3Edee1F18E0157C05861564")
    #token --> partnerToken
    uniswapAmount = token.balanceOf(token_whale)*0.1
    token.approve(uniswapv3, uniswapAmount, {"from": token_whale})
    uniswapv3.exactInputSingle((token, partnerToken, 100, token_whale, 1856589943, uniswapAmount, 0, 0), {"from": token_whale})
    chain.sleep(1)

    # Withdraw large amount so remaining debt is under floor
    withdraw_tx = vault.withdraw(800*10**token.decimals(), token_whale_BIG, 500, {"from": token_whale_BIG})
    withdraw_tx.wait(1)
    time.sleep(1)

    # Because debt is under floor, we expect Ratio to be 0
    assert test_strategy.balanceOfDebt() == 0    
    assert test_strategy.balanceOfMakerVault() == 0

def test_large_deposit_does_not_generate_debt_over_ceiling(
    vault, test_strategy, token, token_whale_BIG, borrow_token, gov
):
    test_strategy.setMinMaxSingleTrade(test_strategy.minSingleTrade(), 1e40, {"from": gov})
    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, 2 ** 256 - 1, {"from": token_whale_BIG})
    vault.deposit(token.balanceOf(token_whale_BIG), {"from": token_whale_BIG})
    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    # Debt ceiling is ~100 million in ETH-C at this time
    # The whale should deposit >2x that to hit the ceiling
    assert test_strategy.balanceOfDebt() > 0
    assert token.balanceOf(vault) == 0

    # Collateral ratio should be larger due to debt being capped by ceiling
    assert (test_strategy.getCurrentMakerVaultRatio()/(10 ** token.decimals()) > 3)


def test_withdraw_everything_with_vault_in_debt_ceiling(
    vault, test_strategy, token, token_whale_BIG, gov, RELATIVE_APPROX_ROUGH
):
    amount = token.balanceOf(token_whale_BIG)

    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, 2 ** 256 - 1, {"from": token_whale_BIG})
    vault.deposit(amount, {"from": token_whale_BIG})
    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    #test_strategy.setLeaveDebtBehind(False, {"from": gov})
    vault.withdraw(vault.balanceOf(token_whale_BIG), token_whale_BIG, 1000, {"from": token_whale_BIG})
    time.sleep(1)

    assert vault.strategies(test_strategy).dict()["totalDebt"] == 0
    assert test_strategy.getCurrentMakerVaultRatio() == 0
    assert pytest.approx(token.balanceOf(token_whale_BIG), rel=RELATIVE_APPROX_ROUGH) == amount


def test_large_want_balance_does_not_generate_debt_over_ceiling(
    vault, test_strategy, token, token_whale_BIG, borrow_token, gov
):
    test_strategy.setMinMaxSingleTrade(test_strategy.minSingleTrade(), 1e40, {"from": gov})
    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, 2 ** 256 - 1, {"from": token_whale_BIG})
    vault.deposit(token.balanceOf(token_whale_BIG), {"from": token_whale_BIG})

    # Send the funds through the strategy to invest
    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    # Debt ceiling is ~100 million in ETH-C at this time
    # The whale should deposit >2x that to hit the ceiling
    assert test_strategy.balanceOfDebt() > 0
    assert token.balanceOf(vault) == 0

    # Collateral ratio should be larger due to debt being capped by ceiling
    assert (test_strategy.getCurrentMakerVaultRatio()/(10 ** token.decimals()) > 3)


# Fixture 'amount' is included so user has some balance
def test_withdraw_everything_cancels_entire_debt(
    vault, test_strategy, token, token_whale_BIG, user, amount, dai, dai_whale, gov, RELATIVE_APPROX_LOSSY, partnerToken, token_whale
):
    amount_user = 25000 * 10 ** token.decimals()
    amount_whale = token.balanceOf(token_whale_BIG)

    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, 2 ** 256 - 1, {"from": token_whale_BIG})
    vault.deposit(amount_whale, {"from": token_whale_BIG})

    token.approve(vault.address, 2 ** 256 - 1, {"from": user})
    vault.deposit(amount_user, {"from": user})

    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    #PROFITS:
    #Create profits for UNIV3 DAI<->USDC
    #uniswapv3 = Contract("0xE592427A0AEce92De3Edee1F18E0157C05861564")
    #token --> partnerToken
    #uniswapAmount = token.balanceOf(token_whale)*0.1
    #token.approve(uniswapv3, uniswapAmount, {"from": token_whale})
    #uniswapv3.exactInputSingle((token, partnerToken, 100, token_whale, 1856589943, uniswapAmount, 0, 0), {"from": token_whale})
    #chain.sleep(1)

    assert vault.withdraw(vault.balanceOf(token_whale_BIG), token_whale_BIG, 100, {"from": token_whale_BIG}).return_value + 10**token.decimals() >= amount_whale
    assert vault.withdraw(vault.balanceOf(user), user, 100, {"from": user}).return_value + 10**token.decimals() >= amount_user
    assert vault.strategies(test_strategy).dict()["totalDebt"] == 0


def test_tend_trigger_with_debt_under_dust_returns_false(
    vault, test_strategy, token, token_whale_BIG, gov
):
 
    # Amount in want that generates 'floor' debt minus a treshold
    token_floor = 200* 10 ** token.decimals()

    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, token_floor, {"from": token_whale_BIG})

    vault.deposit(token_floor, {"from": token_whale_BIG})
    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    # Debt floor is 5k for ETH-C, so the strategy should not take any debt
    # with a lower deposit amount
    assert test_strategy.tendTrigger(1) == False


def test_tend_trigger_without_more_mintable_dai_returns_false(
    vault, strategy, token, token_whale_BIG, gov
):
    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, 2 ** 256 - 1, {"from": token_whale_BIG})
    vault.deposit(token.balanceOf(token_whale_BIG), {"from": token_whale_BIG})
    chain.sleep(1)
    strategy.harvest({"from": gov})

    assert strategy.tendTrigger(1) == False

