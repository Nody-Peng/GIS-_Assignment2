import os
import glob

# 指定資料夾路徑
folder_path = "path_to_Raw_data"  # 請根據您的實際路徑調整

# 取得資料夾中所有的 CSV 檔案
csv_files = glob.glob(os.path.join(folder_path, "*.csv"))

for file in csv_files:
    print(f"處理檔案: {os.path.basename(file)}")
    
    # 讀取檔案內容
    with open(file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 處理每一行，移除所有空格
    processed_lines = []
    for line in lines:
        # 分割每一行的欄位
        fields = line.split(',')
        
        # 移除每個欄位中的空格
        cleaned_fields = [field.replace(' ', '') for field in fields]
        
        # 重新組合行
        processed_lines.append(','.join(cleaned_fields))
    
    # 寫回檔案
    with open(file, 'w', encoding='utf-8', newline='') as f:
        f.writelines(processed_lines)
    
    print(f"已完成處理: {os.path.basename(file)}")

print(f"總共處理了 {len(csv_files)} 個 CSV 檔案")
