# Pre-Earnings Straddle Option Trader
## Description
- Python Trading Algorithm to Identify Profitable Options Strategies Before Earnings Reports.
- Leverages the increased volatility preceding earnings announcements. Buys straddles at predicted strike prices a week before earnings date and sells right before earnings.

# File Overview
## For Current Day Trading
- get_stocks.py: Returns a list of stocks with earnings reports coming out next week. Input: Current Date, Output: stock_list.csv
- get_options.py: Utilizes decision logic to create a list of suggested straddles to buy based off given company names. Input: stock_list.csv, Output: options_data.xlsx
- decision_making.py: Utilizes a gradient boosting algorithm to sort out unprofitable trades and returns predicted profitable trades. Input: data.xlsx, options_data.xlsx, Output: predicted_options_data.xlsx

## Backtesting
- get_stocks_backtest.py: Returns a list of stocks with earnings reports coming out next week. Input: backtest_date, Output: stock_list_backtest.csv
- get_options_backtest.py: Utilizes the same decision logic to create a list of suggested straddles and calculates the return of each straddle trade. Input: stock_list_backtest.csv, Output: options_data_backtest.xlsx
- decision_making_backtest.py: Trains multiple models and determines the model with the best accuracy. Repredicts on the data and returns all suggested options trades. Input: data.xlsx, Output: final_stock_list_backtest.xlsx
  
## Data
- data.xlsx: Cumulative data generated from the backtesting files for training the decision tree model
- final_stock_list_backtest.xlsx: Sample backtested generated stock suggestions over the past 2 months with their individual gains/losses. Showcases an average return of 40% on each trade suggestion.

## File Hierarchy Rationale
- Dividing get_stocks and get_options allows for tweaking the decision making algorithm for straddles without waiting to re-retrieve the stock data
- Current suggestions and backtesting are divided because of the differences in API usage and overall code

# Requirements
## Libraries
pip install the following libraries
- requests
- pandas
- datetime
- yfinance
- pandas_market_calendars
- sklearn
- matplotlib
- seaborn
- numpy

## APIs
Enter API Keys
- Orats
- Finnhub
- Alpha Vantage

# How To Run
- Current Suggestions: run get_stocks.py -> get_options.py -> decision_making.py. Change variables and logic as needed.
- Backtesting: run get_stocks_backtest.py -> get_options_backtest.py -> decision_making_backtest.py. Change variables and logic as needed.
