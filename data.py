import time as t
# import refinitiv.dataplatform as ek
from datetime import date, datetime, timedelta, timezone
from random import random

import eikon as ek
import pandas as pd
import pytz
import win32com.client
from win32com.client import pythoncom, VARIANT

# q = win32com.client.Dispatch("REDI.Query")

# ek.set_app_key('71f602a117a3487e82c765770a9e310c78cdc613')
# ek.set_log_level(logging.DEBUG)

requestId = 250


def next_request_id():
    global requestId
    requestId += 1
    return requestId


class Data:

    def __init__(self, contract, **kwargs):
        self.tick = contract.ticker
        self.contract = contract
        self.start_date = (date.today() - timedelta(days=4)).strftime('%Y-%m-%d')
        # self.start_date = (date.today() - timedelta(days=4)).strftime('%Y-%m-%d')
        self.end_date = datetime.now().replace(microsecond=0, second=0).strftime('%Y-%m-%dT%H:%M:%S')
        self.app = kwargs.get('app', None)
        self.account = kwargs.get('account', '')

    def requestDataEikon(self, interval, data_timezone=pytz.timezone('America/Chicago'), fields=None, parameters=None):
        """Returns a dataframe with bars of the length set my the interval parameter. Gets a timeseries from
        Eikon containing minute bars, and congregates the minute data into the desired bar size.

        :return DataFrame
        """
        if parameters is None:
            parameters = {'SDate': self.start_date, 'EDate': self.end_date, 'Frq': 'D'}
        if fields is None:
            fields = ["TR.PriceClose.date", "TR.PriceClose"]
        # time series with HIGH, LOW, OPEN, CLOSE, COUNT, VOLUME
        stk = self.tick
        start = self.start_date
        end = self.end_date
        t.sleep(random())
        data_1min = ek.get_timeseries(stk, start_date=start, end_date=end, interval='minute')
        for _ in range(60):
            if data_1min is not None:
                break
            t.sleep(0.25)
        if data_1min is None:
            return None
        newDFs = {}
        for sym in self.tick:
            timestamps = []
            results = []
            idx = 0
            start_slice = data_1min[sym].index[idx]
            while start_slice.minute % interval != 1:
                idx += 1
                start_slice = data_1min[sym].index[idx]
            while True:
                end_slice = start_slice + timedelta(minutes=interval - 1)
                # Dataframe of minute bars from start_slice to end_slice
                # Some minute bars from the time period may be missing.
                interval_slice = data_1min[sym].loc[start_slice: end_slice]
                try:
                    data = self.thirtyMinuteBarExtraction(interval_slice)  # HIGH, LOW, OPEN, CLOSE, COUNT, VOLUME
                except IndexError:
                    start_slice = start_slice + timedelta(minutes=interval)
                    continue
                temp_slice = start_slice.to_pydatetime().replace(tzinfo=timezone.utc).astimezone(tz=data_timezone)
                if temp_slice.time() < self.contract.lastBar:
                    temp_slice = temp_slice - timedelta(minutes=1)
                    timestamps.append(temp_slice)
                    results.append(data)
                start_slice = start_slice + timedelta(minutes=interval)
                if start_slice > data_1min[sym].index[-1]:
                    break
            # labels = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']
            labels = ['Close']
            data_new_interval = pd.DataFrame.from_records(results, columns=labels)
            data_new_interval['Time'] = timestamps
            data_new_interval.set_index(['Time'], inplace=True)
            newDFs[sym] = data_new_interval
        return newDFs

    def thirtyMinuteBarExtraction(self, df):
        """Returns a list of values from a dataframe in the order of: OPEN, HIGH, LOW, CLOSE, VOLUME.

        :return DataFrame
        """
        # return [df['OPEN'][0], df['HIGH'].max(), df['LOW'].min(),
        #         df['CLOSE'][-1], int(df['VOLUME'].sum())]
        return [df['CLOSE'][-1]]

    def requestDataIBAPI(self, ib_contract, interval, contract, type='TRADES'):
        req_id = next_request_id()
        contract.data_id = req_id
        self.app.idMap[req_id] = ib_contract.symbol
        self.app.barData[req_id] = []
        self.app.timezones[req_id] = contract.timezone
        self.app.reqHistoricalData(req_id, ib_contract, '', '4 D', str(interval) + ' mins', type, 0, 1,
                                   False, [])

    def requestLongDataIBAPI(self, ib_contract, interval, contract, bar_type='AGGTRADES'):
        req_id = next_request_id()
        contract.data_id = req_id
        self.app.idMap[req_id] = ib_contract.symbol
        self.app.barData[req_id] = []
        self.app.timezones[req_id] = contract.timezone
        self.app.reqHistoricalData(req_id, ib_contract, '', '2 M', str(interval) + ' mins', bar_type, 0, 1,
                                   False, [])

    def requestVolumeIBAPI(self, ib_contract, contract):
        req_id = next_request_id()
        contract.data_id = req_id
        self.app.idMap[req_id] = ib_contract.symbol
        self.app.barData[req_id] = []
        self.app.reqHistoricalData(req_id, ib_contract, '', '1 W', '1 day', 'TRADES', 0, 1,
                                   False, [])

    def request_position(self, source):
        """For non-stock contracts, request positions from the REDI API. Takes a dictionary of tickers and their
        contracts as input and the account the contracts belong to.
        For stock contracts request the position from SRSE
        """
        if source == "REDI":
            q = win32com.client.Dispatch("REDI.Query", pythoncom.CoInitialize())

            # Prepare a variable which can handle returned values from submit method of the order object.
            row = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, 0)
            cellVar = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, 0)
            cellVal = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, 0)
            retVar = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, 0)

            # add watch on accounts
            myaccounts = [self.contract.account]
            for account in myaccounts:
                tmpVal = q.AddWatch("2", "", account, retVar)

            # Prepare the query
            vTable = "Position"
            vWhere = "true"
            tmpVal = q.Submit(vTable, vWhere, retVar)

            for i in range(0, q.RowCount):  # Iterate through every row of the table
                cellVar.value = "Symbol"
                ret = q.GetCell(i, cellVar, cellVal, retVar)
                ticker = cellVal.value
                if ticker != self.tick:
                    continue

                cellVar.value = "Position"
                ret = q.GetCell(i, cellVar, cellVal, retVar)
                position = cellVal.value
                self.contract.position = position

                cellVar.value = "PandL"
                ret = q.GetCell(i, cellVar, cellVal, retVar)
                self.contract.pnl = cellVal.value
        elif source == "TWS":
            app = self.app
            app.reqPositions()
            try:
                if self.tick in app.positions.index:
                    self.contract.position = app.positions.loc[self.tick, "Position"]
            except IndexError:
                pass

    def request_pnl(self, source):
        if source == 'TWS':
            req_id = next_request_id()
            self.app.reqPnL(req_id, self.account, '')
            t.sleep(0.25)
        pass

    def request_pnl_single(self, source):
        if source == 'TWS':
            req_id = next_request_id()
            self.app.idMap[req_id] = self.tick
            self.app.reqPnLSingle(req_id, self.account, "", self.contract.conId)
        pass


if __name__ == '__main__':
    pass
