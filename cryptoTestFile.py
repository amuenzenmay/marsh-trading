import time as t

from datetime import datetime, time
from threading import Thread

import pandas as pd

import util
from contracts import Contract, VixContract, CryptoContract
from strategies import StockThirtyMin, VixFiveMin, Crypto
from IBAPI import IBapi, Connection

app = IBapi()

Stocks = {'CAR': 40673933, 'AFRM': 465119069, 'DOCU': 316073742, 'MDB': 292833239, 'RBLX': 476026060,
          'RIVN': 525768800, 'CROX': 37792836, 'ROKU': 290651477, 'SNAP': 268060148, 'SHOP': 195014116,
          'TSLA': 76792991, 'SNOW': 444884769, 'CCL': 5516, 'DASH': 459309417, 'SQ': 212671971, 'TEAM': 589316251,
          'TWLO': 237794430, 'DDOG': 383858515, 'ZS': 310621426, 'KMX': 2586156, 'GME': 36285627, 'AA': 251962528,
          'W': 168812158, 'U': 445423543, 'NET': 382633646, 'CELH': 71364351, 'PARA': 393897513, 'OKTA': 272356196,
          'SE': 292735472, 'TTD': 248755440}


def create_contracts_stk():
    """
    Creates a future contract for the VIX

    :return: None
    """
    # Create stock contracts
    contracts = []
    for tick in Stocks.keys():
        inceptions = True
        contracts.append(
            Contract(tick, exchange='SMART', allowInceptions=inceptions,
                     last_trade=datetime.now().replace(hour=14, minute=58, second=0, microsecond=0),
                     conid=Stocks[tick]))

    return contracts


def create_contracts_vix():
    """
    Creates a future contract for the VIX

    return: [Contract]
    """
    vix_contract = VixContract('VX', first_trade=datetime.now().replace(hour=10, minute=30, second=0, microsecond=0),
                               last_trade=datetime.now().replace(hour=15, minute=10, second=0, microsecond=0),
                               first_bar=time(8, 30), last_bar=time(hour=15, minute=5, second=0),
                               multiplier=1000, exchange='CFE')
    vix_contract.current_weights = (0, 1.0)

    return [vix_contract]


def create_contracts_crypto():
    """
    Creates a contract for the Cryptos
    return: [Contract]
    """
    eth_contract = CryptoContract('ETH', multiplier=50, exchange='CME',
                                  first_trade=datetime.now().replace(hour=2, minute=0, second=0, microsecond=0),
                                  first_bar=time(1, 30),
                                  last_trade=datetime.now().replace(hour=15, minute=30, second=0, microsecond=0),
                                  last_bar=time(15, 0))
    bit_contract = CryptoContract('BRR', multiplier=5, exchange='CME',
                                  first_trade=datetime.now().replace(hour=2, minute=0, second=0, microsecond=0),
                                  first_bar=time(1, 30),
                                  last_trade=datetime.now().replace(hour=15, minute=30, second=0, microsecond=0),
                                  last_bar=time(15, 0))

    return [eth_contract]


def set_contract_months(contracts):
    """
    Iterates through the contracts field, and adjusts each local symbol to the desired contract month for the
    future contract.
    :return:
    """
    for contract in contracts:
        contract.allowInceptions = True
        if contract.ticker == 'VX':
            contract.set_ticker('VXG3')
            contract.conId = 563580774
        elif contract.ticker == 'MBT':
            contract.set_ticker('MBTF3')
            contract.conId = 576721268
        elif contract.ticker == 'MET':
            contract.set_ticker('METF3')
            contract.conId = 576721278
        elif contract.ticker == 'ETH':
            contract.set_ticker('ETHF3')
            contract.conId = 576721275
        elif contract.ticker == 'BRR':
            contract.set_ticker('BTCF3')
            contract.conId = 576721265


def get_long_ma(strategy):
    for tick in strategy.contracts.keys():
        con = strategy.contracts[tick]
        strategy.get_long_ma(con)
        print(tick, " 460SMA: ", con.longMa)


def strategy_iteration(strategy):
    """Runs the iterations of tasks that pertain to the strategy as a whole."""
    strategy.get_positions()
    # strategy.get_contract_pnl("TWS")
    # strategy.combine_pnl_position()
    # strategy.update_strategy_notional()
    strategy.shorten_positions()

    local_time = datetime.now().strftime("%H:%M:%S") + '\n'
    pos = str(strategy.positions)
    print(local_time + pos, end='\n\n')

    if strategy.end_day():
        print(strategy.name, " Done")
        return

    wait = (strategy.wait_time() * 60) - datetime.now().second
    t.sleep(wait)
    strategy_iteration(strategy)


def contract_iteration(strategy, contract):
    """Runs the iterations of tasks that pertain to individual contracts"""
    if contract.terminate():
        # print('All Done ', contract.ticker)
        return
    t.sleep(10)

    if contract.last_trade():
        contract.working_bars = True  # Allow unfinished bars for the last trade of the day
        if contract.simple_ending():
            contract.shortAlgo = True

    strategy.get_bar_data(contract)
    if 'VX' in contract.ticker:
        print("Contract: {}".format(contract.lastClose))

    if contract.data is not None and (
            contract.ticker == 'ROKU' or 'VX' in contract.ticker or 'ETH' in contract.ticker
            or 'BRR' in contract.ticker):
        ticker_time = contract.ticker + ': ' + str(contract.position) + '\t' + datetime.now().strftime("%H:%M:%S")
        # print(ticker_time)
        try:
            # Avoid "Gaps in blk ref_locs". If it does happen in the print, re-request data and move on
            print(ticker_time, "\n", contract.data[-10:], end='\n\n')
        except AssertionError:
            strategy.get_bar_data(contract)

    if contract.last_trade() and strategy.name == 'Stk30':
        strategy.check_for_adjustment(contract)
    elif contract.last_trade() and 'VX' in contract.ticker:
        strategy.close_position(contract)
    else:
        strategy.check_for_trade(contract)

    contract.allowAdjustment = strategy.allow_adjustment
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
    while datetime.now().replace(second=0, microsecond=0) < contract.firstTrade:
        t.sleep(1)
    while datetime.now().minute % strategy.interval >= (strategy.interval - strategy.day_algo_time):
        t.sleep(1)
    contract_iteration(strategy, contract)


def start_threads(strategy_list):
    """Begin threads and have them run until all are complete

    :param strategy_list List of Strategy objects
    """
    threads = []
    for strategy in strategy_list:
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
    """
    EXCHANGES/ DESTINATIONS
    FUT DMA: 'GSFF DMA'
    FUT ALGO: 'GSFF ALGOS'
    STK TWAP_redi: 'GSGU Algo'
    STK Limit: 'GSGU DMA' (or 'GSCE DMA' but it wasn't working)
    
    VALID ORDER TYPES:
        'Market'
        'Limit'
        'TWAP_redi'
        'IS_redi'
        'VWAP_redi'
    """
    # TODO adjust at the beginning of the run
    c = Connection(live=True)  # For TWS connection
    app = c.app

    # STOCK STRATEGY at TWS
    stk_contracts = create_contracts_stk()
    stk_strategy = StockThirtyMin(app=app, account='U11095454', notional=86175, order_type='Adaptive',
                                  day_algo_time=25,
                                  endTime=datetime.now().replace(hour=14, minute=58, second=0, microsecond=0),
                                  barType='TRADES')  # Should be TWAP
    stk_strategy.set_contracts(stk_contracts)

    # VIX STRATEGY at TWS
    vix_contracts = create_contracts_vix()
    set_contract_months(vix_contracts)
    vix_strategy = VixFiveMin(app=app, account='U11095454', notional=20000, order_type='Adaptive',
                              limit_time=180, day_algo_time=1.5,
                              startTime=datetime.now().replace(hour=10, minute=30, second=0, microsecond=0),
                              endTime=datetime.now().replace(hour=15, minute=10, second=0, microsecond=0),
                              barType='TRADES')  # should be limit
    # Set up the contract to be able to request data from IB
    vix_strategy.set_contracts(vix_contracts)

    # CRYPTO STRATEGY at TWS
    crypto_contracts = create_contracts_crypto()
    set_contract_months(crypto_contracts)
    crypto_strategy = Crypto(app=app, account='U11095454', notional=65000, order_type='Adaptive',
                             startTime=datetime.now().replace(hour=2, minute=0, second=0, microsecond=0),
                             endTime=datetime.now().replace(hour=15, minute=30, second=0, microsecond=0),
                             day_algo_time=20, barType='AGGTRADES')
    crypto_strategy.set_contracts(crypto_contracts)
    get_long_ma(crypto_strategy)

    # Only the strategies in this list will be executed.
    strategies = [stk_strategy, vix_strategy, crypto_strategy]

    start_threads(strategies)

    print("\n\nPnL by Strategy:")
    for strategy in strategies:
        strategy.get_positions()
        strategy.get_contract_pnl("TWS")
        strategy.combine_pnl_position()
        strategy.update_strategy_notional()
        print(strategy.name, ":\t", strategy.notional)
    app.disconnect()
