import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- 1. 直接從成功的「籌碼表」中萃取全市場名單 ---
def get_real_chip_data():
    print("正在抓取最新三大法人籌碼分布與股票清單...")
    # 不指定日期，證交所會自動回傳「最新一個交易日」的資料！(解決假日抓不到資料的問題)
    url = "https://www.twse.com.tw/rwd/zh/fund/T86?selectType=ALL&response=json"
    
    try:
        # 加上 verify=False 繞過 SSL 檢查
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        data = res.json()
        if data['stat'] == 'OK':
            df = pd.DataFrame(data['data'], columns=data['fields'])
            # 轉換數字格式
            df['外資'] = df['外陸資買賣超股數(不含外資自營商)'].str.replace(',', '').astype(float) / 1000
            df['投信'] = df['投信買賣超股數'].str.replace(',', '').astype(float) / 1000
            print(f"✅ 真實籌碼抓取成功！共取得 {len(df)} 檔股票資料。")
            return df
    except Exception as e:
        print(f"❌ 籌碼抓取失敗: {e}")
    return pd.DataFrame()

# --- 主程式 ---
chip_table = get_real_chip_data()
results = []

# 檢查是否成功抓到資料
if chip_table.empty:
    print("⚠️ 無法取得資料，使用備用名單測試。")
    stock_dict = {'2330.TW': '台積電', '2317.TW': '鴻海'}
    chip_table = pd.DataFrame([{'證券代號': '2330', '外資': 0, '投信': 0}])
else:
    # 🌟 魔法在這裡：直接把籌碼表變成我們要掃描的股票清單！
    stock_dict = {}
    for _, row in chip_table.iterrows():
        # 只過濾出 4 位數的正常股票代號
        if len(row['證券代號']) == 4:
            stock_dict[f"{row['證券代號']}.TW"] = row['證券名稱']

# 將表格的索引設定為代號，方便後面快速查詢
chip_table = chip_table.set_index('證券代號')

print(f"🚀 開始全市場掃描 (共 {len(stock_dict)} 檔)...")

count = 0
for ticker, name in stock_dict.items():
    code = ticker.replace('.TW', '')
    count += 1
    if count % 100 == 0: print(f"🔄 已分析 {count} 檔...")
    
    try:
        hist = yf.download(ticker, period="4mo", progress=False)
        if len(hist) < 60: continue # 資料不足 60 天跳過
        
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
        
        # 🔥 門檻設為 2 分，顯示更多觀察股
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
print(f"🎉 掃描完成！共過濾出 {len(results)} 檔潛力股。")
