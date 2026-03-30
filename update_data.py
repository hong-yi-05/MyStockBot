import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import time

# --- 1. 工具函數：抓取全市場代碼 ---
def get_all_tickers():
    print("正在抓取全市場股票清單...")
    url = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBYM_ALL"
    try:
        res = requests.get(url)
        df = pd.DataFrame(res.json())
        return {f"{row['Code']}.TW": row['Name'] for _, row in df.iterrows() if len(row['Code']) == 4}
    except:
        return {'2330.TW': '台積電', '2317.TW': '鴻海'}

# --- 2. 工具函數：抓取今日真實籌碼對照表 ---
def get_real_chip_data():
    print("正在抓取今日三大法人籌碼分布...")
    # 取得最新交易日 (簡單處理：抓今天的日期，若沒資料則由 Actions 報錯)
    date_str = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALL&response=json"
    try:
        res = requests.get(url, verify=False)
        data = res.json()
        if data['stat'] == 'OK':
            df = pd.DataFrame(data['data'], columns=data['fields'])
            # 整理出外資與投信的買賣張數
            # 索引設為代號，方便等一下快速查詢
            df['外資'] = df['外陸資買賣超股數(不含外資自營商)'].str.replace(',', '').astype(float) / 1000
            df['投信'] = df['投信買賣超股數'].str.replace(',', '').astype(float) / 1000
            return df.set_index('證券代號')[['外資', '投信']]
    except:
        print("今日籌碼資料尚未更新或抓取失敗。")
    return pd.DataFrame()

# --- 主程式 ---
chip_table = get_real_chip_data()
stock_list = get_all_tickers()
results = []

print(f"🚀 開始全市場掃描 (共 {len(stock_list)} 檔)...")

count = 0
for ticker, name in stock_list.items():
    code = ticker.replace('.TW', '')
    count += 1
    if count % 100 == 0: print(f"已分析 {count} 檔...")
    
    try:
        hist = yf.download(ticker, period="4mo", progress=False)
        if len(hist) < 60: continue
        
        # 技術面數據
        close_px = hist['Close'].squeeze()
        volume = hist['Volume'].squeeze()
        open_px = hist['Open'].squeeze()
        
        # 計算均線
        ma_list = [close_px.rolling(w).mean().iloc[-1] for w in [5, 10, 20, 60]]
        ma_max, ma_min = max(ma_list), min(ma_list)
        
        # 條件 1: 均線糾結
        cond1 = ((ma_max - ma_min) / ma_min) < 0.05
        # 條件 2: 量縮
        cond2 = volume.rolling(5).mean().iloc[-1] < volume.rolling(20).mean().iloc[-1]
        # 條件 3: 帶量長紅突破
        curr_c, curr_o, curr_v = float(close_px.iloc[-1]), float(open_px.iloc[-1]), float(volume.iloc[-1])
        vol_ma5 = volume.rolling(5).mean().iloc[-1]
        cond3 = (curr_c > curr_o * 1.02) and (curr_v > vol_ma5 * 1.5) and (curr_c > ma_max)
        
        # --- 真實籌碼比對 ---
        cond4 = False # 條件 4: 法人雙買
        cond5 = False # 條件 5: 外資重倉 (單日買超 > 500張)
        
        if code in chip_table.index:
            f_buy = chip_table.loc[code, '外資']
            i_buy = chip_table.loc[code, '投信']
            if f_buy > 0 and i_buy > 0: cond4 = True
            if f_buy > 500: cond5 = True
            
        score = sum([cond1, cond2, cond3, cond4, cond5])
        
        if score >= 3:
            met = []
            if cond1: met.append("1.均線糾結")
            if cond2: met.append("2.極致量縮")
            if cond3: met.append("3.帶量突破")
            if cond4: met.append("4.法人雙買")
            if cond5: met.append("5.外資大買")
            
            results.append({
                "更新日期": datetime.now().strftime("%Y-%m-%d"),
                "股票代號": code, "股票名稱": name, "最新收盤價": round(curr_c, 2),
                "總分": score, "符合條件": "、".join(met)
            })
            
    except:
        continue

# 儲存結果
pd.DataFrame(results).sort_values(by='總分', ascending=False).to_csv("daily_stock_score.csv", index=False, encoding='utf-8-sig')
print("🎉 全市場真實籌碼掃描完成！")
