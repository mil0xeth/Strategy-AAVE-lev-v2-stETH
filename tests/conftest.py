import pytest
from brownie import config, convert, interface, Contract
##################
#################
#Decide on Strategy Contract
@pytest.fixture(autouse=True)
def StrategyChoice(Strategy):    
    choice = Strategy
    yield choice
@pytest.fixture(autouse=True)
def TestStrategyChoice(TestStrategy):    
    choice = TestStrategy #TestStrategy, NewTestStrategy
    yield choice
@pytest.fixture(autouse=True)
def MarketLibClonerChoice(MarketLibCloner):    
    choice = MarketLibCloner 
    yield choice
#######################################################
#Decide on wantToken = token
@pytest.fixture(autouse=True)
def wantNr():    
    wantNr = 0 #Currently: 
    #0 = WETH,   1 = stETH,   2 = wstETH 
    yield wantNr
#######################################################
#Decide on yieldBearing = collateral Token on Money Market
@pytest.fixture(autouse=True)
def yieldBearingNr():    
    yieldBearingNr = 0
    # 0 = stETH, 1 =    
    yield yieldBearingNr
#######################################################
@pytest.fixture
def token(weth, steth, wsteth, wantNr):   
    #signifies want token given by wantNr
    token_address = [
    weth,   #0 = ETH
    steth,  #1 = steth
    wsteth  #2 = wsteth
    ]
    yield token_address[wantNr]

@pytest.fixture
def yieldBearing(weth, steth, wsteth, yieldBearingNr):   
    #signifies want token given by wantNr
    yieldBearingToken_address = [
    steth,  #0 = steth
    wsteth  #1 = wsteth
    ]
    yield yieldBearingToken_address[yieldBearingNr]


@pytest.fixture
def borrow_token(weth):
    yield weth

@pytest.fixture
def borrow_whale(weth_whale):
    yield weth_whale
 
#chainlinkWantToETHPriceFeed
@pytest.fixture
def price_oracle_want_to_eth(wantNr):
    oracle_address = [
    "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419",  #ETH/USD
    "0x86392dC19c0b719886221c78AB11eb8Cf5c52812",  #stETH/USD
    "0x86392dC19c0b719886221c78AB11eb8Cf5c52812",  #stETH/USD
    ]
    yield interface.AggregatorInterface(oracle_address[wantNr])
#############################################################

@pytest.fixture
def weth():
    token_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2" #WETH
    yield Contract(token_address)   

@pytest.fixture
def steth(interface):
    #weth
    yield interface.ERC20('0xae7ab96520de3a18e5e111b5eaab095312d7fe84')

@pytest.fixture
def wsteth(interface):
    contract = interface.IWstETH("0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0")
    yield contract

@pytest.fixture
def weth_amount(user, weth):
    weth_amout = 10 ** weth.decimals()
    user.transfer(weth, weth_amout)
    yield weth_amout

@pytest.fixture
def weth_amout(user, weth):
    weth_amout = 10 ** weth.decimals()
    user.transfer(weth, weth_amout)
    yield weth_amout

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

@pytest.fixture
def wsteth_whale(accounts):
    yield accounts.at("0x629e7Da20197a5429d30da36E77d06CdF796b71A", force=True)

@pytest.fixture
def token_whale(accounts, wantNr, dai_whale, weth_whale):
    #eth_whale = accounts.at("0xda9dfa130df4de4673b89022ee50ff26f6ea73cf", force=True)
    #token_whale_address = [
    #"0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8",   #0 = ETH
    #"0xe78388b4ce79068e89bf8aa7f218ef6b9ab0e9d0",   #1 = WETH  0x030bA81f1c18d280636F32af80b9AAd02Cf0854e, 0x57757e3d981446d585af0d9ae4d7df6d64647806  
    #"0x2faf487a4414fe77e2327f0bf4ae2a264a776ad2",  #2 = steth
    #"0x62e41b1185023bcc14a465d350e1dde341557925"  #3 = wsteth
    #]
    #token_whale_account = accounts.at(token_whale_address[wantNr], force=True) 
    #eth_whale.transfer(token_whale_account, "100000 ether")
    yield weth_whale

@pytest.fixture
def token_whale_BIG(accounts, wantNr, dai_whale, weth_whale):
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
    yield weth_whale

@pytest.fixture
def steth_holder(accounts, steth):
    #big binance7 wallet
    #acc = accounts.at('0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8', force=True)
    #EthLidoPCVDeposit
    acc = accounts.at('0xAc38Ee05C0204A1E119C625d0a560D6731478880', force=True)
    assert steth.balanceOf(acc)  > 0
    yield acc

@pytest.fixture
def yieldBearing_whale(accounts, steth):
    #big binance7 wallet
    #acc = accounts.at('0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8', force=True)
    #EthLidoPCVDeposit
    acc = accounts.at('0x7153d2ef9f14a6b1bb2ed822745f65e58d836c3f', force=True)
    assert steth.balanceOf(acc)  > 0
    yield acc

@pytest.fixture
def steth_whale(accounts, steth):
    #big binance7 wallet
    #acc = accounts.at('0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8', force=True)
    #EthLidoPCVDeposit
    acc = accounts.at('0x7153d2ef9f14a6b1bb2ed822745f65e58d836c3f', force=True)
    assert steth.balanceOf(acc)  > 0
    yield acc


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
def lib(gov, MarketLib):
    yield MarketLib.deploy({"from": gov})

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
    "0xa258C4606Ca8206D8aA700cE2143D7db854D168c",  #yvWETH
    "0xa258C4606Ca8206D8aA700cE2143D7db854D168c",  #yvWETH
    "",  #yvstETH
    ""  #yvwstETH
    ]
    yield Contract(vault_address[wantNr])


@pytest.fixture
def healthCheck(gov):
    healthCheck = Contract("0xDDCea799fF1699e98EDF118e0629A974Df7DF012")
    healthCheck.setProfitLimitRatio(1000, {"from": gov})  #default 100, # 1%
    healthCheck.setlossLimitRatio(100, {"from": gov})  #default 1 # 0.01%
    #healthCheck.setProfitLimitRatio(5000, {"from": gov})  #default 100, # 1%
    #healthCheck.setlossLimitRatio(100, {"from": gov})  #default 1 # 0.01%
    yield healthCheck

@pytest.fixture
def basefeeChecker():
    basefee = Contract("0xb5e1CAcB567d98faaDB60a1fD4820720141f064F")
    yield basefee

@pytest.fixture
def maxIL():
    yield 1000e18

@pytest.fixture
def strategy(vault, StrategyChoice, gov, cloner, healthCheck):
    strategy = StrategyChoice.at(cloner.original())
    #healthcheck = healthCheck
    #strategy.setRetainDebtFloorBool(False, {"from": gov})
    strategy.setDoHealthCheck(False, {"from": gov})
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
    #price_oracle_want_to_eth,
    gov, healthCheck
):
    strategy = strategist.deploy(
        TestStrategyChoice,
        vault,
        "Strategy-AAVE-lev-v2-stETH",
        #ilk_want,
        #ilk_yieldBearing,
        #gemJoinAdapter,
      #  osmProxy_want,
      #  osmProxy_yieldBearing,
      #  price_oracle_want_to_eth
    )
    strategy.setDoHealthCheck(False, {"from": gov})

    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})

    yield strategy

@pytest.fixture(scope="session")
def RELATIVE_APPROX():
    yield 1e-2

@pytest.fixture(scope="session")
def RELATIVE_APPROX_LOSSY():
    yield 1e-2

@pytest.fixture(scope="session")
def RELATIVE_APPROX_ROUGH():
    yield 1e-1

@pytest.fixture
def cloner(
    strategist,
    vault,
    token,
    yieldBearing,
   # price_oracle_want_to_eth,
    MarketLibClonerChoice,
):
    cloner = strategist.deploy(
        MarketLibClonerChoice,
        vault,
        "Strategy-AAVE-lev-v2-stETH",
        #ilk_want,
        #ilk_yieldBearing,
        #gemJoinAdapter,
     #   osmProxy_want,
     #   osmProxy_yieldBearing,
     #   price_oracle_want_to_eth,
    )
    yield cloner
