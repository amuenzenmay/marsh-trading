import pandas as pd

from contracts import *
from order import Order
from datetime import datetime, time
import time as t
import mysql.connector


class Strategy:
    def __init__(self, **kwargs):
        self.name = kwargs.get('name', '')
        self.interval = 0
        self.contracts = {}
        self.orderType = kwargs.get('order_type', '')
        self.limit_time = kwargs.get('limit_time', 60)
        self.notional = kwargs.get('notional', 0)
        self.starting_notional = kwargs.get('notional', 0)
        self.exchange = kwargs.get('dma_exchange', '')
        self.algo_exchange = kwargs.get('algo_exchange', '')
        self.account = kwargs.get('account', '')
        self.data_source = kwargs.get('data_source', 'IBAPI')
        self.app = kwargs.get('app', None)
        self.positions = pd.DataFrame(columns=['Ticker', 'Position', 'PnL'])
        self.positions.set_index('Ticker', inplace=True)
        self.startTime = kwargs.get('startTime', time(9, 30))
        self.endTime = kwargs.get('endTime', time(hour=15, minute=30, second=0))
        self.day_algo_time = kwargs.get('day_algo_time', 20)
        self.last_algo_time = kwargs.get('last_algo_time', 3)
        self.strategy_Data = pd.DataFrame()
        self.average = ''
        self.srse_username = ''
        self.srse_password = ''
        self.timezone = kwargs.get('timezone', pytz.timezone('America/Chicago'))
        self.converter = None
        self.trade_location = kwargs.get('brokerage', 'TWS')
        self.twsPositions = None
        self.pnl = None
        self.allow_adjustment = kwargs.get('adjust', False)
        self.bar_type = kwargs.get('barType', 'TRADES')

    def get_contracts(self):
        """
        Returns a diction of keys and values. Keys are tickers, and the values are contract objects for the
        corresponding ticker.
        :return:
        """
        return self.contracts

    def get_bars_from_df(self, contract, tries=0):
        try:
            if tries > 3:
                return 0, 0, 0, 0
            df = contract.data
            if contract.working_bars:
                i = 0
            else:
                i = -1
            while len(df.index) < 5:
                if tries >= 15:
                    print('Unable to get {} bars from dataframe'.format(contract.ticker))
                    return 0, 0, 0, 0
                t.sleep(1)
            if self.average in df.columns:
                curr = df.iloc[i - 1][self.average]
                pre1 = df.iloc[i - 2][self.average]
                pre2 = df.iloc[i - 3][self.average]
                pre3 = df.iloc[i - 4][self.average]
            else:
                self.calculate_moving_averages(contract)
                return self.get_bars_from_df(contract, tries=tries + 1)
            return pre3, pre2, pre1, curr
        except IndexError:
            return 0, 0, 0, 0

    def long_signal(self, contract):
        util.raiseNotDefined()

    def short_signal(self, contract):
        util.raiseNotDefined()

    def close_long_signal(self, contract):
        util.raiseNotDefined()

    def close_short_signal(self, contract):
        util.raiseNotDefined()

    def adjustment(self, contract):
        if not contract.allowInceptions:
            return 0
        if contract.position < 0:
            new_position = -contract.getTradeAmount(side='Sell')
            diff = new_position - contract.position
            if diff != 0:
                return diff
            return 0
        elif contract.position > 0:
            new_position = contract.getTradeAmount(side='Buy')
            diff = new_position - contract.position
            if diff != 0:
                return diff
            return 0
        else:
            return 0

    def close_position(self, contract, msg='END OF DAY CLOSE'):
        """Close out a contract"""
        if contract.position == 0:
            return
        msg = contract.ticker + ' ' + msg
        print(msg)
        trade_value = -contract.position
        self.create_order(contract, trade_value, 0)

    def close_all_positions(self):
        for tick in self.contracts.keys():
            self.close_position(self.contracts[tick])

    def create_order(self, contract, trade_value, adjustment):
        if trade_value > 0:
            side = 'Buy'
        else:
            side = 'Sell'
        order = Order(trade_value, side, contract, day_algo_time=self.day_algo_time, last_algo_time=self.last_algo_time,
                      strategy=self.name, app=self.app)
        order.account = self.account
        order.dma_destination = self.exchange
        order.algo_destination = self.algo_exchange
        if self.orderType.upper() == 'MARKET' or adjustment != 0:
            order.market_order_ib()
        elif self.orderType.upper() == 'LIMIT':
            order.limit_time = self.limit_time
            order.limit_order_ib()
        elif self.orderType.upper() == 'TWAP':
            order.twap_order_ib()
        elif self.orderType.upper() == 'VWAP':
            order.vwap_order_ib()
        elif self.orderType.upper() == 'IS':
            order.is_order_ib()
        elif self.orderType.upper() == 'ARRIVAL':
            order.arrival_price_ib()
        else:
            print('Invalid Order Type')

    def check_for_trade(self, contract):
        """Check for any trade signals. Return the number of shares that need to be bought or sold based on the
        signals detected."""
        trade_value = 0
        signals = []
        adjust = 0
        if 'VX' in contract.ticker or contract.ticker == 'ROKU':
            bars = self.get_bars_from_df(contract)
            sbars = [str(i) for i in bars]
            msg = 'Oldest to most recent: ' + '\t'.join(sbars)
            print(msg)
        if self.long_signal(contract):
            trade_value += contract.getTradeAmount(side='Buy', size_type='inception')
            signals.append('LONG')
        if self.short_signal(contract):
            trade_value -= contract.getTradeAmount(side='Sell', size_type='inception')
            signals.append('SHORT')
        if self.close_short_signal(contract):
            trade_value += abs(contract.position)
            signals.append('CLOSE SHORT')
        if self.close_long_signal(contract):
            trade_value -= abs(contract.position)
            signals.append('CLOSE LONG')
        if trade_value == 0:
            adjust = self.adjustment(contract)
            if adjust != 0 and self.allow_adjustment:
                signals.append('ADJUST')
                trade_value = adjust

        if trade_value != 0:
            self.create_order(contract, trade_value, adjust)  # Create and submit an order

        if len(signals) != 0:
            sig = ' & '.join(signals)
            msg = contract.ticker + ' ' + sig
            print(msg)
        return trade_value

    def set_contracts(self, arr, size=0):
        if size == 0:
            size = len(arr)
        for contract in arr:
            contract.notional = self.notional / size
            contract.starting_notional = self.notional / size
            contract.account = self.account
            contract.interval = self.interval
            self.contracts[contract.ticker] = contract
        if self.data_source == 'IBAPI':
            self.create_ibapi_contracts()

    def get_positions(self):
        """Request the positions from the REDI API. Code is based off the Refinitiv Developer Community"""
        if self.trade_location == "TWS":
            app = self.app
            app.reqPositions()
            t.sleep(0.25)
            self.twsPositions = app.positions
        elif self.trade_location == "REDI":
            q = win32com.client.Dispatch("REDI.Query", pythoncom.CoInitialize())

            # Prepare a variable which can handle returned values from submit method of the order object.
            # row = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, 0)
            cell_var = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, 0)
            cell_val = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, 0)
            ret_var = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, 0)

            # add watch on accounts
            myaccounts = [self.account]
            for account in myaccounts:
                temp_val = q.AddWatch("2", "", account, ret_var)

            # Prepare the query
            vtable = "Position"
            vwhere = "true"
            temp_val = q.Submit(vtable, vwhere, ret_var)

            interested_pos = self.contracts.keys()
            for i in range(0, q.RowCount):  # Iterate through every row of the table
                cell_var.value = "Symbol"
                ret = q.GetCell(i, cell_var, cell_val, ret_var)
                ticker = cell_val.value
                if ticker not in interested_pos:
                    continue
                contract = self.contracts[ticker]

                cell_var.value = "Position"
                ret = q.GetCell(i, cell_var, cell_val, ret_var)
                position = cell_val.value
                contract.position = position

                cell_var.value = "PandL"
                ret = q.GetCell(i, cell_var, cell_val, ret_var)
                contract.pnl = cell_val.value
                self.positions.loc[contract.ticker] = [contract.position, contract.pnl]
        elif self.trade_location == "SRSE":
            connection = mysql.connector.connect(host='198.102.4.55', port=3307, database='sranalytics',
                                                 user=self.srse_username, password=self.srse_password)
            cursor = connection.cursor()
            cursor.execute("SELECT ticker_tk, (stkopnpos+shBot-shSld) AS Position, "
                           "(opnPnlMidMark+dayPnL+opnDivPnL) AS 'PnL' FROM srrisk.msgstockpositionrecord "
                           "WHERE ticker_at='EQT' AND accnt='{Account}' "
                           "AND recordType='Live'".format(Account=self.account))
            record = cursor.fetchall()
            for r in record:
                if r[0] not in self.contracts.keys():
                    continue
                contract = self.contracts[r[0]]
                contract.position = r[1]
                contract.pnl = r[2]
                self.positions.loc[r[0]] = [contract.position, contract.pnl]
        else:
            quit("Trade location not specified")

    def get_eikon_data(self):
        # ticks = self.contracts.keys()
        util.raiseNotDefined()

    def update_strategy_notional(self):
        """Update the contracts notional value based on the daily pnl"""
        temp_sum = self.starting_notional
        for tick in self.positions.index:
            temp_sum += self.positions.loc[tick]['PnL']
        self.notional = temp_sum
        self.update_contract_notionals()
        # msg = 'Starting Notional: {}\tAdjusted Notional: {}'.format(self.starting_notional, self.notional)
        # print(msg)

    def update_contract_notionals(self, size=0):
        if size == 0:
            size = len(self.contracts)
        for tick in self.contracts.keys():
            contract = self.contracts[tick]
            contract.notional = self.notional / size

    def create_ibapi_contracts(self):
        util.raiseNotDefined()

    def get_bar_data(self, contract, tries=0):
        if tries > 2:
            msg = contract.ticker + ' data unable to update. Possible connection issue.'
            print(msg)
            contract.data = pd.DataFrame()  # empty data frame
            return
        if self.data_source == 'IBAPI':
            self.app.volume_request = False
            data = Data(contract, app=self.app)
            data.requestDataIBAPI(contract.data_contract, self.interval, contract)
            data.request_position("TWS")  # update the contract's position and PnL
            self.update_contract_notionals()  # update the contracts notional value

            # wait for data to populate
            delay_count = 0
            t.sleep(0.5)
            while contract.data_id not in self.app.barDF.keys():
                delay_count += 1
                if delay_count > 60:  # Wait for data for 15 seconds, otherwise move on
                    msg = contract.ticker + " data not updating. Trying again."
                    print(msg)
                    self.get_bar_data(contract, tries + 1)
                    return
                t.sleep(0.25)
            try:
                if self.app.barDF[contract.data_id]['Close'].size <= 10:
                    self.get_bar_data(contract, tries + 1)
                contract.data = self.app.barDF[contract.data_id]
                contract.lastClose = contract.data['Close'].iloc[-1]
            except IndexError:
                self.get_bar_data(contract, tries + 1)
            self.convert_pricing(contract)
            self.calculate_moving_averages(contract)
            t.sleep(0.25)
        elif self.data_source == 'Eikon':
            contract.data = None
            data = Data(contract)
            data.requestDataEikon(self.interval, self.timezone)
            i = 0
            while contract.ticker not in self.strategy_Data.keys():
                i += 1
                if i > 60:
                    msg = contract.ticker + ' data not available'
                    print(msg)
                    return
                t.sleep(0.25)
            contract.data = self.strategy_Data[contract.ticker]
            data.request_position()  # update the contract's position and PnL
            contract.lastClose = contract.data['Close'].iloc[-1]
            self.convert_pricing(contract)
            self.calculate_moving_averages(contract)
            t.sleep(0.25)

    def convert_pricing(self, contract):
        """Unless it is a commodity or VIX, the last close does not need to be adjusted"""
        pass

    def calculate_moving_averages(self, contract):
        """Calculate the moving averages for a contract's data. Adds a column to the contract's DataFrame with a 10 SMA
        of the close prices."""
        contract.data['10SMA'] = self.app.barDF[contract.data_id]['Close'].rolling(10).mean()
        delay_count = 0
        while '10SMA' not in contract.data.columns or pd.isnull(contract.data['10SMA'].iloc[-1]):
            if delay_count >= 60:
                msg = contract.ticker + " data not calculating, attempting manual calculation"
                print(msg)
                self.manual_sma(contract, 10, 'Close', '10SMA')
                break
                # contract.data['10SMA'] = [0] * len(contract.data['Close'])
            t.sleep(0.25)
            delay_count += 1

    def end_day(self, tzone=pytz.timezone('America/Chicago')):
        """Returns True if the strategy has reached the end of its day"""
        utc_date = datetime.now(tz=pytz.timezone('UTC')).date()
        comb_end_time = datetime.combine(utc_date, self.endTime)
        tz = self.timezone
        loc_end_time = tz.localize(comb_end_time)
        if loc_end_time <= datetime.now(tz=tzone).replace(second=0, microsecond=0):
            return True
        else:
            return False

    def wait_time(self, current_time=None):
        if current_time is None:
            current_time = datetime.now(tz=self.timezone).replace(second=0, microsecond=0)
        last_full = datetime.now(tz=self.timezone).replace(hour=self.endTime.hour,
                                                           minute=self.endTime.minute - (
                                                                       self.endTime.minute % self.interval),
                                                           second=0, microsecond=0)
        if current_time.time() >= last_full.time():
            if self.endTime.minute % self.interval == 0:
                return self.interval - (current_time.minute % self.interval)
            else:
                return self.endTime.minute - (current_time.minute % self.endTime.minute)
        else:
            return self.interval - (current_time.minute % self.interval)

    def manual_sma(self, contract, length, label1, label2):
        averages = [0.0] * len(contract.data[label1])
        for i in range(length - 1, len(averages)):
            tempSum = 0
            for j in range(i - (length - 1), i + 1):
                tempSum += contract.data[label1].iloc[j]
            averages[i] = (tempSum / length)
        contract.data[label2] = averages

    def get_volume(self, contract, tries=0):
        if tries > 2:
            msg = contract.ticker + ' data unable to update. Possible connection issue.'
            print(msg)
            return
        if self.data_source == 'IBAPI':
            data = Data(contract, app=self.app)
            data.requestVolumeIBAPI(contract.trade_contract, contract)

            # wait for data to populate
            delay_count = 0
            t.sleep(0.5)
            while contract.data_id not in self.app.barDF.keys():
                delay_count += 1
                if delay_count > 60:  # Wait for data for 15 seconds, otherwise move on
                    msg = contract.ticker + " data not updating. Trying again."
                    print(msg)
                    self.get_volume(contract, tries + 1)
                    return
                t.sleep(0.25)

            df = self.app.barDF[contract.data_id]
            contract.currVol = df['Volume'].iloc[-2]

            # NEXT Contract
            data.requestVolumeIBAPI(contract.next_ib_contract, contract)

            # wait for data to populate
            delay_count = 0
            t.sleep(0.5)
            while contract.data_id not in self.app.barDF.keys():
                delay_count += 1
                if delay_count > 60:  # Wait for data for 15 seconds, otherwise move on
                    msg = contract.ticker + " data not updating. Trying again."
                    print(msg)
                    self.get_volume(contract, tries + 1)
                    return
                t.sleep(0.25)

            df = self.app.barDF[contract.data_id]
            contract.nextVol = df['Volume'].iloc[-2]
            print('{}\tCurrent: {}\tNext: {}'.format(contract.ticker, contract.currVol, contract.nextVol))
            t.sleep(0.25)
        elif self.data_source == 'Eikon':
            print("Volume data not set up for Eikon")
            pass

    def get_overall_pnl(self, source):
        if source == 'TWS':
            data = Data(Contract(''), app=self.app, account=self.account)
            data.request_pnl("TWS")
            self.pnl = self.app.tws_pnl
        pass

    def get_contract_pnl(self, source):
        if source == "TWS":
            for tick in self.contracts.keys():
                con = self.contracts[tick]
                data = Data(con, app=self.app, account=self.account)
                data.request_pnl_single("TWS")
            t.sleep(0.25)
            self.pnl = self.app.single_pnl

    def combine_pnl_position(self):
        for tick in self.contracts.keys():
            pos = 0
            pnl = 0.0
            if tick in self.twsPositions.index:
                pos = self.twsPositions.loc[tick, 'Position']
            if tick in self.pnl.index:
                pnl = self.pnl.loc[tick, 'Daily']
            self.positions.loc[tick] = pos, pnl


class ThirtyMin(Strategy):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.numberBars = 4
        self.average = ''
        self.interval = 30

    def long_signal(self, contract, working_bar=False):
        contract = contract
        bars = self.get_bars_from_df(contract)
        i = 0
        while len(bars) != self.numberBars:
            if i > 60:
                print('Data not available')
                return False
            t.sleep(0.25)
        if contract.position > 0 or not contract.allowInceptions:
            return False
        else:
            try:
                if bars[3] > bars[2] > bars[1] > bars[0]:  # Four increasing in a row
                    return True
                else:
                    return False
            except (IndexError, TypeError) as error:
                print(contract.ticker, end='\n')
                print(contract.data)
                return False

    def short_signal(self, contract, working_bar=False):
        contract = contract
        bars = self.get_bars_from_df(contract)
        i = 0
        while len(bars) != self.numberBars:
            if i > 60:
                print('Data not available')
                return False
            t.sleep(0.25)
        if contract.position < 0 or not contract.allowInceptions:
            return False
        else:
            try:
                if bars[3] < bars[2] < bars[1] < bars[0]:
                    return True
                else:
                    return False
            except (IndexError, TypeError) as error:
                print(contract.data)
                return False

    def close_long_signal(self, contract, working_bar=False):
        contract = contract
        bars = self.get_bars_from_df(contract)
        i = 0
        while len(bars) != self.numberBars:
            if i > 60:
                print('Data not available')
                return False
            t.sleep(0.25)
        if contract.position <= 0:
            return False
        else:
            try:
                if bars[3] < bars[2] and bars[3] < bars[0]:
                    return True
                else:
                    return False
            except (IndexError, TypeError) as error:
                print(contract.data)
                return False

    def close_short_signal(self, contract, working_bar=False):
        contract = contract
        bars = self.get_bars_from_df(contract)
        i = 0
        while len(bars) != self.numberBars:
            if i > 60:
                print('Data not available')
                return False
            t.sleep(0.25)
        if contract.position >= 0:
            return False
        else:
            try:
                if bars[3] > bars[2] and bars[3] > bars[0]:
                    return True
                else:
                    return False
            except (IndexError, TypeError) as error:
                print(contract.data)
                return False


class StockThirtyMin(ThirtyMin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.average = '10SMA'
        self.interval = 30
        self.name = 'Stk30'

    def check_for_adjustment(self, contract):
        """Check only for adjustment trades, and submit any trades as needed."""
        trade_value = 0
        signals = []
        if contract.ticker == 'GME':
            bars = self.get_bars_from_df(contract)
            sbars = [str(i) for i in bars]
            barMsg = 'Oldest to most recent: ' + '\t'.join(sbars)
            print(barMsg)

        adjust = self.adjustment(contract)
        if trade_value == 0 and adjust != 0:
            signals.append('ADJUST')
            trade_value = adjust

        if trade_value != 0:
            self.create_order(contract, trade_value, adjust)  # Create and submit an order

        if len(signals) != 0:
            sig = ' & '.join(signals)
            msg = contract.ticker + ' ' + sig
            print(msg)
        return trade_value

    def set_contracts(self, arr, size=0):
        """Set the starting notional value for every contract and determine whether inception trades will be
        allowed. If a contract has no locates, inception trades will not be allowed. If the SDIV is greater than 0.15,
        inceptions will not be allowed."""

        if size == 0:
            size = len(arr)
        for contract in arr:
            contract.notional = self.notional / size
            contract.starting_notional = self.notional / size
            contract.account = self.account
            contract.interval = self.interval
            self.contracts[contract.ticker] = contract
        if self.data_source == 'IBAPI':
            self.create_ibapi_contracts()
        # tickers = str(tuple(self.contracts.keys()))
        # connection = mysql.connector.connect(host='198.102.4.55', port=3307, database='sranalytics',
        #                                      user=self.srse_username, password=self.srse_password)
        #
        # cursor = connection.cursor()
        # # Retrieve tickers with SDIV less than or equal to 0.15
        # cursor.execute(
        #     "SELECT ticker_tk FROM `msglivesurfaceterm` WHERE ticker_tk IN {stocks} AND surfaceType='PrevDay'"
        #     "AND sdiv_42d <= .15".format(stocks=tickers))
        # tradable = [c[0] for c in cursor.fetchall()]
        #
        # # Retrieve all tickers with surfaceType PrevDay
        # cursor.execute(
        #     "SELECT ticker_tk FROM `msglivesurfaceterm` WHERE ticker_tk IN {stocks} AND surfaceType='PrevDay'".format(
        #         stocks=tickers))
        # all_stocks = cursor.fetchall()
        #
        # # Retrieve locates for each ticker
        # cursor.execute("SELECT ticker_tk, locateQuan FROM srcontrol.msgavailablestocklocates WHERE locatePool = 'RZM' ")
        # locate_records = cursor.fetchall()
        # locates = {}
        # for num in locate_records:
        #     locates[num[0]] = num[1]
        #
        # # Retrieve EDAY values for each contract
        # cursor.execute("SELECT ticker_tk,edays FROM srrisk.msgsymbolriskdetail WHERE accnt='{accnt}' AND ticker_tk " \
        #                "IN {stocks}".format(accnt=self.account, stocks=tickers))
        # eday_record = cursor.fetchall()
        # edays = {}
        # for eday in eday_record:
        #     edays[eday[0]] = eday[1]  # Dictionary with ticker as a key, and eday as the value
        #
        # # Set allowInceptions to True or False depending on locates and SDIV value of each contract
        # for record in all_stocks:
        #     con = self.contracts[record[0]]
        #     if con.ticker in edays.keys():
        #         con.edays = edays[con.ticker]
        #     if record[0] not in tradable or record[0] not in locates.keys() or locates[record[0]] == 0:
        #         con.allowInceptions = False
        #     else:
        #         con.allowInceptions = True

    def adjustment(self, contract):
        """Contract value adjustment based for the Stock Thirty Minute Strategy."""
        if not contract.allowInceptions:
            return 0
        if contract.position == 0:
            return 0
        elif contract.position < 0:
            new_position = -contract.getTradeAmount(side='Sell')
        else:
            new_position = contract.getTradeAmount(side='Buy')
        diff = new_position - contract.position
        pct_diff = diff / contract.position
        if pct_diff >= 0.005 and contract.position < 0:
            return -abs(diff)
        elif pct_diff <= -0.005 and contract.position < 0:
            return abs(diff)
        elif pct_diff >= 0.005 and contract.position > 0:
            return abs(diff)
        elif pct_diff <= -0.005 and contract.position > 0:
            return -abs(diff)
        else:
            return 0

    def calculate_moving_averages(self, contract):
        contract.data[self.average] = contract.data['Close'].rolling(10).mean()
        i = 0
        while self.average not in contract.data.columns or pd.isnull(contract.data[self.average].iloc[-8]):
            if i > 60:
                print('{} averages not calculating, attempting manual calculation'.format(contract.ticker))
                self.manual_sma(contract, 10, 'Close', self.average)
                break
            t.sleep(0.25)
            i += 1

    def create_ibapi_contracts(self):
        for tick in self.contracts.keys():
            con = self.contracts[tick]
            ibapi_contract = self.app.Stock_contract(tick, con_id=con.data_id, data_range=(con.firstBar, con.lastBar))
            # con.ib_contract = ibapi_contract
            con.data_contract = ibapi_contract
            con.trade_contract = ibapi_contract

    def create_order(self, contract, trade_value, adjustment):
        if trade_value > 0:
            side = 'Buy'
        else:
            side = 'Sell'
        order = Order(trade_value, side, contract, day_algo_time=self.day_algo_time, last_algo_time=self.last_algo_time,
                      strategy=self.name, app=self.app)
        order.account = self.account
        order.dma_destination = self.exchange
        order.algo_destination = self.algo_exchange
        if self.orderType.upper() == 'MARKET' or adjustment != 0:
            order.market_order_ib()
        elif self.orderType.upper() == 'LIMIT':
            order.limit_time = self.limit_time
            order.limit_order_ib()
        elif self.orderType.upper() == 'TWAP':
            order.twap_order_ib()
        elif self.orderType.upper() == 'VWAP':
            order.vwap_order_ib()
        elif self.orderType.upper() == 'IS':
            order.is_order_ib()
        elif self.orderType.upper() == 'ARRIVAL':
            order.arrival_price_ib()
        else:
            print('Invalid Order Type')


class VixThirtyMin(ThirtyMin):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.average = '10WMA'
        self.interval = 30
        self.name = 'Vix30'

    def create_order(self, contract, trade_value, adjustment):
        if trade_value > 0:
            side = 'Buy'
        else:
            side = 'Sell'
        order = Order(trade_value, side, contract, day_algo_time=self.day_algo_time, last_algo_time=self.last_algo_time,
                      strategy=self.name, app=self.app)
        order.account = self.account
        order.dma_destination = self.exchange
        order.algo_destination = self.algo_exchange
        if self.orderType.upper() == 'MARKET':
            order.market_order_ib()
        elif self.orderType.upper() == 'LIMIT':
            order.limit_time = self.limit_time
            order.limit_order_ib()
        elif self.orderType.upper() == 'TWAP':
            order.twap_order_ib()
        elif self.orderType.upper() == 'VWAP':
            order.vwap_order_ib()
        elif self.orderType.upper() == 'IS':
            order.is_order_ib()
        elif self.orderType.upper() == 'ARRIVAL':
            order.arrival_price_ib()
        else:
            print('Invalid Order Type')

    def convert_pricing(self, contract):
        nearestNickel = round(contract.lastClose / 0.05) * 0.05
        nearestNickel = round(nearestNickel, 2)
        contract.lastClose = nearestNickel

    def calculate_moving_averages(self, contract):
        """Calculate the 10 weighted moving average of close prices
        """
        closePrices = contract.data['Close']
        averages = [None] * 9
        for i in range(9, len(closePrices)):  # Start at index 9 (10th index)
            averages.append(
                (10 * closePrices[i] + 9 * closePrices[i - 1] + 8 * closePrices[i - 2] + 7 * closePrices[i - 3]
                 + 6 * closePrices[i - 4] + 5 * closePrices[i - 5] + 4 * closePrices[i - 6] + 3 * closePrices[i - 7]
                 + 2 * closePrices[i - 8] + closePrices[i - 9]) / 55)
        contract.data[self.average] = averages

    def create_ibapi_contracts(self):
        for tick in self.contracts.keys():
            con = self.contracts[tick]
            ibapi_contract = self.app.Future_contract('VIX', con.ticker, con.multiplier, exchange=con.exchange,
                                                      con_id=con.data_id, data_range=(con.firstBar, con.lastBar))
            # con.ib_contract = ibapi_contract
            con.trade_contract = ibapi_contract
            con.data_contract = ibapi_contract
            # Must include matching data range for spot contract and future contract due to having the same ticker
            # key in the TWS app connection. Or create spot contract first.
            con.spot_ib_contract = self.app.Stock_contract('VIX', 'IND', 'CBOE', data_range=(con.firstBar, con.lastBar))

    def get_spot_data(self, contract, tries=0):
        if tries > 2:
            msg = contract.ticker + ' data unable to update. Possible connection issue.'
            print(msg)
            return
        if self.data_source == 'IBAPI':
            data = Data(contract, app=self.app)
            data.requestDataIBAPI(contract.spot_ib_contract, self.interval, contract)

            # wait for data to populate
            delay_count = 0
            t.sleep(0.5)
            while contract.data_id not in self.app.barDF.keys():
                delay_count += 1
                if delay_count > 60:  # Wait for data for 15 seconds, otherwise move on
                    msg = contract.ticker + " data not updating. Trying again."
                    print(msg)
                    self.get_bar_data(contract, tries + 1)
                    return
                t.sleep(0.25)

            contract.spotData = self.app.barDF[contract.data_id]
            contract.spotClose = contract.spotData['Close'].iloc[-1]
            t.sleep(0.25)


class StockFiveMin(Strategy):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.numberBars = 4
        self.average = '2MA'
        self.interval = 5

    def create_ibapi_contracts(self):
        for tick in self.contracts.keys():
            con = self.contracts[tick]
            ibapi_contract = self.app.Stock_contract(tick, con_id=con.data_id, data_range=(con.firstBar, con.lastBar))
            # con.ib_contract = ibapi_contract
            con.trade_contract = ibapi_contract
            con.data_contract = ibapi_contract

    def long_signal(self, contract, working_bar=False):
        contract = contract
        bars = self.get_bars_from_df(contract)
        i = 0
        while len(bars) != self.numberBars:
            if i > 60:
                print('Data not available')
                return False
            t.sleep(0.25)
        if contract.position > 0 or not contract.allowInceptions:
            return False
        else:
            try:
                if bars[3] > bars[2] > bars[1] > bars[0]:  # Four increasing in a row
                    msg = '{} LONG at'.format(contract.ticker)
                    # TODO LOG logger.info(msg)
                    return True
                else:
                    return False
            except (IndexError, TypeError) as error:
                print(error)
                return False

    def short_signal(self, contract, working_bar=False):
        contract = contract
        bars = self.get_bars_from_df(contract)
        i = 0
        while len(bars) != self.numberBars:
            if i > 60:
                print('Data not available')
                return False
            t.sleep(0.25)
        if contract.position < 0 or not contract.allowInceptions:
            return False
        else:
            try:
                if bars[3] < bars[2] < bars[1] < bars[0]:
                    msg = '{} SHORT'.format(contract.ticker)
                    # TODO LOG logger.info(msg)
                    return True
                else:
                    return False
            except (IndexError, TypeError) as error:
                print(error)
                return False

    def close_long_signal(self, contract, working_bar=False):
        contract = contract
        bars = self.get_bars_from_df(contract)
        i = 0
        while len(bars) != self.numberBars:
            if i > 60:
                print('Data not available')
                return False
            t.sleep(0.25)
        if contract.position <= 0:
            return False
        else:
            try:
                if bars[3] < bars[2] and bars[3] < bars[0]:
                    msg = '{} CLOSED LONG'.format(contract.ticker)
                    return True
                else:
                    return False
            except (IndexError, TypeError) as error:
                print(error)
                return False

    def calculate_moving_averages(self, contract):
        contract.data['20SMA'] = contract.data['Close'].rolling(20).mean()
        i = 0
        while '20SMA' not in contract.data.columns or pd.isnull(contract.data['20SMA'].iloc[-9]):
            if i >= 60:
                print('Averages not calculating')
                self.manual_sma(contract, 20, 'Close', '20SMA')
                break
            t.sleep(0.25)
            i += 1
        contract.data['2MA'] = contract.data['20SMA'].rolling(2).mean()
        i = 0
        while '2MA' not in contract.data.columns or pd.isnull(contract.data['2MA'].iloc[-5]):
            if i >= 60:
                print('Averages not calculating')
                self.manual_sma(contract, 2, '20SMA', '2MA')
                break
            t.sleep(0.25)
            i += 1

    def close_short_signal(self, contract, working_bar=False):
        contract = contract
        bars = self.get_bars_from_df(contract)
        i = 0
        while len(bars) != self.numberBars:
            if i > 60:
                print('Data not available')
                return False
            t.sleep(0.25)
        if contract.position >= 0:
            return False
        else:
            try:
                if bars[3] > bars[2] and bars[3] > bars[0]:
                    msg = '{} CLOSED SHORT'.format(contract.ticker)
                    return True
                else:
                    return False
            except (IndexError, TypeError) as error:
                print(error)
                return False


class VixFiveMin(Strategy):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.numberBars = 4
        self.average = '2MA'
        self.interval = 5
        self.startTime = time(10, 15)
        self.endTime = time(15, 15)
        self.name = 'Vix5'

    def convert_pricing(self, contract):
        nearestNickel = round(contract.lastClose / 0.05) * 0.05
        nearestNickel = round(nearestNickel, 2)
        contract.lastClose = nearestNickel

    def long_signal(self, contract, working_bar=False):
        contract = contract
        bars = self.get_bars_from_df(contract)
        if contract.position > 0 or not contract.allowInceptions:
            return False
        else:
            try:
                if bars[3] > bars[2] > bars[1] > bars[0] and (
                        (bars[3] / bars[0]) - 1) > 0.005:  # Four increasing in a row
                    msg = '{} LONG at'.format(contract.ticker)
                    return True
                else:
                    return False
            except (IndexError, TypeError) as error:
                print(error)
                return False

    def short_signal(self, contract, working_bar=False):
        contract = contract
        bars = self.get_bars_from_df(contract)
        if contract.position < 0 or not contract.allowInceptions:
            return False
        else:
            try:
                if bars[3] < bars[2] < bars[1] < bars[0] and (
                        (bars[3] / bars[0]) - 1) < -0.00125:
                    msg = '{} SHORT'.format(contract.ticker)
                    return True
                else:
                    return False
            except (IndexError, TypeError) as error:
                print(error)
                return False

    def close_long_signal(self, contract, working_bar=False):
        contract = contract
        bars = self.get_bars_from_df(contract)
        if contract.position <= 0:
            return False
        else:
            try:
                if bars[3] < bars[2] and bars[3] < bars[0] and (
                        (bars[3] / bars[1]) - 1) < -0.0005:
                    msg = '{} CLOSED LONG'.format(contract.ticker)
                    # TODO LOG logger.info(msg)
                    return True
                else:
                    return False
            except (IndexError, TypeError) as error:
                print(error)
                return False

    def close_short_signal(self, contract, working_bar=False):
        contract = contract
        bars = self.get_bars_from_df(contract)
        if contract.position >= 0:
            return False
        else:
            try:
                if bars[3] > bars[2] and bars[3] > bars[0] and (
                        (bars[3] / bars[1]) - 1) > 0.00125:
                    msg = '{} CLOSED SHORT'.format(contract.ticker)
                    return True
                else:
                    return False
            except:
                return False

    def calculate_moving_averages(self, contract):
        contract.data['20SMA'] = contract.data['Close'].rolling(20).mean()
        i = 0
        while '20SMA' not in contract.data.columns or pd.isnull(contract.data['20SMA'].iloc[-9]):
            if i >= 60:
                print('20SMA unable to calculate, attempting manual calculation')
                self.manual_sma(contract, 20, 'Close', '20SMA')
                break
            t.sleep(0.25)
            i += 1
        contract.data['2MA'] = contract.data['20SMA'].rolling(2).mean()
        j = 0
        while '2MA' not in contract.data.columns or pd.isnull(contract.data['2MA'].iloc[-5]):
            if j >= 60:
                contract.data['2MA'] = [0] * len(contract.data['Close'])
                print('2MA unable to calculate, attempting manual calculation')
                self.manual_sma(contract, 2, '20SMA', '2MA')
                break
            t.sleep(0.25)
            j += 1

    def create_ibapi_contracts(self):
        for tick in self.contracts.keys():
            con = self.contracts[tick]
            ibapi_contract = self.app.Future_contract('VIX', con.ticker, con.multiplier, exchange=con.exchange,
                                                      con_id=con.data_id, data_range=(con.firstBar, con.lastBar))
            # con.ib_contract = ibapi_contract
            con.trade_contract = ibapi_contract
            con.data_contract = ibapi_contract

    def create_order(self, contract, trade_value, adjustment):
        if trade_value > 0:
            side = 'Buy'
        else:
            side = 'Sell'
        order = Order(trade_value, side, contract, day_algo_time=self.day_algo_time, last_algo_time=self.last_algo_time,
                      strategy=self.name, app=self.app)
        order.account = self.account
        order.dma_destination = self.exchange
        order.algo_destination = self.algo_exchange
        if self.orderType.upper() == 'MARKET':
            order.market_order_ib()
        elif self.orderType.upper() == 'LIMIT':
            order.limit_time = self.limit_time
            order.limit_order_ib()
        elif self.orderType.upper() == 'TWAP':
            order.twap_order_ib()
        elif self.orderType.upper() == 'VWAP':
            order.vwap_order_ib()
        elif self.orderType.upper() == 'IS':
            order.is_order_ib()
        else:
            print('Invalid Order Type')


class Crypto(Strategy):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.numberBars = 4
        self.average = '56SMA'
        self.interval = 30
        self.startTime = time(2, 0)
        self.endTime = time(15, 30)
        self.name = 'Crypto'

    # TODO implement contract creation
    def create_ibapi_contracts(self):
        for tick in self.contracts.keys():
            con = self.contracts[tick]
            con.trade_contract = self.app.Future_contract(tick[:-2], tick, con.multiplier, exchange=con.exchange)
            con.data_contract = con.trade_contract

            '''The API needs to support at least version 163 to handle the cash cryptocurrency contracts. Until that is
            possible these will not work'''
            # if tick[:-2] == "MET":
            #     con.data_contract = self.app.crypto_contract("ETH", con_id=con.data_id,
            #                                                  data_range=(con.firstBar, con.lastBar))
            # elif tick[:-2] == "MBT":
            #     con.data_contract = self.app.crypto_contract("BTC", con_id=con.data_id,
            #                                                  data_range=(con.firstBar, con.lastBar))

    def long_signal(self, contract):
        contract = contract
        bars = self.get_bars_from_df(contract)
        if contract.position > 0 or not contract.allowInceptions:
            return False
        else:
            try:
                # Four increasing in a row and current price greater than the long term moving average
                if bars[3] > bars[2] > bars[1] > bars[0] and \
                        contract.lastClose >= contract.longMa:
                    msg = '{} LONG at'.format(contract.ticker)
                    return True
                else:
                    return False
            except (IndexError, TypeError) as error:
                print(error)
                return False

    def short_signal(self, contract, working_bar=False):
        contract = contract
        bars = self.get_bars_from_df(contract)
        i = 0
        while len(bars) != self.numberBars:
            if i > 60:
                print('Data not available')
                return False
            t.sleep(0.25)
        if contract.position < 0 or not contract.allowInceptions:
            return False
        else:
            try:
                if bars[3] < bars[2] < bars[1] < bars[0] and contract.lastClose <= contract.longMa:
                    return True
                else:
                    return False
            except (IndexError, TypeError) as error:
                print(contract.data)
                return False

    def close_long_signal(self, contract, working_bar=False):
        contract = contract
        bars = self.get_bars_from_df(contract)
        i = 0
        while len(bars) != self.numberBars:
            if i > 60:
                print('Data not available')
                return False
            t.sleep(0.25)
        if contract.position <= 0:
            return False
        else:
            try:
                if bars[3] < bars[2] and bars[3] < bars[0]:
                    return True
                else:
                    return False
            except (IndexError, TypeError) as error:
                print(contract.data)
                return False

    def close_short_signal(self, contract, working_bar=False):
        contract = contract
        bars = self.get_bars_from_df(contract)
        i = 0
        while len(bars) != self.numberBars:
            if i > 60:
                print('Data not available')
                return False
            t.sleep(0.25)
        if contract.position >= 0:
            return False
        else:
            try:
                if bars[3] > bars[2] and bars[3] > bars[0]:
                    return True
                else:
                    return False
            except (IndexError, TypeError) as error:
                print(contract.data)
                return False

    def calculate_moving_averages(self, contract):
        """Calculate the moving averages for a contract's data. Adds a column to the contract's DataFrame with a 10 SMA
        of the close prices."""
        contract.data['56SMA'] = self.app.barDF[contract.data_id]['Close'].rolling(10).mean()
        delay_count = 0
        while '56SMA' not in contract.data.columns or pd.isnull(contract.data['56SMA'].iloc[-1]):
            if delay_count >= 60:
                msg = contract.ticker + " data not calculating, attempting manual calculation"
                print(msg)
                self.manual_sma(contract, 10, 'Close', '56SMA')
                break
                # contract.data['10SMA'] = [0] * len(contract.data['Close'])
            t.sleep(0.25)
            delay_count += 1

    def get_long_ma(self, contract, tries=0):
        if tries > 2:
            msg = contract.ticker + ' data unable to update. Possible connection issue.'
            print(msg)
            return
        if self.data_source == 'IBAPI':
            data = Data(contract, app=self.app)
            data.requestLongDataIBAPI(contract.data_contract, 30, contract)

            # wait for data to populate
            delay_count = 0
            t.sleep(0.5)
            while contract.data_id not in self.app.barDF.keys():
                delay_count += 1
                if delay_count > 60:  # Wait for data for 15 seconds, otherwise move on
                    msg = contract.ticker + " data not updating. Trying again."
                    print(msg)
                    self.get_long_ma(contract, tries + 1)
                    return
                t.sleep(0.25)

            df = self.app.barDF[contract.data_id]
            df['MA'] = df['Close'].rolling(312).mean()  # 560 for cash value

            contract.longMa = df['MA'].iloc[-2]
            t.sleep(0.25)
