import threading
import time as t
import sched
from datetime import datetime, time
from threading import Thread
from contracts import Contract
from strategies import StockFiveMin
from data import Data
from IBAPI import IBapi, Connection

Stocks = ['TTD', 'DDOG', 'ZS', 'ENPH', 'TSLA', 'DASH', 'BABA', 'Z', 'ZM', 'PENN', 'CHWY', 'NVDA', 'ETSY',
          'AA', 'AMD', 'UBER', 'SE', 'UAL', 'AMC', 'DOCU', 'RIVN', 'GME', 'UPST', 'PTON', 'AFRM', 'RBLX', 'NET',
          'CAR', 'ROKU', 'PLUG', 'XPEV', 'MDB', 'MSTR', 'SNOW', 'U', 'NIO', 'CVNA', 'TDOC', 'COIN']


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
    for tick in Stocks:
        contracts.append(
            # TODO remove end and last execution
            Contract(tick, exchange='SMART', first_trade=time(9, 40), last_trade=time(hour=14, minute=55),
                     first_bar=time(8, 30), last_bar=time(hour=14, minute=45)))

    return contracts


def strategy_iteration(strategy):
    """Runs the iterations of tasks that pertain to the strategy as a whole."""
    if strategy.end_day():
        print('Strategy Done')
        return

    strategy.get_positions()
    strategy.update_strategy_notional()
    # TODO Log or print positions
    print(datetime.now().strftime("%H:%M:%S"))
    print(strategy.positions)

    wait = strategy.interval * 60
    t.sleep(wait)
    strategy_iteration(strategy)


def contract_iteration(strategy, contract):
    """Runs the iterations of tasks that pertain to individual contracts"""
    if contract.terminate():
        print('All Done ', contract.ticker)
        return

    if contract.last_trade() and not contract.simple_ending():
        contract.working_bars = True  # Allow unfinished bars for the last trade of the day
        contract.shortAlgo = True

    strategy.get_bar_data(contract)
    if contract.final_execution():
        strategy.close_position(contract)
    else:
        strategy.check_for_trade(contract)

    wait = contract.time_to_next_trade() * 60
    t.sleep(wait)
    contract_iteration(strategy, contract)


def strategy_scheduler(strategy):
    while datetime.now().minute % strategy.interval != 0:
        t.sleep(1)
    strategy_iteration(strategy)


def contract_scheduler(strategy, contract):
    while datetime.now().replace(second=0, microsecond=0).time() < contract.firstTrade:
        t.sleep(1)
    while datetime.now().minute % strategy.interval != 0:
        t.sleep(1)
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
    c = Connection()
    app = c.app

    stk_contracts = create_contracts()
    stk_strategy = StockFiveMin(app=app, account='DEMO', notional=1000000, exchange='DEMO algo', order_type='TWAP_redi',
                                limit_time=60)
    stk_strategy.set_contracts(stk_contracts)
    strategies = [stk_strategy]
    start_threads(strategies)

    app.disconnect()
