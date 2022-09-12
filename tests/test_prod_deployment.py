import pytest, time

from brownie import reverts, chain, Contract, Wei, history, ZERO_ADDRESS
from eth_abi import encode_single


def test_prod(
    healthCheck, productionVault, yieldBearing, token, weth, dai, strategist, token_whale, dai_whale, MakerDaiDelegateClonerChoice, Strategy, partnerToken
):

    vault = productionVault
    gov = vault.governance()

    cloner = strategist.deploy(
        MakerDaiDelegateClonerChoice,
        vault,
        "Strategy-Maker-lev-GUNIV3DAIUSDC",
    )

    original_strategy_address = history[-1].events["Deployed"]["original"]
    strategy = Strategy.at(original_strategy_address)

    assert strategy.strategist() == "0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7"
    assert strategy.keeper() == "0x736D7e3c5a6CB2CE3B764300140ABF476F6CFCCF"
    assert strategy.rewards() == "0xc491599b9A20c3A2F0A85697Ee6D9434EFa9f503"

    # Reduce other strategies debt allocation
    for i in range(0, 20):
        strat_address = vault.withdrawalQueue(i)
        if strat_address == ZERO_ADDRESS:
            break
        vault.updateStrategyDebtRatio(strat_address, 0, {"from": gov})

    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})
    strategy.setMinMaxSingleTrade(strategy.minSingleTrade(), 1e40, {"from": gov})
    token.approve(vault, 2 ** 256 - 1, {"from": token_whale})
    vault.deposit(2500 * (10 ** token.decimals()), {"from": token_whale})

    tx1 = strategy.harvest({"from": gov})
    tx1.wait(1)
    time.sleep(1)

    print(f"After first harvest")
    print(f"strat estimatedTotalAssets: {strategy.estimatedTotalAssets()/1e18:_}")

    assert vault.strategies(strategy).dict()["totalLoss"] == 0
    # Sleep for 2 days
    chain.sleep(60 * 60 * 24 * 2)
    chain.mine(1)
    assert vault.strategies(strategy).dict()["totalLoss"] == 0
    #PROFITS:
    #Create profits for UNIV3 DAI<->USDC
    uniswapv3 = Contract("0xE592427A0AEce92De3Edee1F18E0157C05861564")
    #token --> partnerToken
    uniswapAmount = token.balanceOf(token_whale)*0.1
    token.approve(uniswapv3, uniswapAmount, {"from": token_whale})
    uniswapv3.exactInputSingle((token, partnerToken, 100, token_whale, 1856589943, uniswapAmount, 0, 0), {"from": token_whale})
    chain.sleep(1)

    tx2 = strategy.harvest({"from": gov})
    tx2.wait(1) 
    time.sleep(1)
    assert vault.strategies(strategy).dict()["totalLoss"] == 0
    print(f"After second harvest")
    print(f"strat estimatedTotalAssets: {strategy.estimatedTotalAssets()/1e18:_}")

    assert vault.strategies(strategy).dict()["totalGain"] > 0
    assert vault.strategies(strategy).dict()["totalLoss"] == 0
    chain.sleep(60 * 60 * 8)
    chain.mine(1)
    assert vault.strategies(strategy).dict()["totalLoss"] == 0
    vault.updateStrategyDebtRatio(strategy, 0, {"from": gov})
    lossyharvest = strategy.harvest({"from": gov})
    assert vault.strategies(strategy).dict()["totalLoss"] > 0
    print(f"After third harvest")
    print(f"strat estimatedTotalAssets: {strategy.estimatedTotalAssets()/1e18:_}")
    print(f"totalLoss: {vault.strategies(strategy).dict()['totalLoss']/1e18:_}")

    assert vault.strategies(strategy).dict()["totalLoss"] < Wei("0.75 ether")
    assert vault.strategies(strategy).dict()["totalDebt"] == 0
