import unittest
from strategies import *
from contracts import *
import pytz
import util
from IBAPI import *


class MyTestCase(unittest.TestCase):
    def test_something(self):
        self.assertEqual(True, False)  # add assertion here

    def test_30min_long(self):
        con = Contract()
        con.ticker = 'AAPL'
        con.data = [1.01, 1.00, 0.99, 0.98]
        dec = ThirtyMin()
        dec.contract = con

        long = dec.long_signal()
        self.assertEqual(True, long, "Supposed to be long")

    def test_30min_long2(self):
        con = Contract()
        con.ticker = 'AAPL'
        con.data = [1.01, 1.00, 1.00, 1.01]
        dec = ThirtyMin()
        dec.contract = con

        long = dec.long_signal()
        self.assertEqual(False, long, "Should not be long")

    def test_30min_short(self):
        con = Contract()
        con.ticker = 'AAPL'
        con.data = [456.835, 456.84, 456.865, 456.87]
        dec = ThirtyMin()
        dec.contract = con

        short = dec.short_signal()
        self.assertEqual(True, short, "Supposed to be short")

    def test_30min_short2(self):
        con = Contract()
        con.ticker = 'AAPL'
        con.data = [34.49, 34.495, 34.520, 34.519]
        dec = ThirtyMin()
        dec.contract = con

        short = dec.short_signal()
        self.assertEqual(False, short, "Should not be long")

    def test_30min_close_short(self):
        con = Contract()
        con.ticker = 'AAPL'
        con.data = [456.835, 456.84, 456.825, 456.87]
        dec = ThirtyMin()
        dec.contract = con

        con.position = -1
        close = dec.close_short_signal()
        self.assertFalse(close, "Should not close")

        con.position = 0
        close = dec.close_short_signal()
        self.assertFalse(close, "Should not close a nonexistent position")

    def test_30min_close_short2(self):
        con = Contract()
        con.ticker = 'AAPL'
        con.data = [34.505, 34.495, 34.520, 34.50]
        dec = ThirtyMin()
        dec.contract = con

        con.position = -1
        close = dec.close_short_signal()
        self.assertTrue(close, "Should close")

        con.position = 0
        close = dec.close_short_signal()
        self.assertFalse(close, "Should not close a nonexistent position")

    def test_next_trade_LAST(self):
        con = VixContract('VX', first_trade=time(9, 0), last_trade=time(hour=15, minute=10),
                          first_bar=time(8, 30), last_bar=time(hour=15, minute=0, second=0),
                          multiplier=1000, exchange='CFE', interval=30)
        currTime = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
        wait = con.time_to_next_trade(currTime)
        self.assertEqual(10, wait, 'Incorrect Value for wait')


if __name__ == '__main__':
    unittest.main()
