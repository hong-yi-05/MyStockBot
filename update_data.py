import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import os

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# --- 0. 讀取你上傳的「進階彈藥庫」 ---
advanced_dict = {}
try:
    if os.path.exists("advanced_data.csv"):
        adv_df = pd.read_csv("advanced_data.csv", dtype={'股票代號': str})
        today_str = datetime.now().strftime("%Y-%m-%d")
        for _, row in adv_df.iterrows():
            code = row['股票代號']
            exp_date = str(row.get('有效截止日', '1970-01-01'))
            if today_str > exp_date: continue # 過期不計分
            advanced_dict[code] = {
                'cond9': bool(int(row.get('高融券軋空', 0))),
                'cond10': bool(int(row.get('營收年月雙增', 0)))
            }
        print(f"📥 成功載入進階數據！(共 {len(advanced_dict)} 檔有效)")
except:
    print("⚠️ 未偵測到有效進階數據，將以 0 分計算。")

# --- 1. 抓取 3 天籌碼 ---
def get_3_days_chip_data():
    days_data = []
    curr = datetime.now()
    while len(days_data) < 3:
        if curr.weekday() < 5:
            d_str = curr.strftime("%Y%m%d")
            url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={d_str}&selectType=ALL&response=json"
            try:
                res = requests.get(url, headers=headers, verify=False, timeout=10)
                data = res.json()
                if data.get('stat') == 'OK':
                    df = pd.DataFrame(data['data'], columns=data['fields'])
                    df['證券代號'] = df['證券代號'].astype(str)
                    df['外資'] = df['外陸資買賣超股數(不含外資自營商)'].str.replace(',', '').astype(float) / 1000
                    df['投信'] = df['投信買賣超股數'].str.replace(',', '').astype(float) / 1000
                    days_data.append(df.set_index('證券代號')[['證券名稱', '外資', '投信']])
                    time.sleep(3)
            except: pass
        curr -= timedelta(days=1)
    return days_data

chip_tables = get_3_days_chip_data()
today_chip, yest_chip, prev_chip = chip_tables[0], chip_tables[1], chip_tables[2]
stock_dict = {f"{c}.TW": r['證券名稱'] for c, r in today_chip.iterrows() if len(c) == 4}

# --- 2. 技術面分析 ---
results = []
print(f"🚀 開始全市場掃描...")
for ticker, name in stock_dict.items():
    code = ticker.replace('.TW', '')
    try:
        hist = yf.download(ticker, period="6mo", progress=False)
        if len(hist) < 100: continue
        close_px, volume = hist['Close'].squeeze(), hist['Volume'].squeeze()
        open_px, high_px, low_px = hist['Open'].squeeze(), hist['High'].squeeze(), hist['Low'].squeeze()
        vol_ma5 = volume.rolling(5).mean().iloc[-1]
        if vol_ma5 < 1000000: continue # 1000張門檻
        
        # 條件 1~8
        ma_list = [close_px.rolling(w).mean().iloc[-1] for w in [5, 10, 20, 60]]
        cond1 = (max(ma_list) - min(ma_list)) / min(ma_list) < 0.05
        cond2 = vol_ma5 < volume.rolling(20).mean().iloc[-1]
        curr_c = float(close_px.iloc[-1])
        cond3 = (curr_c > float(open_px.iloc[-1]) * 1.02) and (float(volume.iloc[-1]) > vol_ma5 * 1.5) and (curr_c > max(ma_list))
        f_buy_1 = today_chip.loc[code, '外資'] if code in today_chip.index else 0
        cond4 = (f_buy_1 > 0) and (yest_chip.loc[code, '外資'] if code in yest_chip.index else 0 > 0)
        cond5 = (f_buy_1 > 0) and (today_chip.loc[code, '投信'] if code in today_chip.index else 0 > 0)
        high_9, low_9 = high_px.rolling(9).max(), low_px.rolling(9).min()
        rsv = (close_px - low_9) / (high_9 - low_9) * 100
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        cond6 = (k.iloc[-1] > d.iloc[-1]) and (k.iloc[-2] <= d.iloc[-2])
        cond7 = curr_c > close_px.rolling(100).mean().iloc[-1]
        cond8 = float(low_px.iloc[-1]) > float(high_px.iloc[-2])
        
        # 條件 9~10 (從進階資料讀取)
        adv = advanced_dict.get(code, {'cond9': False, 'cond10': False})
        cond9, cond10 = adv['cond9'], adv['cond10']
        
        score = sum([cond1, cond2, cond3, cond4, cond5, cond6, cond7, cond8, cond9, cond10])
        if score >= 3:
            met = []
            if cond1: met.append("1")
            if cond2: met.append("2")
            if cond3: met.append("3")
            if cond4: met.append("4")
            if cond5: met.append("5")
            if cond6: met.append("6")
            if cond7: met.append("7")
            if cond8: met.append("8")
            if cond9: met.append("🔥9.高融券軋空")
            if cond10: met.append("🔥10.營收年月雙增")
            results.append({"更新日期": datetime.now().strftime("%Y-%m-%d"), "股票代號": code, "股票名稱": name, "最新收盤價": round(curr_c, 2), "總分": score, "符合條件": "、".join(met)})
    except: continue

pd.DataFrame(results).sort_values(by='總分', ascending=False).to_csv("daily_stock_score.csv", index=False, encoding='utf-8-sig')
