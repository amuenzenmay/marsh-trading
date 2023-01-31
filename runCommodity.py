import threading
import time as t
from datetime import datetime, time, timedelta
from threading import Thread

import util
from contracts import Contract, CommodityContract, CurrencyContract
from strategies import CommodityStrategy, CurrencyStrategy
from CurrencyConverter import CurrencyConverter
from data import Data
from IBAPI import IBapi, Connection

app = IBapi()

Currencies = {'USD.JPY': 229484467, 'USD.ZAR': 230949949, 'GBP.USD': 230949810, 'GBP.JPY': 229484470,
              'GBP.ZAR': 230949991, 'EUR.USD': 143916318, 'EUR.JPY': 229484473, 'EUR.GBP': 143916322,
              'EUR.ZAR': 230949992}
# Currencies = {'USD.JPY': 229484467, 'EUR.JPY': 229484473}


def runLoop():
    app.run()


def startIBConnection(liveAccount):
    app.nextorderId = None
    if liveAccount:
        port = 7496
    else:
        port = 7497
    app.connect('127.0.0.1', port, 123)

    # Start the socket in a thread
    api_thread = threading.Thread(target=runLoop)  # set to daemon=True
    api_thread.start()

    # Check if the API is connected via orderid
    while True:
        if isinstance(app.nextorderId, int):
            print('connected\n')
            break
        else:
            print('waiting for connection...')
            t.sleep(1)


def create_contracts_curr():
    contracts = []

    for tick in Currencies:
        symbol, curr = tick.split(".")
        contracts.append(
            CurrencyContract(tick, currency=curr, conid=Currencies[tick]))

    return contracts


def create_contracts_comm():
    """
    Creates future commodity contracts for the commodity strategy. Appends each individual contract to the
    contracts field of a CommodityStrategy object.

    :return: None
    """
    # Create Future contracts for commodities

    contracts = []

    # Platinum October
    contracts.append(
        CommodityContract('PL', first_trade=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
                          last_trade=datetime.now().replace(hour=15, minute=30, second=0, microsecond=0),
                          first_bar=time(8, 30), last_bar=time(hour=15, minute=0),
                          multiplier=50, months=[1, 4, 7, 10], exchange='NYMEX', trade_amount=1))

    # # Silver December
    contracts.append(
        CommodityContract('SI', first_trade=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
                          last_trade=datetime.now().replace(hour=15, minute=30, second=0, microsecond=0),
                          first_bar=time(8, 30), last_bar=time(hour=15, minute=0),
                          multiplier=1000, months=[3, 7, 9, 12], exchange='COMEX', trade_amount=3))

    # # GOLD October
    # contracts.append(
    #     CommodityContract('GC', first_trade=time(hour=9, minute=0), last_trade=time(hour=15, minute=30),
    #                    first_bar=time(8, 30), last_bar=time(hour=15, minute=0),
    #                    multiplier=100, months=[2, 4, 6, 8, 12], exchange='NYMEX'))

    # # Lean Hogs October (RTH actually goes to 13:05)
    contracts.append(
        CommodityContract('HE', first_trade=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
                          last_trade=datetime.now().replace(hour=13, minute=0, second=0, microsecond=0),
                          first_bar=time(8, 30), last_bar=time(hour=12, minute=30),
                          multiplier=40000, months=[2, 4, 6, 7, 8, 10, 12], exchange='CME', trade_amount=1))

    # # Live Cattle October (RTH actually goes to 13:05)
    contracts.append(
        CommodityContract('LE', first_trade=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
                          last_trade=datetime.now().replace(hour=13, minute=0, second=0, microsecond=0),
                          first_bar=time(8, 30), last_bar=time(hour=12, minute=30),
                          multiplier=40000, months=[2, 4, 6, 8, 10, 12], exchange='CME', trade_amount=2))

    # # Feeder Cattle November (RTH actually goes to 13:05)
    contracts.append(
        CommodityContract('GF', first_trade=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
                          last_trade=datetime.now().replace(hour=13, minute=0, second=0, microsecond=0),
                          first_bar=time(8, 30), last_bar=time(hour=12, minute=30),
                          multiplier=50000, months=[1, 3, 5, 8, 9, 11], exchange='CME', trade_amount=1))

    # # Corn December (RTH actually goes to 13:20)
    contracts.append(
        CommodityContract('ZC', first_trade=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
                          last_trade=datetime.now().replace(hour=13, minute=15, second=0, microsecond=0),
                          first_bar=time(8, 30), last_bar=time(hour=13, minute=0),
                          multiplier=5000, months=[3, 5, 7, 12], exchange='CBOT', trade_amount=2))

    # # Soybeans November (RTH actually goes to 13:20)
    contracts.append(
        CommodityContract('ZS', first_trade=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
                          last_trade=datetime.now().replace(hour=13, minute=15, second=0, microsecond=0),
                          first_bar=time(8, 30), last_bar=time(hour=13, minute=0),
                          multiplier=5000, months=[1, 3, 5, 7, 11], exchange='CBOT', trade_amount=1))

    # # Wheat December (RTH actually goes to 13:20)
    contracts.append(
        CommodityContract('ZW', first_trade=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
                          last_trade=datetime.now().replace(hour=13, minute=15, second=0, microsecond=0),
                          first_bar=time(8, 30), last_bar=time(hour=13, minute=0),
                          multiplier=5000, months=[3, 5, 7, 9, 12], exchange='CBOT', trade_amount=1))

    # # Bean Oil December (RTH actually goes to 13:20)
    contracts.append(
        CommodityContract('ZL', first_trade=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
                          last_trade=datetime.now().replace(hour=13, minute=15, second=0, microsecond=0),
                          first_bar=time(8, 30), last_bar=time(hour=13, minute=0),
                          multiplier=60000, months=[3, 5, 7, 12], exchange='CBOT', trade_amount=1))

    # # Soymeal December (RTH actually goes to 13:20)
    contracts.append(
        CommodityContract('ZM', first_trade=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
                          last_trade=datetime.now().replace(hour=13, minute=15, second=0, microsecond=0),
                          first_bar=time(8, 30), last_bar=time(hour=13, minute=0),
                          multiplier=100, months=[3, 5, 7, 12], exchange='CBOT', trade_amount=1))

    # # Coffee December (Cut off at 12:27)
    # contracts.append(
    #     CommodityContract('KC', first_trade=time(hour=7, minute=30), last_trade=time(hour=12, minute=27),
    #                       first_bar=time(7, 0), last_bar=time(hour=12, minute=0),
    #                       multiplier=37500, months=[3, 5, 7, 9, 12], exchange='NYBOT', trade_amount=2))

    # # Cotton March (Cut off at 13:17)
    # contracts.append(
    #     CommodityContract('CT', first_trade=time(hour=7, minute=30), last_trade=time(hour=13, minute=17),
    #                    first_bar=time(7, 0), last_bar=time(hour=13, minute=0),

    #                    multiplier=50000, months=[3, 5, 7, 12], exchange='NYBOT'))
    # # # Cocoa December (Cut off at 12:27)
    # contracts.append(
    #     CommodityContract('CC', first_trade=time(hour=4, minute=0), last_trade=time(hour=12, minute=27),
    #                    first_bar=time(3, 45), last_bar=time(hour=12, minute=0),
    #                    multiplier=10, months=[3, 5, 7, 9, 12], exchange='NYBOT'))

    # # Sugar March (Cut off at 11:57)
    # contracts.append(
    #     CommodityContract('SB', first_trade=time(hour=7, minute=30), last_trade=time(hour=11, minute=57),
    #                    first_bar=time(7, 0), last_bar=time(hour=11, minute=30),
    #                    multiplier=112000, months=[3, 5, 7, 10], exchange='NYBOT'))
    return contracts


def set_contract_months(contracts):
    """
    Iterates through the contracts field, and adjusts each local symbol to the desired contract month for the
    future contract.
    :return:
    """
    for contract in contracts:
        contract.allowInceptions = True
        if contract.ticker == 'ZM':
            contract.set_ticker('ZM   MAR 23')
            contract.conId = 460126182
        elif contract.ticker == 'ZL':
            contract.set_ticker('ZL   MAR 23')
            contract.conId = 460126255
        elif contract.ticker == 'ZW':
            contract.set_ticker('ZW   MAR 23')
            contract.conId = 434140037
        elif contract.ticker == 'ZS':
            contract.set_ticker('ZS   MAR 23')
            contract.conId = 455229196
        elif contract.ticker == 'ZC':
            contract.set_ticker('ZC   MAR 23')
            contract.conId = 460126199
        elif contract.ticker == 'KC':
            contract.set_ticker('KCH3')
            contract.conId = 415492841
        elif contract.ticker == 'SI':
            contract.set_ticker('SILH3')
            contract.conId = 553616291
        elif contract.ticker == 'PL':
            contract.set_ticker('PLJ3')
            contract.conId = 541450752
        elif contract.ticker == 'HE':
            contract.set_ticker('HEG3')
            contract.conId = 508146607
        elif contract.ticker == 'LE':
            contract.set_ticker('LEG3')
            contract.conId = 511851967
        elif contract.ticker == 'GF':
            contract.set_ticker('GFH3')
            contract.conId = 553809383


def strategy_iteration(strategy):
    """Runs the iterations of tasks that pertain to the strategy as a whole."""
    strategy.get_positions()
    strategy.shorten_positions()

    local_time = datetime.now().strftime("%H:%M:%S") + '\n'
    pos = str(strategy.positions)
    print(local_time + pos, end='\n\n')

    # Save contract months every trade iteration after any potential contract rolls
    t.sleep(15)
    if strategy.end_day():
        print("Strategy Done")
        return

    wait = (strategy.wait_time() * 60) - datetime.now().second
    t.sleep(wait)
    strategy_iteration(strategy)


def contract_iteration(strategy, contract):
    """Runs the iterations of tasks that pertain to individual contracts"""
    t.sleep(10)  # Check positions before a checking for a roll
    if contract.terminate():
        print('All Done ', contract.ticker)
        return

    current_time = datetime.now().replace(second=0, microsecond=0).time()
    if current_time == contract.lastBar and contract.ticker[:2] in ['ZC', 'ZS', 'ZW', 'ZL', 'ZM', 'CT']:
        contract.shortAlgo = True

    if contract.last_trade():
        if not contract.simple_ending():
            contract.working_bars = True  # Allow unfinished bars for the last trade of the day
            contract.shortAlgo = True

    # PL, SI, and GC have final trades at 15:30, must wait until 15:31 due to the REDI reset
    if contract.last_trade() and contract.ticker[:-2] in ['PL', 'SIL', 'GC']:
        sec = 60 - datetime.now().second  # Seconds until the next minute
        t.sleep(sec)

    strategy.get_bar_data(contract)
    if contract.data is not None and 'SIL' in contract.ticker:
        ticker_time = contract.ticker + ': ' + str(contract.position) + '\t' + datetime.now().strftime("%H:%M:%S")
        try:
            # Avoid "Gaps in blk ref_locs". If it does happen in the print, re-request data and move on
            print(ticker_time, "\n", contract.data[-10:], end='\n\n')
        except AssertionError:
            strategy.get_bar_data(contract)

    strategy.check_for_trade(contract)

    wait = (contract.time_to_next_trade() * 60) - datetime.now().second
    t.sleep(wait)
    contract_iteration(strategy, contract)


def strategy_scheduler(strategy):
    if datetime.now().replace(second=0, microsecond=0) < strategy.startTime:
        print(strategy.name, "waiting")
        while datetime.now().replace(second=0, microsecond=0) < strategy.startTime:
            t.sleep(1)
    print(strategy.name, " starting")
    strategy_iteration(strategy)


def contract_scheduler(strategy, contract):
    if datetime.now().replace(second=0, microsecond=0) < contract.firstTrade:
        print(contract.ticker, "waiting")
        while datetime.now().replace(second=0, microsecond=0) < contract.firstTrade:
            t.sleep(1)
    # while datetime.now().minute % strategy.interval >= 10:
    #     t.sleep(1)
    print(contract.ticker, "starting")
    contract_iteration(strategy, contract)


# def start_strategy(strategy):
#     if datetime.now().replace(second=0, microsecond=0) > strategy.endTime:
#         print(strategy.name, " waiting")
#         while datetime.now().replace(second=0, microsecond=0) > strategy.endTime:
#             t.sleep(5)
#     strategy_scheduler(strategy)
#
#
# def start_contract(strategy, contract):
#     if datetime.now().replace(second=0, microsecond=0) > contract.lastTrade:
#         print(contract.ticker, "waiting")
#         while datetime.now().replace(second=0, microsecond=0) > contract.lastTrade:
#             t.sleep(5)
#     contract_iteration(strategy, contract)


def start_threads(strategies):
    """Begin threads and have them run until all are complete

    :param strategies List of Strategy objects
    """
    threads = []
    for strategy in strategies:
        threads.append(Thread(target=strategy_scheduler, args=(strategy,)))
        threads[-1].name = strategy.name
        threads[-1].start()
        for con in strategy.contracts.keys():
            contract = strategy.contracts[con]
            threads.append(Thread(target=contract_scheduler, args=(strategy, contract)))
            threads[-1].name = contract.ticker
            threads[-1].start()
    while True:
        for thr in threads:
            if not thr.is_alive():
                threads.remove(thr)
        if not threads:
            break
        t.sleep(1)


if __name__ == '__main__':
    # startIBConnection(False)
    while datetime.now().replace(second=0, microsecond=0).time() < time(5, 0):
        t.sleep(1)
    c = Connection(live=True)
    app = c.app

    com_contracts = create_contracts_comm()
    set_contract_months(com_contracts)
    curr_contracts = create_contracts_curr()

    converter = CurrencyConverter()
    # Rates are from USD to the respective currency
    converter.rates = {'USD': 1,
                       'EUR': 0.926,
                       'GBP': 0.807,
                       'JPY': 134.33}

    """Future ALGOS: 'GSFF ALGOS'
    Future DMA: GSFF DMA
    use parameter: limit_time={integer} for limit orders
    use parameter: day_algo_time={integer} and/or last_algo_time={integer} for Algo trades
    limit_time is in seconds
    day_algo_time and last_algo_time are in minutes"""

    # com_endTime = datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)
    com_strategy = CommodityStrategy(app=app, account='U11095454', order_type='Adaptive',
                                     day_algo_time=5)
    com_strategy.set_contracts(com_contracts, 10)
    com_strategy.set_start_time()
    com_strategy.set_end_time()

    # curr_endTime = datetime.now().replace(hour=16, minute=15, second=0, microsecond=0) + timedelta(days=1)
    # curr_startTime = datetime.now().replace(hour=16, minute=30, second=0, microsecond=0)
    curr_strategy = CurrencyStrategy(app=app, account='U11095454', notional=355590, order_type='Market',
                                     day_algo_time=20, limit_time=1500,
                                     barType='MIDPOINT')
    curr_strategy.set_start_time()
    curr_strategy.set_end_time()
    curr_strategy.set_contracts(curr_contracts)


    for tick in curr_strategy.contracts:
        con = curr_strategy.contracts[tick]
        con.notional = converter.convert('USD', con.ticker[:3], con.notional)

    strategies = [com_strategy, curr_strategy]
    start_threads(strategies)
    app.disconnect()
