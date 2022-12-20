import pandas as pd
import pythoncom
import pytz
import win32com.client
from win32com.client import pythoncom, VARIANT
from datetime import datetime, time, timedelta
from time import gmtime, strftime

from IBAPI import Connection
from data import Data
from order import Order
from contracts import Contract, JapaneseContract, VixThirtyContract

ticker = 'AAPL'
destination = "GSDE Algo"
price_type = 'TWAP ' + destination.split(' ')[0]


def VWAP():
    o = win32com.client.Dispatch("REDI.ORDER")
    o.Side = 'Buy'
    o.symbol = 'AAPL'  # "SBUX"
    o.Exchange = 'DEMF algo'  # 'DEMF DMA'
    o.PriceType = 'VWAP DEMF'
    o.Price = "22.30"
    o.TIF = 'Day'
    o.Account = 'DEMO'
    o.Ticket = 'Bypass'
    o.Quantity = '46'
    o.SetNewVariable("(MB) End Time", "150000")

    msg = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_VARIANT, None)
    result = o.Submit(msg)

    print(result)  # 'True' if order submission was successful; otherwise 'False'
    print(msg)  # message from sumbit


def TWAPVix():
    o = win32com.client.Dispatch("REDI.ORDER")
    o.Side = 'Sell'
    o.symbol = 'FFIU2'  # "SBUX"
    o.Exchange = 'GSFF ALGOS'  # 'GSFF ALGOS'  # 'DEMF DMA'
    o.PriceType = "TWAP GSFF"  # 'TWAP GSFU'
    # o.price = ''
    o.TIF = 'Day'
    o.Account = 'QATEST01'
    o.Ticket = 'Bypass'
    o.Quantity = '1.0'
    curr_time = datetime.now()
    comb_time = curr_time + timedelta(minutes=20)
    end_time = str(comb_time.hour) + ":" + str(comb_time.minute) + ":00"
    print(end_time)
    o.SetNewVariable("(MB) End Time", str(end_time))
    # o.SetNewVariable("(MB) Execution Style", "Normal")
    # o.SetNewVariable("(MB) Disclosed Quantity", "10")

    msg = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_VARIANT, None)
    result = o.Submit(msg)

    print(result)  # 'True' if order submission was successful; otherwise 'False'
    print(msg)  # message from sumbit


def TWAPStock():
    o = win32com.client.Dispatch("REDI.ORDER")
    o.Side = 'Buy'
    o.symbol = 'AAPL'  # "SBUX"
    o.Exchange = 'GSDE Algo'  # # 'GSFF ALGOS'  # 'DEMF DMA'
    o.PriceType = 'TWAP GSDE'  # "TWAP GSCE"  # 'TWAP GSFF'
    # o.price = ''
    o.TIF = 'Day'
    o.Account = 'QATEST01'
    o.Ticket = 'Bypass'
    o.Quantity = '100'
    start_time = datetime.now().strftime("%H:%M:%S")
    end_time = datetime.now() + timedelta(minutes=20)
    end_time = end_time.strftime("%H:%M:%S")
    # start_time = curr_time.strftime("%H:%M:%S")
    print(start_time)
    print(end_time)
    o.SetNewVariable("(MB) End Time", str(end_time))
    # o.SetNewVariable("(MB) Start Time", str(start_time))
    # o.SetNewVariable("(MB) BlockStrike", "YES")
    # o.SetNewVariable("(MB) LEGS", "9")
    # o.SetNewVariable("(MB) Price Incr", "-0.26")
    # o.SetNewVariable("(MB) Scaler", "NO")
    o.SetNewVariable("(MB) Execution Style", "Normal")
    # o.SetNewVariable("(MB) Disclosed Quantity", "10")
    o.SetNewVariable("(MB) DUH", "-0.26")

    msg = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_VARIANT, None)
    result = o.Submit(msg)

    print(result)  # 'True' if order submission was successful; otherwise 'False'
    print(msg)  # message from sumbit


def Limit():
    o = win32com.client.Dispatch("REDI.ORDER")
    o.Side = 'Buy'
    o.symbol = 'AAPL'  # "SBUX"
    o.Exchange = 'GSCE DMA'  # 'DEMF DMA'
    o.PriceType = 'Market'
    o.Price = "100"
    o.TIF = 'Day'
    o.Account = 'QATEST01'
    o.Ticket = 'Bypass'
    o.Quantity = '100'
    o.Warning = False

    # o.SetNewVariable("(MB) End Time", "150000")
    msg = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_VARIANT, None)
    result = o.Submit(msg)
    print(result)
    print(msg)


def example_order():
    o = win32com.client.Dispatch("REDI.ORDER")
    o.Side = "Buy"
    o.symbol = "VXQ2"
    o.Exchange = "DEMF DMA"
    o.Quantity = "10"
    o.PriceType = "Market"
    o.Price = "30.0"  # test for NBBO popup message
    o.TIF = "Day"
    o.Account = "DEMO"
    o.Ticket = "Bypass"
    o.Warning = False

    # Prepare a variable which can handle returned values from submit method of the order object.
    msg = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_VARIANT, None)

    # Send an options order
    result = o.Submit(msg)

    print(result)  # 'True' if order submission was successful; otherwise 'False'
    print(msg)  # message from sumbit


def japanese_market():
    o = win32com.client.Dispatch("REDI.ORDER")
    o.Side = "Sell"
    o.symbol = "4268.T"
    o.Exchange = "DEMO algo"
    o.Quantity = "1"
    o.PriceType = "TWAP"
    # o.Price = "30.0"  # test for NBBO popup message
    o.TIF = "Day"
    o.Account = "QATEST02"
    o.Ticket = "Bypass"
    o.Warning = False

    # Prepare a variable which can handle returned values from submit method of the order object.
    msg = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_VARIANT, None)

    # Send an options order
    result = o.Submit(msg)

    print(result)  # 'True' if order submission was successful; otherwise 'False'
    print(msg)  # message from sumbit


def data_from_redi():
    q = win32com.client.Dispatch("REDI.Query", pythoncom.CoInitialize())

    # Prepare a variable which can handle returned values from submit method of the order object.
    msg1 = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, 0)
    symbolVar = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, 0)
    fieldVar = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, 0)
    tgtVarName = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, 0)

    vTable = "L1"
    vWhere = "true"
    tmpVal = q.Submit(vTable, vWhere, msg1)

    symbolVar.value = "4268.T"
    ret = q.GetL1Value(symbolVar, "Last", tgtVarName)
    print(strftime("%Y-%m-%d %H:%M:%S", gmtime()) + " Symbol=" + str(tgtVarName.value) + " Last" + "=" + str(
        symbolVar.value) + " success=" + str(ret))

    symbolVar.value = "T"
    ret = q.GetL1Value(symbolVar, "Ask", tgtVarName)
    print(strftime("%Y-%m-%d %H:%M:%S", gmtime()) + " Symbol=" + str(tgtVarName.value) + " " + "Ask" + "=" + str(
        symbolVar.value) + " success=" + str(ret))


def eikonData():
    # con = JapaneseContract(['4268.T', '4270.T', '4412.T', '2438.T'], interval=60)
    s = ['8698', '6532']
    stocks = [tick + '.T' for tick in s]
    con = JapaneseContract(stocks, interval=15)
    d = Data(con)
    dic = d.requestDataEikon(con.interval, data_timezone='Asia/Tokyo')
    pd.set_option('display.max_rows', None)
    # df.index = pd.to_datetime(df.index)
    # print(con.data.tail(20))
    for tick in stocks:
        print(tick, '\n', dic[tick])
        # print(con.data[tick]['CLOSE'])


def eikonStreaming():
    con = JapaneseContract('4268.T', interval=60)
    d = Data(con)
    data = d.eikon_streaming('4268.T')
    df = data.get_snapshot()
    print(df)


# japanese_market()
# TWAPVix()
# Limit()
# TWAPStock()
# con = Contract('AAPL')
# o = Order(100, 'Buy', 'GSDE Algo', con, account='QATEST01', limit_time=20)
# o.TWAP()
data_from_redi()
# eikonData()
# eikonStreaming()
# example_order()
