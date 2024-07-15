import requests
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf

# Your API keys
FINNHUB_API_KEY = 'cq7lm3pr01qormuiknrgcq7lm3pr01qormuikns0'
ALPHA_VANTAGE_API_KEY = 'LSMGD7ONMMBCPNBP'

# Function to get earnings reports from Finnhub for a given date range
def get_earnings_reports(start_date, end_date):
    url = f'https://finnhub.io/api/v1/calendar/earnings?from={start_date}&to={end_date}&token={FINNHUB_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get('earningsCalendar', [])
    else:
        raise Exception(f"Failed to retrieve data: {response.status_code}")

# Function to get stock profile (including market cap) from Finnhub
def get_stock_profile_finnhub(symbol):
    url = f'https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={FINNHUB_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return {}

# Function to get market cap from Alpha Vantage
def get_market_cap_alpha_vantage(symbol):
    url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={ALPHA_VANTAGE_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'MarketCapitalization' in data:
            try:
                return float(data['MarketCapitalization']) / 1e6  # Convert to millions
            except ValueError:
                return None
        else:
            return None
    else:
        return None

# Function to filter earnings reports for the next week by market cap
def filter_reports_by_market_cap(reports, min_market_cap):
    filtered_reports = []
    total_reports = len(reports)
    
    for i, report in enumerate(reports):
        symbol = report.get('symbol')
        profile = get_stock_profile_finnhub(symbol)
        market_cap = profile.get('marketCapitalization')
        
        if not market_cap:  # If Finnhub does not have market cap data, use Alpha Vantage
            market_cap = get_market_cap_alpha_vantage(symbol)
        
        if market_cap and market_cap >= min_market_cap:
            report['market_cap'] = market_cap
            filtered_reports.append(report)
        
        # Print progress
        progress = (i + 1) / total_reports * 100
        print(f"Progress: {progress:.2f}% complete", end='\r')
    
    return filtered_reports

# Function to calculate the next Monday and Friday based on a given date
def get_next_week_dates(backtest_date=None):
    if backtest_date:
        today = pd.to_datetime(backtest_date)
    else:
        today = datetime.today()
    days_until_next_monday = (7 - today.weekday() + 7) % 7  # Ensure it's always at least 7 days ahead
    next_monday = today + timedelta(days=days_until_next_monday)
    next_friday = next_monday + timedelta(days=4)
    return next_monday.strftime('%Y-%m-%d'), next_friday.strftime('%Y-%m-%d')

# Function to get the average price change around earnings before a specified date
def get_average_price_change(ticker, before_date=None):
    stock = yf.Ticker(ticker)
    earnings = stock.earnings_dates

    if earnings is None or earnings.empty:
        return None

    # Extract only the date part
    earnings_dates = earnings.index.date

    # Convert the before_date to a date object
    if before_date:
        before_date = pd.to_datetime(before_date).date()
        # Filter out earnings dates after the specified before_date
        past_earnings = earnings_dates[earnings_dates <= before_date]
    else:
        past_earnings = earnings_dates

    # Sort by date to ensure we get the latest ones
    past_earnings = sorted(past_earnings, reverse=True)

    # Check if there are at least four past earnings reports
    if len(past_earnings) < 4:
        return None

    # Extract the last four past earnings report dates
    last_four_past_earnings = past_earnings[:4]

    price_changes = []

    for date in last_four_past_earnings:
        # Get the previous and next trading day close prices
        hist = yf.download(ticker, start=pd.Timestamp(date) - pd.Timedelta(days=5), end=pd.Timestamp(date) + pd.Timedelta(days=5))

        if hist.empty:
            continue

        # Find the close prices before and after the earnings date
        date_before = hist.loc[hist.index < pd.Timestamp(date)].index[-1]
        date_after = hist.loc[hist.index > pd.Timestamp(date)].index[0]

        price_before = hist.loc[date_before]['Close']
        price_after = hist.loc[date_after]['Close']
        
        # Calculate the price difference
        price_change = price_after - price_before
        price_changes.append(abs(price_change))

    if not price_changes:
        return None

    # Calculate the average of the absolute values of the price changes
    average_price_change = sum(price_changes) / len(price_changes)

    return average_price_change

# Function to get the stock price on or around a given date (handle weekends and holidays)
def get_stock_price_on_date(ticker, date):
    stock = yf.Ticker(ticker)
    hist = yf.download(ticker, start=pd.Timestamp(date) - pd.Timedelta(days=5), end=pd.Timestamp(date) + pd.Timedelta(days=5))

    if hist.empty:
        return None

    # Find the closest trading day price to the given date
    date_before = hist.loc[hist.index < pd.Timestamp(date)].index[-1] if not hist.loc[hist.index < pd.Timestamp(date)].empty else None
    date_after = hist.loc[hist.index > pd.Timestamp(date)].index[0] if not hist.loc[hist.index > pd.Timestamp(date)].empty else None

    if date_before is not None:
        price_before = hist.loc[date_before]['Close']
        return price_before
    elif date_after is not None:
        price_after = hist.loc[date_after]['Close']
        return price_after
    else:
        return None

# Main function for backtesting
def main(backtest_date=None):
    # Ensure backtest_date is a datetime object
    backtest_date = pd.to_datetime(backtest_date)
    
    # Get the start and end dates for the week after the backtest date
    start_date, end_date = get_next_week_dates(backtest_date)
    
    try:
        earnings_reports = get_earnings_reports(start_date, end_date)
    except Exception as e:
        print(e)
        return
    
    filtered_reports = filter_reports_by_market_cap(earnings_reports, 100)
    
    if not filtered_reports:
        print("No earnings reports found with market cap >= $100M.")
        return
    
    # Convert to DataFrame for better visualization
    df = pd.DataFrame(filtered_reports)

    # Filter reports to include only those strictly after the backtest_date
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['date'] > backtest_date]

    # Calculate the average price change around earnings for each stock
    df['average_price_change'] = df['symbol'].apply(lambda x: get_average_price_change(x, before_date=backtest_date))
    
    # Remove rows with NaN values in 'average_price_change'
    df = df.dropna(subset=['average_price_change'])
    
    # Get the current stock price and calculate the price change ratio
    df['current_price'] = df['symbol'].apply(lambda x: get_stock_price_on_date(x, backtest_date))
    df['price_change_ratio'] = df['average_price_change'] / df['current_price']
    
    # Sort the DataFrame by price_change_ratio from highest to lowest
    df = df.sort_values(by='price_change_ratio', ascending=False)

    # Remove rows with price_change_ratio below 0.04
    df = df[df['price_change_ratio'] >= 0.04]

    # Select and rename columns
    df = df[['symbol', 'price_change_ratio', 'average_price_change', 'date', 'current_price']]

    # Save the DataFrame to a CSV file
    df.to_csv('stock_list_backtest.csv', index=False)

    print(df)
    return df

# Run the script
if __name__ == '__main__':
    # Set the backtest date (e.g., '2024-06-23')
    backtest_date = '2024-06-16'
    main(backtest_date)
