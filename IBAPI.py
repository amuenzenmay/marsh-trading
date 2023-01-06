import sys
import time as t

import pandas as pd

# sys.path.insert(0, r'C:\Augie Files\TWS API\TWS API\source\pythonclient')
# Augie had me locate this folder path

from datetime import date, time

import pytz
from ibapi.client import EClient
from ibapi.common import TickerId, OrderId
from ibapi.contract import Contract
from ibapi.tag_value import TagValue
import threading

from ibapi.order import Order
from ibapi.wrapper import EWrapper

import util


class Connection:
    def __init__(self, **kwargs):
        self.live = kwargs.get("live", True)
        self.app = IBapi()
        self.start_connection()

    def run_loop(self):
        self.app.run()

    def start_connection(self):
        self.app.nextorderId = None
        if self.live:
            port = 7496
        else:
            port = 7497
        self.app.connect('127.0.0.1', port, 123)

        # Start the socket in a thread
        api_thread = threading.Thread(target=self.run_loop)  # set to daemon=True
        api_thread.start()

        # Check if the API is connected via orderid
        while True:
            if isinstance(self.app.nextorderId, int):
                print('connected\n')
                break
            else:
                print('waiting for connection...')
                t.sleep(1)


class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.nextorderId = None
        self.reqid = 0
        self.idMap = {}  # ID to Symbol
        self.barData = {}  # ID to unformated data
        self.barDF = {}  # ID to DataFrame
        self.dataTimes = {}
        self.timezone = {}
        self.volume_request = True
        self.timezones = {}  # 'America/Chicago'
        self.positions = pd.DataFrame([], columns=['Position', 'Average Cost'])
        self.tws_pnl = pd.DataFrame([], columns=['Daily', 'Realized', 'Unrealized'])
        self.single_pnl = pd.DataFrame([], columns=['Daily', 'Unrealized', 'Realized', 'Value'])
        self.open_orders = {}

    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        super().error(reqId, errorCode, errorString)
        if errorCode == 399:
            self.cancelOrder(reqId)
        if errorCode == 102:
            pass
        if errorCode == 200:
            print('ERROR 200 for {}'.format(self.idMap[reqId]))
        if errorCode == 504:
            print('TWS CONNECTION LOST. RESTART ASAP')

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextorderId = orderId

    def Stock_contract(self, symbol, secType='STK', exchange='SMART', currency='USD', con_id=0,
                       data_range=(None, None)):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = secType
        contract.exchange = exchange
        contract.currency = currency
        contract.localSymbol = symbol
        contract.id = con_id
        contract.data_range = data_range
        self.dataTimes[symbol] = data_range
        if contract.symbol == 'SPCE':
            contract.primaryExchange = 'NYSE'
        return contract

    def Future_contract(self, symbol, localSymbol, multiplier, secType='FUT', exchange='GLOBEX',
                        currency='USD', con_id=0, data_range=(None, None)):
        contract = Contract()
        contract.symbol = symbol
        contract.localSymbol = localSymbol
        contract.multiplier = multiplier
        contract.secType = secType
        contract.exchange = exchange
        contract.currency = currency
        contract.id = con_id
        contract.data_range = data_range
        self.dataTimes[symbol] = data_range
        return contract

    def crypto_contract(self, symbol, secType='CRYPTO', exchange='PAXOS', currency='USD', con_id=0,
                       data_range=(None, None)):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = secType
        contract.exchange = exchange
        contract.currency = currency
        contract.id = con_id
        contract.data_range = data_range
        self.dataTimes[symbol] = data_range

        return contract

    def nextReqId(self):
        """Returns a unique ID for data requests."""
        self.reqid += 1
        return self.reqid

    def startEndBars(self, reqId: int):
        try:
            symbol = self.idMap[reqId]
            if symbol in self.dataTimes.keys():
                if None in self.dataTimes[symbol]:
                    return None
                return self.dataTimes[symbol]
            else:
                return None
        except KeyError:
            return None

    # def historicalData(self, reqId, bar):
    #     print("Date: ", bar.date, "\tClose: ", bar.close)

    def historicalData(self, reqId, bar):
        barDate = pd.to_datetime(bar.date)
        barDate = barDate.to_pydatetime().astimezone(tz=self.timezones[reqId])
        # self.barData[reqId].append([bar.date, bar.close])
        if self.startEndBars(reqId) is None or self.volume_request:
            self.barData[reqId].append([bar.date, bar.close, bar.volume])
        else:
            times = self.startEndBars(reqId)
            startBar = times[0]
            endBar = times[1]  # End bar time is included in the dataframes
            if barDate.date() == date(2021, 11, 25):
                endBar = time(hour=12, minute=0)  # This bar time DOES get included
            if startBar <= barDate.time() <= endBar:
                self.barData[reqId].append([barDate, bar.close, bar.volume])

    def historicalDataUpdate(self, reqId, bar):
        self.barDF[reqId].loc[pd.to_datetime(bar.date)] = bar.close
        self.barDF[reqId]['PctChng'] = self.barDF[reqId]['Close'].pct_change()

    # self.barDF[reqId]['Close'].rolling(10).mean()

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        # print("HistoricalDataEnd. ReqId:", reqId, "from", start, "to", end)
        try:
            self.barDF[reqId] = pd.DataFrame(data=self.barData[reqId], columns=['Date', 'Close', 'Volume'])
            self.barDF[reqId]['Date'] = pd.to_datetime(self.barDF[reqId]['Date'])
            self.barDF[reqId].set_index('Date', inplace=True)
            self.barDF[reqId]['PctChng'] = self.barDF[reqId]['Close'].pct_change()
        except IndexError as e:
            util.exception_alert(e, self.idMap[reqId])
            self.barDF[reqId] = pd.DataFrame(data=self.barData[reqId], columns=['Date', 'Close'])
            self.barDF[reqId]['Date'] = pd.to_datetime(self.barDF[reqId]['Date'])

    def position(self, account, contract, pos, avgCost):
        index = str(contract.localSymbol)
        self.positions.loc[index] = pos, avgCost

    def pnl(self, reqId: int, dailyPnL: float, unrealizedPnL: float, realizedPnL: float):
        self.tws_pnl.loc[reqId] = dailyPnL, realizedPnL, unrealizedPnL

    def pnlSingle(self, reqId: int, pos: int, dailyPnL: float, unrealizedPnL: float, realizedPnL: float, value: float):
        try:
            self.single_pnl.loc[self.idMap[reqId]] = dailyPnL, unrealizedPnL, realizedPnL, value
        except IndexError:
            self.single_pnl.loc[reqId] = dailyPnL, unrealizedPnL, realizedPnL, value

    @staticmethod
    def create_order(direction, qty, orderType, transmit=True, lmtPrice=sys.float_info.max):
        order = Order()
        order.action = direction
        order.totalQuantity = qty
        order.orderType = orderType
        order.transmit = transmit
        order.lmtPrice = lmtPrice
        order.eTradeOnly = False
        order.firmQuoteOnly = False
        return order

    def fill_arrival_params(self, baseOrder, end):
        baseOrder.algoStrategy = "ArrivalPx"
        baseOrder.algoParams = []
        baseOrder.algoParams.append(TagValue("maxPctVol", '0.01'))
        baseOrder.algoParams.append(TagValue("riskAversion", "Aggressive"))

        baseOrder.algoParams.append(TagValue("endTime", end))
        baseOrder.algoParams.append(TagValue("forceCompletion", '1'))
        baseOrder.algoParams.append(TagValue("allowPastEndTime", '0'))

    def fill_twap_params(self, baseOrder, end):
        baseOrder.algoStrategy = "Twap"
        baseOrder.algoParams = []
        baseOrder.algoParams.append(TagValue("strategyType", 'Midpoint'))
        baseOrder.algoParams.append(TagValue("endTime", end))
        baseOrder.algoParams.append(TagValue("allowPastEndTime", '0'))

    def orderStatus(self, orderId:OrderId , status:str, filled:float,
                    remaining:float, avgFillPrice:float, permId:int,
                    parentId:int, lastFillPrice:float, clientId:int,
                    whyHeld:str, mktCapPrice: float):
        self.open_orders[orderId] = remaining
