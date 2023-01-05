import time as t

from datetime import datetime, time
from threading import Thread

import pandas as pd

from contracts import Contract, VixContract
from strategies import StockThirtyMin, VixThirtyMin
from IBAPI import IBapi, Connection

app = IBapi()
locates = pd.DataFrame()
Stocks = ['APA', 'TEAM', 'NFLX', 'PINS', 'DDOG', 'DASH', 'DOCU', 'LI', 'CCL', 'ZS', 'AFRM', 'PLUG',
          'ETSY', 'AR', 'DKNG', 'SQ', 'SE', 'SHOP', 'SNAP', 'AAL', 'RIVN', 'ZM', 'TWLO', 'EQT', 'COIN',
          'RBLX', 'TSLA', 'ENPH', 'ROKU', 'TGT', 'WBD', 'MDB', 'CRWD', 'SNOW', 'UBER', 'NIO', 'MELI', 'AA',
          'UAL', 'PLTR']
csv_file_path = r'C:\Users\Augie\Downloads\AT2W1209_Short_Locate_Result (1).csv'


def get_locates():
    global locates
    locates = pd.read_csv(csv_file_path, usecols=['Symbol', ' Filled'])
    locates.set_index('Symbol', inplace=True)
    print(locates)


def create_contracts():
    """
    Creates a future contract for the VIX

    :return: None
    """
    # Create stock contracts
    contracts = []
    for tick in Stocks:
        inceptions = True
        if tick in locates.index and locates.loc[tick][' Filled'] == 0:
            inceptions = False
        contracts.append(
            Contract(tick, exchange='SMART', allowInceptions=inceptions, last_trade=time(14, 58)))

    return contracts


def create_contracts_vix():
    """
    Creates a future contract for the VIX

    :return: None
    """
    vix_contract = VixContract('VX', first_trade=time(9, 0), last_trade=time(hour=15, minute=10),
                               first_bar=time(8, 30), last_bar=time(hour=15, minute=0, second=0),
                               multiplier=1000, exchange='CFE')
    vix_contract.current_weights = (0, 1.0)

    return [vix_contract]


def set_contract_months(contracts):
    """
    Iterates through the contracts field, and adjusts each local symbol to the desired contract month for the
    future contract.
    :return:
    """
    for contract in contracts:
        contract.allowInceptions = True
        if contract.ticker == 'VX':
            contract.set_ticker('VXQ2')


def strategy_iteration(strategy):
    """Runs the iterations of tasks that pertain to the strategy as a whole."""
    strategy.get_positions()
    strategy.update_strategy_notional()
    print(datetime.now().strftime("%H:%M:%S"))
    print(strategy.positions, end='\n\n')

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

    # Set the SRSE username and Password:
    username = 'rzm.drasmussen'
    password = 'KfW983#'

    c = Connection()  # For TWS connection
    app = c.app
    # get_locates()

    # STOCK STRATEGY at SRSE
    stk_contracts = create_contracts()
    stk_strategy = StockThirtyMin(app=app, account='RZMAVM5', notional=8854492, order_type='TWAP_redi', day_algo_time=25,
                                  endTime=time(14, 58))
    stk_strategy.srse_username = username
    stk_strategy.srse_password = password
    # Retrieves SDIV and locates for contracts, and set up contracts to receive data from IB
    stk_strategy.set_contracts(stk_contracts)

    # VIX STRATEGY at REDI
    vix_contracts = create_contracts_vix()
    set_contract_months(vix_contracts)
    vix_strategy = VixThirtyMin(app=app, account='AVM6F', notional=1842501, order_type='Limit',
                                dma_exchange='GSFF DMA', limit_time=180,
                                algo_exchange='GSFF ALGOS', day_algo_time=1.5, endTime=time(15, 10))
    # Set up the contract to be able to request data from IB
    vix_strategy.set_contracts(vix_contracts)

    # Only the strategies in this list will be executed.
    strategies = [stk_strategy, vix_strategy]
    start_threads(strategies)
    app.disconnect()
