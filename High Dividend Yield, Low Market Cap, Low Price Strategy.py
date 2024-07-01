import datetime
import numpy as np


def init(context):
    '''
    Initialization function
    *Special Note*:
    - Executes only when the strategy runs for the first time
    - In the research environment, when executing the strategy using the research_trade interface, a folder with the same name as the strategy (customizable by the user passing to the research_trade interface) will be generated under './persist' to persist global variables.
    - If a path with the same name exists under './persist' when executing this strategy, init will not be executed.
    '''
    select_sentence = '股价大于1.5;股价小于9;市值小于200亿;剔除科创;剔除北交所;过滤停牌;过滤涨停;过滤跌停'  # Selection criteria
    sort_sentence = '市值从小到大排序;股息率从高到底排序'  # Sorting criteria
    get_iwencai('{},{}'.format(select_sentence, sort_sentence))  # Natural language selection of stocks
    g.max_nums = 10  # Maximum number of stocks to hold
    g.max_tdays = 15  # Maximum holding period
    g.stop_gain = 0.2  # Take profit
    g.stop_gain_drawdown = 100  # Drawdown take profit, 1 is basically no drawdown take profit
    g.stop_loss = 0.05  # Stop loss
    g.black_stocks = []  # Blacklist
    g.holdings = {}  # Holding information
    g.adjust_time = datetime.time(15, 30, 0)  # Allow buying operations before this time

    g.ignore_initstock = False  # Whether to ignore initial holdings
    g.sale_initstock = True  # Whether to sell initial holdings
    if not g.ignore_initstock:  # Do not ignore initial holdings
        for symbol in context.portfolio.positions:
            g.holdings[symbol] = HoldingInfo(symbol)  # Write initial holdings into holdings
            if g.sale_initstock:
                g.holdings[symbol].holding_days = g.max_tdays + 1
    log.info('Initialization function completed')


def before_trading(context):
    '''
    Executed before market open, scheduled at 9:00 AM
    '''
    g.sale_order_ids = {}  # Clearing order information
    g.buy_order_ids = {}  # Opening order information
    g.buy_target = {}  # Opening target information
    g.on_exec = {}  # Current execution of reducing positions + holding quantity
    g.sale_finished = []  # List of completed sales
    g.buy_finished = []  # List of completed purchases
    g.holding_list = list(g.holdings.keys())  # List of holdings
    g.st_stocks = get_st_stocks()  # ST stocks list
    log.info('Before market open completed')


def open_auction(context, bar_dict):
    '''
    Executed after opening call auction, scheduled at 9:26 AM
    '''
    g.stock_pool = [s for s in context.iwencai_securities if
                    s not in g.st_stocks]  # Update stock pool, exclude ST stocks
    g.stock_pool = g.stock_pool[:(g.max_nums)]  # Take the top g.max_nums stocks as backup
    # Take 2 more to prevent selling without backup stocks.
    log.info('After opening call auction completed')


def handle_bar(context, bar_dict):
    # log.info('{}Execution started'.format(get_datetime().strftime('%Y-%m-%d %H:%M:%S')))
    try:  # Attempt
        cancel_order_all()  # Cancel all orders
    except Exception as e:  # If error occurs
        log.warn(e)  # Log error information

    # Take profit, stop loss + holding days reach maximum holding days + update holding information
    for symbol in list(g.holdings.keys()):  # Stock holdings
        holding_info = g.holdings.get(symbol)  # Get holding information for current symbol
        profit_rate = context.portfolio.stock_account.positions[symbol].profit_rate  # Get current profit rate
        if profit_rate >= holding_info.max_return:  # If current profit is greater than historical maximum holding profit
            holding_info.max_return = float(profit_rate)  # Update historical maximum holding profit

        # If the current symbol triggers take profit or stop loss
        # And not a stock bought on the same day
        # And the stock is not in today's selected stock pool, then
        if not holding_info.stop_gain_or_loss and holding_info.holding_days > 1 and symbol not in g.stock_pool:
            if holding_info.holding_days >= g.max_tdays:  # Check if holding days reach maximum holding days
                holding_info.stop_gain_or_loss = True  # If yes, update take profit and stop loss status to sell
            if profit_rate >= g.stop_gain:  # or profit_rate <= -g.stop_loss:# Check if take profit is triggered
                holding_info.stop_gain_or_loss = True  # If yes, update take profit status to sell
            if symbol in g.black_stocks:  # Check if the stock is in the blacklist
                holding_info.stop_gain_or_loss = True  # If yes, update take profit and stop loss status to sell
            if symbol in g.st_stocks:  # Check if it's an ST or delisted stock
                holding_info.stop_gain_or_loss = True  # If yes, update take profit and stop loss status to sell

        # Stop loss logic is separated out separately without checking whether it is in the stock_pool.
        # If the current symbol triggers stop loss
        # And not a stock bought on the same day, then
        if not holding_info.stop_gain_or_loss and holding_info.holding_days > 1:
            if profit_rate <= -g.stop_loss:  # Check if stop loss is triggered
                holding_info.stop_gain_or_loss = True  # If yes, update take profit status to sell
                log.info('{}Stop loss triggered'.format(symbol))
            if profit_rate - holding_info.max_return <= -g.stop_gain_drawdown:  # Check if high point drawdown stop profit is triggered
                holding_info.stop_gain_or_loss = True  # If yes, update take profit and stop loss status to sell

        g.holdings[symbol] = holding_info  # Update holding information

        # Check if this stock needs to be sold and there is currently no pending sale order
        if g.holdings[symbol].stop_gain_or_loss and g.holdings[symbol].sale_order_id is None:
            order_id = order_target(symbol, 0)  # Sell this stock

    # Buy within time limit
    if get_datetime().time() <= g.adjust_time:  # Check if buying can be executed now

        target_value = context.portfolio.stock_account.total_value / g.max_nums  # Maximum purchase fund per stock
        available_buy_num = g.max_nums + len(g.sale_finished) - len(g.buy_finished) - len(
            g.holding_list)  # Number of stocks that can still be bought now
        if available_buy_num < 0:
            available_buy_num = 0
        n = 0  # Number of stocks purchased in this round
        for symbol in g.stock_pool:  # Loop through the stock pool
            if n == available_buy_num:  # If the number of stocks purchased this round is equal to the number of stocks that can still be bought now
                break  # Stop looping, terminate purchase
            if symbol in g.buy_finished or symbol in g.holding_list or symbol in list(
                    g.buy_order_ids.values()):  # If the stock has finished buying today, or the stock has been bought before today, or is currently being bought
                continue  # Skip this stock

            target_volume = aContractDetail[symbol].adjust_vol(target_value / bar_dict[symbol].close,
                                                               max_limit=False)  # Calculate target purchase quantity
            g.buy_target[symbol] = target_volume  # Update purchase target

            v = target_volume - g.on_exec.get(symbol,
                                              0)  # Calculate the difference between holding + current pending orders and the purchase target, as the amount still to be chased
            if v > 0:  # If the amount to be chased is greater than 0
                available_cash = context.portfolio.stock_account.available_cash  # Current available cash
                if available_cash > v * bar_dict[
                    symbol].close:  # If available cash is greater than the cash required for chasing
                    order_id = order(symbol, v)  # Chase order
                else:  # If available cash is less than or equal to the cash required for chasing
                    v = 100 * int(available_cash / bar_dict[
                        symbol].close / 100)  # Calculate the actual number of orders that can be chased
                    order_id = order(symbol, v)  # Chase order
                    break  # At this point, it means that there is no available cash, end the loop
            n += 1  # Number of stocks purchased in this round +1


# Order status update event push
def on_order(context, odr):
    if odr.order_type == SIDE.SELL:  # If the pushed order is a sell order
        if odr.order_id not in g.sale_order_ids.keys():
            g.sale_order_ids[odr.order_id] = odr.symbol
            g.holdings[odr.symbol].sale_order_id = odr.order_id
        # Check if the order status is rejected or canceled
        if odr.status == ORDER_STATUS.REJECTED or odr.status == ORDER_STATUS.CANCELLED:
            g.sale_order_ids.pop(odr.order_id)  # Remove clearing order information
            g.holdings[odr.symbol].sale_order_id = None  # Delete sale order ID
        # Check if the order status is complete
        if odr.status == ORDER_STATUS.FILLED:
            g.holdings.pop(odr.symbol)  # Remove holding information
            g.sale_finished.append(odr.symbol)  # Write to the completed sale list
            g.holding_list.remove(odr.symbol)  # Update the holding list
            g.sale_order_ids.pop(odr.order_id)  # Remove clearing order information
            g.holdings[odr.symbol].sale_order_id = None  # Delete sale order ID

    if odr.order_type == SIDE.BUY:  # If the pushed order is a purchase order
        if odr.order_id not in g.buy_order_ids.keys():
            g.buy_order_ids[odr.order_id] = odr.symbol  # Write in the opening order information
            g.buy_target[odr.symbol] = odr.volume  # Write in the purchase target information
        # Check if the order status is rejected or canceled
        if odr.status == ORDER_STATUS.REJECTED or odr.status == ORDER_STATUS.CANCELLED:
            g.buy_order_ids.pop(odr.order_id)  # Remove opening order information
            g.buy_target.pop(odr.symbol)  # Remove opening target information
        # Check if the order status is complete
        if odr.status == ORDER_STATUS.FILLED:
            g.buy_finished.append(odr.symbol)  # Write in the completed purchase list
            g.holding_list.append(odr.symbol)  # Write in the holding list
            g.buy_order_ids.pop(odr.order_id)  # Remove opening order information
            g.buy_target.pop(odr.symbol)  # Remove opening target information


def after_trading(context):
    '''
    Executed after market close, scheduled at 15:00 PM
    '''
    # log.info('Post-market execution started'.format(get_datetime().strftime('%Y-%m-%d %H:%M:%S')))
    try:  # Attempt
        cancel_order_all()  # Cancel all orders
    except Exception as e:  # If error occurs
        log.warn(e)  # Log error information


class aContractDetail:
    def adjust_vol(aBabbar, bMinimum, max_limit):
        print('code block ran')
        pass


class HoldingInfo:
    def __init__(aParam, symbol):
        pass
