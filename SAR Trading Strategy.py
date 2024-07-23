# SAR策略
# 策略逻辑: 当股票价格从SAR曲线下方开始向上突破SAR曲线时，为买入信号；
#          当股票价格从SAR曲线上方开始向下突破SAR曲线时，为卖出信号。


# 初始化账户
def init(context):
    # 设置要交易的证券(600519.SH 贵州茅台)
    context.security = '600519.SH'
    # 在handle_bar_dict函数中判断：如果是第一天，初始化前日PSAR参数
    context.first_day = True


# 设置买卖条件，每个交易频率（日/分钟/tick）调用一次
def handle_bar(context, bar_dict):
    # 获取证券过去3日的价格数据
    price = history(context.security, ['open', 'high', 'low', 'close'], 3, '1d')

    # 如果是第一天
    if context.first_day:
        # 初始化前期PSAR参数
        context.pre_acc = 0.02

        # 如果前日的收盘价高于前日的开盘价
        if price.at[price.index[-2], 'close'] > price.at[price.index[-2], 'open']:
            # 前日的行情为上涨行情
            context.pre_trend = 'bull'
            # 前日的极值应为前日最高价
            context.pre_EP = price.at[price.index[-2], 'high']
            # 前日的PSAR值应为前日最低价
            context.pre_PSAR = price.at[price.index[-2], 'low']
        else:
            # 前日的行情为下跌行情
            context.pre_trend = 'bear'
            # 前日的极值应为前日最低价
            context.pre_EP = price.at[price.index[-2], 'low']
            # 前日的PSAR值应为前日最高价
            context.pre_PSAR = price.at[price.index[-2], 'high']

        log.info("PSAR初始化完成")
        context.first_day = False

    # 先计算昨日PSAR的公式值
    # 昨日PSAR值 = 前日PSAR - 前日加速因子 * (前日PSAR - 前日极值)
    PSAR = context.pre_PSAR - context.pre_acc * (context.pre_PSAR - context.pre_EP)

    # 如果前日是下跌行情且昨日最高价高于计算出的PASR值时
    if context.pre_trend == 'bear' and price.at[price.index[-1], 'high'] > PSAR:
        # PSAR值应为前日极值
        PSAR = context.pre_EP
    # 如果前日是上涨行情且昨日最低价高于计算出的PASR值时
    if context.pre_trend == 'bull' and price.at[price.index[-1], 'low'] < PSAR:
        # PSAR值应为前日极值
        PSAR = context.pre_EP

    # 判断昨日的行情趋势
    # 如果昨日PSAR值大于昨日收盘价
    if PSAR > price.at[price.index[-1], 'close']:
        # 跌势
        trend = 'bear'
    # 如果昨日PSAR值小于昨日收盘价
    else:
        # 涨势
        trend = 'bull'

    # 计算昨日的极值
    # 如果昨日为下跌趋势，昨日极值为前日极值和昨日最低价中的较小值
    if trend == 'bear': EP = min(context.pre_EP, price.at[price.index[-1], 'low'])
    # 如果昨日为上涨趋势，昨日极值为前日极值和昨日最高价中的较大值
    if trend == 'bull': EP = max(context.pre_EP, price.at[price.index[-1], 'high'])

    # 计算昨日加速因子
    acc = context.pre_acc
    # 如果趋势延续且价格极值改变
    if trend == context.pre_trend and EP != context.pre_EP:
        # 加速因子增加0.02
        acc += 0.02
        # 加速因子不能大于0.2
        acc = min(acc, 0.2)
    # 如果趋势改变
    if trend != context.pre_trend:
        # 加速因子初始化为0.02
        acc = 0.02

    # 更新前期PSAR参数，为下一个交易日PSAR的计算做准备
    context.pre_EP = EP
    context.pre_PSAR = PSAR
    context.pre_acc = acc
    context.pre_trend = trend
    # log.info('PSAR: %f' % (PSAR))
    # log.info('trend: %s' % (trend))

    # 如果是上涨行情
    if trend == 'bull':
        # 使用所有现金买入证券
        order_value(context.security, context.portfolio.available_cash)

        # 如果是下跌行情且持有股票
    if trend == 'bear' and context.portfolio.portfolio_value > 0:
        # 卖出所有证券
        order_target(context.security, 0)
        # 记录这次卖出
        log.info("卖出 %s" % (context.security))