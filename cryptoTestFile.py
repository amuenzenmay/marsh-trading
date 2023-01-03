import time as t

from datetime import datetime, time
from threading import Thread

import pandas as pd

import util
from contracts import Contract, VixThirtyContract, CryptContract
from strategies import StockThirtyMin, VixThirtyMin, Crypto
from IBAPI import IBapi, Connection

app = IBapi()
locates = pd.DataFrame()
# Stocks = ['APA', 'TEAM', 'NFLX', 'PINS', 'DDOG', 'DASH', 'DOCU', 'LI', 'CCL', 'ZS', 'AFRM', 'PLUG',
#           'ETSY', 'AR', 'DKNG', 'SQ', 'SE', 'SHOP', 'SNAP', 'AAL', 'RIVN', 'ZM', 'TWLO', 'EQT', 'COIN',
#           'RBLX', 'TSLA', 'ENPH', 'ROKU', 'TGT', 'WBD', 'MDB', 'CRWD', 'SNOW', 'UBER', 'NIO', 'MELI', 'AA',
#           'UAL', 'PLTR']
# Stocks = ['AAPL']
# Stocks = {'AAPL': 265598, 'MSFT': 272093, 'TEAM': 589316251}
Stocks = {'APA': 474515500, 'TEAM': 589316251, 'NFLX': 15124833, 'PINS': 360975915, 'DDOG': 383858515,
          'DASH': 459309417, 'DOCU': 316073742, 'LI': 436980133, 'CCL': 5516, 'ZS': 310621426, 'AFRM': 465119069,
          'PLUG': 88385302, 'ETSY': 190480965, 'AR': 135942630, 'DKNG': 560105364, 'SQ': 212671971, 'SE': 292735472,
          'SHOP': 195014116, 'SNAP': 268060148, 'AAL': 139673266, 'RIVN': 525768800, 'ZM': 361181057, 'TWLO': 237794430,
          'EQT': 57698865, 'COIN': 481691285}
#           'RBLX', 'TSLA', 'ENPH', 'ROKU', 'TGT', 'WBD', 'MDB', 'CRWD', 'SNOW', 'UBER', 'NIO', 'MELI', 'AA',
#           'UAL', 'PLTR'}


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
            Contract(tick, exchange='SMART', allowInceptions=inceptions, last_trade=time(14, 58), conid=Stocks[tick]))

    return contracts


def create_contracts_vix():
    """
    Creates a future contract for the VIX

    return: [Contract]
    """
    vix_contract = VixThirtyContract('VX', first_trade=time(9, 0), last_trade=time(hour=15, minute=10),
                                     first_bar=time(8, 30), last_bar=time(hour=15, minute=0, second=0),
                                     multiplier=1000, exchange='CFE')
    vix_contract.current_weights = (0, 1.0)

    return [vix_contract]


def create_contracts_crypto():
    """
    Creates a contract for the Cryptos
    return: [Contract]
    """
    # TODO add starting and ending times for crypto contracts
    eth_contract = CryptContract('MBT', multiplier=0.1, exchange='CME')
    bit_contract = CryptContract('MET', multiplier=0.1, exchange='CME')

    return [eth_contract, bit_contract]


def set_contract_months(contracts):
    """
    Iterates through the contracts field, and adjusts each local symbol to the desired contract month for the
    future contract.
    :return:
    """
    for contract in contracts:
        contract.allowInceptions = True
        if contract.ticker == 'VX':
            contract.set_ticker('VXF3')
            contract.conId = 558276419
        elif contract.ticker == 'MBT':
            contract.set_ticker('MBTF3')
            contract.conId = 576721268
        elif contract.ticker == 'MET':
            contract.set_ticker('METF3')
            contract.conId = 576721278


def get_long_ma(strategy):
    for tick in strategy.contracts.keys():
        con = strategy.contracts[tick]
        strategy.get_long_ma(con)


def strategy_iteration(strategy):
    """Runs the iterations of tasks that pertain to the strategy as a whole."""
    strategy.get_positions()
    strategy.update_strategy_notional()
    # print(datetime.now().strftime("%H:%M:%S"))
    # print(strategy.twsPositions, end='\n\n')

    strategy.get_contract_pnl("TWS")
    # print(strategy.pnl, end='\n\n')

    strategy.combine_pnl_position()
    local_time = datetime.now().strftime("%H:%M:%S") + '\n'
    pos = str(strategy.positions)
    print(local_time + pos, end='\n\n')

    if strategy.end_day():
        print("Strategy Done")
        return

    wait = (strategy.wait_time() * 60) - datetime.now().second
    t.sleep(wait)
    strategy_iteration(strategy)


def contract_iteration(strategy, contract):
    """Runs the iterations of tasks that pertain to individual contracts"""
    if contract.terminate():
        print('All Done ', contract.ticker)
        return
    t.sleep(10)

    if contract.last_trade():
        contract.working_bars = True  # Allow unfinished bars for the last trade of the day
        if contract.simple_ending():
            contract.shortAlgo = True

    strategy.get_bar_data(contract)
    if 'VX' in contract.ticker:
        strategy.get_spot_data(contract)
        print("Spot: {}\tContract: {}".format(contract.spotClose, contract.lastClose))

    if contract.data is not None and (contract.ticker == 'ROKU' or 'VX' in contract.ticker):
        ticker_time = contract.ticker + ': ' + str(contract.position) + '\t' + datetime.now().strftime("%H:%M:%S")
        print(ticker_time)
        try:
            # Avoid "Gaps in blk ref_locs". If it does happen in the print, re-request data and move on
            print(contract.data[-10:], end='\n\n')
        except AssertionError:
            strategy.get_bar_data(contract)

    if contract.last_trade() and strategy.name == 'Stk30':
        strategy.check_for_adjustment(contract)
    else:
        strategy.check_for_trade(contract)

    wait = (contract.time_to_next_trade() * 60) - datetime.now().second
    t.sleep(wait)
    contract_iteration(strategy, contract)


def strategy_scheduler(strategy):
    # while datetime.now().minute % strategy.interval != 0:
    #     t.sleep(1)
    strategy_iteration(strategy)


def contract_scheduler(strategy, contract):
    while datetime.now().replace(second=0, microsecond=0).time() < contract.firstTrade:
        t.sleep(1)
    # while datetime.now().minute % strategy.interval >= (strategy.interval - strategy.day_algo_time):
    #     t.sleep(1)
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

    c = Connection(live=False)  # For TWS connection
    app = c.app
    # get_locates()

    # STOCK STRATEGY at TWS
    stk_contracts = create_contracts_stk()
    stk_strategy = StockThirtyMin(app=app, account='DU6393014', notional=20, order_type='Market', day_algo_time=25,
                                  endTime=time(14, 58), barType='MIDPOINT')  # Should be TWAP

    # Retrieves SDIV and locates for contracts, and set up contracts to receive data from IB
    stk_strategy.set_contracts(stk_contracts)

    # VIX STRATEGY at TWS
    vix_contracts = create_contracts_vix()
    set_contract_months(vix_contracts)
    vix_strategy = VixThirtyMin(app=app, account='DU6393014', notional=10, order_type='Market',
                                limit_time=180, day_algo_time=1.5, endTime=time(15, 10), barType='MIDPOINT')  # should be limit
    # Set up the contract to be able to request data from IB
    vix_strategy.set_contracts(vix_contracts)

    # CRYPTO STRATEGY at TWS
    crypto_contracts = create_contracts_crypto()
    set_contract_months(crypto_contracts)
    crypto_strategy = Crypto(app=app, account='DU6393014', notional=10, order_type='Market', startTime=time(2, 0),
                             endTime=time(15, 30), barType='MIDPOINT')
    crypto_strategy.set_contracts(crypto_contracts)
    get_long_ma(crypto_strategy)


    # Only the strategies in this list will be executed.
    strategies = [stk_strategy, vix_strategy, crypto_strategy]
    start_threads(strategies)
    app.disconnect()
