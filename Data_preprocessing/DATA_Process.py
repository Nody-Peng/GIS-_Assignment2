import os
import pandas as pd
import numpy as np
import calendar
from datetime import datetime
import re

# 設定輸入和輸出資料夾路徑
input_dir = "觀測_日資料_宜蘭縣_降雨量_ALL"
output_dir = "output"
monthly_dir = os.path.join(output_dir, "monthly")

# 創建輸出資料夾
os.makedirs(output_dir, exist_ok=True)
os.makedirs(monthly_dir, exist_ok=True)

# 步驟 1: 將日資料轉換為月資料
def convert_daily_to_monthly(input_dir, output_dir):
    # 獲取所有年份的CSV檔案
    csv_files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]
    
    for csv_file in csv_files:
        print(f"處理檔案: {csv_file}")
        
        # 讀取CSV檔案
        file_path = os.path.join(input_dir, csv_file)
        df = pd.read_csv(file_path, index_col=False)
        
        # 獲取年份
        year_match = re.search(r'_(\d{4})\.csv$', csv_file)
        if not year_match:
            print(f"無法從檔名獲取年份: {csv_file}")
            continue
        
        year = year_match.group(1)
        
        # 創建新的DataFrame來存儲月資料
        monthly_df = pd.DataFrame()
        monthly_df['LON'] = df['LON']
        monthly_df['LAT'] = df['LAT']
        
        # 處理每個月
        for month in range(1, 13):
            month_str = f"{year}{month:02d}"
            
            # 獲取該月的所有日期列
            days_in_month = calendar.monthrange(int(year), month)[1]
            date_cols = [f"{year}{month:02d}{day:02d}" for day in range(1, days_in_month + 1)]
            
            # 過濾出存在於DataFrame中的日期列
            existing_cols = [col for col in date_cols if col in df.columns]
            
            if existing_cols:
                # 創建一個臨時DataFrame，將-99.9替換為NaN
                temp_df = df[existing_cols].replace(-99.9, np.nan)
                
                # 檢查每一行是否所有值都是NaN (原始值都是-99.9)
                all_missing = temp_df.isna().all(axis=1)
                
                # 計算月累積降雨量 (忽略NaN值)
                monthly_df[month_str] = temp_df.sum(axis=1, skipna=True)
                
                # 如果某行全部都是-99.9 (無資料)，將結果設為-99.9
                monthly_df.loc[all_missing, month_str] = -99.9
            else:
                monthly_df[month_str] = -99.9
        
        # 保存月資料為CSV
        output_file = os.path.join(output_dir, f"月降雨量_{year}.csv")
        monthly_df.to_csv(output_file, index=False)
        print(f"已保存: {output_file}")

# 步驟 2: 合併所有年份的月資料
def merge_monthly_data(monthly_dir, output_dir):
    # 獲取所有月資料CSV檔案
    csv_files = [f for f in os.listdir(monthly_dir) if f.startswith('月降雨量_') and f.endswith('.csv')]
    csv_files.sort()  # 確保按年份排序
    
    if not csv_files:
        print("找不到月降雨量資料檔案")
        return
    
    # 讀取第一個檔案以獲取坐標資訊
    first_file = os.path.join(monthly_dir, csv_files[0])
    result_df = pd.read_csv(first_file)[['LON', 'LAT']]
    
    # 處理每個年份的檔案
    for csv_file in csv_files:
        print(f"合併: {csv_file}")
        file_path = os.path.join(monthly_dir, csv_file)
        df = pd.read_csv(file_path)
        
        # 獲取月份列 (排除LON和LAT)
        month_cols = [col for col in df.columns if col not in ['LON', 'LAT']]
        
        # 將月份資料加入結果DataFrame
        for col in month_cols:
            result_df[col] = df[col]
    
    # 保存最終結果
    result_file = os.path.join(output_dir, "result.csv")
    result_df.to_csv(result_file, index=False)
    print(f"已完成合併，結果保存為: {result_file}")

# 執行轉換和合併
print("開始處理日降雨量資料轉換為月累積降雨量...")
convert_daily_to_monthly(input_dir, monthly_dir)

print("\n開始合併所有年份的月降雨量資料...")
merge_monthly_data(monthly_dir, output_dir)

print("\n處理完成！")
