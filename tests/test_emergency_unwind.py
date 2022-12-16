import pytest
from brownie import chain, reverts, Wei, Contract


def test_passing_everything_should_repay_all_debt(
    vault, strategy, token, token_whale, user, gov, dai, dai_whale, RELATIVE_APPROX_LOSSY, yieldBearing, partnerToken, RELATIVE_APPROX
):
    amount = 1_000 * (10 ** token.decimals())

    # Deposit to the vault
    token.approve(vault.address, amount, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})

    # Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert strategy.balanceOfDebt() > 0

    #Create profits for UNIV3 DAI<->USDC
    uniswapv3 = Contract("0xE592427A0AEce92De3Edee1F18E0157C05861564")
    #token --> partnerToken
    uniswapAmount = token.balanceOf(token_whale)*0.1
    token.approve(uniswapv3, uniswapAmount, {"from": token_whale})
    uniswapv3.exactInputSingle((token, partnerToken, 100, token_whale, 1856589943, uniswapAmount, 0, 0), {"from": token_whale})
    chain.sleep(1)

    # Harvest 2: Realize profit
    strategy.harvest({"from": gov})
    chain.sleep(3600 * 6)  # 6 hrs needed for profits to unlock
    chain.mine(1)

    prev_collat = strategy.balanceOfCollateral()
    strategy.emergencyUnwind(strategy.estimatedTotalAssets(), {"from": vault.management()})

    # All debt is repaid and collateral is left untouched
    assert strategy.balanceOfDebt() == 0
    #strategy unlocks all collateral if there is not enough to take debt
    #assert strategy.balanceOfCollateral() == prev_collat
    assert strategy.balanceOfCollateral() == 0
    assert pytest.approx(yieldBearing.balanceOf(strategy) == prev_collat, rel=RELATIVE_APPROX_LOSSY)

    # Re-harvest with same funds
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert strategy.balanceOfDebt() > 0
    assert strategy.balanceOfCollateral() > 0
    assert yieldBearing.balanceOf(strategy)/1e18 < 1 


def test_passing_everything_should_repay_all_debt_then_new_deposit_create_debt_again(
    yieldBearing, vault, strategy, token, token_whale, user, gov, dai, dai_whale, RELATIVE_APPROX_LOSSY, partnerToken, RELATIVE_APPROX
):
    amount = 1_000 * (10 ** token.decimals())

    # Deposit to the vault
    token.approve(vault.address, amount, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})

    # Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert strategy.balanceOfDebt() > 0

    #Create profits for UNIV3 DAI<->USDC
    uniswapv3 = Contract("0xE592427A0AEce92De3Edee1F18E0157C05861564")
    #token --> partnerToken
    uniswapAmount = token.balanceOf(token_whale)*0.1
    token.approve(uniswapv3, uniswapAmount, {"from": token_whale})
    uniswapv3.exactInputSingle((token, partnerToken, 100, token_whale, 1856589943, uniswapAmount, 0, 0), {"from": token_whale})
    chain.sleep(1)

    # Harvest 2: Realize profit
    strategy.harvest({"from": gov})
    chain.sleep(3600 * 6)  # 6 hrs needed for profits to unlock
    chain.mine(1)

    prev_collat = strategy.balanceOfCollateral()
    strategy.emergencyUnwind(strategy.estimatedTotalAssets(), {"from": vault.management()})

    # All debt is repaid and collateral is left untouched
    assert strategy.balanceOfDebt() == 0
    #strategy unlocks all collateral if there is not enough to take debt
    #assert strategy.balanceOfCollateral() == prev_collat
    assert pytest.approx(yieldBearing.balanceOf(strategy) == prev_collat, rel=RELATIVE_APPROX_LOSSY)

    ##Deposit AGAIN, test for debt

    # Deposit to the vault
    token.approve(vault.address, amount, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})

     # Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert strategy.balanceOfDebt() > 0
    assert strategy.balanceOfCollateral() > 0
    assert yieldBearing.balanceOf(strategy)/1e18 < 1 

def test_passing_value_same_collat_ratio(
    vault, strategy, token, amount, user, gov, RELATIVE_APPROX, RELATIVE_APPROX_LOSSY, yieldBearing
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert strategy.balanceOfDebt() > 0

    assert ( pytest.approx(strategy.getCurrentCollRatio(), rel=RELATIVE_APPROX) == strategy.collateralizationRatio())
    assert ( pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == vault.totalAssets())
    collateralizationRatioBefore = strategy.getCurrentCollRatio()
    totalInitial = strategy.estimatedTotalAssets()
    strategy.emergencyUnwind(totalInitial*0.2, {"from": vault.management()})
    assert ( pytest.approx(strategy.getCurrentCollRatio(), rel=RELATIVE_APPROX) == collateralizationRatioBefore)
    assert ( pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == vault.totalAssets())
    strategy.emergencyUnwind(totalInitial*0.2, {"from": vault.management()})
    assert ( pytest.approx(strategy.getCurrentCollRatio(), rel=RELATIVE_APPROX) == collateralizationRatioBefore)
    assert ( pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == vault.totalAssets())
    strategy.emergencyUnwind(totalInitial*0.2, {"from": vault.management()})
    assert ( pytest.approx(strategy.getCurrentCollRatio(), rel=RELATIVE_APPROX) == collateralizationRatioBefore)
    assert ( pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == vault.totalAssets())
    strategy.emergencyUnwind(totalInitial*0.2, {"from": vault.management()})
    assert ( pytest.approx(strategy.getCurrentCollRatio(), rel=RELATIVE_APPROX) == collateralizationRatioBefore)
    assert ( pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == vault.totalAssets())
    strategy.emergencyUnwind(strategy.estimatedTotalAssets(), {"from": vault.management()})
 
    # All debt is repaid and collateral is left untouched
    assert strategy.balanceOfDebt() == 0
    #strategy unlocks all collateral if there is not enough to take debt
    #assert strategy.balanceOfCollateral() == prev_collat
    assert strategy.balanceOfCollateral() == 0
