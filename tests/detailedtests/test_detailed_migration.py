import pytest

from brownie import Contract, reverts


def test_detailed_migration(
    chain,
    token,
    vault,
    strategy,
    strategist,
    amount,
    Strategy,
    gov,
    user,
    cloner,
    RELATIVE_APPROX_LOSSY,
):
    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_LOSSY) == amount

    # migrate to a new strategy
    new_strategy = Strategy.at(
        cloner.cloneMakerDaiDelegate(
            vault,
            strategist,
            strategist,
            strategist,
            "name",
            #ilk_want,
            #ilk_yieldBearing,
            #gemJoinAdapter,
            #strategy.wantToUSDOSMProxy(),
            #strategy.yieldBearingToUSDOSMProxy(),
            #strategy.chainlinkWantToETHPriceFeed(),
        ).return_value
    )

    # migration with more than dust reverts, there is no way to transfer the debt position
    with reverts():
        vault.migrateStrategy(strategy, new_strategy, {"from": gov})

    vault.revokeStrategy(strategy, {"from": gov})
    strategy.harvest({"from": gov})

    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    vault.updateStrategyDebtRatio(new_strategy, 10_000, {"from": gov})
    new_strategy.harvest({"from": gov})

    assert (pytest.approx(new_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_LOSSY) == amount )
