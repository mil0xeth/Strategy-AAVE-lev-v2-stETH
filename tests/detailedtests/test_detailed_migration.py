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
    ilk_yieldBearing,
    gemJoinAdapter,
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

    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    new_strategy.harvest({"from": gov})

    assert new_strategy.balanceOfDebt() > amount
    assert (pytest.approx(new_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX_LOSSY) == amount )
    assert vault.strategies(new_strategy).dict()["totalDebt"] == amount
