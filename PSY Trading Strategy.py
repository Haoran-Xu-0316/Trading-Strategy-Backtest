

# --- 1.导入所需库包----------------------------------------------------------------
import numpy as np


# --- 2.初始化账户------------------------------------------------------------------
def init(context):
    context.n = 4  # 设置交易股票数量
    # 使用get_iwencai函数进行智能选股
    get_iwencai('PB<1，dde大单净量由大到小排名')


# --- 3.自定义PSY函数----------------------------------------------------------
def PSY_cal(prices, timeperiod=12):
    PSY = np.zeros(len(prices))
    for i in range(len(PSY)):
        PSY[i] = np.nan
    if len(prices) <= timeperiod:
        return PSY
    for i in range(timeperiod, len(prices)):
        PSY[i] = 0
        for j in range(timeperiod):
            if prices[i - j] > prices[i - j - 1]:
                PSY[i] += 1
        PSY[i] *= 100 / timeperiod
    return PSY


# --- 4. 盘中设置买卖条件，每个交易频率（日/分钟）调用一次-------------
def handle_bar(context, bar_dict):
    # 卖出股票
    for stock in list(context.portfolio.stock_account.positions.keys()):
        # 获取股票收盘价数据
        values = history(stock, ['close'], 14, '1d', False, None)
        if values.empty or len(values) < 14:
            continue
        # 计算PSY值
        PSY = PSY_cal(values['close'].values, timeperiod=12)
        # 若PSY向上突破85，则卖出股票
        if PSY[-2] < 85 and PSY[-1] > 85:
            order_target(stock, 0)

    # 买入股票
    for stock in context.iwencai_securities:
        # 若股票数量到达限制，则跳出
        if len(list(context.portfolio.stock_account.positions.keys())) >= context.n:
            break
        if stock not in list(context.portfolio.stock_account.positions.keys()):
            # 获取股票收盘价数据
            values = history(stock, ['close'], 14, '1d', False, None)
            if values.empty or len(values) < 14:
                continue
            # 计算PSY值
            PSY = PSY_cal(values['close'].values, timeperiod=12)
            # 若PSY向下突破15，则买入1/n仓位的股票
            if PSY[-2] > 15 and PSY[-1] < 15:
                order_target_percent(stock, 1 / context.n)
