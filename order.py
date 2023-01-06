import mysql.connector

import util
import win32com.client
from data import *
import random
import time as t
from datetime import datetime, time, timedelta

username = 'rzm.drasmussen'
password = 'KfW983#'
groupCode = random.randint(0, 1000)
riskId = random.randint(0, 1000)


class Order:

    def __init__(self, quantity, side, contract, account='DEMO', limit_time=60, **kwargs):
        self.size = int(abs(quantity))
        self.side = side
        self.contract = contract
        # self.destination = exchange  # 'DEMO DMA'
        self.account = account
        self.limit_time = limit_time
        # self.set_limit_time(contract, limit_time)
        self.client_data = self.random_client_data_key()
        self.expected = self.expected_pos()
        self.app = kwargs.get('app', None)
        self.dma_destination = kwargs.get('dma_dest', '')
        self.algo_destination = kwargs.get('algo_dest', '')
        self.start_time = kwargs.get('start', None)  # Must be in "HHMMSS" format
        self.end_time = kwargs.get('end', None)  # Must be in "HHMMSS" format
        self.limit_price = kwargs.get('limit_price', self.contract.lastClose)
        self.day_algo_time = kwargs.get('day_algo_time', 20)
        self.last_algo_time = kwargs.get('last_algo_time', 1)
        self.strategy = kwargs.get('strategy', '')
        self.vix_short_limit = False
        self.algo_time = self.set_algo_time()
        self.timezone = kwargs.get('timezone', pytz.timezone('America/Chicago'))
        self.set_limit_time()

    def set_limit_time(self):
        """Change the limit time for the Vix five-minute strategy if it is past 3pm CT"""
        if self.strategy == 'Vix5' and \
                datetime.now(tz=self.timezone).replace(second=0, microsecond=0).time() >= time(15, 0) and \
                self.contract.allowInceptions:
            self.limit_time = 30
            self.vix_short_limit = True

    @property
    def next_ids(self):
        global groupCode, riskId
        groupCode += 1
        riskId += 1
        return groupCode, riskId

    def set_algo_time(self):
        if self.contract.shortAlgo and not self.contract.working_bars:
            # NOT the last trade of the day, but shorter duration is required leading into the last trade
            # Ex: It is 13:00, last trade should be 13:12, but normal duration of 20 minutes would be too long.
            if self.contract.ticker[:2] in ['ZC', 'ZS', 'ZW', 'ZL', 'ZM']:
                return 13  # 13 minute duration for the grain commodities at 13:00
            elif self.contract.ticker[:2] in ['CT']:
                return 15  # 15 minute duration for CT at the 13:00 bar
            return 9  # If a 9-minute duration is submitted, the program logic is off
        elif self.contract.shortAlgo:
            if self.contract.ticker[:2] in ['HE', 'LE', 'GF']:
                return 3
            elif self.contract.ticker[:2] in ['ZC', 'ZS', 'ZW', 'ZL', 'ZM']:
                return 4
            elif self.contract.ticker[:2] in ['KC', 'CT', 'SB']:
                return 2
            elif self.contract.ticker[:2] in ['GC', 'PL', 'SI']:
                return 10
            return self.last_algo_time  # If a 1-minute duration is submitted, the program logic is off
        else:
            return self.day_algo_time

    def expected_pos(self):
        if self.side == 'Sell':
            expectation = self.contract.position - abs(self.size)
        elif self.side == 'Buy':
            expectation = self.contract.position + abs(self.size)
        else:
            expectation = 0
        return expectation

    def random_client_data_key(self):
        """Returns a random string for order identification

        :return String
        """
        values = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'
        return ''.join(random.choice(values) for i in range(8))

    def limit_order_redi(self):
        """Limit order that runs for a specified number of seconds. At the end of that time period, the order will
        be canceled, position will be checked, and any remaining shares left unfilled will be acquired through a
        market order.

        :return boolean
        """
        o = win32com.client.Dispatch("REDI.ORDER", pythoncom.CoInitialize())
        o.Side = str(self.side)
        o.symbol = self.contract.ticker  # "SBUX"
        o.Exchange = self.dma_destination
        o.PriceType = 'Limit'
        o.Price = str(self.limit_price)
        o.TIF = 'Day'
        o.Account = self.account
        o.Ticket = 'Bypass'
        o.Quantity = str(self.size)
        o.Warning = False
        o.ClientData = self.client_data

        # TODO Log order submission
        msg = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_VARIANT, None)
        result = o.Submit(msg)

        if result:  # 'True' if order submission was successful; otherwise 'False'
            self.monitor_order_redi()
        else:
            print(msg)  # message from sumbit

    def monitor_order_redi(self):
        """Waits the desired amount of time before canceling a limit order. Then checks current position to determine
        how many shares from the original order were left unfilled. If any portion of the order did not fill, submits
        a market order for the remaining shares.
        """
        t.sleep(self.limit_time)
        o = win32com.client.Dispatch("REDI.APPLICATION")
        msg = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_VARIANT, None)
        o.CancelOrder(self.client_data, msg)

        d = Data(self.contract)
        d.request_position()

        if self.contract.position != self.expected:
            self.size = abs(self.contract.position - self.expected)
            # If Vix Five limit unfilled at or after 15:00 CT, do not replace the order, and turn off inceptions
            if self.vix_short_limit:
                self.contract.allowInceptions = False
            elif 'VX' in self.contract.ticker:
                self.IS_redi()
            else:
                self.switch_market_order_redi()

    def switch_market_order_redi(self):
        switch_message = self.contract.ticker + 'switch limit to market'
        print(switch_message)
        o = win32com.client.Dispatch("REDI.ORDER", pythoncom.CoInitialize())
        o.Side = str(self.side)
        o.symbol = self.contract.ticker  # "SBUX"
        o.Exchange = self.dma_destination
        o.PriceType = 'Market'
        o.TIF = 'Day'
        o.Account = self.account
        o.Ticket = 'Bypass'
        o.Quantity = str(self.size)
        o.Warning = False

        # TODO Log order submission
        msg = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_VARIANT, None)
        result = o.Submit(msg)

        if not result:  # 'True' if order submission was successful; otherwise 'False'
            print(msg)  # message from sumbit

    def market_order_redi(self):
        # message = self.contract.ticker + 'SUBMITTING A MARKET ORDER'
        # print(message)
        o = win32com.client.Dispatch("REDI.ORDER", pythoncom.CoInitialize())
        o.Side = str(self.side)
        o.symbol = self.contract.ticker  # "SBUX"
        o.Exchange = self.dma_destination
        o.PriceType = 'Market'
        o.TIF = 'Day'
        o.Account = self.account
        o.Ticket = 'Bypass'
        o.Quantity = str(self.size)
        o.Warning = False

        # TODO Log order submission
        msg = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_VARIANT, None)
        result = o.Submit(msg)

        if not result:  # 'True' if order submission was successful; otherwise 'False'
            print(msg,
                  '\n{}\t{}\t{}'.format(self.contract.ticker, self.dma_destination,
                                        self.account))  # message from sumbit

    def TWAP_redi(self):
        price_type = 'TWAP_redi ' + self.algo_destination.split()[0]
        curr_time = datetime.now()
        start_time = datetime.now().strftime("%H:%M:%S")
        end_time = datetime.now() + timedelta(minutes=self.algo_time)
        end_time = end_time.strftime("%H:%M:%S")

        o = win32com.client.Dispatch("REDI.ORDER")
        o.Side = str(self.side)
        o.symbol = self.contract.ticker  # "SBUX"
        o.Exchange = self.algo_destination  # 'GSFF ALGOS', 'GSCE Algo'
        o.PriceType = price_type
        o.TIF = 'Day'
        o.Account = self.account
        o.Ticket = 'Bypass'
        o.Quantity = str(self.size)
        o.Warning = False
        o.SetNewVariable("(MB) Start Time", str(start_time))
        o.SetNewVariable("(MB) End Time", str(end_time))
        # o.SetNewVariable("(MB) Execution Style", "Normal")

        # TODO Log order submission
        msg = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_VARIANT, None)
        result = o.Submit(msg)

        if not result:  # 'True' if order submission was successful; otherwise 'False'
            print(msg)  # message from sumbit

    def VWAP_redi(self):
        start_time = datetime.now().strftime("%H:%M:%S")
        end_time = datetime.now() + timedelta(minutes=self.algo_time)
        end_time = end_time.strftime("%H:%M:%S")

        o = win32com.client.Dispatch("REDI.ORDER")
        o.Side = str(self.side)
        o.symbol = self.contract.ticker  # "SBUX"
        o.Exchange = self.algo_destination
        o.PriceType = 'VWAP_redi ' + self.algo_destination.split()[0]
        o.TIF = 'Day'
        o.Account = self.account
        o.Ticket = 'Bypass'
        o.Quantity = str(self.size)
        o.Warning = False
        o.SetNewVariable("(MB) Start Time", str(start_time))
        o.SetNewVariable("(MB) End Time", str(end_time))

        msg = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_VARIANT, None)
        result = o.Submit(msg)
        if not result:  # 'True' if order submission was successful; otherwise 'False'
            print(msg)  # message from sumbit

    def IS_redi(self):
        start_time = datetime.now().strftime("%H:%M:%S")
        end_time = datetime.now() + timedelta(minutes=self.algo_time)
        end_time = end_time.strftime("%H:%M:%S")

        o = win32com.client.Dispatch("REDI.ORDER")
        o.Side = str(self.side)
        o.symbol = self.contract.ticker  # "SBUX"
        o.Exchange = self.algo_destination
        o.PriceType = 'IS_redi ' + self.algo_destination.split()[0]
        o.TIF = 'Day'
        o.Account = self.account
        o.Ticket = 'Bypass'
        o.Quantity = str(self.size)
        o.Warning = False
        o.SetNewVariable("(MB) Start Time", str(start_time))
        o.SetNewVariable("(MB) End Time", str(end_time))

        msg = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_VARIANT, None)
        result = o.Submit(msg)
        if not result:  # 'True' if order submission was successful; otherwise 'False'
            print(msg)  # message from sumbit

    def cancel_redi(self):
        util.raiseNotDefined()

    def modify(self):
        util.raiseNotDefined()

    def srse_market(self):
        stk_market_order = "REPLACE INTO srtrade.msgstkordergateway(ticker_at, ticker_ts, ticker_tk, accnt, " \
                           "orderSide, groupingCode, spdrActionType, orderSize, timeInForce, parentOrderHandling,  " \
                           "parentBalanceHandling, orderLimitType, takeLimitClass, makeLimitClass, riskGroupId, " \
                           "traderName, CHECKSUM) VALUES ('EQT','NMS','{ticker}','{account}', '{action}',  " \
                           "{group_code}, 'AddReplace',  {size}, 'GTD', 'ActiveTaker', 'None', 'market','simple'," \
                           "'simple', {risk_id},'{trader_name}', 13); "
        group, risk = self.next_ids
        connection = mysql.connector.connect(host='198.102.4.55', port=3307, database='srtrade',
                                             user=username, password=password)
        cursor = connection.cursor()
        cursor.execute(stk_market_order.format(trader_name=username, account=self.account,
                                               ticker=self.contract.ticker, action=self.side.upper(), size=self.size,
                                               group_code=group, risk_id=risk))

    def srse_limit(self):
        util.raiseNotDefined()

    def srse_vwap(self):
        util.raiseNotDefined()

    def srse_is(self):
        util.raiseNotDefined()

    def srse_twap(self):
        twap_order = "REPLACE INTO msgstkordergateway(accnt,spdractiontype,groupingcode,riskgroupid," \
                     "timeinforce,ticker_at,ticker_ts,spdrStageType,ticker_tk,orderside,ordersize,progressrule," \
                     "twapslicecnt,orderduration,orderactivesize,parentorderhandling,parentbalancehandling," \
                     "takelimitclass,makelimitclass,orderlimitType,tradername,CHECKSUM) " \
                     "VALUES ('{account}','addreplace',{group_code},{risk_id},'DAY','EQT','NMS','none','{ticker}'," \
                     "'{action}',{size1},'TWAP_redi',20,{seconds},{size2},'activetaker','none','simple','simple'," \
                     "'market', '{trader_name}',13);"
        seconds = self.algo_time * 60  # Minutes to seconds
        group, risk = self.next_ids
        connection = mysql.connector.connect(host='198.102.4.55', port=3307, database='srtrade',
                                             user=username, password=password)
        cursor = connection.cursor()
        cursor.execute(twap_order.format(trader_name=username, account=self.account,
                                         group_code=group,
                                         risk_id=risk, ticker=self.contract.ticker,
                                         action=self.side.upper(),
                                         size1=self.size, size2=self.size, seconds=seconds))

    def market_order_ib(self):
        order = self.app.create_order(self.side, self.size, 'MKT')
        self.app.nextorderId += 1
        self.app.placeOrder(self.app.nextorderId, self.contract.trade_contract, order)
        # time.sleep(2)

    def limit_order_ib(self):
        order = self.app.create_order(self.side, self.size, 'LMT', lmtPrice=self.limit_price)
        self.app.nextorderId += 1
        order_id = self.app.nextorderId
        self.app.placeOrder(order_id, self.contract.trade_contract, order)
        # # self.monitor_order_ib()

    def arrival_price_ib(self):
        endtime = (datetime.now() + timedelta(minutes=self.algo_time)).replace(second=0, microsecond=0).strftime("%H:%M:%S") + " America/Chicago"
        order = self.app.create_order(self.side, self.size, 'LMT', lmtPrice=self.limit_price)
        self.app.fill_arrival_params(order, endtime)

        self.app.nextorderId += 1
        self.app.placeOrder(self.app.nextorderId, self.contract.trade_contract, order)

    def twap_order_ib(self):
        endtime = (datetime.now() + timedelta(minutes=self.algo_time)).replace(second=0, microsecond=0).strftime(
            "%H:%M:%S") + " US/Eastern"
        order = self.app.create_order(self.side, self.size, 'LMT', lmtPrice=self.limit_price)
        self.app.fill_arrival_params(order, endtime)

        self.app.nextorderId += 1
        self.app.placeOrder(self.app.nextorderId, self.contract.trade_contract, order)

    def vwap_order_ib(self):
        util.raiseNotDefined()

    def is_order_ib(self):
        util.raiseNotDefined()

    def monitor_order_ib(self, order_id):
        t.sleep(self.algo_time)
        self.app.reqAllOpenOrders()
        remaining = 0
        if order_id in self.app.openOrders.keys():
            remaining = self.app.openOrders[order_id]
        if remaining != 0:
            self.app.cancelOrder(order_id)
            self.size = remaining
            self.market_order_ib()

    def switch_to_market_ib(self):
        util.raiseNotDefined()

