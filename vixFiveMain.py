import threading
import time as t
from datetime import datetime, time
from threading import Thread
from contracts import FutureContract
from strategies import VixFiveMin
from data import Data
from IBAPI import IBapi, Connection
import logging

logging.basicConfig(filename="vixFiveTesting.log", filemode='w', format='%(asctime)s %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
LOG_INFO = True


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


def create_contracts():
    """
    Creates a future contract for the VIX

    :return: None
    """
    contracts = []
    contracts.append(
        FutureContract('VX', first_trade=time(hour=10, minute=30, second=0), last_trade=time(hour=15, minute=10),
                       first_bar=time(8, 30), last_bar=time(hour=15, minute=5, second=0),
                       multiplier=1000, exchange='CFE'))

    return contracts


def set_contract_months(contracts):
    """
    Iterates through the contracts field, and adjusts each local symbol to the desired contract month for the
    future contract.
    :return:
    """
    for contract in contracts:
        # TODO GC is a manual change, still need to incorporate a universal change
        contract.allowInceptions = True
        if contract.ticker == 'VX':
            contract.set_ticker('VXU2')


def strategy_iteration(strategy):
    """Runs the iterations of tasks that pertain to the strategy as a whole."""
    strategy.get_positions()
    strategy.update_strategy_notional()
    # TODO Log or print positions
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
    # if contract.terminate():
    #     print('All Done ', contract.ticker)
    #     return
    # t.sleep(10)

    if contract.last_trade() and not contract.simple_ending():
        contract.working_bars = True  # Allow unfinished bars for the last trade of the day
        contract.shortAlgo = True

    strategy.get_bar_data(contract)
    if contract.data is not None and 'VX' in contract.ticker:
        ticker_time = contract.ticker + ': ' + str(contract.position) + '\t' + datetime.now().strftime("%H:%M:%S")
        print(ticker_time)
        print(contract.data[-10:], end='\n\n')

    if contract.final_execution():
        contract.allowInceptions = False
        strategy.close_position(contract)
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
    # while datetime.now().replace(second=0, microsecond=0).time() < contract.firstTrade:
    #     t.sleep(1)
    # while datetime.now().minute % strategy.interval != 0:
    #     t.sleep(1)
    contract_iteration(strategy, contract)


def start_threads(strategies):
    """Begin threads and have them run until all are complete

    :param strategies List of Strategy objects
    """
    threads = []
    for strategy in strategies:
        threads.append(Thread(target=strategy_scheduler, args=(strategy,)))
        threads[-1].start()
        for con in strategy.contracts.keys():
            contract = strategy.contracts[con]
            threads.append(Thread(target=contract_scheduler, args=(strategy, contract)))
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
        VIX ALGO: 'GSFF ALGOS'
        VIX Limit or Market: 'GSFF DMA'

        VALID ORDER TYPES:
            'Market'
            'Limit'
            'TWAP'
            
        Algo times are in minutes
        Limit times are in seconds
        """
    c = Connection()
    app = c.app

    vix_contract = create_contracts()
    set_contract_months(vix_contract)
    vix_strategy = VixFiveMin(app=app, account='AVM7F', order_type='Limit', dma_exchange='GSFF DMA',
                              algo_exchange='GSFF ALGOS', notional=1452538,
                              day_algo_time=1.5, limit_time=180, endTime=time(15, 10))
    vix_strategy.set_contracts(vix_contract)

    strategies = [vix_strategy]
    start_threads(strategies)

    app.disconnect()
