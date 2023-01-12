from IBAPI import Connection
from contracts import CryptContract
from strategies import Crypto
from datetime import datetime
import time as t
import pytz


c = Connection(live=False)  # For TWS connection
app = c.app

eth_contract = app.crypto_contract("ETH")
app.idMap[1] = eth_contract.symbol
app.barData[1] = []
app.reqHistoricalData(1, eth_contract, '', '4 D', str(30) + ' mins', 'AGGTRADES', 0, 1, False, [])

t.sleep(5)
print(app.barDF[1])

