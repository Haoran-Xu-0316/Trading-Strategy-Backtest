'''

Stock Selection Strategy:
A. The stock's debt-to-equity ratio is less than 80%.
B. The stock's price-to-earnings ratio is no more than 1.5 times the market average.
C. The stock's price-to-cash-flow ratio for the past four quarters is no more than 1.5 times the market average.
D. The stock's price-to-book ratio is no more than 1.5 times the market average.
E. The stock's price-to-book ratio is less than 2.0 times.
F. Select the top 30 stocks that meet the above conditions.

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
    log.info(months)
    if months in context.trade_date:

        ##获得购买股票列表
        PE_list = stocks_PE(context, bar_dict)
        PB_list = stocks_PB(context, bar_dict)
        PCF_ttm_list = stocks_PCF_ttm(context, bar_dict)
        Debt_asset_list = stocks_Debt_asset(context, bar_dict)
        stock_list = list(set(PE_list)&set(PB_list)&set(PCF_ttm_list)&set(Debt_asset_list))

        ## 卖出股票
        if len(context.portfolio.positions) > 0:
            for stock in list(context.portfolio.positions):
                if stock not in stock_list:
                    order_target(stock, 0)
        ## 买入股票
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

    ## 个股止损
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
                    #log.info('%s 大盘下跌' %(last_date))

################## 以下为功能函数, 在主要函数中调用 ##########################
# 1. 根据PE因子选出的股票列表
def stocks_PE(context, bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    PE = get_fundamentals(query(
            valuation.symbol,
            valuation.pe
        ).filter(
            valuation.pe > 0,
        ).order_by(
            valuation.pe.asc()
        ),date = last_date)
    PE_limit = PE['valuation_pe'].mean()*1.5
    PE = PE[PE['valuation_pe']<=PE_limit]
    #log.info(PE)
    return list(PE['valuation_symbol'])
# 2. 根据PB因子选出的股票列表
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
        ),date = last_date)
    PB_limit = PB['valuation_pb'].mean()*1.5
    PB = PB[PB['valuation_pb']<=PB_limit]
    return list(PB['valuation_symbol'])
# 3. 根据PCF_ttm因子选出的股票列表
def stocks_PCF_ttm(context, bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    PCF_ttm = get_fundamentals(query(
            valuation.symbol,
            valuation.pcf_ttm
        ).filter(
            valuation.pcf_ttm > 0
        ).order_by(
            valuation.pb.asc()
        ),date = last_date)
    PCF_ttm_limit = PCF_ttm['valuation_pcf_ttm'].mean()*1.5
    PCF_ttm = PCF_ttm[PCF_ttm['valuation_pcf_ttm']<=PCF_ttm_limit]
    return list(PCF_ttm['valuation_symbol'])

# 4. 根据长期负债与运营资金比率条件筛选股票列表
def stocks_Debt_asset(context, bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    Debt_asset = get_fundamentals(query(
            debtrepay.symbol,
            debtrepay.equity_ratio
        ).filter(
            debtrepay.equity_ratio<0.8
            ),date = last_date)
    return list(Debt_asset['debtrepay_symbol'])