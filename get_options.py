import pandas as pd
import yfinance as yf

# Function to get option contracts
def get_option_contracts(ticker, rounded_price_with_change, option_type='call', earnings_date=None):
    stock = yf.Ticker(ticker)
    expiration_dates = stock.options
    
    # Filter expiration dates to be after the earnings date
    valid_expiration_dates = [date for date in expiration_dates if pd.to_datetime(date) > pd.to_datetime(earnings_date)]
    
    if not valid_expiration_dates:
        return (None, None)
    
    # Get the nearest valid expiration date
    nearest_expiration = valid_expiration_dates[0]
    options = stock.option_chain(nearest_expiration)
    if option_type == 'call':
        options_data = options.calls
    else:
        options_data = options.puts

    if options_data.empty:
        return (None, None)
    
    # Find the closest strike price
    closest_option = options_data.iloc[(options_data['strike'] - rounded_price_with_change).abs().argsort()[:1]]

    return (closest_option.iloc[0], nearest_expiration)

# Function to calculate the inverse of the call to put ratio
def calculate_inverse_call_put_ratio(call_premium, put_premium):
    if call_premium == 0 or put_premium == 0:
        return None
    return put_premium / call_premium

# Main function
def main():
    # Load the stock list from the CSV file
    df = pd.read_csv('stock_list.csv')

    # Round the price change to the nearest dollar
    df['rounded_price_change'] = df['average_price_change'].round()

    # Add columns for the closest call and put options
    df[['closest_call_option', 'closest_call_expiration']] = df.apply(
        lambda row: pd.Series(get_option_contracts(row['symbol'], row['current_price'] + row['rounded_price_change'], 'call', row['date'])),
        axis=1
    )
    df[['closest_put_option', 'closest_put_expiration']] = df.apply(
        lambda row: pd.Series(get_option_contracts(row['symbol'], row['current_price'] - row['rounded_price_change'], 'put', row['date'])),
        axis=1
    )

    # Remove rows where either call or put options are not found
    df = df.dropna(subset=['closest_call_option', 'closest_put_option'])

    # Extract strike prices, expiration dates, premiums, volume, and open interest for the options
    df['call_strike'] = df['closest_call_option'].apply(lambda x: x['strike'] if x is not None else None)
    df['call_premium'] = df['closest_call_option'].apply(lambda x: x['lastPrice'] if x is not None else None)
    df['call_volume'] = df['closest_call_option'].apply(lambda x: x['volume'] if x is not None else None)
    df['call_open_interest'] = df['closest_call_option'].apply(lambda x: x['openInterest'] if x is not None else None)
    df['put_strike'] = df['closest_put_option'].apply(lambda x: x['strike'] if x is not None else None)
    df['put_premium'] = df['closest_put_option'].apply(lambda x: x['lastPrice'] if x is not None else None)
    df['put_volume'] = df['closest_put_option'].apply(lambda x: x['volume'] if x is not None else None)
    df['put_open_interest'] = df['closest_put_option'].apply(lambda x: x['openInterest'] if x is not None else None)
    df['expiration_date'] = df['closest_call_expiration'].apply(lambda x: x if x is not None else None)

    # Calculate the inverse of the call to put ratio
    df['call_put_ratio'] = df.apply(lambda row: calculate_inverse_call_put_ratio(row['call_premium'], row['put_premium']), axis=1)

    # Remove the temporary columns
    df = df.drop(columns=['closest_call_option', 'closest_call_expiration', 'closest_put_option', 'closest_put_expiration', 'rounded_price_change'])

    # Save the updated DataFrame to an Excel file
    df.to_excel('options_data.xlsx', engine='xlsxwriter', index=False)

    print(df)
    return df

# Run the script
if __name__ == '__main__':
    main()
