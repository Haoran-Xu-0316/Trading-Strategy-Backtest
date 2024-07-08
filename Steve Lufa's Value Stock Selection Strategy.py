'''
Stock Selection Strategy:
A. Stocks with P/B ratio greater than 0 and below the market average, sorted by ascending P/B ratio
B. Stocks with P/E ratio greater than 0 and below the market average, sorted by ascending P/E ratio
C. Current assets are at least 30% of total market capitalization
D. Price-to-cash-flow ratio greater than 0 and below the market average, sorted by ascending price-to-cash-flow ratio
E. Long-term debt-to-capital ratio less than 50%
F. Current ratio higher than the market average, sorted by descending current ratio
G. Selecting the top 30 stocks from the stock pool that meet all of the above conditions

Trading Method:
Monthly rebalancing

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
        log.info(len(PB_list))
        PE_list = stocks_PE(context,bar_dict)
        log.info(len(PE_list))
        curAst_to_cap_list = stocks_curAst_to_cap(context,bar_dict)
        log.info(len(curAst_to_cap_list))
        PCF_list = stocks_PCF(context,bar_dict)
        log.info(len(PCF_list))
        equity_ratio_list = stocks_equity_ratio(context,bar_dict)
        log.info(len(equity_ratio_list))
        current_ratio_list = stocks_current_ratio(context,bar_dict)
        log.info(len(current_ratio_list))
        ## 获得满足每种条件的股票池
        stock_list = list(set(PB_list)&set(PE_list)&set(PCF_list)&set(equity_ratio_list)&set(curAst_to_cap_list)&set(current_ratio_list))
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

    else:
        pass

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
def stocks_PB(context,bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    PB = get_fundamentals(query(
            valuation.symbol,
            valuation.pb
        ).filter(
            valuation.pb > 0
        ).order_by(
            valuation.pb.asc()
        ),date = last_date)
    PB_mean = PB['valuation_pb'].mean()
    PB = PB[PB['valuation_pb']<PB_mean]
    return list(PB['valuation_symbol'])

# 2. 根据市盈率筛选股票列表
def stocks_PE(context,bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    PE = get_fundamentals(query(
            valuation.symbol,
            valuation.pe
        ).filter(
            valuation.pe > 0
        ).order_by(
            valuation.pe.asc()
        ),date = last_date)
    PE_mean = PE['valuation_pe'].mean()
    PE = PE[PE['valuation_pe']<PE_mean]
    return list(PE['valuation_symbol'])
# 3. 根据流动资产和市值条件来筛选股票列表
def stocks_curAst_to_cap(context,bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    curAst_to_cap_list = get_fundamentals(query(
            balance.symbol,
            balance.total_current_assets,
            valuation.market_cap
        ),date = last_date)
    curAst_to_cap_list['curAst_to_cap'] = curAst_to_cap_list['balance_total_current_assets']/curAst_to_cap_list['valuation_market_cap']
    curAst_to_cap_list = curAst_to_cap_list[curAst_to_cap_list['curAst_to_cap']>=0.3]
    return list(curAst_to_cap_list['balance_symbol'])
# 4. 根据市现率筛选股票列表
def stocks_PCF(context,bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    PCF = get_fundamentals(query(
            valuation.symbol,
            valuation.pcf
        ).filter(
            valuation.pcf > 0
        ).order_by(
            valuation.pcf.asc()
        ),date = last_date)

    PCF_mean = PCF['valuation_pcf'].mean()
    PCF = PCF[PCF['valuation_pcf']<PCF_mean]
    return list(PCF['valuation_symbol'])
# 5. 根据产权比率条件来筛选股票列表
def stocks_equity_ratio(context,bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    equity_ratio = get_fundamentals(query(
            debtrepay.symbol,
            debtrepay.equity_ratio
        ).filter(
            debtrepay.equity_ratio<0.5
            ),date = last_date)
    return list(equity_ratio['debtrepay_symbol'])
# 6. 根据流动比率筛选股票列表
def stocks_current_ratio(context,bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    Current_ratio = get_fundamentals(query(
            debtrepay.symbol,
            debtrepay.current_ratio
        ).order_by(
            debtrepay.current_ratio.desc()
        ),date = last_date)
    Current_ratio_mean = Current_ratio['debtrepay_current_ratio'].mean()
    Current_ratio = Current_ratio[Current_ratio['debtrepay_current_ratio']>Current_ratio_mean]
    return list(Current_ratio['debtrepay_symbol'])
