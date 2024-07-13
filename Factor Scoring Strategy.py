from datetime import timedelta, date
# 1.导入时间数据包
import pandas as pd


# 2.导入pandas数据包，快捷使用为pd
# 初始化函数 ##################################################################
def init(context):
    context.n = 30  # 最大持股数
    # 调仓月份设置，为1-12月
    context.trade_date = range(1, 13, 1)
    ## 按月调仓，调仓日为月末最后一个交易日
    run_monthly(trade, date_rule=2)
    # 运用I问财进行股票筛选
    get_iwencai('未停牌,上市时间超过2年')


# 每日检查止损条件 #############################################################
def handle_bar(context, bar_dict):
    # 获取账户持仓信息
    holdstock = list(context.portfolio.stock_account.positions.keys())
    if len(holdstock) > 0:
        num = -0.1
        for stock in holdstock:
            close = history(stock, ['close'], 1, '1d').values
            if close / context.portfolio.positions[stock].last_price - 1 <= num:
                order_target(stock, 0)
                log.info('股票{}已止损'.format(stock))


# 1. 筛选股票列表
def stocks_jz(context, bar_dict):
    # 创建字典用于存
    time = get_datetime()
    date = time.strftime('%Y%m%d')
    df = {'security': [], 1: [], 2: [], 3: [], 'score': []}
    stocks = context.iwencai_securities
    for security in stocks:
        q = query(
            profit.symbol,
            valuation.pe_ttm,  # 市盈率
            valuation.pb,  # 市净率
            valuation.ps_ttm,  # 市销率
        ).filter(
            profit.symbol == security
        )

        # 缺失值填充为0
        yz = get_fundamentals(q, date=date).fillna(0)
        df['security'].append(security)
        # 判断是否有数据
        if (not (yz['valuation_pe_ttm'].empty or
                 yz['valuation_ps_ttm'].empty or
                 yz['valuation_pb'].empty)):
            if yz['valuation_pe_ttm'][0] < 33:
                df[1].append(10)
            else:
                df[1].append(0)
            if yz['valuation_ps_ttm'][0] < 2.01:
                df[2].append(10)
            elif yz['valuation_ps_ttm'][0] < 10.01 and yz['valuation_ps_ttm'][0] > 2.01:
                df[2].append(5)
            else:
                df[2].append(0)
            if yz['valuation_pb'][0] < 1.01:
                df[3].append(10)
            elif yz['valuation_pb'][0] < 3.01 and yz['valuation_pb'][0] > 1.01:
                df[3].append(5)
            else:
                df[3].append(0)
        else:
            df[1].append(0)
            df[2].append(0)
            df[3].append(0)
        # 计算综合因子得分
    for i in range(len(df['security'])):
        # 等权重计算(注意因子方向)
        s = (df[1][i] + df[2][i] + df[3][i])
        df['score'].append(s)
        # 由小到大排序
    df = pd.DataFrame(df).sort_values(by='score', ascending=False)
    context.sample = df['security'][:30]
    return context.sample


def trade(context, bar_dict):
    date = get_datetime()
    months = get_datetime().month
    if months in context.trade_date:
        ##获得50只股票列表
        jz_list = stocks_jz(context, bar_dict)
        ## 获得满足每种条件的股票池
        stock_list = list(set(jz_list))
        ## 卖出
        if len(list(context.portfolio.stock_account.positions.keys())) > 0:
            for stock in list(context.portfolio.stock_account.positions.keys()):
                if stock not in stock_list:
                    order_target(stock, 0)
        ## 买入
        if len(stock_list) > 0:
            for stock in stock_list:
                if stock not in list(context.portfolio.stock_account.positions.keys()):
                    if len(list(context.portfolio.stock_account.positions.keys())) < context.n:
                        number = context.n - len(list(context.portfolio.stock_account.positions.keys()))
                        order_value(stock, context.portfolio.stock_account.available_cash / number)
                    else:
                        order_value(stock, context.portfolio.stock_account.available_cash)
