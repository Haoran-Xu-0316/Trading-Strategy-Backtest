from datetime import timedelta, date
import pandas as pd


############################## Main Functions Below ##############################
# Initialization Function #######################################################
def initialize(account):
    # set_commission(PerTrade(cost=0.0003, min_trade_cost=5))
    # set_slippage(PriceRelatedSlippage())
    account.n = 20  # Number of stocks to hold
    # Rebalancing frequency
    # Weekly call to the trade function
    run_weekly(trade, date_rule=-1)


# Weekend Rebalancing Function ##################################################
def trade(account, data):
    date = get_datetime()
    C_list = stocks_C(account, data)
    A_list = stocks_A(account, data)
    S_list = stocks_S(account, data)
    L_list = stocks_L(account, data)
    ## Get stock pool satisfying each condition
    stock_list = list(set(C_list) & set(A_list) & set(S_list) & set(L_list))
    log.info(len(stock_list))
    log.info(stock_list)
    ## Sell
    if len(account.positions) > 0:
        for stock in list(account.positions):
            if stock not in stock_list:
                order_target(stock, 0)
    ## Buy
    if len(stock_list) > 0:
        for stock in stock_list:
            if stock not in list(account.positions):
                if len(account.positions) < account.n:
                    number = account.n - len(account.positions)
                    order_value(stock, account.cash / number)
                else:
                    order_value(stock, account.cash)
    else:
        pass


# Daily Stop Loss Check #########################################################
def handle_data(account, data):
    last_date = get_last_datetime().strftime('%Y%m%d')
    if len(account.positions) > 0:
        # Stop loss: Sell if individual stock falls more than 7%
        securities = list(account.positions)
        for stock in securities:
            price = data.attribute_history(stock, ['close'], 1, '1d', skip_paused=False, fq='pre')
            if account.positions[stock].cost_basis / price['close'][0] - 1 < -0.07:
                order_target(stock, 0)
                log.info('%s Stop loss triggered for %s' % (last_date, stock))

        # Stop loss: If the benchmark falls suddenly by 7% in 3 days, sell all positions
        price_bench = data.attribute_history('000300.SH', ['close'], 3, '1d', skip_paused=False, fq=None)
        if price_bench['close'][-3] / price_bench['close'][-1] - 1 > 0.07:
            if len(list(account.positions)) > 0:
                for stock in list(account.positions):
                    order_target(stock, 0)
                    log.info('%s Market suddenly dropped' % (last_date))


################## Below are the Helper Functions, Called in Main Functions ######################
# 1. C - Recent profit growth rate
def stocks_C(account, data):
    last_date = get_last_datetime().strftime('%Y%m%d')
    securities = list(get_all_securities('stock', last_date).index)
    C = get_fundamentals(query(
        growth.symbol,
        growth.parent_company_profit_growth_ratio
    ).filter(
        growth.parent_company_profit_growth_ratio > 20,
        growth.symbol.in_(securities)
    ).order_by(
        growth.parent_company_profit_growth_ratio.desc()
    ), date=last_date)
    return list(C['growth_symbol'])


# 2. A - Compound growth rate over the past three years
def stocks_A(account, data):
    last_date = get_last_datetime().strftime('%Y%m%d')
    securities = list(get_all_securities('stock', last_date).index)
    A = get_fundamentals(query(
        growth.symbol,
        growth.parent_company_share_holders_net_profit_years_growth_ratio
    ).filter(
        growth.parent_company_share_holders_net_profit_years_growth_ratio > 72,
        growth.symbol.in_(securities)
    ).order_by(
        growth.parent_company_share_holders_net_profit_years_growth_ratio.desc()
    ), date=last_date)
    return list(A['growth_symbol'])


# 3. S - Market capitalization
def stocks_S(account, data):
    last_date = get_last_datetime().strftime('%Y%m%d')
    securities = list(get_all_securities('stock', last_date).index)
    S = get_factors(query(
        factor.symbol,
        factor.current_market_cap
    ).filter(
        factor.symbol.in_(securities),
        factor.date == last_date
    ).order_by(
        factor.current_market_cap.asc()
    ))
    return list(S['factor_symbol'].head(500))


# 4. L - Overbought/oversold
def stocks_L(account, data):
    last_date = get_last_datetime().strftime('%Y%m%d')
    securities = list(get_all_securities('stock', last_date).index)
    L = get_factors(query(
        factor.symbol,
        factor.rsi
    ).filter(
        factor.symbol.in_(securities),
        factor.rsi < 50,
        factor.date == last_date
    ).order_by(
        factor.rsi.asc()
    ))
    return list(L['factor_symbol'])
