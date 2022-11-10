import pytest
from brownie import chain, reverts, Contract, ZERO_ADDRESS


def test_prod_migration_scale_down(
    chain,
    token,
    amount,
    Strategy,
    gov,
    RELATIVE_APPROX,
    usdc,
    accounts
):
    strategy = Contract("0xAa0Bae32a068C8685160eF8d8003A81b2E13ab2f")
    if (strategy.isActive() == False):
        assert 0 == 1
    sms = accounts.at(strategy.strategist(), force=True)
    vault = Contract(strategy.vault()) 
    strategy_assets_before = strategy.estimatedTotalAssets()
    strategy_debt_before = vault.strategies(strategy)["totalDebt"]

    # migrate to a new strategy
    new_strategy = sms.deploy(Strategy, vault, "Strategy-Maker-lev-GUNIDAIUSDC-0.01%")
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    orig_cdp_id = strategy.cdpId()
    new_strategy.shiftToCdp(orig_cdp_id, {"from": gov})
    assert new_strategy.estimatedTotalAssets() == strategy_assets_before 
    assert vault.strategies(new_strategy)["totalDebt"] == strategy_debt_before

    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18 #there can be small amounts of realized IL

    ## scale strategy down
    vault.updateStrategyDebtRatio(new_strategy, 0, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    ## scale strategy down
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    ## scale strategy down
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

def test_prod_migration_scale_up_then_down(
    chain,
    token,
    amount,
    Strategy,
    gov,
    RELATIVE_APPROX,
    usdc,
    accounts
):
    strategy = Contract("0xAa0Bae32a068C8685160eF8d8003A81b2E13ab2f")
    if (strategy.isActive() == False):
        assert 0 == 1
    sms = accounts.at(strategy.strategist(), force=True)
    vault = Contract(strategy.vault()) 
    strategy_assets_before = strategy.estimatedTotalAssets()
    strategy_debt_before = vault.strategies(strategy)["totalDebt"]

    # migrate to a new strategy
    new_strategy = sms.deploy(Strategy, vault, "Strategy-Maker-lev-GUNIDAIUSDC-0.01%")
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    orig_cdp_id = strategy.cdpId()
    new_strategy.shiftToCdp(orig_cdp_id, {"from": gov})
    assert new_strategy.estimatedTotalAssets() == strategy_assets_before 
    assert vault.strategies(new_strategy)["totalDebt"] == strategy_debt_before

    ##scale up using guni-0.05% funds from vault:
    guni2 = Contract("0x9E3aeF1fb3dE09b8c46247fa707277b7331406B5")
    vault.updateStrategyDebtRatio(guni2, 0, {"from": gov})
    guni2.harvest({"from": gov})

    ##give dr to new_strategy:
    vault.updateStrategyDebtRatio(new_strategy, 1090+10000-vault.debtRatio(), {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    ##play around with dr:
    vault.updateStrategyDebtRatio(new_strategy, 1000, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    vault.updateStrategyDebtRatio(new_strategy, 1000+10000-vault.debtRatio(), {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    vault.updateStrategyDebtRatio(new_strategy, 0, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.setDoHealthCheck(False, {"from": gov})
    new_strategy.setHealthCheck(ZERO_ADDRESS, {"from": gov})

    vault.updateStrategyDebtRatio(new_strategy, 1000, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    vault.updateStrategyDebtRatio(new_strategy, 0, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.setDoHealthCheck(False, {"from": gov})
    vault.updateStrategyDebtRatio(new_strategy, 300, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.setDoHealthCheck(False, {"from": gov})
    vault.updateStrategyDebtRatio(new_strategy, 0, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

def test_prod_migration_harvest_scale_up_then_down(
    chain,
    token,
    amount,
    Strategy,
    gov,
    RELATIVE_APPROX,
    usdc,
    accounts
):
    strategy = Contract("0xAa0Bae32a068C8685160eF8d8003A81b2E13ab2f")
    if (strategy.isActive() == False):
        assert 0 == 1
    sms = accounts.at(strategy.strategist(), force=True)
    vault = Contract(strategy.vault()) 
    strategy_assets_before = strategy.estimatedTotalAssets()
    strategy_debt_before = vault.strategies(strategy)["totalDebt"]

    # migrate to a new strategy
    new_strategy = sms.deploy(Strategy, vault, "Strategy-Maker-lev-GUNIDAIUSDC-0.01%")
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    orig_cdp_id = strategy.cdpId()
    new_strategy.shiftToCdp(orig_cdp_id, {"from": gov})
    assert new_strategy.estimatedTotalAssets() == strategy_assets_before 
    assert vault.strategies(new_strategy)["totalDebt"] == strategy_debt_before

    ##scale up using guni-0.05% funds from vault:
    guni2 = Contract("0x9E3aeF1fb3dE09b8c46247fa707277b7331406B5")
    vault.updateStrategyDebtRatio(guni2, 0, {"from": gov})
    guni2.harvest({"from": gov})

    ##give dr to new_strategy:
    vault.updateStrategyDebtRatio(new_strategy, 1090+10000-vault.debtRatio(), {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    ##play around with dr:
    vault.updateStrategyDebtRatio(new_strategy, 1000, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    vault.updateStrategyDebtRatio(new_strategy, 1000+10000-vault.debtRatio(), {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    vault.updateStrategyDebtRatio(new_strategy, 0, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.setDoHealthCheck(False, {"from": gov})
    new_strategy.setHealthCheck(ZERO_ADDRESS, {"from": gov})

    vault.updateStrategyDebtRatio(new_strategy, 1000, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    vault.updateStrategyDebtRatio(new_strategy, 0, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.setDoHealthCheck(False, {"from": gov})
    vault.updateStrategyDebtRatio(new_strategy, 300, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.setDoHealthCheck(False, {"from": gov})
    vault.updateStrategyDebtRatio(new_strategy, 0, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18


def test_prod_migration_harvest_scale_up_then_profits_then_down(
    chain,
    token,
    amount,
    Strategy,
    gov,
    RELATIVE_APPROX,
    usdc,
    accounts,
    token_whale,
    partnerToken
):
    strategy = Contract("0xAa0Bae32a068C8685160eF8d8003A81b2E13ab2f")
    if (strategy.isActive() == False):
        assert 0 == 1
    sms = accounts.at(strategy.strategist(), force=True)
    vault = Contract(strategy.vault()) 
    strategy_assets_before = strategy.estimatedTotalAssets()
    strategy_debt_before = vault.strategies(strategy)["totalDebt"]

    # migrate to a new strategy
    new_strategy = sms.deploy(Strategy, vault, "Strategy-Maker-lev-GUNIDAIUSDC-0.01%")
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    orig_cdp_id = strategy.cdpId()
    new_strategy.shiftToCdp(orig_cdp_id, {"from": gov})
    assert new_strategy.estimatedTotalAssets() == strategy_assets_before 
    assert vault.strategies(new_strategy)["totalDebt"] == strategy_debt_before

    ##scale up using guni-0.05% funds from vault:
    guni2 = Contract("0x9E3aeF1fb3dE09b8c46247fa707277b7331406B5")
    vault.updateStrategyDebtRatio(guni2, 0, {"from": gov})
    guni2.harvest({"from": gov})

    ##give dr to new_strategy:
    vault.updateStrategyDebtRatio(new_strategy, 1090+10000-vault.debtRatio(), {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    #Create profits for UNIV3 DAI<->USDC
    uniswapv3 = Contract("0xE592427A0AEce92De3Edee1F18E0157C05861564")
    #token --> partnerToken
    uniswapAmount = token.balanceOf(token_whale)*0.1
    token.approve(uniswapv3, uniswapAmount, {"from": token_whale})
    uniswapv3.exactInputSingle((token, partnerToken, 100, token_whale, 1856589943, uniswapAmount, 0, 0), {"from": token_whale})
    chain.sleep(1)

    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    ##play around with dr:
    vault.updateStrategyDebtRatio(new_strategy, 1000, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    vault.updateStrategyDebtRatio(new_strategy, 1000+10000-vault.debtRatio(), {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    vault.updateStrategyDebtRatio(new_strategy, 0, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.setDoHealthCheck(False, {"from": gov})
    new_strategy.setHealthCheck(ZERO_ADDRESS, {"from": gov})

    vault.updateStrategyDebtRatio(new_strategy, 1000, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    vault.updateStrategyDebtRatio(new_strategy, 0, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.setDoHealthCheck(False, {"from": gov})
    vault.updateStrategyDebtRatio(new_strategy, 300, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18

    new_strategy.setDoHealthCheck(False, {"from": gov})
    vault.updateStrategyDebtRatio(new_strategy, 0, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert vault.strategies(new_strategy)["totalLoss"] < 10e18






