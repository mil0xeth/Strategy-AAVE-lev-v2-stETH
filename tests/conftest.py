import pytest
from brownie import config, convert, interface, Contract
##################
#################
#Decide on Strategy Contract
@pytest.fixture(autouse=True)
def StrategyChoice(Strategy):    
    choice = Strategy #Strategy = maker-eth-dai-delegator, NewStrategy = maker-wsteth-dai-lev 
    yield choice
@pytest.fixture(autouse=True)
def TestStrategyChoice(TestStrategy):    
    choice = TestStrategy #TestStrategy, NewTestStrategy
    yield choice
@pytest.fixture(autouse=True)
def MakerDaiDelegateClonerChoice(MakerDaiDelegateCloner):    
    choice = MakerDaiDelegateCloner 
    yield choice
#######################################################
#Decide on wantToken = token
@pytest.fixture(autouse=True)
def wantNr():    
    wantNr = 0 #Currently: 
    #0 = DAI,   1 = USDC 
    yield wantNr
#######################################################
#Decide on yieldBearing = collateral Token on Money Market
@pytest.fixture(autouse=True)
def yieldBearingNr():    
    yieldBearingNr = 1 #Currently: GUNIV3DAIUSDC1 0.05%
    #0 = GUNIV3DAIUSDC1 0.0%,   1 =  
    yield yieldBearingNr
#######################################################
@pytest.fixture
def token(dai, usdc, wantNr):   
    #signifies want token given by wantNr
    token_address = [
    dai,   #0 = DAI
    usdc,   #1 = USDC
    ]
    yield token_address[wantNr]

@pytest.fixture
def partnerToken(dai, usdc, wantNr):   
    #signifies want token given by wantNr
    token_address = [
    usdc,   #0 = DAI
    dai,   #1 = USDC
    ]
    yield token_address[wantNr]

@pytest.fixture
def yieldBearing(guniv3daiusdc1, guniv3daiusdc2, yieldBearingNr):   
    #signifies want token given by wantNr
    yieldBearing_address = [
    guniv3daiusdc1,   #0 = GUNIV3DAIUSDC1 0.05%
    guniv3daiusdc2,   #1 = GUNIV3DAIUSDC2 0.01%
    ]
    yield yieldBearing_address[yieldBearingNr]

@pytest.fixture
def borrow_token(dai):
    yield dai

@pytest.fixture
def borrow_whale(dai_whale):
    yield dai_whale
 
#chainlinkWantToETHPriceFeed
@pytest.fixture
def price_oracle_want_to_eth(wantNr):
    oracle_address = [
    "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419",  #ETH/USD
    "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419",  #ETH/USD
    "0xcfe54b5cd566ab89272946f602d76ea879cab4a8",  #stETH/USD
    "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419"  #ETH/USD    no wsteth/USD available!
    ]
    yield interface.AggregatorInterface(oracle_address[wantNr])
#############################################################

@pytest.fixture
def weth():
    token_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2" #WETH
    yield Contract(token_address)   

@pytest.fixture
def weth_amout(user, weth):
    weth_amout = 10 ** weth.decimals()
    user.transfer(weth, weth_amout)
    yield weth_amout

@pytest.fixture
def guniv3daiusdc1():
    token_address = "0xAbDDAfB225e10B90D798bB8A886238Fb835e2053"
    yield Contract(token_address)

@pytest.fixture
def guniv3daiusdc2():
    token_address = "0x50379f632ca68D36E50cfBC8F78fe16bd1499d1e"  
    yield Contract(token_address)

@pytest.fixture
def dai():
    dai_address = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
    yield Contract(dai_address)

@pytest.fixture
def usdc():
    token_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    yield Contract(token_address)

#@pytest.fixture
#def steth_whale(accounts):
#    yield accounts.at("0x2faf487a4414fe77e2327f0bf4ae2a264a776ad2") 

#@pytest.fixture
#def wsteth_whale(accounts):
#    yield accounts.at("0x62e41b1185023bcc14a465d350e1dde341557925") 

@pytest.fixture
def token_whale(accounts, wantNr, dai_whale):
    #eth_whale = accounts.at("0xda9dfa130df4de4673b89022ee50ff26f6ea73cf", force=True)
    #token_whale_address = [
    #"0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8",   #0 = ETH
    #"0xe78388b4ce79068e89bf8aa7f218ef6b9ab0e9d0",   #1 = WETH  0x030bA81f1c18d280636F32af80b9AAd02Cf0854e, 0x57757e3d981446d585af0d9ae4d7df6d64647806  
    #"0x2faf487a4414fe77e2327f0bf4ae2a264a776ad2",  #2 = steth
    #"0x62e41b1185023bcc14a465d350e1dde341557925"  #3 = wsteth
    #]
    #token_whale_account = accounts.at(token_whale_address[wantNr], force=True) 
    #eth_whale.transfer(token_whale_account, "100000 ether")
    yield dai_whale

@pytest.fixture
def token_whale_BIG(accounts, wantNr, dai_whale):
    #eth_whale = accounts.at("0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8", force=True)
    #token_whale_address = [
    #"0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8",   #0 = ETH
    #"0xe78388b4ce79068e89bf8aa7f218ef6b9ab0e9d0",   #1 = WETH  0x030bA81f1c18d280636F32af80b9AAd02Cf0854e, 0x57757e3d981446d585af0d9ae4d7df6d64647806  
    #"0x2faf487a4414fe77e2327f0bf4ae2a264a776ad2",  #2 = steth
    #"0x62e41b1185023bcc14a465d350e1dde341557925"  #3 = wsteth
    #]
    #token_whale_account = accounts.at(token_whale_address[wantNr], force=True) 
    #eth_whale.transfer(token_whale_account, eth_whale.balance()*0.95)
    #ethwrapping.deposit({'from': token_whale_account, 'value': token_whale_account.balance()*0.95})
    #yield token_whale_account
    yield dai_whale

@pytest.fixture
def yieldBearing_whale(accounts, yieldBearingNr, token_whale, yieldBearing, token, partnerToken, strategy):
    token.approve(yieldBearing, 100000000000000000000e18, {"from": token_whale})
    partnerToken.approve(yieldBearing, 10000000000000000000000e6, {"from": token_whale})
    yieldBearing.mint(yieldBearing.getMintAmounts(token.balanceOf(token_whale)*0.1, partnerToken.balanceOf(token_whale)*0.1)[2], token_whale, {"from": token_whale})
    yield token_whale

@pytest.fixture
def weth_amount(user, weth):
    weth_amount = 10 ** weth.decimals()
    user.transfer(weth, weth_amount)
    yield weth_amount

@pytest.fixture
def weth_whale(accounts):
    yield accounts.at("0x57757e3d981446d585af0d9ae4d7df6d64647806", force=True)

@pytest.fixture
def dai_whale(accounts, dai):
    #yield accounts.at("0xF977814e90dA44bFA03b6295A0616a897441aceC", force=True)
    yield accounts.at("0x5d3a536e4d6dbd6114cc1ead35777bab948e3643", force=True)

@pytest.fixture
def yvDAI():
    vault_address = "0xdA816459F1AB5631232FE5e97a05BBBb94970c95"
    yield Contract(vault_address)

@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

@pytest.fixture(autouse=True)
def lib(gov, MakerDaiDelegateLib):
    yield MakerDaiDelegateLib.deploy({"from": gov})

@pytest.fixture
def gov(accounts):
    yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)

@pytest.fixture
def user(accounts):
    yield accounts[0]

@pytest.fixture
def user2(accounts):
    yield accounts[4]

@pytest.fixture
def rewards(accounts):
    yield accounts[1]

@pytest.fixture
def guardian(accounts):
    yield accounts[2]

@pytest.fixture
def management(accounts):
    yield accounts[3]

@pytest.fixture
def strategist(accounts):
    yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

@pytest.fixture
def keeper(accounts):
    yield accounts[5]

@pytest.fixture
def router(unirouter, sushirouter):
    yield unirouter

@pytest.fixture
def sushirouter():
    sushiswap_router = interface.ISwap("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F")
    yield sushiswap_router

@pytest.fixture
def unirouter():
    uniswap_router = interface.ISwap("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")
    yield uniswap_router

@pytest.fixture
def amount(accounts, token, user, token_whale):
    #amount = 50000 * 10 ** token.decimals()
    amount = 500 * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate an exchange address to use it's funds.
    reserve = token_whale
    #reserve = accounts.at("0xF977814e90dA44bFA03b6295A0616a897441aceC", force=True)
    token.transfer(user, amount, {"from": reserve})
    yield amount

@pytest.fixture
def amount2(accounts, token, user2, token_whale):
    #amount = 100000 * 10 ** token.decimals()
    amount = 100 * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate an exchange address to use it's funds.
    #reserve = accounts.at("0xF977814e90dA44bFA03b6295A0616a897441aceC", force=True)
    reserve = token_whale
    token.transfer(user2, amount, {"from": reserve})
    yield amount

@pytest.fixture
def amountBIGTIME(accounts, token, user, token_whale):
    #amount = 200000 * 10 ** token.decimals()
    amount = 200 * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate an exchange address to use it's funds.
    #reserve = accounts.at("0xF977814e90dA44bFA03b6295A0616a897441aceC", force=True)
    reserve = token_whale
    token.transfer(user, amount, {"from": reserve})
    yield amount

@pytest.fixture
def amountBIGTIME2(accounts, token, user2, token_whale):
    #amount = 1000000 * 10 ** token.decimals()
    amount = 100 * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate an exchange address to use it's funds.
    #reserve = accounts.at("0xF977814e90dA44bFA03b6295A0616a897441aceC", force=True)
    reserve = token_whale
    token.transfer(user2, amount, {"from": reserve})
    yield amount

@pytest.fixture
def vault(pm, gov, rewards, guardian, management, token):
    Vault = pm(config["dependencies"][0]).Vault
    vault = guardian.deploy(Vault)
    vault.initialize(token, gov, rewards, "", "", guardian, management)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(management, {"from": gov})
    yield vault
    
@pytest.fixture
def productionVault(wantNr):
    vault_address = [
    "0xdA816459F1AB5631232FE5e97a05BBBb94970c95",  #yvDAI
    "0xa354F35829Ae975e850e23e9615b11Da1B3dC4DE",  #yvUSDC
    "",  #yvstETH
    ""  #yvwstETH
    ]
    yield Contract(vault_address[wantNr])


@pytest.fixture
def osmProxy_want():
    # Allow the strategy to query the OSM proxy
    osm = Contract("0xCF63089A8aD2a9D8BD6Bb8022f3190EB7e1eD0f1")   # Points to ETH/USD
    # osm = interface.IOSMedianizer("0xCF63089A8aD2a9D8BD6Bb8022f3190EB7e1eD0f1")
    yield osm

@pytest.fixture
def osmProxy_yieldBearing():
    # Allow the strategy to query the OSM proxy
    osm = Contract("0xCF63089A8aD2a9D8BD6Bb8022f3190EB7e1eD0f1")
    #osm = interface.IOSMedianizer("0xCF63089A8aD2a9D8BD6Bb8022f3190EB7e1eD0f1")
    yield osm

#@pytest.fixture
#def gemJoinAdapter():
#    gemJoin = Contract("0xF04a5cC80B1E94C69B48f5ee68a08CD2F09A7c3E")  # WETH-C
#    yield gemJoin
    
#This is the collateral adapter, so yieldbearing token, not want token if want != yieldBearing
@pytest.fixture
def gemJoinAdapter(yieldBearingNr):
    gemJoin = [
    "0xbFD445A97e7459b0eBb34cfbd3245750Dba4d7a4",   #0 = GUNIV3DAIUSDC1 0.05%
    "0xA7e4dDde3cBcEf122851A7C8F7A55f23c0Daf335",   #1 = GUNIV3DAIUSDC2 0.01%
    ]
    yield Contract(gemJoin[yieldBearingNr])

@pytest.fixture
def healthCheck(gov):
    healthCheck = Contract("0xDDCea799fF1699e98EDF118e0629A974Df7DF012")
    healthCheck.setProfitLimitRatio(1000, {"from": gov})  #default 100, # 1%
    healthCheck.setlossLimitRatio(100, {"from": gov})  #default 1 # 0.01%
    #healthCheck.setProfitLimitRatio(5000, {"from": gov})  #default 100, # 1%
    #healthCheck.setlossLimitRatio(100, {"from": gov})  #default 1 # 0.01%
    yield healthCheck

@pytest.fixture
def custom_osm(TestCustomOSM, gov):
    yield TestCustomOSM.deploy({"from": gov})

#@pytest.fixture
#def custom_osm(TestCustomOSM, gov):
#    yield TestCustomOSM.deploy({"from": gov})

@pytest.fixture
def basefeeChecker():
    basefee = Contract("0xb5e1CAcB567d98faaDB60a1fD4820720141f064F")
    yield basefee

@pytest.fixture
def maxIL():
    yield 1000e18

@pytest.fixture
def strategy(vault, StrategyChoice, gov, osmProxy_want, osmProxy_yieldBearing, cloner, healthCheck):
    strategy = StrategyChoice.at(cloner.original())
    #healthcheck = healthCheck
    #strategy.setRetainDebtFloorBool(False, {"from": gov})
    strategy.setDoHealthCheck(True, {"from": gov})
    # set a high acceptable max base fee to avoid changing test behavior
    #strategy.setMaxAcceptableBaseFee(1500 * 1e9, {"from": gov})

    vault.addStrategy(strategy, 
        10_000, #debtRatio 
        0,  #minDebtPerHarvest
        2 ** 256 - 1,  #maxDebtPerHarvest
        1_000, #performanceFee = 10% = 1_000
        #5_000, #= 50%, profitLimitRatio, default = 100 = 1%
        #2_500, #= 25% lossLimitRatio, default = 1 == 0.01%  
        {"from": gov}) 

    # Allow the strategy to query the OSM proxy
    #osmProxy_want.setAuthorized(strategy, {"from": gov})
    #osmProxy_yieldBearing.setAuthorized(strategy, {"from": gov})
    yield strategy

@pytest.fixture
def test_strategy(
    TestStrategyChoice,
    strategist,
    vault,
    token,
    yieldBearing,
    gemJoinAdapter,
    osmProxy_want,
    osmProxy_yieldBearing,
    #price_oracle_want_to_eth,
    gov, ilk_yieldBearing, ilk_want, healthCheck
):
    strategy = strategist.deploy(
        TestStrategyChoice,
        vault,
        "Strategy-Maker-lev-GUNIV3DAIUSDC",
        #ilk_want,
        #ilk_yieldBearing,
        #gemJoinAdapter,
      #  osmProxy_want,
      #  osmProxy_yieldBearing,
      #  price_oracle_want_to_eth
    )
    #strategy.setRetainDebtFloorBool(False, {"from": gov})
    strategy.setDoHealthCheck(True, {"from": gov})

    # set a high acceptable max base fee to avoid changing test behavior
    # strategy.setMaxAcceptableBaseFee(1500 * 1e9, {"from": gov})

    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})

    # Allow the strategy to query the OSM proxy
    #osmProxy_want.setAuthorized(strategy, {"from": gov})
    #osmProxy_yieldBearing.setAuthorized(strategy, {"from": gov})
    yield strategy


#@pytest.fixture
#def ilk_WETH_C():
#    ilk = "0x4554482d43000000000000000000000000000000000000000000000000000000"  # WETHC
#    yield ilk

#@pytest.fixture
#def ilk_wstETH():
#    ilk = "0x5753544554482d41000000000000000000000000000000000000000000000000"  # wstETH
#    yield ilk

@pytest.fixture
def ilk_want(wantNr):
    ilk_hashes = [
    "0x4554482d43000000000000000000000000000000000000000000000000000000",   #0 = WETH
    "0x4554482d43000000000000000000000000000000000000000000000000000000",   #1 = WETH
    "0x5753544554482d41000000000000000000000000000000000000000000000000",  #2 = wsteth
    "0x5753544554482d41000000000000000000000000000000000000000000000000"  #3 = wsteth
    ]
    yield ilk_hashes[wantNr]


@pytest.fixture
def ilk_yieldBearing(yieldBearingNr):
    ilk_hashes = [
    "0x47554e49563344414955534443312d4100000000000000000000000000000000",   #0 = GUNIV3DAIUSDC1 0.05%
    "0x47554e49563344414955534443322d4100000000000000000000000000000000",   #1 = GUNIV3DAIUSDC2 0.01%
    ]
    yield ilk_hashes[yieldBearingNr]

@pytest.fixture(scope="session")
def RELATIVE_APPROX():
    yield 1e-4

@pytest.fixture(scope="session")
def RELATIVE_APPROX_LOSSY():
    yield 1e-2

@pytest.fixture(scope="session")
def RELATIVE_APPROX_ROUGH():
    yield 1e-1

# Obtaining the bytes32 ilk (verify its validity before using)
# >>> ilk = ""
# >>> for i in "YFI-A":
# ...   ilk += hex(ord(i)).replace("0x","")
# ...
# >>> ilk += "0"*(64-len(ilk))
# >>>
# >>> ilk
# '5946492d41000000000000000000000000000000000000000000000000000000'

@pytest.fixture
def cloner(
    strategist,
    vault,
    token,
    yieldBearing,
    gemJoinAdapter,
    osmProxy_want,
    osmProxy_yieldBearing,
   # price_oracle_want_to_eth,
    MakerDaiDelegateClonerChoice,
    ilk_yieldBearing, ilk_want
):
    cloner = strategist.deploy(
        MakerDaiDelegateClonerChoice,
        vault,
        "Strategy-Maker-lev-GUNIV3DAIUSDC",
        #ilk_want,
        #ilk_yieldBearing,
        #gemJoinAdapter,
     #   osmProxy_want,
     #   osmProxy_yieldBearing,
     #   price_oracle_want_to_eth,
    )
    yield cloner
