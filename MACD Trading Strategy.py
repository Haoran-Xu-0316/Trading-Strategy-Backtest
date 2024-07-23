
import talib


def init(context):
    g.security = '600519.SH'  # 输入股票代码
    # 设置MACD模型参数
    g.Short = 12  # 短周期平滑均线参数
    g.Long = 26  # 长周期平滑均线参数
    g.M = 9  # DIFF的平滑均线参数
    set_benchmark('000300.SH')  # 设置基准指数，默认为沪深300


def handle_bar(context, bar_dict):
    macd = get_macd(g.security)
    if macd[-1] > 0 and macd[-2] < 0 and len(list(context.portfolio.stock_account.positions.keys())) == 0:
        order_value(g.security, context.portfolio.available_cash)
        log.info("买入 %s" % (g.security))
    if macd[-2] > 0 and macd[-1] < 0 and len(list(context.portfolio.stock_account.positions.keys())) > 0:
        order_target(g.security, 0)
        log.info("卖出 %s" % (g.security))


def get_macd(stock):
    price = history(stock, ['close'], 500, '1d', True, 'pre', is_panel=1)['close']
    DIFF, DEA, MACD = talib.MACD(price.values,
                                 fastperiod=g.Short, slowperiod=g.Long, signalperiod=g.M)
    return MACD