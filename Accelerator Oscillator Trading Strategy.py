# 加速震荡指标（Accelerator Oscillator）

import talib
import datetime
import numpy as np


def init(context):
    context.nday = 5  # 短期值
    context.mday = 20  # 长期值
    # 定义股票池
    context.stocks = ['600519.SH', '000333.SZ', '600816.SH', '300072.SZ']


def before_trading(context):
    cash = context.portfolio.available_cash
    date = get_datetime()
    pass


def handle_bar(context, bar_dict):
    for stk in context.stocks:
        high = history(stk, ['high'], 30, '1d')['high']  # 获取最高价数据
        low = history(stk, ['low'], 30, '1d')['low']  # 获取最低价数据
        MP = np.array((high.values + low.values) / 2)  # 计算MP = (high + low)/2
        AO = talib.MA(MP, context.nday) - talib.MA(MP, context.mday)  # 计算AO值
        AC = AO - talib.MA(AO, context.nday)  # 计算AC值
        curPosition = context.portfolio.positions[stk].amount  # 获取持股数量
        shares = context.portfolio.available_cash  # 取得当前资金
        # AC值自下而上穿越零轴时全仓买进
        if AC[-1] > 0 and AC[-2] < 0:
            order_value(stk, shares)
            log.info("买入 %s" % (stk))
        # AC值自上而下下穿零轴时清仓
        if AC[-1] < 0 and AC[-2] > 0 and curPosition > 0:
            order_target_value(stk, 0)
            log.info("卖出 %s" % (stk))