import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import time

# --- 準備偽裝成一般瀏覽器的身分證 ---
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- 1. 工具函數：抓取全市場代碼 ---
def get_all_tickers():
    print("正在抓取全市場股票清單...")
    url = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBYM_ALL"
    try:
        # 加入 headers 偽裝
        res = requests.get(url, headers=headers, timeout=10)
        df = pd.DataFrame(res.json())
        tickers = {f"{row['Code']}.TW": row['Name'] for _, row in df.iterrows() if len(row['Code']) == 4}
        print(f"✅ 成功騙過守衛！取得 {len(tickers)} 檔股票。")
        return tickers
    except Exception as e:
        print(f"❌ 抓取清單依然失敗: {e}")
        return {'2330.TW': '台積電', '2317.TW': '鴻海'}

# --- 2. 工具函數：抓取今日真實籌碼對照表 ---
def get_real_chip_data():
    print("正在抓取今日三大法人籌碼分布...")
    date_str = datetime.now().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALL&response=json"
    try:
        # 這裡也加入 headers
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        if data['stat'] == 'OK':
            df = pd.DataFrame(data['data'], columns=data['fields'])
            df['外資'] = df['外陸資買賣超股數(不含外資自營商)'].str.replace(',', '').astype(float) / 1000
            df['投信'] = df['投信買賣超股數'].str.replace(',', '').astype(float) / 1000
            print("✅ 真實籌碼抓取成功！")
            return df.set_index('證券代號')[['外資', '投信']]
    except Exception as e:
        print(f"❌ 籌碼抓取失敗: {e}")
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
        
        close_px = hist['Close'].squeeze()
        volume = hist['Volume'].squeeze()
        open_px = hist['Open'].squeeze()
        
        ma_list = [close_px.rolling(w).mean().iloc[-1] for w in [5, 10, 20, 60]]
        ma_max, ma_min = max(ma_list), min(ma_list)
        
        cond1 = ((ma_max - ma_min) / ma_min) < 0.05
        cond2 = volume.rolling(5).mean().iloc[-1] < volume.rolling(20).mean().iloc[-1]
        
        curr_c, curr_o, curr_v = float(close_px.iloc[-1]), float(open_px.iloc[-1]), float(volume.iloc[-1])
        vol_ma5 = volume.rolling(5).mean().iloc[-1]
        cond3 = (curr_c > curr_o * 1.02) and (curr_v > vol_ma5 * 1.5) and (curr_c > ma_max)
        
        cond4 = False 
        cond5 = False 
        
        if code in chip_table.index:
            f_buy = chip_table.loc[code, '外資']
            i_buy = chip_table.loc[code, '投信']
            if f_buy > 0 and i_buy > 0: cond4 = True
            if f_buy > 500: cond5 = True
            
        score = sum([cond1, cond2, cond3, cond4, cond5])
        
        # 🔥 把門檻降為 2 分，讓你能看到更多觀察股
        if score >= 2:
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
