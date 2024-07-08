'''
Stock Selection Strategy:
A. Stocks with P/E ratio greater than 0, selecting the 400 stocks with the lowest P/E ratio
B. Stocks with P/B ratio greater than 0 and less than 2.5, selecting the 400 stocks with the lowest P/B ratio
C. Current assets of the enterprise are at least 1.2 times current liabilities
D. Total borrowings of the enterprise do not exceed 1.5 times net current assets
E. Net profit of the enterprise is greater than 0
F. Most recent cash dividends are greater than 0
G. Net profit growth rate sorted in descending order, selecting the top 400 stocks
H. Selecting the top 30 stocks that meet all of the above 7 conditions

Trading Method:
Rebalancing monthly

Stop-Loss Method:
A. Sell the stock if its price falls below the cost price by 7%
B. Sell all stocks if the market declines by 13% within 5 days

'''
from datetime import timedelta, date
import pandas as pd

############################## 以下为主要函数  ################################
# 初始化函数 ##################################################################
def init(context):
    # set_commission(PerTrade(cost=0.0003, min_trade_cost=5))
    # set_slippage(PriceRelatedSlippage())
    context.selected = 400
    context.n = 30 # 持股数
    #调仓频率
    context.trade_date = range(1,13,1)
    ## 按月调用程序
    run_monthly(trade,date_rule=-1)
# 月末调仓函数 #################################################################
def trade(context, bar_dict):
    date = get_datetime()
    months = get_datetime().month
    if months in context.trade_date:


        ##获得购买股票列表
        PE_list = stocks_PE(context,bar_dict)
        PB_list = stocks_PB(context,bar_dict)
        current_ratio_list = stocks_current_ratio(context,bar_dict)
        Debt_asset_list = stocks_Debt_asset(context,bar_dict)
        netProfitGrowthrate_list = stocks_netProfitGrowthrate(context,bar_dict)
        netprofit = stocks_netprofit(context,bar_dict)
        ## 获得满足每种条件的股票池
        stock_list = list(set(PE_list)&set(PB_list)&set(current_ratio_list)&set(Debt_asset_list)&set(netProfitGrowthrate_list)&set(netprofit))
        log.info(len(stock_list))

        ## 卖出
        if len(list(context.portfolio.stock_account.positions.keys())) > 0:
            for stock in list(context.portfolio.stock_account.positions.keys()):
                if stock not in stock_list:
                    order_target(stock, 0)
        ## 买入
        if len(stock_list) > 0:
            for stock in stock_list:
                if stock not in list(context.portfolio.stock_account.positions.keys()):
                    if len(list(context.portfolio.stock_account.positions.keys())) < context.n :
                        number = context.n  - len(list(context.portfolio.stock_account.positions.keys()))
                        order_value(stock,context.portfolio.available_cash/number)
                    else:
                        order_value(stock,context.portfolio.available_cash)

    else:
        pass

# 每日检查止损条件 #############################################################
def handle_bar(context, bar_dict):
    #获取账户持仓信息
    holdstock = list(context.portfolio.stock_account.positions.keys())
    if len(holdstock) > 0:
        num = -0.07
        for stock in holdstock:
            close = history(stock,['close'],1,'1d').values
            if close/context.portfolio.positions[stock].last_price -1 <= num:
                order_target(stock,0)
                log.info('股票{}已止损'.format(stock))
    #获取账户持仓信息
    holdstock = list(context.portfolio.stock_account.positions.keys())
    if len(holdstock) > 0:
        num = - 0.13
        T = history('000001.SH',['quote_rate'],5,'1d').values.sum()
        if T < num*100:
            log.info('上证指数连续三天下跌{}已清仓'.format(T))
            for stock in holdstock:
                order_target(stock,0)

################## 以下为功能函数, 在主要函数中调用 ##########################

# 1. 根据市盈率筛选股票列表
def stocks_PE(context,bar_dict):
    current_date = get_last_datetime().strftime('%Y%m%d')
    PE = get_fundamentals(query(
            valuation.symbol,
            valuation.pe
        ).filter(
            valuation.pe > 0,
        ).order_by(
            valuation.pe.asc()
        ).limit(
            context.selected
        ),date = current_date)

    return list(PE['valuation_symbol'])
# 2. 根据市净率筛选股票列表
def stocks_PB(context,bar_dict):
    current_date = get_last_datetime().strftime('%Y%m%d')
    PB = get_fundamentals(query(
            valuation.symbol,
            valuation.pb
        ).filter(
            valuation.pb > 0,
            valuation.pb < 2.5
        ).order_by(
            valuation.pb.asc()
        ).limit(
            context.selected
        ),date = current_date)


    return list(PB['valuation_symbol'])
# 3. 根据流动比率筛选股票列表
def stocks_current_ratio(context,bar_dict):
    current_date = get_last_datetime().strftime('%Y%m%d')
    Current_ratio = get_fundamentals(query(
            debtrepay.symbol,
            debtrepay.current_ratio
        ).filter(
            debtrepay.current_ratio>1.2
        ).order_by(
            debtrepay.current_ratio.desc()
        ),date = current_date)

    return list(Current_ratio['debtrepay_symbol'])

# 4. 根据长期与运营资金比率条件筛选股票列表
def stocks_Debt_asset(context,bar_dict):
    current_date = get_last_datetime().strftime('%Y%m%d')
    Debt_asset = get_fundamentals(query(
            debtrepay.symbol,
            debtrepay.long_term_debt_to_opt_capital_ratio
        ).filter(
            debtrepay.long_term_debt_to_opt_capital_ratio<1.5
            ),date = current_date)
    return list(Debt_asset['debtrepay_symbol'])

# 5. 根据净利润增长率条件筛选股票列表
def stocks_netProfitGrowthrate(context,bar_dict):
    current_date = get_last_datetime().strftime('%Y%m%d')
    net_profit_growth_ratio = get_fundamentals(query(
            growth.symbol,
            growth.net_profit_growth_ratio
        ).filter(
            growth.net_profit_growth_ratio>0
        ).order_by(
            growth.net_profit_growth_ratio.desc()

        ),date = current_date)
    return list(net_profit_growth_ratio['growth_symbol'])

# 6. 根据净利润条件筛选股票列表
def stocks_netprofit(context,bar_dict):
    current_date = get_last_datetime().strftime('%Y%m%d')
    netprofit = get_fundamentals(query(
            income.symbol,
            income.net_profit
        ).filter(
            income.net_profit > 0
            ),date = current_date)

    return list(netprofit['income_symbol'])
