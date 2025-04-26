import os
import sys
from osgeo import gdal, ogr
import numpy as np
import pandas as pd
import calendar
from datetime import datetime

# 啟用GDAL/OGR異常處理
gdal.UseExceptions()
ogr.UseExceptions()

def calculate_monthly_averages(csv_path, output_folder, lon_field='LON', lat_field='LAT', nodata_value=-99.9):
    """
    計算1960~2020年每個月的平均雨量並生成柵格檔案
    """
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
        
        # 讀取CSV檔案
        print("正在讀取CSV檔案...")
        df = pd.read_csv(csv_path)
        print(f"CSV檔案讀取完成，共 {len(df)} 筆資料")
        
        # 檢查必要欄位是否存在
        required_fields = [lon_field, lat_field]
        for field in required_fields:
            if field not in df.columns:
                print(f"錯誤: 找不到必要欄位 '{field}'")
                return False
        
        # 將資料從寬格式轉換為長格式
        print("正在轉換資料格式...")
        # 先選擇座標欄位
        id_vars = [lon_field, lat_field]
        # 選擇所有年月欄位
        value_vars = [col for col in df.columns if col not in id_vars]
        
        # 轉換為長格式
        df_long = pd.melt(df, id_vars=id_vars, value_vars=value_vars, var_name='YEARMONTH', value_name='RAINFALL')
        
        # 從YEARMONTH欄位提取年和月
        df_long['YEAR'] = df_long['YEARMONTH'].astype(str).str[:4].astype(int)
        df_long['MONTH'] = df_long['YEARMONTH'].astype(str).str[4:6].astype(int)
        
        # 檢查資料
        print(f"轉換後的資料筆數: {len(df_long)}")
        
        # 計算每個月的平均雨量 (跨年)
        print("正在計算每月平均雨量...")
        monthly_avg = df_long.groupby([lon_field, lat_field, 'MONTH'])['RAINFALL'].mean().reset_index()
        
        # 為每個月創建柵格
        for month in range(1, 13):
            print(f"處理第 {month} 月的資料...")
            month_name = calendar.month_name[month]
            
            # 篩選當月資料
            month_data = monthly_avg[monthly_avg['MONTH'] == month]
            
            # 創建臨時的Shapefile
            driver = ogr.GetDriverByName('MEMORY')
            data_source = driver.CreateDataSource('memory')
            
            # 創建空間參考
            srs = ogr.osr.SpatialReference()
            srs.ImportFromEPSG(4326)  # WGS84
            
            # 創建圖層
            layer = data_source.CreateLayer('points', srs, ogr.wkbPoint)
            
            # 添加雨量欄位
            field_defn = ogr.FieldDefn('RAIN_AVG', ogr.OFTReal)
            layer.CreateField(field_defn)
            
            # 添加點資料
            for _, row in month_data.iterrows():
                # 創建點幾何
                point = ogr.Geometry(ogr.wkbPoint)
                point.AddPoint(row[lon_field], row[lat_field])
                
                # 創建要素
                feature = ogr.Feature(layer.GetLayerDefn())
                feature.SetGeometry(point)
                
                # 設定雨量值
                if not np.isnan(row['RAINFALL']):
                    feature.SetField('RAIN_AVG', float(row['RAINFALL']))
                
                # 添加要素到圖層
                layer.CreateFeature(feature)
                feature = None
            
            print(f"第 {month} 月: 成功載入 {layer.GetFeatureCount()} 個點")
            
            # 如果沒有點，跳過此月
            if layer.GetFeatureCount() == 0:
                print(f"第 {month} 月沒有有效資料，跳過")
                continue
            
            # 獲取圖層的範圍
            extent = layer.GetExtent()
            x_min, x_max, y_min, y_max = extent[0], extent[1], extent[2], extent[3]
            
            # 設定柵格分辨率
            res_x = 0.0083
            res_y = 0.0083
            
            # 設定柵格化參數
            width = int((x_max - x_min) / res_x) + 1
            height = int((y_max - y_min) / res_y) + 1
            
            # 創建輸出檔案名稱
            output_file = os.path.join(output_folder, f"Monthly_Avg_Rain_{month:02d}_{month_name}.tif")
            
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
            gdal.RasterizeLayer(raster, [1], layer, options=["ATTRIBUTE=RAIN_AVG"])
            
            # 清理
            band = None
            raster = None
            
            print(f"已生成第 {month} 月平均雨量柵格檔案: {output_file}")
        
        print("所有月份平均雨量柵格檔案已生成完成")
        return True
    
    except Exception as e:
        print(f"處理CSV檔案時發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# 主程式
if __name__ == "__main__":
    # 直接指定CSV檔案路徑
    csv_file = r"ALL\result.csv"
    
    # 如果沒有指定CSV檔案，讓使用者輸入
    if not os.path.exists(csv_file):
        csv_file = input("請輸入含有雨量資料的CSV檔案的完整路徑: ")
    
    # 輸出資料夾
    output_folder = r"raster_output\monthly"
    
    # 確保輸出資料夾存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # 處理CSV檔案
    if os.path.exists(csv_file):
        print(f"\n開始處理: {csv_file}")
        calculate_monthly_averages(csv_file, output_folder)
    else:
        print(f"錯誤: 找不到CSV檔案 '{csv_file}'")
    
    print("\n處理完成")
