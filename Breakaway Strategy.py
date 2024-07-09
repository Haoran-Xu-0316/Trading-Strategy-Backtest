'''

In a downtrend:

Day 1: A long bearish candlestick (long black/red candlestick).
Day 2: A gap down with a bearish candlestick, continuing the downtrend and beginning to fluctuate.
Day 5: A long bullish candlestick (long white/green candlestick), with the closing price between the first day’s closing price and the second day’s opening price, indicating a potential price increase.

'''
import talib as tl
import datetime


# 初始化函数 ###################################################################
def init(context):
    set_params(context)  # 设置策略常量
    set_variables(context)  # 设置中间变量
    set_backtest(context)  # 设置回测条件


# 1.设置策略参数
def set_params(context):
    context.holdMax = 2  # 最大持有股票数
    context.periods = 5  # 持有天数


# 2.设置中间变量
def set_variables(context):
    context.Count = 0  # 当前持仓数
    context.hold_days = {}  # 各股票持仓时间


# 3.设置回测条件
def set_backtest(context):
    set_benchmark('000001.SH')  # 设置基准
    set_slippage(PriceSlippage(0.002))  # 设置可变滑点


# 每日开盘执行###################################################################
def handle_bar(context, bar_dict):
    # 获得卖出股票池
    sell_stocks = stocks_to_sell(context)

    # 获得买入股票池
    buy_stocks = stocks_to_buy(context, bar_dict)

    # 交易操作
    trade_stocks(sell_stocks, buy_stocks, context)


# 4.获得卖出股票池
def stocks_to_sell(context):
    sell_stocks = []
    # 持仓到期股票
    for stock in context.hold_days:
        if context.hold_days[stock] > context.periods:
            sell_stocks.append(stock)
    # 更新当前持仓数
    context.Count = len(list(context.portfolio.stock_account.positions.keys())) - len(sell_stocks)
    return sell_stocks


# 5.获得买入股票池
def stocks_to_buy(context, bar_dict, ):
    CDLBREAKAWAY_stocks = []
    # 持仓数未达上限
    if context.Count < context.holdMax:
        # 获取初始股票池
        stocks = get_raw_stocks(bar_dict)
        # 挑选CDLBREAKAWAY形态股票
        CDLBREAKAWAY_stocks = get_CDLBREAKAWAY_stocks(stocks, bar_dict)
    return CDLBREAKAWAY_stocks


# 6.获取初始股票池
def get_raw_stocks(bar_dict):
    tdate = get_datetime().strftime("%Y%m%d")  # 当天日期
    today_datetime = datetime.datetime.strptime(tdate, "%Y%m%d")
    yesterday_time = get_datetime() - datetime.timedelta(days=1)
    yesterday_date = yesterday_time.strftime("%Y%m%d")  # 昨日日期

    # 获取所有股票
    stocks = get_all_securities("stock", tdate)
    # 排除新股
    stocks = stocks[(today_datetime - stocks.start_date) > datetime.timedelta(60)].index.values
    # 排除停牌股票
    stocks = [stock for stock in stocks if bar_dict[stock].is_paused == 0]
    # 排除开盘涨跌停
    stocks = [stock for stock in stocks if bar_dict[stock].open != bar_dict[stock].high_limit
              and bar_dict[stock].open != bar_dict[stock].low_limit]
    # 排除st
    stocks = [stock for stock in stocks if bar_dict[stock].is_st == 0]

    return stocks


# 7.挑选CDLBREAKAWAY形态股票
def get_CDLBREAKAWAY_stocks(stocks, bar_dict):
    CDLBREAKAWAY_stocks = []
    for stock in stocks:
        value = history(stock, ['open', 'high', 'low', 'close'], 20, '1d', True)
        open_P = value.open.values
        high = value.high.values
        low = value.low.values
        close = value.close.values
        try:
            integer = tl.CDLBREAKAWAY(open_P, high, low, close)
            is_CDLBREAKAWAY = integer[-1]
        # 跳过无数据的股票
        except:
            log.info(stock + "无数据")
            continue
        if is_CDLBREAKAWAY != 0:
            CDLBREAKAWAY_stocks.append(stock)
    return CDLBREAKAWAY_stocks


# 8.交易操作
def trade_stocks(sell_stocks, buy_stocks, context):
    # 卖出操作
    for stock in sell_stocks:
        order_target_value(stock, 0)
    # 每股资金
    Count = max([1, len(buy_stocks)])
    one_cash = context.portfolio.stock_account.available_cash / Count
    # 买入操作
    for stock in buy_stocks:
        order_target_value(stock, one_cash)
        context.hold_days[stock] = 0


# 盘后计算###################################################################
def after_trading_end(context, bar_dict):
    # 持仓天数增加
    for stock in context.hold_days:
        context.hold_days[stock] += 1
