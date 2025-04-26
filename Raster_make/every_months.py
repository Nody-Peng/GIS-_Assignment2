import os
import sys
from osgeo import gdal, ogr
import numpy as np

# 啟用GDAL/OGR異常處理
gdal.UseExceptions()
ogr.UseExceptions()

def list_csv_files(directory):
    """列出指定目錄中的所有CSV檔案"""
    print(f"搜尋目錄: {directory}")
    csv_files = []
    if os.path.exists(directory):
        for file in os.listdir(directory):
            if file.lower().endswith('.csv'):
                csv_files.append(os.path.join(directory, file))
        print(f"找到 {len(csv_files)} 個CSV檔案")
    else:
        print(f"目錄不存在: {directory}")
    return csv_files

def csv_to_raster(csv_path, output_folder, x_field='LON', y_field='LAT', delimiter=',', nodata_value=-99.9):
    """將CSV檔案轉換為柵格檔案，將特定值設為NoData"""
    try:
        # 確保輸出資料夾存在
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"已創建輸出資料夾: {output_folder}")
        
        # 檢查CSV檔案是否存在
        if not os.path.exists(csv_path):
            print(f"錯誤: 找不到CSV檔案 '{csv_path}'")
            return False
        
        print(f"處理CSV檔案: {csv_path}")
        
        # 讀取CSV檔案的標頭
        with open(csv_path, 'r') as f:
            header = f.readline().strip().split(delimiter)
        
        print(f"檢測到的欄位: {header}")
        
        # 確認經緯度欄位是否存在
        if x_field not in header or y_field not in header:
            print(f"錯誤: 找不到經緯度欄位 '{x_field}' 或 '{y_field}'")
            return False
        
        # 獲取所有可能的數值欄位（排除經緯度欄位）
        value_fields = [field for field in header if field not in [x_field, y_field]]
        print(f"找到 {len(value_fields)} 個可能的數值欄位")
        
        # 創建臨時的Shapefile
        driver = ogr.GetDriverByName('MEMORY')
        data_source = driver.CreateDataSource('memory')
        
        # 創建空間參考
        srs = ogr.osr.SpatialReference()
        srs.ImportFromEPSG(4326)  # WGS84
        
        # 創建圖層
        layer = data_source.CreateLayer('points', srs, ogr.wkbPoint)
        
        # 添加欄位
        for field in value_fields:
            field_defn = ogr.FieldDefn(field, ogr.OFTReal)
            layer.CreateField(field_defn)
        
        # 讀取CSV資料
        with open(csv_path, 'r') as f:
            next(f)  # 跳過標頭
            for line in f:
                parts = line.strip().split(delimiter)
                if len(parts) != len(header):
                    continue  # 跳過格式不正確的行
                
                try:
                    x = float(parts[header.index(x_field)])
                    y = float(parts[header.index(y_field)])
                    
                    # 創建點幾何
                    point = ogr.Geometry(ogr.wkbPoint)
                    point.AddPoint(x, y)
                    
                    # 創建要素
                    feature = ogr.Feature(layer.GetLayerDefn())
                    feature.SetGeometry(point)
                    
                    # 設定欄位值，將 nodata_value 視為 NULL
                    for field in value_fields:
                        try:
                            value = float(parts[header.index(field)])
                            # 如果值等於 nodata_value，則不設置該欄位，讓它保持為 NULL
                            if abs(value - nodata_value) > 0.0001:  # 使用近似比較避免浮點誤差
                                feature.SetField(field, value)
                        except (ValueError, IndexError):
                            pass  # 不設置欄位，讓它保持為 NULL
                    
                    # 添加要素到圖層
                    layer.CreateFeature(feature)
                    feature = None
                except (ValueError, IndexError) as e:
                    print(f"跳過無效行: {line.strip()} - {str(e)}")
        
        print(f"成功載入 {layer.GetFeatureCount()} 個點")
        
        # 獲取圖層的範圍
        extent = layer.GetExtent()
        x_min, x_max, y_min, y_max = extent[0], extent[1], extent[2], extent[3]
        
        # 設定柵格分辨率
        res_x = 0.0083
        res_y = 0.0083
        
        # 為每個數值欄位創建柵格
        for field in value_fields:
            print(f"處理欄位: {field}")
            output_file = os.path.join(output_folder, f"{field}.tif")
            
            # 設定柵格化參數
            width = int((x_max - x_min) / res_x)
            height = int((y_max - y_min) / res_y)
            
            # 創建目標柵格
            driver = gdal.GetDriverByName('GTiff')
            raster = driver.Create(output_file, width, height, 1, gdal.GDT_Float32)
            
            # 設定地理參考
            raster.SetGeoTransform((x_min, res_x, 0, y_max, 0, -res_y))
            raster.SetProjection(srs.ExportToWkt())
            
            # 設定無資料值
            band = raster.GetRasterBand(1)
            band.SetNoDataValue(nodata_value)
            band.Fill(nodata_value)
            
            # 執行柵格化
            gdal.RasterizeLayer(raster, [1], layer, options=[f"ATTRIBUTE={field}"])
            
            # 處理柵格資料，確保 -99.9 被設為 NoData
            data = band.ReadAsArray()
            
            # 將資料寫回柵格
            band.WriteArray(data)
            
            # 清理
            band = None
            raster = None
            
            print(f"已生成柵格檔案: {output_file}")
        
        return True
    
    except Exception as e:
        print(f"處理CSV檔案時發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# 主程式
if __name__ == "__main__":
    # 設定可能的CSV檔案位置
    possible_directories = [
        r"D:\TEST\ALL",
        r"D:\NCCU\研究所\研一\研一下\地理資訊系統特論\Assignment",
        # 如果您知道檔案在其他位置，請添加更多路徑
    ]
    
    # 輸出資料夾
    output_folder = r"D:\TEST\raster_output"
    
    # 搜尋CSV檔案
    csv_files = []
    for directory in possible_directories:
        csv_files.extend(list_csv_files(directory))
    
    if not csv_files:
        print("未找到CSV檔案。請確認檔案路徑。")
        # 讓使用者輸入CSV檔案路徑
        user_input = input("請輸入CSV檔案的完整路徑: ")
        if os.path.exists(user_input) and user_input.lower().endswith('.csv'):
            csv_files = [user_input]
    
    # 處理找到的CSV檔案
    for csv_file in csv_files:
        print(f"\n開始處理: {csv_file}")
        
        # 嘗試不同的分隔符和欄位名稱
        delimiters = [',', ';', '\t', '  ']  # 添加雙空格作為可能的分隔符
        x_fields = ['LON', 'lon', 'Lon', 'longitude', 'Longitude', 'LONGITUDE', 'X', 'x']
        y_fields = ['LAT', 'lat', 'Lat', 'latitude', 'Latitude', 'LATITUDE', 'Y', 'y']
        
        success = False
        for delimiter in delimiters:
            if success:
                break
            for x_field in x_fields:
                if success:
                    break
                for y_field in y_fields:
                    print(f"嘗試: 分隔符='{delimiter}', X={x_field}, Y={y_field}")
                    if csv_to_raster(csv_file, output_folder, x_field, y_field, delimiter, nodata_value=-99.9):
                        success = True
                        print(f"成功處理CSV檔案，使用分隔符='{delimiter}', X={x_field}, Y={y_field}")
                        break
        
        if not success:
            print(f"無法處理CSV檔案: {csv_file}")
    
    print("\n處理完成")
