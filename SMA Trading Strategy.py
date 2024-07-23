import talib
import numpy as np
import pandas as pd


# 初始化证券账户及策略信息
def init(context):
    # 设置要交易的股票池
    context.stk = '000002.SZ'
    # 设置参照基准
    set_benchmark(context.stk)
    # 设置获取历史数据的时间周期
    g.period = 10


# 该函数用来定时执行买卖条件，每个交易频率（日/分钟）自动调用一次.
def handle_bar(context, bar_dict):
    # 获取过去g.period天的历史行情数据
    price = history(context.stk, ['close', 'high', 'low'], g.period, '1d', False, 'pre', is_panel=0)
    # 获取收盘价数据
    close = price['close'].values
    # 计算SMA
    SMA = talib.SMA(close, g.period)
    # 获取当前的股票价格
    crtprice = bar_dict[context.stk].open
    # 获取当前个股的持仓
    curposition = context.portfolio.positions[context.stk].amount
    # 若开盘价上穿均线，且持仓为0,则全仓买入
    if crtprice > SMA[-1] and curposition == 0:
        order_target_percent(context.stk, 1)
        print('买入价格：' + str(crtprice))
    # 若开盘价下穿均线，且有持仓，则清仓
    if crtprice < SMA[-1] and curposition != 0:
        order_target_percent(context.stk, 0)
        print('卖出价格：' + str(crtprice))
    # 绘图
    record(SMA=SMA[-1], crtprice=crtprice)