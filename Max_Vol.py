import matplotlib.pyplot as plt
import pandas as pd
import glob

plt.rcParams['font.family'] = 'Microsoft YaHei'

# 读取文件
files = [file for file in glob.glob("*.csv") if not file.endswith('result.csv')]
dfs = [pd.read_csv(file,encoding='gbk',header=1,usecols=['股票名称','交易日期','成交额']) for file in files]

# 修改日期索引
for df in dfs:
    df['交易日期'] = pd.to_datetime(df['交易日期'])
    df.rename(columns={'交易日期':'日期'}, inplace=True)
    df.set_index('日期',inplace=True)
    print(df)

# 找到所有数据框时间索引的交集
common_index = dfs[0].index
for df in dfs:
    common_index = common_index.intersection(df.index)
    df.rename(columns={'成交额': df.iloc[0,0]},inplace=True)
    df.drop(df.columns[0], axis=1, inplace=True)

# 用索引交集过滤原数据框
filtered_dfs = [df.loc[common_index] for df in dfs]

# 合并成交额列
vol_dfs = pd.concat(filtered_dfs, axis=1)
print(vol_dfs)

vol_dfs.plot()
plt.legend(frameon=False)
plt.margins(x=0)
plt.tight_layout()

# 找出最大的成交额和对应的股票代码
vol_dfs['股票名称'] = vol_dfs.idxmax(axis=1)
vol_dfs['成交额'] = vol_dfs.max(axis=1)

result = vol_dfs[['股票名称','成交额']]
result.to_csv('result.csv')

print(result)
plt.show()