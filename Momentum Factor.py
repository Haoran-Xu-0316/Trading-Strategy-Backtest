import matplotlib.pyplot as plt
import pandas as pd
import zipfile
import glob

plt.rcParams['font.family'] = 'Microsoft YaHei'
con = pd.read_excel('000300cons.xls',usecols=['成份券代码Constituent Code','交易所Exchange'],dtype=str)
cons = list(con['成份券代码Constituent Code'])
# print(cons)

# 根据交易所添加前缀
def add_prefix(row):
    if row['交易所Exchange'] == '深圳证券交易所':
        return 'sz' + row['成份券代码Constituent Code'] + '.csv'
    elif row['交易所Exchange'] == '上海证券交易所':
        return 'sh' + row['成份券代码Constituent Code'] + '.csv'
    else:
        return row['成份券代码Constituent Code']

files = list(con.apply(add_prefix, axis=1))


# 读取文件
with zipfile.ZipFile('stock-trading-data-pro-2024-04-17N.zip', 'r') as z:

    dfs = []
    for file in files:
        with z.open(file) as f:
            df = pd.read_csv(f, encoding='gbk', header=1,
                             usecols=['股票名称', '最低价', '最高价', '收盘价','交易日期'])
            dfs.append(df)

# print(len(dfs))
#
# 修改日期索引
for df in dfs:
    df['交易日期'] = pd.to_datetime(df['交易日期'])
    df.rename(columns={'交易日期':'日期'}, inplace=True)
    df.set_index('日期',inplace=True)
    # print(df)


date_range = pd.date_range(start='2019-12-31', end='2024-05-31', freq='M')
end_of_month_dates = date_range + pd.offsets.MonthEnd(0)
dates = [date for date in end_of_month_dates]
str_dates = [time.strftime('%Y-%m-%d') for time in dates]



# 计算长端动量因子
def momentum_factor(adj_date):
    momentums = []
    for df in dfs:
        df['涨跌幅'] = df['收盘价'].pct_change()
        df160 = df.loc[df.index <= adj_date].tail(160)

        df160['每日振幅'] = (df160['最高价'] / df160['最低价']) - 1

        df160 = df160.sort_values(by='每日振幅')
        threshold = int(len(df) * 0.7)
        df160_top70 = df160.head(threshold)

        momentum = df160_top70['涨跌幅'].sum()

        momentums.append(momentum)

    return momentums


# 投资组合构建
def portfolio_construction():
    portfolio = []
    for adjust in dates:
        mmts = pd.DataFrame({'股票代码': cons, '长端动量因子': momentum_factor(adjust)})
        mmts_sorted = mmts.sort_values(by='长端动量因子', ascending=False)
        mmts_top_30 = mmts_sorted.head(30)
        portfolio.append(list(mmts_top_30['股票代码']))

    return portfolio


port=portfolio_construction()



# for i in range(len(dates)):
for j in port[1]:
    index = cons.index(j)
    clp = dfs[index][["收盘价",'最高价']]
    clp.index = clp.index.strftime('%Y-%m-%d')
    b=clp[str_dates[0]:str_dates[0]][['收盘价']]
    print(b)


