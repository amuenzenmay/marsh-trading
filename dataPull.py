import pytz
from ibapi import server_versions
server_versions.MAX_CLIENT_VER = 163
from strategies import Crypto
from contracts import CryptContract, Contract
from IBAPI import Connection, IBapi
from data import Data
import time as t



c = Connection(live=False)  # For TWS connection
app = c.app

# eth_contract = CryptContract("ETH")
# ib_eth_contract = app.crypto_contract("ETH")
# d = Data(eth_contract, app=app)
# d.requestDataIBAPI(ib_eth_contract, 30, eth_contract, type='MIDPOINT')

# app.barData[1] = []
# app.timezones[1] = pytz.timezone('America/Chicago')
# app.reqHistoricalData(1, eth_contract, '', '4 D', '30 mins', 'MIDPOINT', 0, 1, False, [])

netflix = Contract("NFLX")
stk_contract = app.Stock_contract('NFLX')
d = Data(netflix, app=app)
d.requestDataIBAPI(stk_contract, 30, netflix, type='MIDPOINT')
# app.reqHistoricalData(1, stk_contract, '', '1 D', '30 mins', 'TRADES', 0, 1, False, [])




t.sleep(5)

