from IBAPI import Connection
from contracts import CryptoContract
from strategies import Crypto, CurrencyStrategy
from datetime import datetime
import time as t
import pytz


c = Connection(live=False)  # For TWS connection
app = c.app

currContract = app.currency_contract('EUR', 'USD', secType='CFD')
currContract.localSymbol = 'EUR.USD'

fut_contract = app.Future_contract('GF', 'GFH3', 50000, exchange='CME', secType='CFD')


app.idMap[1] = currContract.symbol
app.barData[1] = []
app.reqHistoricalData(1, currContract, '', '4 D', str(30) + ' mins', 'MIDPOINT', 0, 1, False, [])

t.sleep(5)
print(app.barDF[1])

import pytz
from datetime import datetime, date, time, timedelta

# eth_contract = CryptoContract('ETH', multiplier=50, exchange='CME', first_trade=time(2, 0),
#                                   first_bar=time(1, 30),
#                                   last_trade=time(15, 30), last_bar=time(15, 0))
# crypto_strategy = Crypto(account='U11095454', notional=65000, order_type='Adaptive', startTime=time(2, 0),
#                              endTime=time(15, 30), day_algo_time=20, barType='AGGTRADES')
#
# curr_endTime = datetime.now().replace(hour=16, minute=15, second=0, microsecond=0) + timedelta(days=1)
# curr_startTime = datetime.now().replace(hour=16, minute=30, second=0, microsecond=0)
# curr_strategy = CurrencyStrategy(account='U11095454', notional=693000, order_type='Arrival',
#                                      day_algo_time=10, startTime=curr_startTime, endTime=curr_endTime,
#                                      barType='MIDPOINT')
#
# print(curr_strategy.end_day())


