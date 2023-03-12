import math

import util
from data import *
from datetime import datetime, time, timedelta
import pandas

conId = 0


class Contract:
    """Represents the data and values required to trade a contract. Can check for trades, and determine
    trade amounts.
    """

    def __init__(self, ticker, **kwargs):
        self.ticker = ticker
        self.exchange = kwargs.get('exchange', '')
        self.position = kwargs.get('position', 0)
        self.notional = kwargs.get('notional', 0.0)
        self.starting_notional = kwargs.get('notional', 0.0)
        self.lastClose = kwargs.get('lastClose', 0.0)
        self.interval = kwargs.get('interval', 0)
        self.working_bars = kwargs.get('working_bars', False)
        self.allowInceptions = kwargs.get('allowInceptions', True)
        self.allowAdjustment = kwargs.get('allowAdjustment', True)
        self.firstTrade = kwargs.get('first_trade', datetime.now().replace(hour=9, minute=0, second=0, microsecond=0))  # The time of the first trade
        self.lastTrade = kwargs.get('last_trade', datetime.now().replace(hour=14, minute=30, second=0, microsecond=0))  # Time of the last trade
        self.firstBar = kwargs.get('first_bar', time(hour=8, minute=30, second=0))  # Last Bar included in data
        self.lastBar = kwargs.get('last_bar', time(hour=14, minute=30, second=0))  # Last Bar included in data
        self.account = kwargs.get('account', '')
        self.secType = kwargs.get('secType', 'Stk')
        self.timezone = kwargs.get('timezone', pytz.timezone('America/Chicago'))
        self.currency = kwargs.get('currency', 'USD')
        self.conId = kwargs.get('conid', 0)
        self.hardTradeValue = kwargs.get('trade_amount', 0)
        self.shortAlgo = False
        self.short_algo_time = None
        self.pnl = 0.0
        self.data = None
        self.ib_contract = None
        self.trade_contract = None
        self.data_contract = None
        self.data_id = None
        self.id = self.next_con_id
        self.currVol = 0
        self.nextVol = 0
        self.edays = -1
        self.ib_ticker = []
        self.tradingBrokerage = ''

    @property
    def next_con_id(self):
        global conId
        conId += 1
        return conId

    def time_to_next_trade(self, currentTime=None):
        if currentTime is None:
            currentTime = datetime.now().replace(second=0, microsecond=0)
        if self.lastBar <= currentTime.time():
            if self.lastTrade.minute % self.interval == 0:
                return self.interval - (currentTime.minute % self.interval)
            else:
                return self.lastTrade.minute - (currentTime.minute
                                                % self.lastTrade.minute)
        else:
            return self.interval - (currentTime.minute % self.interval)

    def simple_ending(self):
        """Returns true if and last execution time is along the normal interval and the last execution does not equal
        the start of the next bar"""
        return self.lastTrade.minute % self.interval == 0 and self.lastBar == self.lastTrade.time()

    def terminate(self):
        """Returns True if the time of last execution has already passed.

        :return Boolean"""
        # utc_date = datetime.now(tz=pytz.timezone('UTC')).date()
        # comb_end_time = datetime.combine(utc_date, self.lastTrade.time())
        # tz = self.timezone
        # loc_end_time = tz.localize(comb_end_time)
        # return loc_end_time < datetime.now(tz=self.timezone).replace(second=0, microsecond=0)
        if self.lastTrade < datetime.now().replace(second=0, microsecond=0):
            return True
        else:
            return False

    def final_execution(self):
        return self.lastTrade == datetime.now().replace(second=0, microsecond=0)

    def last_trade(self):
        """Returs True if the contract is on its last trade of the day.

        :return Boolean
        """
        return self.lastTrade <= datetime.now().replace(second=0, microsecond=0)

    def set_ticker(self, string):
        self.ticker = string

    def getTradeAmount(self, side='', size_type=''):
        """Returns an integer value for how many shares of a contract should be traded upon an
        inception trade.

        return int
        """
        try:
            value = int(self.notional // self.lastClose)
            return max(value, 1)
        except ValueError:
            print(self.ticker, " could not calculate trade amount")
            return 0

    def updateDataIBAPI(self):
        pass

    def halt_inceptions(self):
        """Set allow inceptions to false if nearing the end of the day."""
        last_trade = datetime.combine(datetime.now().date(), self.lastTrade)
        final_inception = last_trade - timedelta(minutes=15)
        if final_inception.time() < datetime.now(tz=self.timezone).replace(second=0, microsecond=0).time():
            self.allowInceptions = False
        else:
            self.allowInceptions = True

    def set_last_trade(self):
        pass

    def set_first_trade(self):
        pass


class FutureContract(Contract):

    def __init__(self, ticker, **kwargs):
        super().__init__(ticker, **kwargs)
        self.localSymbol = kwargs.get('localSymbol', '')
        self.multiplier = kwargs.get('multiplier', 0)
        self.secType = 'Fut'
        self.lastTradeDate = None
        self.months = kwargs.get('months', [])
        self.next_ib_contract = None
        self.month_map = util.TwoWayDict({1: 'F', 2: 'G', 3: 'H', 4: 'J', 5: 'K', 6: 'M', 7: 'N', 8: 'Q', 9: 'U',
                                          10: 'V', 11: 'X', 12: 'Z'})
        self.grain_month_map = util.TwoWayDict({1: 'JAN', 2: 'FEB', 3: 'MAR', 4: 'APR', 5: 'MAY', 6: 'JUN', 7: 'JUL',
                                                8: 'AUG', 9: 'SEP', 10: 'OCT', 11: 'NOV', 12: 'DEC'})
        self.next_tick = ''

    def set_ticker(self, string):
        self.ticker = string
        self.localSymbol = string

    def switch_tick_format(self, tick=None):
        """Return the IB formatting for grain contracts"""
        if tick is None:
            tick = self.ticker
        if tick[:2] not in ['ZC', 'ZS', 'ZL', 'ZM', 'ZW']:
            return tick
        month_code = self.month_map[tick[2]]
        ib_month = self.grain_month_map[month_code]

        if str(datetime.now().year)[-1] == tick[-1]:
            year = str(datetime.now().year)[-2:]
        else:
            year = str(datetime.now().year + 1)[-2:]

        return tick[:2] + '   ' + ib_month + ' ' + year

    def next_month(self):
        """Returns the tick of the next available contract"""
        year = int(self.ticker[-1])
        curr_month_idx = self.months.index(self.month_map[self.ticker[-2]])
        next_month_idx = (curr_month_idx + 1) % len(self.months)
        if next_month_idx < curr_month_idx:
            year += 1
        # First two letters of contract code + the next available month in fut code terms + the year of the contract
        # In __MY (GCU2)
        new_tick = self.ticker[:-2] + self.month_map[self.months[next_month_idx]] + str(year)
        return new_tick

    def roll_contract(self):
        if self.position != 0:
            return
        elif self.currVol < self.nextVol:
            print('{} rolled to {}'.format(self.ticker, self.next_tick))
            # self.ib_contract = self.next_ib_contract
            self.data_contract = self.next_ib_contract
            self.trade_contract = self.next_ib_contract

            self.ticker = self.next_tick

    def getTradeAmount(self, side='', size_type=''):
        try:
            trueMultiplier = self.multiplier
            if self.ticker[:-2] in ['FFI']:
                trueMultiplier /= 100  # Adjust the FFI multiplier from 1000 on IB to true value of 10
            value = int(self.notional // (trueMultiplier * self.lastClose))
            return max(value, 1)
        except ValueError:
            print(self.ticker, " could not calculate trade amount")


class VixContract(FutureContract):
    def __init__(self, ticker, **kwargs):
        super().__init__(ticker, **kwargs)
        self.spotClose = 0.0
        self.spotData = None
        self.spot_ib_contract = None
        self.current_weights = (0, 0)
        self.contango_weights = (0.0, 1.0)  # (long, short)
        self.backward_weights = (0.2, 0.8)  # (long, short)

    def halt_inceptions(self):
        """Set allow inceptions to false if nearing the end of the day."""
        final_inception = datetime.now().replace(hour=14, minute=50, second=0, microsecond=0)
        if final_inception.time() < datetime.now(tz=self.timezone).replace(second=0, microsecond=0).time():
            self.allowInceptions = False
        else:
            self.allowInceptions = True


class CryptoContract(FutureContract):
    """This contract type holds two other contracts. One contract is the cash value of the cryptocurrencies and its
    data is used for the trade decisions. The other contract is a future contract of the cryptocurrencies, and is the
    contract that is traded depending on the previously mentioned decisions."""
    def __init__(self, ticker, **kwargs):
        super().__init__(ticker, **kwargs)
        self.fut_contract = None # TODO create IB crypto future contract
        self.longMa = None

    # def set_ticker(self, string):
    #     self.localSymbol = string

    def next_month(self):
        """Returns the tick of the next available contract"""
        year = int(self.ticker[-1])
        curr_month_idx = self.months.index(self.month_map[self.ticker[-2]])
        next_month_idx = (curr_month_idx + 1) % len(self.months)
        if next_month_idx < curr_month_idx:
            year += 1
        # First two letters of contract code + the next available month in fut code terms + the year of the contract
        # In __MY (GCU2)
        new_tick = self.ticker[:-2] + self.month_map[self.months[next_month_idx]] + str(year)
        return new_tick

    def roll_contract(self):
        if self.position != 0:
            return
        elif self.currVol < self.nextVol:
            print('{} rolled to {}'.format(self.ticker, self.next_tick))
            self.ib_contract = self.next_ib_contract
            self.ticker = self.next_tick

    def getTradeAmount(self, side='', size_type=''):
        try:
            trueMultiplier = self.multiplier
            value = int(self.notional // (trueMultiplier * self.lastClose))
            return max(value, 1)
        except ValueError:
            print(self.ticker, " could not calculate trade amount")


class CommodityContract(FutureContract):
    def __init__(self, ticker, **kwargs):
        super().__init__(ticker, **kwargs)

    def getTradeAmount(self, side='', size_type=''):
        return self.hardTradeValue

    def set_last_trade(self):
        if datetime.now().time() > time(16, 15):
            self.lastTrade = self.lastTrade + timedelta(days=1)
        else:
            self.lastTrade = self.lastTrade

    def set_first_trade(self):
        if datetime.now().time() > time(16, 15):
            self.firstTrade = self.firstTrade + timedelta(days=1)
        else:
            self.firstTrade = self.firstTrade


class CurrencyContract(Contract):
    def __init__(self, ticker, **kwargs):
        super().__init__(ticker, **kwargs)
        self.firstBar = time(0, 0)
        self.lastBar = time(23, 30)
        self.firstTrade = datetime.now().replace(hour=16, minute=30, second=0, microsecond=0)
        self.lastTrade = datetime.now().replace(hour=16, minute=0, second=0, microsecond=0)
        self.interval = 30

    def getTradeAmount(self, side='', size_type=''):
        try:
            value = int(self.notional)  # Must multiply by the last close for the currencies
            return round(max(value, 1), -3)  # round to the nearest thousands
        except ValueError:
            print(self.ticker, " could not calculate trade amount")
            return 0

    def set_last_trade(self):
        if datetime.now().time() > time(16, 0):
            self.lastTrade = self.lastTrade + timedelta(days=1)
        else:
            self.lastTrade = self.lastTrade

    def set_first_trade(self):
        if datetime.now().time() > time(16, 30):
            self.firstTrade = self.firstTrade
        else:
            self.firstTrade = self.firstTrade - timedelta(days=1)



