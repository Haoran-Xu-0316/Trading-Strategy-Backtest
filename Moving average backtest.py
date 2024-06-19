# 导入三方库
#%%
import pandas as pd
import tushare as ts
#%%
# 链接token
ts.set_token('0f5e59816a37d4650e2512523000f31a45ed30b755a4d0df4f4be127')
pro = ts.pro_api()
#%%
def get_close(ticker, start_date, end_date):
    df = pro.daily(ts_code = ticker,
                   start_date = start_date,
                   end_date = end_date)
    df = df.set_index('trade_date').sort_index()
    df_close = df[['close']]
    
    return df_close
#%%
def get_ma(df, n):
    df['ma'+str(n)] = df['close'].rolling(n).mean()
    return df
#%%
gzmt = get_close('600519.sh','2015-01-01','2021-12-31')
#%%
gzmt = get_ma(gzmt, 5)
gzmt = get_ma(gzmt, 10)
#%%
'''
股票价格连续上涨 ---> ma5>ma10
策略逻辑： ma5>ma10 ---> buy
          ma5<ma10 ---> sell
假设：
(1) all buy or all sell.
(2) trade at close.
(3) fund = 1000000.

策略信号：
(1) cash[i-1] != 0, ma5>ma10, buy;
(2) cash[i-1] == 0, ma5>ma10, hold stock;
(3) cash[i-1] != 0, ma5<ma10, hold cash;
(4) cash[i-1] == 0, ma5<ma10, sell.
'''
#%%
# 策略回测（利用历史数据，基于交易逻辑测试收益表现）
# 去除空值
gzmt = gzmt.dropna()
# 初始化
gzmt['cash'] = gzmt['outstanding'] = gzmt['stocks'] = 0
#%%
# 初始化现金
gzmt['cash'].iloc[0] = 1000000
#%%
for i in range(1, len(gzmt)):
    '''
    策略信号：
    (1) cash[i-1] != 0, ma5>=ma10, buy;
    (2) cash[i-1] == 0, ma5>=ma10, hold stock;
    (3) cash[i-1] != 0, ma5<ma10, hold cash;
    (4) cash[i-1] == 0, ma5<ma10, sell.
    '''
    if gzmt['cash'].iloc[i-1] != 0:
        if gzmt['ma5'].iloc[i] >= gzmt['ma10'].iloc[i]:
            # buy
            gzmt['outstanding'].iloc[i] = gzmt['cash'].iloc[i-1]
            gzmt['stocks'].iloc[i] = gzmt['outstanding'].iloc[i]/gzmt['close'].iloc[i]
            gzmt['cash'].iloc[i] = 0
        if gzmt['ma5'].iloc[i] < gzmt['ma10'].iloc[i]:
            # hold cash
            gzmt['cash'].iloc[i] = gzmt['cash'].iloc[i-1]
            gzmt['outstanding'].iloc[i] = 0
            gzmt['stocks'].iloc[i] = 0
    if gzmt['cash'].iloc[i-1] == 0:
        if gzmt['ma5'].iloc[i] >= gzmt['ma10'].iloc[i]:
            # hold stocks
            gzmt['stocks'].iloc[i] = gzmt['stocks'].iloc[i-1]
            gzmt['outstanding'].iloc[i] = gzmt['stocks'].iloc[i] * gzmt['close'].iloc[i]
            gzmt['cash'].iloc[i] = 0
        if gzmt['ma5'].iloc[i] < gzmt['ma10'].iloc[i]:
            # sell
            gzmt['cash'].iloc[i] = gzmt['stocks'].iloc[i-1] * gzmt['close'].iloc[i]
            gzmt['outstanding'].iloc[i] = 0
            gzmt['stocks'].iloc[i] = 0
#%%
gzmt['total_capital'] = gzmt['cash']+gzmt['outstanding']
# H1. 完善如下函数（思路见上）

#%%
# H2. 计算策略年化收益率、年化波动率，及夏普比率Sharpe Ratio
# 策略收益波动计算
ret = gzmt['total_capital'].iloc[-1]/gzmt['total_capital'].iloc[0]-1
# 年化收益率(annual return)

'''
1year 10%
2year 21%

'''
#%%
# T1. 思考在现有框架下，如何提高均线策略的夏普比







