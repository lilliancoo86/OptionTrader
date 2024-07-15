import requests
import pandas as pd
import pandas_market_calendars as mcal
import yfinance as yf

ORATS_API_KEY = "322e1a9b-090e-4918-be10-27ac5c40d742"

# Get the market calendar for NYSE
nyse = mcal.get_calendar('NYSE')

def find_closest(number, lst):
    return min(lst, key=lambda x: abs(x - number))

def has_options(ticker):
    stock = yf.Ticker(ticker)
    options = stock.options
    return len(options) > 0

def get_strike_prices(ticker, tradeDate, currentPrice, averageChange):
    url = "https://api.orats.io/datav2/hist/strikes"

    querystring = {
        "token": ORATS_API_KEY,
        "ticker": ticker,
        "tradeDate": tradeDate,
        "fields": "ticker,tradeDate,expirDate,strike"
    }

    response = requests.get(url, params=querystring)
    
    if response.status_code != 200:
        print(f"API request failed with status code {response.status_code}: {response.text}")
        return None
    
    data = response.json()
    
    if 'data' not in data:
        print("'data' key not found in the API response")
        return None
    
    df = pd.DataFrame(data['data'])
    
    if 'expirDate' not in df.columns:
        print("'expirDate' not found in the API response data")
        return None
    
    tradeDate = pd.to_datetime(tradeDate)
    df['expirDate'] = pd.to_datetime(df['expirDate'])
    
    valid_expirations = df[df['expirDate'] >= tradeDate]
    
    if valid_expirations.empty:
        print("No valid expirations found")
        return None
    
    sorted_expirations = valid_expirations['expirDate'].sort_values().unique()
    
    if len(sorted_expirations) < 2:
        print("Not enough expiration dates available to get the second nearest expiration")
        return None
    
    second_nearest_expiration = sorted_expirations[1]
    
    strike_prices = valid_expirations[valid_expirations['expirDate'] == second_nearest_expiration]['strike'].unique()
    strike_prices = list(strike_prices)
    
    currentPrice = float(currentPrice)
    averageChange = float(averageChange)
    
    putPrice = currentPrice - averageChange
    callPrice = currentPrice + averageChange
    
    putPrice = find_closest(putPrice, strike_prices)
    callPrice = find_closest(callPrice, strike_prices)
    
    return (second_nearest_expiration, callPrice, putPrice)

def get_num_days_before_tradeDate(tradeDate):
    tradeDate = pd.to_datetime(tradeDate)
    schedule = nyse.schedule(start_date=tradeDate - pd.Timedelta(days=10), end_date=tradeDate)
    trading_days = schedule.index
    pos = trading_days.get_loc(tradeDate)
    num_days_before = trading_days[pos - 7]
    return num_days_before.strftime('%Y-%m-%d')

def get_day_before_tradeDate(tradeDate):
    tradeDate = pd.to_datetime(tradeDate)
    schedule = nyse.schedule(start_date=tradeDate - pd.Timedelta(days=5), end_date=tradeDate)
    trading_days = schedule.index
    pos = trading_days.get_loc(tradeDate)
    day_before = trading_days[pos - 1]
    return day_before.strftime('%Y-%m-%d')

def get_ask_price(ticker, tradeDate, expiration_date, callPrice, putPrice):
    url = "https://api.orats.io/datav2/hist/strikes/options"

    querystring = {"token": ORATS_API_KEY,"ticker":ticker,"expirDate":expiration_date,"strike":callPrice, "tradeDate":tradeDate}
    response = requests.get(url, params=querystring)
    
    if response.status_code != 200:
        print(f"API request failed with status code {response.status_code}: {response.text}")
        return None
    
    data = response.json()
    
    if 'data' not in data or not data['data']:
        print("'data' key not found in the API response or data is empty")
        return None
    
    call_ask_price = data['data'][0]['callAskPrice']
    call_volume = data['data'][0]['callVolume']
    call_open_interest = data['data'][0]['callOpenInterest']

    querystring = {"token": ORATS_API_KEY,"ticker":ticker,"expirDate":expiration_date,"strike":putPrice, "tradeDate":tradeDate}
    response = requests.get(url, params=querystring)
    
    if response.status_code != 200:
        print(f"API request failed with status code {response.status_code}: {response.text}")
        return None
    
    data = response.json()
    
    if 'data' not in data or not data['data']:
        print("'data' key not found in the API response or data is empty")
        return None
    
    put_ask_price = data['data'][0]['putAskPrice']
    put_volume = data['data'][0]['putVolume']
    put_open_interest = data['data'][0]['putOpenInterest']

    return (call_ask_price, put_ask_price, call_volume, call_open_interest,
            put_volume, put_open_interest)

def main():
    # Load the stock list from the CSV file
    df = pd.read_csv('stock_list_backtest.csv')

    # Eliminate stocks that don't provide options
    df = df[df['symbol'].apply(has_options)]
    

    # Ensure 'average_price_change' column is numeric
    df['average_price_change'] = pd.to_numeric(df['average_price_change'], errors='coerce')

    # Round the price change to the nearest dollar
    df['rounded_price_change'] = df['average_price_change'].round()

    # Add columns for the closest call and put options and their expiration date
    df[['nearest_expiration', 'closest_call_option', 'closest_put_option']] = df.apply(
        lambda row: pd.Series(get_strike_prices(row['symbol'], row['date'], row['current_price'], row['rounded_price_change'])),
        axis=1
    )

    # Remove rows where either call or put options are not found
    df = df.dropna(subset=['closest_call_option', 'closest_put_option'])
    
    # Get the last date and 7th last date before earnings report for each stock
    df['num_days_before'] = df['date'].apply(get_num_days_before_tradeDate)
    df['day_before'] = df['date'].apply(get_day_before_tradeDate)

    # Get ask prices for both dates
    df[['call_ask_price_numd', 'put_ask_price_numd', 'call_volume_numd', 'call_open_interest_numd', 'put_volume_numd', 'put_open_interest_numd']] = df.apply(
        lambda row: pd.Series(get_ask_price(row['symbol'], row['num_days_before'], row['nearest_expiration'], row['closest_call_option'], row['closest_put_option'])),
        axis=1
    )
    df[['call_ask_price_1d', 'put_ask_price_1d', 'call_volume_1d', 'call_open_interest_1d', 'put_volume_1d', 'put_open_interest_1d']] = df.apply(
        lambda row: pd.Series(get_ask_price(row['symbol'], row['day_before'], row['nearest_expiration'], row['closest_call_option'], row['closest_put_option'])),
        axis=1
    )

    # Calculate percentage change
    df['call_price_change'] = ((df['call_ask_price_1d'] - df['call_ask_price_numd']) / df['call_ask_price_numd']) * 100
    df['put_price_change'] = ((df['put_ask_price_1d'] - df['put_ask_price_numd']) / df['put_ask_price_numd']) * 100
    df['total_gain'] = ((df['call_price_change'] + df['put_price_change']) / 2)
    
    # Clean and Rename the Columns
    df = df[['symbol', 'date', 'price_change_ratio', 'current_price','closest_call_option','closest_put_option',
             'num_days_before','day_before','call_ask_price_numd', 'put_ask_price_numd','call_ask_price_numd',
             'put_ask_price_numd', 'call_volume_numd', 'call_open_interest_numd', 'put_volume_numd', 'put_open_interest_numd',
             'call_price_change', 'put_price_change', 'total_gain']]
    
    df = df.rename(columns={
        'symbol': 'Symbol',
        'date': 'Earnings_Date',
        'price_change_ratio': 'Price_Change_Ratio',
        'current_price': 'Current_Price',
        'closest_call_option': 'Call_Strike',
        'closest_put_option': 'Put_Strike',
        'num_days_before': 'Buy_Date',
        'day_before': 'Sell_Date',
        'call_ask_price_numd': 'Buy_Call_Price',
        'put_ask_price_numd': 'Buy_Put_Price',
        'call_volume_numd': 'Call_Volume',
        'call_open_interest_numd': 'Call_Open_Interest',
        'put_volume_numd': 'Put_Volume',
        'put_open_interest_numd': 'Put_Open_Interest',
        'call_price_change': 'Call_Price_Change',
        'put_price_change': 'Put_Price_Change',
        'total_gain': 'Total_Gain'
    })

    # Save the updated DataFrame to an Excel file
    df.to_excel('options_data_backtest.xlsx', engine='xlsxwriter', index=False)

    print(df)

# Run the script
if __name__ == '__main__':
    main()
