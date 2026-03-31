import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# --- 0. 讀取你上傳的「進階彈藥庫」 ---
advanced_dict = {}
try:
    if os.path.exists("advanced_data.csv"):
        adv_df = pd.read_csv("advanced_data.csv", dtype={'股票代號': str})
        today_str = datetime.now().strftime("%Y-%m-%d")
        for _, row in adv_df.iterrows():
            code = str(row['股票代號'])
            exp_date = str(row.get('有效截止日', '1970-01-01'))
            if today_str > exp_date: continue
            advanced_dict[code] = {
                'cond9': bool(int(row.get('高融券軋空', 0))),
                'cond10': bool(int(row.get('營收年月雙增', 0))),
                'exp_date': exp_date # 🌟 新增：把日期存起來
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
                    time.sleep(2)
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
        # 🌟 關鍵修正：必須清掉 Yahoo 產生的空白行，否則價格會變 None
        hist = hist.dropna()
        if len(hist) < 100: continue

        close_px, volume = hist['Close'].squeeze(), hist['Volume'].squeeze()
        open_px, high_px, low_px = hist['Open'].squeeze(), hist['High'].squeeze(), hist['Low'].squeeze()

        vol_ma5 = volume.rolling(5).mean().iloc[-1]
        if vol_ma5 < 1000000: continue

        ma_list = [close_px.rolling(w).mean().iloc[-1] for w in [5, 10, 20, 60]]
        cond1 = (max(ma_list) - min(ma_list)) / min(ma_list) < 0.05
        cond2 = vol_ma5 < volume.rolling(20).mean().iloc[-1]
        curr_c = float(close_px.iloc[-1])
        cond3 = (curr_c > float(open_px.iloc[-1]) * 1.02) and (float(volume.iloc[-1]) > vol_ma5 * 1.5) and (curr_c > max(ma_list))

        f_buy_1 = today_chip.loc[code, '外資'] if code in today_chip.index else 0
        f_buy_2 = yest_chip.loc[code, '外資'] if code in yest_chip.index else 0
        f_buy_3 = prev_chip.loc[code, '外資'] if code in prev_chip.index else 0
        cond4 = (f_buy_1 > 0) and (f_buy_2 > 0) and (f_buy_3 > 0)

        i_buy_1 = today_chip.loc[code, '投信'] if code in today_chip.index else 0
        cond5 = (f_buy_1 > 0) and (i_buy_1 > 0)

        high_9, low_9 = high_px.rolling(9).max(), low_px.rolling(9).min()
        rsv = (close_px - low_9) / (high_9 - low_9) * 100
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        cond6 = (k.iloc[-1] > d.iloc[-1]) and (k.iloc[-2] <= d.iloc[-2])
        cond7 = curr_c > close_px.rolling(100).mean().iloc[-1]
        cond8 = float(low_px.iloc[-1]) > float(high_px.iloc[-2])

        adv = advanced_dict.get(code, {'cond9': False, 'cond10': False, 'exp_date': '-'})
        cond9, cond10 = adv['cond9'], adv['cond10']

        score = int(cond1) + int(cond2) + int(cond3) + int(cond4) + int(cond5) + int(cond6) + int(cond7) + int(cond8) + int(cond9) + int(cond10)

        if score >= 3:
            met = []
            if cond1: met.append("1.均線糾結")
            if cond2: met.append("2.極致量縮")
            if cond3: met.append("3.帶量突破")
            if cond4: met.append("4.外資連買3天")
            if cond5: met.append("5.法人今日同買")
            if cond6: met.append("6.KD黃金交叉")
            if cond7: met.append("7.站上20周線")
            if cond8: met.append("8.跳空缺口")
            if cond9: met.append("🔥9.高融券軋空")
            if cond10: met.append("🔥10.營收年月雙增")

            results.append({
                "更新日期": datetime.now().strftime("%Y-%m-%d"),
                "股票代號": code, "股票名稱": name,
                "最新收盤價": round(float(curr_c), 2),
                "總分": int(score), "符合條件": "、".join(met),
                "進階失效日期": adv.get('exp_date', '-') # 🌟 新增：把日期寫進報表
            })
    except: continue

# 🌟 避免空資料報錯的防呆機制
df = pd.DataFrame(results, columns=["更新日期", "股票代號", "股票名稱", "最新收盤價", "總分", "符合條件", "進階失效日期"])
if not df.empty:
    df = df.sort_values(by='總分', ascending=False)
df.to_csv("daily_stock_score.csv", index=False, encoding='utf-8-sig')
