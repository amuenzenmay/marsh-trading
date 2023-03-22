from IBAPI import Connection
from contracts import CryptoContract
from strategies import Crypto, CurrencyStrategy
from datetime import datetime, time
import time as t
import pytz
import pandas as pd
from IBAPI import IBapi
from strategies import CommodityStrategy
from contracts import CommodityContract


# c = Connection(live=False)  # For TWS connection
# app = c.app
# pd.set_option('display.max_rows', None)
#
# eth_contract = CryptoContract('ETH', multiplier=50, exchange='CME',
#                               first_trade=datetime.now().replace(hour=2, minute=0, second=0, microsecond=0),
#                               first_bar=time(1, 30),
#                               last_trade=datetime.now().replace(hour=15, minute=30, second=0, microsecond=0),
#                               last_bar=time(15, 0))
#
# con = app.crypto_contract("ETH", con_id=eth_contract.data_id, data_range=(eth_contract.firstBar, eth_contract.lastBar))
#
# app.idMap[1] = con.symbol
# app.barData[1] = []
# app.reqHistoricalData(1, con, '', '5 D', str(30) + ' mins', 'MIDPOINT', 0, 1, False, [])
#
# t.sleep(5)
# print(app.barDF[1])

app = IBapi()
ebm = CommodityContract('EBM', first_trade=datetime.now().replace(hour=5, minute=0, second=0, microsecond=0),
                          last_trade=datetime.now().replace(hour=12, minute=28, second=0, microsecond=0),
                          first_bar=time(4, 45), last_bar=time(hour=12, minute=0),
                          multiplier=50, months=[3, 5, 9, 12], exchange='MATIF', currency='EUR', trade_amount=1)
ebm.set_ticker("EBMK3")

sb = CommodityContract('SB', first_trade=datetime.now().replace(hour=7, minute=30, second=0, microsecond=0),
                          last_trade=datetime.now().replace(hour=11, minute=58, second=0, microsecond=0),
                          first_bar=time(7, 0), last_bar=time(hour=11, minute=30),
                          multiplier=112000, months=[3, 5, 7, 10], exchange='NYBOT', trade_amount=1)
sb.set_ticker("SBK3")

com_strategy = CommodityStrategy(app=app, account='U11095454', order_type='Adaptive',
                                     day_algo_time=10)
com_strategy.set_contracts([ebm, sb])

print("Done")
