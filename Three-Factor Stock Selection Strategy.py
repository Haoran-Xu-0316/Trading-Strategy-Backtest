

import pandas as pd
import numpy as np
import datetime


def init(context):
    # 使用智能选股函数设置股票池
    get_iwencai('沪深300')
    # 设置最大持股数

    context.max_stocks = 10
    # 设置调仓周期，每月第二个交易日运行
    run_monthly(reallocation, date_rule=1)


def reallocation(context, bar_dict):
    # 每个调仓日先清仓持有的股票
    for security in list(context.portfolio.stock_account.positions.keys()):
        order_target(security, 0)
    # 首先获得当前日期
    time = get_datetime()
    date = time.strftime('%Y%m%d')
    # 获得股票池列表
    sample = context.iwencai_securities
    # 创建字典用于存储因子值
    df = {'security': [], 1: [], 2: [], 3: [], 'score': []}

    # 因子选择
    for security in sample:
        q = query(
            profit.roic,  # 投资回报率
            valuation.pb,  # 市净率
            valuation.ps_ttm,  # 市销率
        ).filter(
            profit.symbol == security
        )

        # 缺失值填充为0
        fdmt = get_fundamentals(q, date=date).fillna(0)

        # 判断是否有数据
        if (not (fdmt['profit_roic'].empty or
                 fdmt['valuation_pb'].empty or
                 fdmt['valuation_ps_ttm'].empty)):
            # 计算并填充因子值
            df['security'].append(security)
            df[1].append(fdmt['profit_roic'][0])  # 因子1：投资回报率
            df[2].append(fdmt['valuation_pb'][0])  # 因子2：市净率
            df[3].append(fdmt['valuation_ps_ttm'][0])  # 因子3：市销率

    for i in range(1, 4):
        # 因子极值处理，中位数去极值法
        m = np.mean(df[i])
        s = np.std(df[i])
        for j in range(len(df[i])):
            if df[i][j] <= m - 3 * s:
                df[i][j] = m - 3 * s
            if df[i][j] >= m + 3 * s:
                df[i][j] = m + 3 * s
        m = np.mean(df[i])
        s = np.std(df[i])

        # 因子无量纲处理，标准化法
        for j in range(len(df[i])):
            df[i][j] = (df[i][j] - m) / s

    # 计算综合因子得分
    for i in range(len(df['security'])):
        # 等权重计算(注意因子方向)
        s = (df[1][i] - df[2][i] - df[3][i])
        df['score'].append(s)

    # 按综合因子得分由大到小排序
    df = pd.DataFrame(df).sort_values(by='score', ascending=False)

    # 等权重分配资金
    cash = context.portfolio.available_cash / context.max_stocks

    # 买入新调仓股票
    for security in df[:context.max_stocks]['security']:
        order_target_value(security, cash)

