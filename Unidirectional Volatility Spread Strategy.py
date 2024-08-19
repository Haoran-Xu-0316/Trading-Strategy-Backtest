import pandas as pd
#初始化账户
def init(context):
    #设置要交易的股票
    context.security = '600519.SH'
#设置买卖条件，每个交易频率（日/分钟/tick）调用一次
def handle_bar(context,bar_dict):
    stk = context.security
    # 获取过去250天的相关数据（开、高、低价格）
    data = history(stk, ['open','high','low'], 250, '1d')
    # 计算单向波动差值
    dif = (data['high'] + data['low'])/data['open']-2
    # 计算单向波动差值均值
    dif_ma = pd.rolling_mean(dif,60)
    # 若dif_ma为正，则买入或持仓
    if dif_ma.values[-1] > 0:
        order_target_percent(stk,1)
    # 若dif_ma为负，则卖出或空仓
    if dif_ma.values[-1] < 0 and context.portfolio.stock_account.market_value > 0:
        order_target(stk,0)