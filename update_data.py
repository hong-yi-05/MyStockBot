import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

# --- 1. 自動往前抓取 3 個有開盤的交易日籌碼 ---
def get_3_days_chip_data():
    print("正在抓取近 3 個交易日的籌碼資料，請稍候...")
    days_data = []
    current_date = datetime.now()
    
    while len(days_data) < 3:
        # 避開六日 (0-4 代表週一到週五)
        if current_date.weekday() < 5:
            date_str = current_date.strftime("%Y%m%d")
            url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALL&response=json"
            try:
                res = requests.get(url, headers=headers, verify=False, timeout=10)
                data = res.json()
                if data.get('stat') == 'OK':
                    df = pd.DataFrame(data['data'], columns=data['fields'])
                    df['證券代號'] = df['證券代號'].astype(str)
                    df['外資'] = df['外陸資買賣超股數(不含外資自營商)'].str.replace(',', '').astype(float) / 1000
                    df['投信'] = df['投信買賣超股數'].str.replace(',', '').astype(float) / 1000
                    # 將這天的表格存入清單
                    days_data.append(df.set_index('證券代號')[['證券名稱', '外資', '投信']])
                    print(f"✅ 成功取得 {date_str} 籌碼資料")
                    time.sleep(2) # 禮貌性暫停，避免被證交所踢掉
            except Exception as e:
                pass
        current_date -= timedelta(days=1)
        
    return days_data

# --- 主程式 ---
# chip_tables 是一個清單，裡面包含 [今天, 昨天, 前天] 的表格
chip_tables = get_3_days_chip_data()

if len(chip_tables) < 3:
    print("❌ 抓取 3 天籌碼失敗，程式終止。")
    exit()

today_chip = chip_tables[0]
yest_chip = chip_tables[1]
prev_chip = chip_tables[2]

# 直接用今天的籌碼表當作全市場股票名單
stock_dict = {}
for code, row in today_chip.iterrows():
    if len(code) == 4: # 過濾出 4 位數股票
        stock_dict[f"{code}.TW"] = row['證券名稱']

print(f"🚀 開始全市場掃描 (共 {len(stock_dict)} 檔)...")

results = []
count = 0

for ticker, name in stock_dict.items():
    code = ticker.replace('.TW', '')
    count += 1
    if count % 100 == 0: print(f"🔄 已分析 {count} 檔...")
    
    try:
        hist = yf.download(ticker, period="4mo", progress=False)
        if len(hist) < 60: continue
        
        close_px = hist['Close'].squeeze()
        volume = hist['Volume'].squeeze()
        open_px = hist['Open'].squeeze()
        
        # 條件 1 & 2 & 3: 技術面
        ma_list = [close_px.rolling(w).mean().iloc[-1] for w in [5, 10, 20, 60]]
        ma_max, ma_min = max(ma_list), min(ma_list)
        
        cond1 = ((ma_max - ma_min) / ma_min) < 0.05
        cond2 = volume.rolling(5).mean().iloc[-1] < volume.rolling(20).mean().iloc[-1]
        
        curr_c, curr_o, curr_v = float(close_px.iloc[-1]), float(open_px.iloc[-1]), float(volume.iloc[-1])
        vol_ma5 = volume.rolling(5).mean().iloc[-1]
        cond3 = (curr_c > curr_o * 1.02) and (curr_v > vol_ma5 * 1.5) and (curr_c > ma_max)
        
        # 條件 4: 外資連買 3 天 (今天、昨天、前天都大於 0)
        f_buy_1 = today_chip.loc[code, '外資'] if code in today_chip.index else 0
        f_buy_2 = yest_chip.loc[code, '外資'] if code in yest_chip.index else 0
        f_buy_3 = prev_chip.loc[code, '外資'] if code in prev_chip.index else 0
        cond4 = (f_buy_1 > 0) and (f_buy_2 > 0) and (f_buy_3 > 0)
        
        # 條件 5: 法人今日同買 (外資與投信今天都大於 0)
        i_buy_1 = today_chip.loc[code, '投信'] if code in today_chip.index else 0
        cond5 = (f_buy_1 > 0) and (i_buy_1 > 0)
            
        score = sum([cond1, cond2, cond3, cond4, cond5])
        
        # 只要滿足 2 個條件以上就顯示
        if score >= 2:
            met = []
            if cond1: met.append("1.均線糾結")
            if cond2: met.append("2.極致量縮")
            if cond3: met.append("3.帶量突破")
            if cond4: met.append("4.外資連買3天")
            if cond5: met.append("5.法人今日同買")
            
            results.append({
                "更新日期": datetime.now().strftime("%Y-%m-%d"),
                "股票代號": code, "股票名稱": name, "最新收盤價": round(curr_c, 2),
                "總分": score, "符合條件": "、".join(met)
            })
            
    except:
        continue

pd.DataFrame(results).sort_values(by='總分', ascending=False).to_csv("daily_stock_score.csv", index=False, encoding='utf-8-sig')
print(f"🎉 掃描完成！共過濾出 {len(results)} 檔潛力股。")
