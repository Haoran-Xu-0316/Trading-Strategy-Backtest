
import numpy as np
import pandas as pd


# 初始化函数 #######################################################################
def init(context):
    context.last_date = ''
    context.hold_max = 30
    run_monthly(func=func_run_monthly, date_rule=-1)


# 月末调仓函数 #######################################################################
def func_run_monthly(context, bar_dict):
    # 获取昨日日期
    date = get_last_datetime().strftime('%Y%m%d')
    # 获取上个月末调仓日期
    context.last_date = func_get_end_date_of_last_month(date)

    log.info('############################## ' + str(date) + ' ###############################')

    # 获取所有A股股票代码
    securities = list(get_all_securities('stock', date).index)

    # 获取pb, pe, ps财务因子为正的股票
    q = query(
        valuation.symbol,
        valuation.pb,
        valuation.ps_ttm,
        valuation.pe_ttm
    ).filter(
        valuation.pb > 0,
        valuation.ps_ttm > 0,
        valuation.pe_ttm > 0,
        valuation.symbol.in_(securities)
    )
    df = get_fundamentals(q, date)
    securities = list(df['valuation_symbol'].values)

    # 计算过去一个月的股价动量、成交金额、ST信息
    values = get_price(securities, context.last_date, date, '1d', ['close', 'turnover', 'is_st'], skip_paused=False,
                       fq='pre', is_panel=0)

    momentum = []
    turnover = []
    st = []
    for stock in securities:
        try:
            momentum.append((values[stock]['close'][-1] - values[stock]['close'][0]) / values[stock]['close'][0])
            turnover.append(values[stock]['turnover'].sum())
            st.append(values[stock]['is_st'][-1])
        except:
            log.info('数据缺失:  %s' % stock)
            momentum.append(None)
            turnover.append(None)
            st.append(None)

    df['momentum'] = np.array(momentum)
    df['turnover'] = np.array(turnover)
    df['is_st'] = np.array(st)

    # 去掉ST和成交金额为0的股票
    df[df['is_st'] == 1] = None
    df[df['turnover'] == 0] = None
    df = df.dropna()

    # 去极值
    df = winsorize(df, 'valuation_pb', 20).copy()
    df = winsorize(df, 'valuation_ps_ttm', 20).copy()
    df = winsorize(df, 'valuation_pe_ttm', 20).copy()
    df = winsorize(df, 'momentum', 20).copy()
    df = winsorize(df, 'turnover', 20).copy()
    df = df.dropna()

    # 为全部A股打分，综合得分越小越好
    df['scores'] = 0

    list_pb = list(df.sort_values(['valuation_pb'], ascending=True)['valuation_symbol'].values)
    func_scores(df, list_pb)
    list_ps = list(df.sort_values(['valuation_ps_ttm'], ascending=True)['valuation_symbol'].values)
    func_scores(df, list_ps)
    list_pe = list(df.sort_values(['valuation_pe_ttm'], ascending=True)['valuation_symbol'].values)
    func_scores(df, list_pe)
    list_mo = list(df.sort_values(['momentum'], ascending=True)['valuation_symbol'].values)
    func_scores(df, list_mo)
    list_to = list(df.sort_values(['turnover'], ascending=True)['valuation_symbol'].values)
    func_scores(df, list_to)

    # 根据股票综合得分为股票排序
    context.selected = list(df.sort_values(['scores'], ascending=True)['valuation_symbol'].values)

    # 买入挑选的股票
    func_do_trade(context, bar_dict)

    context.last_date = date


#### 每日检查止损条件
def handle_bar(context, bar_dict):
    last_date = get_last_datetime().strftime('%Y%m%d')
    if last_date != context.last_date and len(list(context.portfolio.stock_account.positions.keys())) > 0:
        # 如果不是调仓日且有持仓，判断止损条件
        func_stop_loss(context, bar_dict)


################## 以下为功能函数, 在主要函数中调用 ##########################

#### 1. 获取上月月末日期 #####################################################
def func_get_end_date_of_last_month(current_date):
    trade_days = list(get_trade_days(None, current_date, count=30))

    for i in range(len(trade_days)):
        trade_days[i] = trade_days[i].strftime('%Y%m%d')

    for date in reversed(trade_days):
        if date[5] != current_date[5]:
            return date

    log.info('Cannot find the end date of last month.')
    return


#### 2. 中位数去极值函数 ####################################################
def winsorize(df, factor, n=20):
    '''
    df为bar_dictFrame数据
    factor为需要去极值的列名称
    n 为判断极值上下边界的常数
    '''
    ls_raw = np.array(df[factor].values)
    ls_raw.sort(axis=0)
    # 获取中位数
    D_M = np.median(ls_raw)

    # 计算离差值
    ls_deviation = abs(ls_raw - D_M)
    ls_deviation.sort(axis=0)
    # 获取离差中位数
    D_MAD = np.median(ls_deviation)

    # 将大于中位数n倍离差中位数的值赋为NaN
    df.loc[df[factor] >= D_M + n * D_MAD, factor] = None
    # 将小于中位数n倍离差中位数的值赋为NaN
    df.loc[df[factor] <= D_M - n * D_MAD, factor] = None

    return df


#### 3. 按因子排序打分函数 #############################################################
def func_scores(df, ls):
    '''
    按照因子暴露值将股票分为20档
    第一档股票综合得分+1分
    第二档股票综合得分+2分
    以此类推
    '''
    quotient = len(ls) // 20
    remainder = len(ls) % 20
    layer = np.array([quotient] * 20)

    for i in range(0, remainder):
        layer[-(1 + i)] += 1

    layer = np.insert(layer, 0, 0)
    layer = layer.cumsum()

    for i in range(0, 20):
        for j in range(layer[i], layer[i + 1]):
            df.loc[df['valuation_symbol'] == ls[j], 'scores'] += (i + 1)


#### 4.下单函数 ###################################################################
def func_do_trade(context, bar_dict):
    # 先清空所有持仓
    if len(list(context.portfolio.stock_account.positions.keys())) > 0:
        for stock in list(context.portfolio.stock_account.positions.keys()):
            order_target(stock, 0)

    # 买入前30支股票
    for stock in context.selected:
        order_target_percent(stock, 1. / context.hold_max)
        if len(list(context.portfolio.stock_account.positions.keys())) >= context.hold_max:
            break
    return


#### 5.止损函数 ####################################################################
def func_stop_loss(context, bar_dict):
    # 获取账户持仓信息
    holdstock = list(context.portfolio.stock_account.positions.keys())
    if len(holdstock) > 0:
        num = -0.1
        for stock in holdstock:
            close = history(stock, ['close'], 1, '1d').values
            if close / context.portfolio.positions[stock].last_price - 1 <= num:
                order_target(stock, 0)
                log.info('股票{}已止损'.format(stock))

    # 获取账户持仓信息
    holdstock = list(context.portfolio.stock_account.positions.keys())
    if len(holdstock) > 0:
        num = - 0.13
        T = history('000001.SH', ['quote_rate'], 7, '1d').values.sum()
        if T < num * 100:
            log.info('上证指数连续三天下跌{}已清仓'.format(T))
            for stock in holdstock:
                order_target(stock, 0)

