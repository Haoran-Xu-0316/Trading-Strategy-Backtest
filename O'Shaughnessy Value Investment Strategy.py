'''
Stock Selection Strategy:
A. The market capitalization of the stock is greater than the market median.
B. The equity of the stock is greater than the market median.
C. The price-to-cash-flow ratio of the stock is greater than 0. Sort in ascending order and select the top 400 stocks.
D. The price-to-sales ratio of the stock is greater than 0. Sort in ascending order and select the top 400 stocks.
E. The dividend yield of the stock is sorted in descending order, and the top 400 stocks are selected.
F. Select the top 30 stocks that meet the above five conditions.

Trading Method:
Adjust the portfolio monthly.

Stop-Loss Method:
A. Sell the stock when its price falls below 7% of the cost price.
B. Sell all stocks when the market index drops by 13% within 5 days.
'''
from datetime import timedelta, date
import pandas as pd

############################## 以下为主要函数  ################################
# 初始化函数 ##################################################################

def init(context):
    # 设置手续费为交易额的0.02%，最少5元
    set_commission(PerShare(type='stock', cost=0.0003, min_trade_cost=5.0))
    # 设置可变滑点，买入成交价 = 委托价 * (1 + 0.1%)，卖出成交价 = 委托价 * (1 - 0.1%);
    set_slippage(PriceSlippage(0.002))
    context.selected = 400
    context.n = 30 # 持股数
    context.trade_date = range(1,13,1)
    ## 按月调用程序
    run_monthly(trade,date_rule=-1)

# 月末调仓函数 #################################################################
def trade(context, bar_dict):
    date = get_datetime()
    months = get_datetime().month
    if months in context.trade_date:


        ##获得购买股票列表
        market_cap_list = stocks_market_cap(context, bar_dict)
        PCF_list = stocks_PCF(context, bar_dict)
        PS_list = stocks_PS(context, bar_dict)
        capitalization_list = stocks_capitalization(context, bar_dict)
        DY_list = stocks_DY(context, bar_dict)
        ## 获得满足每种条件的股票池
        stock_list = list(set(market_cap_list)&set(PCF_list)&set(PS_list)&set(capitalization_list)&set(DY_list))
        log.info(len(stock_list))

        ## 卖出
        if len(context.portfolio.positions) > 0:
            for stock in list(context.portfolio.positions):
                if stock not in stock_list:
                    order_target(stock, 0)
        ## 买入
        if len(stock_list) > 0:
            for stock in stock_list:
                if stock not in list(context.portfolio.positions):
                    if len(context.portfolio.positions) < context.n :
                        number = context.n  - len(context.portfolio.positions)
                        order_value(stock,context.portfolio.available_cash/number)
                    else:
                        order_value(stock,context.portfolio.available_cash)

    else:
        pass

# 每日检查止损条件 #############################################################
def handle_bar(context, bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')

    if len(context.portfolio.positions) > 0:
        # 止损：个股跌幅超过8%，卖出
        securities = list(context.portfolio.positions)
        for stock in securities:
            price = history(stock, ['close'], 1, '1d', False,'pre')
            if context.portfolio.positions[stock].cost_basis/price['close'][0]-1 < -0.08:
                order_target(stock, 0)
                #log.info('%s 止损：%s' %(last_date,stock))

        #止损：5天内大盘下跌13%，卖出
        price_bench = history('000300.SH', ['close'], 5, '1d', False,'pre')
        if price_bench['close'][-5]/price_bench['close'][-1]-1 > 0.13:
            if len(list(context.portfolio.positions))>0:
                for stock in list(context.portfolio.positions):
                    order_target(stock, 0)

################## 以下为功能函数, 在主要函数中调用 ##########################

# 1 根据市值来筛选股票列表
def stocks_market_cap(context, bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    market_cap = get_fundamentals(query(
            valuation.symbol,
            valuation.market_cap
        ).order_by(
            valuation.market_cap.desc()
        ),date = last_date)
    length = len(market_cap)
    market_cap = market_cap[:int(length/2)]
    return list(market_cap['valuation_symbol'])

# 2. 根据股本来筛选股票列表
def stocks_capitalization(context, bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    capitalization = get_fundamentals(query(
            valuation.symbol,
            valuation.capitalization
        ).order_by(
            valuation.capitalization.desc()
        ),date = last_date)
    length = len(capitalization)
    capitalization = capitalization[:int(length/2)]
    return list(capitalization['valuation_symbol'])

# 3. 根据市现率来筛选股票列表
def stocks_PCF(context, bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    PCF = get_fundamentals(query(
            valuation.symbol,
            valuation.pcf
        ).filter(
            valuation.pcf > 0
        ).order_by(
            valuation.pcf.asc()
        ).limit(
            context.selected
        ),date = last_date)
    return list(PCF['valuation_symbol'])

# 4. 根据市销率来筛选股票列表
def stocks_PS(context, bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    PS = get_fundamentals(query(
            valuation.symbol,
            valuation.ps
        ).filter(
            valuation.ps>0
        ).order_by(
            valuation.ps.asc()
        ),date = last_date)
    return list(PS['valuation_symbol'])

# 5. 根据股息率（每股收益/每股市价代替）来筛选股票列表

def stocks_DY(context, bar_dict):
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
    return list(dict(DY_stock[:context.selected]).keys())