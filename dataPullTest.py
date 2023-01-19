from IBAPI import Connection
from contracts import CryptoContract
from strategies import Crypto
from datetime import datetime
import time as t
import pytz


c = Connection(live=False)  # For TWS connection
app = c.app

# currContract = app.currency_contract('EUR', 'USD')
# currContract.localSymbol = 'EUR.USD'

fut_contract = app.Future_contract('GF', 'GFH3', 50000, exchange='CME')


app.idMap[1] = fut_contract.symbol
app.barData[1] = []
app.reqHistoricalData(1, fut_contract, '', '4 D', str(30) + ' mins', 'MIDPOINT', 0, 1, False, [])

t.sleep(5)
print(app.barDF[1])

