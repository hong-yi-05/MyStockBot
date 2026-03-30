import yfinance as yf
import pandas as pd
import random
from datetime import datetime

# 1. 準備股票池 (示範 20 檔)
stock_list = {
    '2330.TW': '台積電', '2317.TW': '鴻海', '2454.TW': '聯發科', '2382.TW': '廣達', 
    '2308.TW': '台達電', '2603.TW': '長榮', '2881.TW': '富邦金', '3231.TW': '緯創', 
    '2356.TW': '英業達', '2609.TW': '陽明', '2371.TW': '大同', '2324.TW': '仁寶',
    '3481.TW': '群創', '2409.TW': '友達', '1519.TW': '華城', '1504.TW': '東元',
    '3034.TW': '聯詠', '2303.TW': '聯電', '2891.TW': '中信金', '2882.TW': '國泰金'
}

print(f"🤖 機器人啟動！開始執行盤後資料抓取與評分計算...")
results = []

# 2. 開始迴圈計算每一檔股票
for i, (ticker, name) in enumerate(stock_list.items()):
    print(f"[{i+1}/{len(stock_list)}] 正在分析: {name}...")
    
    try:
        hist = yf.download(ticker, period="4mo", progress=False)
        if len(hist) > 60:
            close_px = hist['Close'].squeeze()
            volume = hist['Volume'].squeeze()
            open_px = hist['Open'].squeeze()
            
            # 計算均線
            ma_list = [
                close_px.rolling(5).mean().iloc[-1],
                close_px.rolling(10).mean().iloc[-1],
                close_px.rolling(20).mean().iloc[-1],
                close_px.rolling(60).mean().iloc[-1]
            ]
            
            # 條件判斷
            cond1 = ((max(ma_list) - min(ma_list)) / min(ma_list)) < 0.05
            cond2 = volume.rolling(5).mean().iloc[-1] < volume.rolling(20).mean().iloc[-1]
            cond3 = (float(close_px.iloc[-1]) > float(open_px.iloc[-1]) * 1.02) and \
                    (float(volume.iloc[-1]) > volume.rolling(5).mean().iloc[-1] * 1.5) and \
                    (float(close_px.iloc[-1]) > max(ma_list))
            cond4 = random.choice([True, False]) # 模擬籌碼
            cond5 = random.choice([True, False]) # 模擬籌碼
            
            # 計算分數
            score = 0
            met_conditions = []
            if cond1: score += 1; met_conditions.append("1.均線糾結")
            if cond2: score += 1; met_conditions.append("2.極致量縮")
            if cond3: score += 1; met_conditions.append("3.帶量突破")
            if cond4: score += 1; met_conditions.append("4.法人連買")
            if cond5: score += 1; met_conditions.append("5.大戶接碼")
            
            # 存入清單
            results.append({
                "更新日期": datetime.now().strftime("%Y-%m-%d"),
                "股票代號": ticker.replace('.TW', ''),
                "股票名稱": name,
                "最新收盤價": round(float(close_px.iloc[-1]), 2),
                "總分": score,
                "符合條件": "、".join(met_conditions) if met_conditions else "無"
            })
    except Exception as e:
        print(f"  ❌ {name} 計算失敗")

# 3. 將結果轉換成表格，並存成 CSV 檔案
df = pd.DataFrame(results)

# 依照總分由高到低排序
df = df.sort_values(by='總分', ascending=False)

# 儲存檔案！(使用 utf-8-sig 編碼，確保 Excel 打開中文不會亂碼)
file_name = "daily_stock_score.csv"
df.to_csv(file_name, index=False, encoding='utf-8-sig')

print(f"\n🎉 報告老闆！所有資料已計算完畢，並成功存入 {file_name} 中！")