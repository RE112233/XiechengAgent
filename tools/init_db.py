import os
import shutil
import sqlite3
import pandas as pd


local_file = "../travel_new.sqlite" # 项目测试过程中使用的
backup_file = "../travel2.sqlite" # 备份数据库

def update_dates():
    """
    更新数据库中的日期，使其与当前时间对齐。

    参数:
        file (str): 要更新的数据库文件路径。

    返回:
        str: 更新后的数据库文件路径。
    """
    # 使用备份文件 覆盖 现有文件，作为重置步骤
    shutil.copy(backup_file, local_file)  # 如果目标路径已经存在一个同名文件，shutil.copy 会覆盖该文件。

    conn = sqlite3.connect(local_file)
    # cursor = conn.cursor()

    # 获取所有表名 sqlite_master 是 SQLite 的系统表，存储数据库的结构信息
    # 使用pandas执行SQL查询返回一个DataFrame，包含一列name，每行是一个表名
    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn).name.tolist() # .name 返回一个 Series .tolist() 将 Series 转换为 Python 列表
    tdf = {}

    # 读取每个表的数据
    for t in tables:
        tdf[t] = pd.read_sql(f"SELECT * from {t}", conn)

    # 找出示例时间（这里用flights表中的actual_departure的最大值）
    #  flights 表中 actual_departure 列  将 将字符串 "\\N" 替换为 pd.NaT（Not a Time，pandas 表示缺失时间的特殊值）
    #  pd.to_datetime将字符串格式的时间转换为 pandas 的 datetime 对象   找出所有时间中的最大值（最晚的日期）
    example_time = pd.to_datetime(tdf["flights"]["actual_departure"].replace("\\N", pd.NaT)).max()
    #  pd.to_datetime("now")  获取当前时间， example_time.tz 获取 example_time 的时区信息  例如：UTC、Asia/Shanghai 等
    #  .tz_localize(example_time.tz) 给当前时间添加时区信息，使其与 example_time 的时区相同
    current_time = pd.to_datetime("now").tz_localize(example_time.tz)
    # pandas中，只有两个时间都带有时区信息且时区相同时，才能直接相减。
    time_diff = current_time - example_time

    # 更新bookings表中的book_date
    tdf["bookings"]["book_date"] = (
            pd.to_datetime(tdf["bookings"]["book_date"].replace("\\N", pd.NaT), utc=True) + time_diff
    )

    # 需要更新的日期列
    datetime_columns = ["scheduled_departure", "scheduled_arrival", "actual_departure", "actual_arrival"]
    for column in datetime_columns:
        tdf["flights"][column] = (
                pd.to_datetime(tdf["flights"][column].replace("\\N", pd.NaT)) + time_diff
        )

    # 将更新后的数据写回数据库
    for table_name, df in tdf.items():
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        del df  # 清理内存
    del tdf  # 清理内存

    conn.commit()
    conn.close()

    return local_file


if __name__ == '__main__':

    # 执行日期更新操作
    db = update_dates()