import jqdata
# 导入聚宽平台函数
import pandas as pd  

def initialize (context):
    set_benchmark('000300.XSHG')
    #设置市场参考标准
    g.security='000001.XSHE'
    #设置要回测的股票代码
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    #设置交易成本
    run_daily(user_function,'every_bar')
    # print("初始化函数被运行了")

def user_function(context):
    security=g.security
    # 设置新变量传递股票代码
    n1=5 
    n2=21 
    # 设置长短均线长度
    close_data=attribute_history(security, n2, '1d', ('close'))
    # 读取历史数据
    # write_file('output_data.csv',close_data.to_csv(),append=False)
    # 将历史数据输出
    
    ma_n1=close_data['close'][-n1:].mean()
    ma_n2=close_data['close'][-n2:].mean()
    ma_n1_pd=close_data['close'][-n1-1:-1].mean()
    ma_n2_pd=close_data['close'][-n2-1:-1].mean()
    #计算当日及昨日长短均线值
    position=context.portfolio.positions 
    # 导入开仓量信息
    
    if security not in context.portfolio.positions:
        # 当没有仓位时
        if ma_n1 > ma_n2 and ma_n1_pd <=ma_n2_pd:
            # 判断均线向上交叉
            order_target(security,10000)
            #按目标股数买入股票
            log.info("开仓操作")
            # 记录日志
    else: 
        # 当有仓位时
         if ma_n1 < ma_n2 and ma_n1_pd >=ma_n2_pd:
            # 判断均线向下交叉 
            order_target(security,0) 
            #将目标股票清仓
            log.info("关仓操作")
            # 记录日志