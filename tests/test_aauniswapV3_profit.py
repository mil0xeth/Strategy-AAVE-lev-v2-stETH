import brownie
from brownie import Contract
import pytest

def test_aauniswapV3_profit(
   router, unirouter, usdc, partnerToken, chain, dai, dai_whale, token_whale, vault, test_strategy, yieldBearing, token, amountBIGTIME, amountBIGTIME2, user2, user, gov, RELATIVE_APPROX, RELATIVE_APPROX_LOSSY
):
    # Initial ratio is 0 because there is no collateral locked
    assert test_strategy.getCurrentCollRatio() == 0
    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, amountBIGTIME, {"from": user})
    vault.deposit(amountBIGTIME, {"from": user})
    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    # Collateral ratio should be the target ratio set
    assert ( pytest.approx(test_strategy.getCurrentCollRatio(), rel=RELATIVE_APPROX) == test_strategy.collateralizationRatio())

    priceBefore = test_strategy.getWantPerYieldBearing()
    strategyAssetsBefore = test_strategy.estimatedTotalAssets()
    vaultAssetsBefore = vault.totalAssets()
    strategyCollateralizationRatioBefore = test_strategy.getCurrentCollRatio()

    #Create profits for UNIV3 DAI<->USDC
    uniswapv3 = Contract("0xE592427A0AEce92De3Edee1F18E0157C05861564")
    #token --> partnerToken
    token.approve(uniswapv3, 2**256-1, {"from": token_whale})
    partnerToken.approve(uniswapv3, 2**256-1, {"from": token_whale})
    for x in range (0, 10):
      uniswapAmount = token.balanceOf(token_whale)*0.3
      uniswapv3.exactInputSingle((token, partnerToken, 100, token_whale, 1856589943, uniswapAmount, 0, 0), {"from": token_whale})
      chain.sleep(1)
      uniswapAmount = partnerToken.balanceOf(token_whale)*0.3
      uniswapv3.exactInputSingle((partnerToken, token, 100, token_whale, 1856589943, uniswapAmount, 0, 0), {"from": token_whale})
      chain.sleep(1)

    priceAfter = test_strategy.getWantPerYieldBearing()
    strategyAssetsAfter = test_strategy.estimatedTotalAssets()
    strategyCollateralizationRatioAfter = test_strategy.getCurrentCollRatio()

    assert strategyAssetsAfter-strategyAssetsBefore > 0

    #collect profits into vault
    test_strategy.setMinMaxSingleTrade(1e12, 2**256-1, {"from": gov})
    test_strategy.harvest({"from": gov})
    vaultAssetsAfter = vault.totalAssets()

    assert vaultAssetsAfter > vaultAssetsBefore
    assert vault.strategies(test_strategy)["totalGain"] > 0

    #reinvest profits into strategy
    test_strategy.harvest({"from": gov})
    assert ( pytest.approx(test_strategy.getCurrentCollRatio(), rel=RELATIVE_APPROX) == test_strategy.collateralizationRatio())
    assert ( pytest.approx(test_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == vault.totalAssets())
