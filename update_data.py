import yfinance as yf
import pandas as pd
import random
import requests
from datetime import datetime
import time

# --- 1. 自動抓取全市場股票代碼 (上市與上櫃) ---
def get_all_tickers():
    print("正在抓取全市場股票清單...")
    # 這裡從證交所開放資料抓取每日本益比清單，它包含了所有股票代號與名稱
    url = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBYM_ALL"
    try:
        res = requests.get(url)
        data = res.json()
        df = pd.DataFrame(data)
        
        # 只過濾出 4 位數的股票代號 (排除認購權證、ETF 等)
        # 並且幫代號加上 .TW (上市) 或 .TWO (上櫃)
        # 備註：這個 API 主要回傳上市股票，若要包含上櫃可另外串接，這裡先以全上市為主測試
        full_list = {}
        for _, row in df.iterrows():
            code = row['Code']
            name = row['Name']
            if len(code) == 4:
                full_list[f"{code}.TW"] = name
        
        print(f"✅ 成功取得 {len(full_list)} 檔股票代號")
        return full_list
    except Exception as e:
        print(f"❌ 抓取清單失敗: {e}")
        # 如果失敗，回傳一個基本的清單保底
        return {'2330.TW': '台積電', '2317.TW': '鴻海'}

# --- 2. 主程式開始 ---
stock_list = get_all_tickers()
print(f"🤖 機器人啟動！開始分析全市場...")

results = []

# 為了避免被 Yahoo 封鎖，我們分批處理
count = 0
for ticker, name in stock_list.items():
    count += 1
    if count % 50 == 0:
        print(f"🔄 已掃描 {count} 檔...")
        time.sleep(1) # 每 50 檔稍微休息 1 秒
        
    try:
        # 抓取 4 個月資料
        hist = yf.download(ticker, period="4mo", progress=False)
        
        if len(hist) > 60:
            close_px = hist['Close'].squeeze()
            volume = hist['Volume'].squeeze()
            open_px = hist['Open'].squeeze()
            
            # 計算 MA
            ma5 = close_px.rolling(5).mean().iloc[-1]
            ma10 = close_px.rolling(10).mean().iloc[-1]
            ma20 = close_px.rolling(20).mean().iloc[-1]
            ma60 = close_px.rolling(60).mean().iloc[-1]
            
            # 條件 1: 均線糾結 (5/10/20/60 差距 < 5%)
            ma_list = [ma5, ma10, ma20, ma60]
            cond1 = ((max(ma_list) - min(ma_list)) / min(ma_list)) < 0.05
            
            # 條件 2: 量縮
            cond2 = volume.rolling(5).mean().iloc[-1] < volume.rolling(20).mean().iloc[-1]
            
            # 條件 3: 帶量長紅突破
            curr_c = float(close_px.iloc[-1])
            curr_o = float(open_px.iloc[-1])
            curr_v = float(volume.iloc[-1])
            cond3 = (curr_c > curr_o * 1.02) and (curr_v > volume.rolling(5).mean().iloc[-1] * 1.5) and (curr_c > max(ma_list))
            
            # 條件 4 & 5 (目前仍為模擬，之後換真實數據)
            cond4 = random.choice([True, False])
            cond5 = random.choice([True, False])
            
            score = sum([cond1, cond2, cond3, cond4, cond5])
            
            if score >= 3: # 只記錄 3 分以上的股票，節省檔案空間
                met = []
                if cond1: met.append("1.均線糾結")
                if cond2: met.append("2.極致量縮")
                if cond3: met.append("3.帶量突破")
                if cond4: met.append("4.法人連買")
                if cond5: met.append("5.大戶接碼")
                
                results.append({
                    "更新日期": datetime.now().strftime("%Y-%m-%d"),
                    "股票代號": ticker.replace('.TW', ''),
                    "股票名稱": name,
                    "最新收盤價": round(curr_c, 2),
                    "總分": score,
                    "符合條件": "、".join(met)
                })
    except:
        continue

# 儲存結果
df = pd.DataFrame(results)
df = df.sort_values(by='總分', ascending=False)
df.to_csv("daily_stock_score.csv", index=False, encoding='utf-8-sig')
print(f"🎉 掃描完畢！共找到 {len(results)} 檔優質候選股。")
