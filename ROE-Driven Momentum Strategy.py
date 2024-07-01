import pandas as pd
import numpy as np
import datetime

def init(context):
    # Set benchmark: CSI 300 Index
    set_benchmark('000300.SH')
    # Log info
    log.info('Strategy started, init() runs once')
    # Set stock trading commission: 0.02% per share
    set_commission(PerShare(type='stock', cost=0.0002))
    # Set slippage: 0.5%
    set_slippage(PriceSlippage(0.005))
    # Set maximum daily and minute trading volume limits
    set_volume_limit(0.25, 0.5)
    # Set the stock to operate on: STHS
    context.security = '300033.SZ'
    # Backtest period, initial capital, frequency settings are configured separately

    # Small and medium-sized board stock pool
    # g.security_universe_index = '399101.SZ'
    # CSI 300
    # g.security_universe_index = '000300.SH'
    # Stock trading commission fee: 0.3% buying, 0.31% selling (including stamp duty), minimum 5 RMB per trade

    # Intraday operations
    # run_daily(market_open_buy, time_rule='after_open', hours=0, minutes=0, reference_security='000300.SH')
    # run_daily(market_open_sell, time_rule='before_close', hours=0, minutes=5, reference_security='000300.SH')
    # After-market operations
    g.stock_list = []
    g.buy_stock_num = 5


# Called once before market opens at 9:00 AM for setting custom parameters, global variables, pre-market stock selection, etc.
def before_trading(context):
    # Get date
    date = get_datetime().strftime('%Y-%m-%d %H:%M:%S')
    # Log date
    log.info('{} Pre-market operations'.format(date))
    g.stock_list = get_stocks(context)


def handle_bar(context, bar_dict):
    time = get_datetime().strftime('%H:%M')
    market_open_buy(context)
    market_open_sell(context)


def get_stocks(context):
    # stocks = get_index_stocks(g.security_universe_index)

    stocklist = list(get_all_securities('stock', date=get_datetime().strftime('%Y%m%d')).index)
    stocklist = stock_filter(context, stocklist)
    stocklist = filter_stock_by_days(context, stocklist, 250)
    stocklist = buy_point_filter(context, stocklist)

    # Order by ROE descending
    q = query(valuation.symbol
              ).filter(valuation.symbol.in_(stocklist),
                       valuation.circulating_cap > 50,  # Circulating market value > 50
                       valuation.roe_ttm > 0  # ROE > 0
                       ).order_by(valuation.roe_ttm.desc()
                                  ).limit(10)
    stocklist = list(get_fundamentals(q, date=get_datetime().strftime('%Y%m%d')).valuation_symbol)
    print('Selected {} stocks: {}'.format(len(stocklist), stocklist))

    return stocklist


# Buy function
def market_open_buy(context):
    if len(context.portfolio.positions) < g.buy_stock_num:
        new_buy_stock_num = g.buy_stock_num - len(context.portfolio.positions)
        buy_cash = context.portfolio.available_cash / new_buy_stock_num
        for s in g.stock_list[:new_buy_stock_num]:
            current_price = get_price(s, start_date=get_datetime().strftime('%Y%m%d') + ' 14:55',
                                      end_date=get_datetime().strftime('%Y%m%d') + ' 14:55', fre_step='1m',
                                      fields=['close'], fq='pre', is_panel=1).close.item()
            if s not in context.portfolio.positions and context.portfolio.available_cash >= buy_cash >= 100 * current_price:
                order_target_value(s, buy_cash)
                print('Bought stock: {}'.format(s))


# Sell function
def market_open_sell(context):
    sells = list(context.portfolio.positions)
    for s in sells:
        loss = context.portfolio.positions[s].last_price / context.portfolio.positions[s].cost_basis
        s_sell, sell_msg = check_sell_point(context, s)
        if s_sell or loss < 0.95:
            if context.portfolio.positions[s].available_amount > 0:
                order_target_value(s, 0)
                print('Sold stock: {}, sell_msg={}'.format(s, sell_msg))


def buy_point_filter(context, stocks):
    final_stocks = []
    for stock in stocks:
        s_buy = check_buy_point(context, stock)
        if s_buy:
            final_stocks.append(stock)

    return final_stocks


def check_buy_point(context, stock):
    import numpy as np
    s_buy = False
    close_data = history(stock, bar_count=120, fre_step='1d', fields=['close', 'high'], is_panel=1)

    closes = close_data['close'].values

    ma55_list = list(np.zeros(120))
    for i in range(54, 120):
        ma55_list[i] = closes[i - 54:i + 1].mean()

    over_55_in_40_days = np.array(closes[-40:]) > np.array(ma55_list[-40:])

    num_over_55_40_days = sum(over_55_in_40_days)
    ever_upcross_ma55 = sum(over_55_in_40_days[:20])
    nowadays_upcross_ma55 = sum(over_55_in_40_days[-3:])
    yesterday_over_ma55 = over_55_in_40_days[-1]

    current_price = get_price(stock, start_date=get_datetime().strftime('%Y%m%d'),
                              end_date=get_datetime().strftime('%Y%m%d'), fre_step='1d', fields=['close'], fq='pre',
                              is_panel=1).close.item()

    current_ma55 = (np.sum(closes[-54:]) + current_price) / 55

    now_over_ma55 = current_price > current_ma55

    ten_days_lowest = min(closes[-10:]) == min(closes[-60:])

    if 1 <= ever_upcross_ma55 <= 3 and nowadays_upcross_ma55 >= 1 and now_over_ma55 and ten_days_lowest:
        s_buy = True

    return s_buy


def check_sell_point(context, stock):
    s_sell = False

    current_price = get_price(stock, start_date=get_datetime().strftime('%Y%m%d') + ' 14:55',
                              end_date=get_datetime().strftime('%Y%m%d') + ' 14:55', fre_step='1m', fields=['close'],
                              fq='pre', is_panel=1).close.item()

    bars = get_price(stock, bar_count=60, end_date=get_datetime().strftime('%Y%m%d'), fre_step='1d',
                     fields=['high', 'close'], is_panel=1)
    closes = bars['close']
    highs = bars['high']

    closes[-1] = current_price

    ma3 = closes[-3:].mean()
    ma5 = closes[-5:].mean()
    ma55 = closes[-55:].mean()

    loss = current_price / context.portfolio.positions[stock].cost_basis

    high_allday = highs[-1]

    signal1 = 0
    signal2 = current_price / closes[-2] < 0.95
    signal3 = current_price / high_allday < 0.95
    signal4 = loss < 0.95
    signal5 = current_price < ma55 * 0.98

    if signal1 or signal2 or signal3 or signal4 or signal5:
        s_sell = True
    msg = []
    if signal1:
        msg.append('Below MA5')
    if signal2:
        msg.append('Down 5%')
    if signal3:
        msg.append('High retracement 5%')
    if signal4:
        msg.append('Total loss 5%')
    if signal5:
        msg.append('Below MA55')

    return s_sell, msg


def filter_stock_by_days(context, stock_list, days):
    import datetime
    tmpList = []
    for stock in stock_list:
        days_public = (get_datetime() - get_security_info(stock).start_date).days
        if days_public > days:
            tmpList.append(stock)
    return tmpList


def stock_filter(context, stock_list):
    date = get_datetime().strftime("%Y%m%d")
    curr_data = get_price(stock_list, end_date=date, fre_step='1d',
                          fields=['open', 'high_limit', 'low_limit', 'is_paused', 'is_st'], skip_paused=False, fq='pre',
                          bar_count=1, is_panel=1)
    return [stock for stock in stock_list if not (
        # (curr_data.open[stock].item() == curr_data.high_limit[stock].item()) or   # Limit up
        # (curr_data.open[stock].item() == curr_data.low_limit[stock].item()) or    # Limit down
            curr_data.is_paused[stock].item() or  # Suspended
            curr_data.is_st[stock].item() or  # ST
            # (stock.startswith('300')) or    # Startup
            (stock.startswith('688'))  # Tech innovation
    )]
