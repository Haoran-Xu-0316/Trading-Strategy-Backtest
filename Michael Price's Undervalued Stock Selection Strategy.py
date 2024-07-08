'''
Stock Selection Strategy:
A. Select the 400 stocks with the lowest P/B ratio where the price-to-book ratio is less than 2.
B. Directors and supervisors' shareholding ratio is higher than the market average (data missing).
C. Debt ratio is lower than the market average.
D. Select the top 30 stocks that meet the above criteria.

Trading Method:

Monthly rebalancing.
Stop-Loss Method:
A. Sell a stock if its price falls below the cost price by 7%.
B. Sell all stocks if the market declines by 13% within 5 days.
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
        PB_list = stocks_PB(context,bar_dict)
        Equity_ratio_list = stocks_equity_ratio(context,bar_dict)
        ## 获得满足每种条件的股票池
        stock_list = list(set(PB_list)&set(Equity_ratio_list))
        log.info(len(stock_list))

        ## 卖出
        if len(list(context.portfolio.stock_account.positions.keys()) ) > 0:
            for stock in list(context.portfolio.stock_account.positions.keys()) :
                if stock not in stock_list:
                    order_target(stock, 0)
        ## 买入
        if len(stock_list) > 0:
            for stock in stock_list:
                if stock not in list(context.portfolio.stock_account.positions.keys()) :
                    if len(list(context.portfolio.stock_account.positions.keys())) < context.n :
                        number = context.n  - len(list(context.portfolio.stock_account.positions.keys()) )
                        order_value(stock,context.portfolio.available_cash/number)
                    else:
                        order_value(stock,context.portfolio.available_cash)

# 每日检查止损条件 #############################################################
def handle_bar(context,bar_dict):
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


# 1. 根据市净率筛选股票列表
def stocks_PB(context, bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    PB = get_fundamentals(query(
            valuation.symbol,
            valuation.pb
        ).filter(
            valuation.pb > 0,
            valuation.pb < 2
        ).order_by(
            valuation.pb.asc()
        ).limit(
            context.selected
        ),date = last_date)


    return list(PB['valuation_symbol'])

# 5. 根据负债比例条件来筛选股票列表
def stocks_equity_ratio(context, bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    equity_ratio = get_fundamentals(query(
            debtrepay.symbol,
            debtrepay.equity_ratio
        ),date = last_date)
    equity_ratio_mean = equity_ratio['debtrepay_equity_ratio'].mean()
    equity_ratio = equity_ratio[equity_ratio['debtrepay_equity_ratio']<equity_ratio_mean]
    return list(equity_ratio['debtrepay_symbol'])