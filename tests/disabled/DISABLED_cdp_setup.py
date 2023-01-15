import pytest

from brownie.convert import to_string
from brownie.network.state import TxHistory
from brownie import chain, Wei




def test_dai_should_be_minted_after_depositing_collateral(
    strategy, vault, token, token_whale, dai, gov
):
    # Make sure there is no balance before the first deposit
    assert yvDAI.balanceOf(strategy) == 0

    amount = 25 * (10 ** token.decimals())
    token.approve(vault.address, amount, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})

    chain.sleep(1)
    strategy.harvest({"from": gov})

    # Minted DAI should be deposited in yvDAI
    assert dai.balanceOf(strategy) < 10000
    assert yvDAI.balanceOf(strategy) > 0


def DISABLED_minted_dai_should_match_collateralization_ratio(
    test_strategy, vault, yvDAI, token, token_whale, gov, RELATIVE_APPROX
):
    assert yvDAI.balanceOf(test_strategy) == 0

    amount = 25 * (10 ** token.decimals())
    token.approve(vault.address, amount, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})

    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    token_price = test_strategy._getPrice()

    assert pytest.approx(
        yvDAI.balanceOf(test_strategy) * yvDAI.pricePerShare() / 1e18,
        rel=RELATIVE_APPROX,
    ) == (
        token_price * amount / test_strategy.collateralizationRatio()  # already in wad
    )


def DISABLED_WETH_test_ethToWant_should_convert_to_yfi(
    strategy, price_oracle_want_to_eth, RELATIVE_APPROX
):
    price = price_oracle_want_to_eth.latestAnswer()
    assert pytest.approx(
        strategy.ethToWant(Wei("1 ether")), rel=RELATIVE_APPROX
    ) == Wei("1 ether") / (price / 1e18)
    assert pytest.approx(
        strategy.ethToWant(Wei(price * 420)), rel=RELATIVE_APPROX
    ) == Wei("420 ether")
    assert pytest.approx(
        strategy.ethToWant(Wei(price * 0.5)), rel=RELATIVE_APPROX
    ) == Wei("0.5 ether")


# Needs to use test_strategy fixture to be able to read token_price
def DISABLED_delegated_assets_pricing(
    test_strategy, vault, yvDAI, token, token_whale, gov, RELATIVE_APPROX
):
    amount = 25 * (10 ** token.decimals())
    token.approve(vault.address, amount, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})

    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    dai_balance = yvDAI.balanceOf(test_strategy) * yvDAI.pricePerShare() / 1e18
    token_price = test_strategy._getPrice()

    assert pytest.approx(test_strategy.delegatedAssets(), rel=RELATIVE_APPROX) == (
        dai_balance / token_price * (10 ** token.decimals())
    )
