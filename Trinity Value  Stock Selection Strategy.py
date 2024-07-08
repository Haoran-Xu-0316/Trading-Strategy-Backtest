'''

Specific Strategy:
1. Monthly rebalancing is employed. Stocks meeting the following criteria are selected for the portfolio:
   - The lowest 400 companies by P/E ratio
   - The lowest 400 companies by P/B ratio
   - The highest 400 companies by dividend yield
   To control the number of stocks selected each period, the following additional condition is applied:
   - If more than 30 stocks are selected, only the top 30 are included in the portfolio.

2. Stop-Loss Method:
   - Sell a stock if its price falls below the cost price by 8%.
   - Sell all stocks if the market declines by 13% within 5 days.

'''
from datetime import timedelta, date
import pandas as pd

############################## 以下为主要函数  ################################
# 初始化函数 ##################################################################
def init(context):

    # set_commission(PerTrade(cost=0.0003, min_trade_cost=5))
    # set_slippage(PriceRelatedSlippage())

    context.selected = 400
    #设置持仓的数量
    context.n = 30
    #月度调仓
    context.trade_date = range(1,13,1)
    #交易按月运行
    run_monthly(trade,date_rule=-1)
# 月末调仓函数 #################################################################
def trade(context, bar_dict):
    months = get_datetime().month
    if months in context.trade_date:


        ##获得购买股票列表
        PE_list = stocks_PE(context,bar_dict)
        PB_list = stocks_PB(context,bar_dict)
        DR_list = stocks_DR(context,bar_dict)
        DY_list = list(dict(DR_list).keys())
        stock_list = list(set(PE_list)&set(PB_list)&set(DY_list))
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
# 1.根据市盈率筛选股票列表
def stocks_PE(context,bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    PE = get_fundamentals(query(
            valuation.symbol,
            valuation.pe
        ).filter(
            valuation.pe > 0,
        ).order_by(
            valuation.pe.asc()
        ).limit(
            context.selected
        ),date = last_date)

    return list(PE['valuation_symbol'])

# 2.根据市净率筛选股票列表
def stocks_PB(context,bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    PB = get_fundamentals(query(
            valuation.symbol,
            valuation.pb
        ).filter(
            valuation.pb > 0,
        ).order_by(
            valuation.pb.asc()
        ).limit(
            context.selected
        ),date = last_date)


    return list(PB['valuation_symbol'])

# 3.根据股息率（每股收益/每股市价代替）来筛选股票列表
def stocks_DR(context,bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    EPS = get_fundamentals(query(
        income.symbol,
        income.basic_eps
    ),date = last_date)
    stock_List = list(EPS['income_symbol'])
    close_price = history(stock_List,['close'],1,'1d',True,None)
    DY_stock = dict(zip(EPS['income_symbol'],EPS['income_basic_eps']))
    log.info(len(DY_stock)-len(EPS['income_symbol']))
    for stock in stock_List:
        try:
            DY_stock[stock] = DY_stock[stock]/close_price[stock]['close'][0]
        except:
            DY_stock[stock] = 0


    DY_stock = sorted(DY_stock.items(),key=lambda t:t[1],reverse=True)
    return DY_stock[:context.selected]






