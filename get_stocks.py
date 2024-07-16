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
            return float(data['MarketCapitalization']) / 1e6  # Convert to millions
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

# Function to calculate the next Monday and Friday
def get_next_week_dates():
    today = datetime.today()
    days_until_monday = (7 - today.weekday()) % 7
    next_monday = today + timedelta(days_until_monday)
    next_friday = next_monday + timedelta(days=4)
    return next_monday.strftime('%Y-%m-%d'), next_friday.strftime('%Y-%m-%d')

# Function to get the average price change around earnings
def get_average_price_change(ticker):
    stock = yf.Ticker(ticker)
    earnings = stock.earnings_dates

    if earnings is None or earnings.empty:
        return None

    # Ensure the dates are in a Timestamp format
    earnings.index = pd.to_datetime(earnings.index)

    # Filter out future earnings dates
    current_time = pd.Timestamp.now(tz='America/New_York')
    past_earnings = earnings[earnings.index <= current_time]

    # Sort by date to ensure we get the latest ones
    past_earnings = past_earnings.sort_index(ascending=False)

    # Check if there are at least four past earnings reports
    if len(past_earnings) < 4:
        return None

    # Extract the last four past earnings report dates
    last_four_past_earnings = past_earnings.index[:4].tolist()

    price_changes = []

    for date in last_four_past_earnings:
        # Get the previous and next trading day close prices
        hist = stock.history(start=date - pd.Timedelta(days=5), end=date + pd.Timedelta(days=5))

        if hist.empty:
            continue

        # Find the close prices before and after the earnings date
        date_before = hist.loc[hist.index < date].index[-1]
        date_after = hist.loc[hist.index > date].index[0]

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

# Function to get the current stock price
def get_current_stock_price(ticker):
    stock = yf.Ticker(ticker)
    current_price = stock.history(period='1d')['Close'].iloc[-1]
    return current_price

# Main function
def main():
    # Get the start and end dates for the next trading week
    start_date, end_date = get_next_week_dates()
    
    try:
        earnings_reports = get_earnings_reports(start_date, end_date)
    except Exception as e:
        print(e)
        return
    
    # Only include stocks with market cap >= 100M
    filtered_reports = filter_reports_by_market_cap(earnings_reports, 100)
    
    if not filtered_reports:
        print("No earnings reports found with market cap >= $100M.")
        return
    
    # Convert to DataFrame for better visualization
    df = pd.DataFrame(filtered_reports)

    # Calculate the average absolute price change for each company and add it to the DataFrame
    df['average_price_change'] = df['symbol'].apply(get_average_price_change)

    # Remove rows with NaN values in 'average_price_change'
    df = df.dropna(subset=['average_price_change'])

    # Get the current stock price and calculate the price change ratio
    df['current_price'] = df['symbol'].apply(get_current_stock_price)
    df['price_change_ratio'] = df['average_price_change'] / df['current_price']

    # Sort the DataFrame by price_change_ratio from highest to lowest
    df = df.sort_values(by='price_change_ratio', ascending=False)

    # Remove rows with price_change_ratio below 0.04
    df = df[df['price_change_ratio'] >= 0.04]

    # Select columns
    df = df[['symbol', 'price_change_ratio', 'average_price_change', 'date', 'current_price']]

    # Save the DataFrame to a CSV file
    df.to_csv('stock_list.csv', index=False)

    print(df)
    return df

# Run the script
if __name__ == '__main__':
    df_next_week_reports = main()
