from IBAPI import Connection
from contracts import CryptoContract
from strategies import Crypto, CurrencyStrategy
from datetime import datetime, time
import time as t
import pytz
import pandas as pd


c = Connection(live=False)  # For TWS connection
app = c.app
pd.set_option('display.max_rows', None)

eth_contract = CryptoContract('ETH', multiplier=50, exchange='CME',
                              first_trade=datetime.now().replace(hour=2, minute=0, second=0, microsecond=0),
                              first_bar=time(1, 30),
                              last_trade=datetime.now().replace(hour=15, minute=30, second=0, microsecond=0),
                              last_bar=time(15, 0))

con = app.crypto_contract("ETH", con_id=eth_contract.data_id, data_range=(eth_contract.firstBar, eth_contract.lastBar))

app.idMap[1] = con.symbol
app.barData[1] = []
app.reqHistoricalData(1, con, '', '5 D', str(30) + ' mins', 'MIDPOINT', 0, 1, False, [])

t.sleep(5)
print(app.barDF[1])

