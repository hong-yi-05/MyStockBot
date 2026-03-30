import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

# --- 1. 自動往前抓取 3 個交易日籌碼 ---
def get_3_days_chip_data():
    print("正在抓取近 3 個交易日的籌碼資料...")
    days_data = []
    current_date = datetime.now()
    
    while len(days_data) < 3:
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
                    days_data.append(df.set_index('證券代號')[['證券名稱', '外資', '投信']])
                    print(f"✅ 成功取得 {date_str} 籌碼")
                    time.sleep(2)
            except:
                pass
        current_date -= timedelta(days=1)
    return days_data

chip_tables = get_3_days_chip_data()
if len(chip_tables) < 3:
    print("❌ 抓取 3 天籌碼失敗，程式終止。")
    exit()

today_chip, yest_chip, prev_chip = chip_tables[0], chip_tables[1], chip_tables[2]

stock_dict = {f"{code}.TW": row['證券名稱'] for code, row in today_chip.iterrows() if len(code) == 4}
print(f"🚀 開始全市場掃描 (共 {len(stock_dict)} 檔)...")

results = []
count = 0

for ticker, name in stock_dict.items():
    code = ticker.replace('.TW', '')
    count += 1
    if count % 100 == 0: print(f"🔄 已分析 {count} 檔...")
    
    try:
        # 改抓 6 個月，為了計算 100 日均線(20周線)
        hist = yf.download(ticker, period="6mo", progress=False)
        if len(hist) < 100: continue
        
        close_px = hist['Close'].squeeze()
        volume = hist['Volume'].squeeze()
        open_px = hist['Open'].squeeze()
        high_px = hist['High'].squeeze()
        low_px = hist['Low'].squeeze()
        
        # 🌟 絕對門檻：5日均量必須 > 1000 張 (1張=1000股，所以是 1,000,000)
        vol_ma5 = volume.rolling(5).mean().iloc[-1]
        if vol_ma5 < 1000000:
            continue
            
        # --- 基本 5 條件 ---
        ma_list = [close_px.rolling(w).mean().iloc[-1] for w in [5, 10, 20, 60]]
        ma_max, ma_min = max(ma_list), min(ma_list)
        
        cond1 = ((ma_max - ma_min) / ma_min) < 0.05
        cond2 = vol_ma5 < volume.rolling(20).mean().iloc[-1]
        
        curr_c, curr_o, curr_v = float(close_px.iloc[-1]), float(open_px.iloc[-1]), float(volume.iloc[-1])
        cond3 = (curr_c > curr_o * 1.02) and (curr_v > vol_ma5 * 1.5) and (curr_c > ma_max)
        
        f_buy_1 = today_chip.loc[code, '外資'] if code in today_chip.index else 0
        f_buy_2 = yest_chip.loc[code, '外資'] if code in yest_chip.index else 0
        f_buy_3 = prev_chip.loc[code, '外資'] if code in prev_chip.index else 0
        cond4 = (f_buy_1 > 0) and (f_buy_2 > 0) and (f_buy_3 > 0)
        
        i_buy_1 = today_chip.loc[code, '投信'] if code in today_chip.index else 0
        cond5 = (f_buy_1 > 0) and (i_buy_1 > 0)
        
        # --- 新增技術面 3 條件 ---
        # 條件 6: KD 黃金交叉 (用 9 日 RSV 計算)
        high_9 = high_px.rolling(9).max()
        low_9 = low_px.rolling(9).min()
        rsv = (close_px - low_9) / (high_9 - low_9) * 100
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        cond6 = (k.iloc[-1] > d.iloc[-1]) and (k.iloc[-2] <= d.iloc[-2])
        
        # 條件 7: 周線站上 MA20 (以日線的 100 日均線作為代理)
        ma100 = close_px.rolling(100).mean().iloc[-1]
        cond7 = curr_c > ma100
        
        # 條件 8: 跳空缺口 (今天的最低價 > 昨天的最高價)
        cond8 = float(low_px.iloc[-1]) > float(high_px.iloc[-2])
        
        # --- 新增進階資料 (暫未接 API，預留欄位) ---
        cond9 = False  # 高融券軋空
        cond10 = False # 內部人大買
        cond11 = False # 營收雙增/轉盈
        
        # 總分滿分現在是 11 分！
        score = sum([cond1, cond2, cond3, cond4, cond5, cond6, cond7, cond8, cond9, cond10, cond11])
        
        # 由於條件變多，我們把上榜門檻設為 3 分以上
        if score >= 3:
            met = []
            if cond1: met.append("均線糾結")
            if cond2: met.append("極致量縮")
            if cond3: met.append("帶量突破")
            if cond4: met.append("外資連買3天")
            if cond5: met.append("法人今日同買")
            if cond6: met.append("KD黃金交叉")
            if cond7: met.append("站上20周線")
            if cond8: met.append("跳空缺口")
            
            results.append({
                "更新日期": datetime.now().strftime("%Y-%m-%d"),
                "股票代號": code, "股票名稱": name, "最新收盤價": round(curr_c, 2),
                "總分": score, "符合條件": "、".join(met)
            })
            
    except Exception as e:
        continue

pd.DataFrame(results).sort_values(by='總分', ascending=False).to_csv("daily_stock_score.csv", index=False, encoding='utf-8-sig')
print(f"🎉 掃描完成！共過濾出 {len(results)} 檔潛力股。")
