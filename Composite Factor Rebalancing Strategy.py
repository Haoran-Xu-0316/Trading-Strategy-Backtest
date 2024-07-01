import pandas as pd
import numpy as np
import datetime

#-------------------------------------Basic Parameter Settings-----------------------------------------------

# Account initialization function
def initialize(account):
    # Use the smart stock selection function get_iwencai to generate stock pool
    get_iwencai('HS300')  # Using iwencai to get the stock pool of the SSE 300 index
    # Set maximum number of stocks to hold
    account.max_stocks = 10
    # Set rebalancing period, run on the 1st trading day of each month
    run_monthly(func=reallocation, date_rule=1)

def reallocation(account, data):
    # ---------------------------------------Data Acquisition--------------------------------------------
    # Get the date of the previous trading day for rebalancing (assuming the function runs on the current day)
    yst_date = get_datetime().strftime('%Y%m%d')

    # Get the list of stocks (result of get_iwencai function is automatically stored in account.iwencai_securities)
    sample = account.iwencai_securities

    # Filtering the required factor data
    q = query(profit.symbol,  # Stock code
              profit.date,  # Date
              profit.roic,  # Return on invested capital
              valuation.pb,  # Price-to-book ratio
              valuation.pe,  # Price-to-earnings ratio
              ).filter(
        profit.symbol.in_(sample)
    )
    # Get factor data from the previous trading day and fill missing values with 0
    df = get_fundamentals(q, date=yst_date).fillna(0)

    #-----------------------------------------Data Processing--------------------------------------------
    # Outlier processing using median de-extremization method
    # The factors are the last 3 columns
    for i in list(df.columns)[-3:]:
        m = np.mean(df[i])  # Calculate mean
        s = np.std(df[i])  # Calculate standard deviation
        df[i] = df[i].where(df[i] > m - 3 * s).fillna(m - 3 * s)  # Replace values less than m-3*s with m-3*s
        df[i] = df[i].where(df[i] < m + 3 * s).fillna(m + 3 * s)  # Replace values greater than m+3*s with m+3*s

    # Dimensionless processing of factors
    for j in list(df.columns)[-3:]:
        m = np.mean(df[j])  # Calculate mean
        s = np.std(df[j])  # Calculate standard deviation
        df[j] = (df[j] - m) / s  # Standardization

    #--------------------------------------Factor Selection--------------------------------------------------------------------------------------------
    # Calculate composite factor (positive direction is +, negative direction is -)
    df['score'] = df['profit_roic'] - df['valuation_pb'] - df['valuation_pe']
    # Sort by composite factor value from largest to smallest
    df = df.sort_values(by='score', ascending=False)
    # Select the top N stocks, where N is the maximum number of stocks to hold
    buy_list = df['profit_symbol'].values[:account.max_stocks]

    # Iterate through current positions
    for stk in list(account.positions):
        # If the current position is not in the buy list, sell it
        if stk not in buy_list:
            order_target_percent(stk, 0)  # Clear the position

    #--------------------------------------Rebalancing------------------------------------------------------------------------------
    # Iterate through the buy list
    for stk in buy_list:
        # If the stock is not in the current positions, buy it
        if stk not in account.positions:
            # Buy the stock, allocate 1/N of funds, where N is the maximum number of stocks to hold
            order_target_percent(stk, 1 / account.max_stocks)

