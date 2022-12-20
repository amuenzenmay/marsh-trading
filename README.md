# RazMar
Contains trading strategies for US stocks, VIX, and commodity futures. Uses the REDI API by Refinitiv for order submissions and TWS API from Interactive Brokers for live data.

## Usage
```bash
py StockFiveMain.py
```
```bash
py StockThirtyMain.py
```

#### REQUIRED PACKAGES:
    ibapi
    mysql
    mysql-connector
    mysqlclient
    pandas
    pytz
    pywin32

#### ACCOUNT DESTINATIONS:
	Futures:
		Algorithmic -> GSFF ALGOS
		Direct -> GSFF DMA
	Equities:
		Algorithmic -> GSGU Algo
		Direct -> GSGU DMA


#### ORDER DESTINATIONS:
    REDI:
        Commodities
        VIX
        Global Indices
        Energies
    SRSE:
        Stocks

## In Progress:    
    Global Indexes:
        Testing for bugs

    Energy Intraday:
        Create new strategy for energy products
            Will not include notional adjustment trades, but will change inception sizes
        Use auto-roll functionality at the beginning of each month
    




