import streamlit as st
import pandas as pd

st.set_page_config(page_title="台股主力起漲監測", layout="wide")
st.title("🔥 雲端主力起漲評分系統")
st.markdown("🤖 本系統由 GitHub 雲端機器人每日盤後自動分析全市場籌碼。")

# --- 新增：展開式的選股條件說明 ---
with st.expander("📚 點我看本系統的 5 大選股條件說明", expanded=False):
    st.markdown("""
    **技術面 (尋找蓄力起漲點)：**
    * 🎯 **1. 均線糾結**：5日、10日、20日、60日均線極度靠近 (差距 < 5%)，代表各天期成本一致，籌碼沉澱。
    * 📉 **2. 極致量縮**：近 5 日平均成交量 < 近 20 日平均成交量，代表浮額清洗乾淨，無人問津。
    * 🚀 **3. 帶量突破**：今日收盤漲幅 > 2%，成交量暴增 (大於 5 日均量 1.5 倍)，且一口氣站上所有均線。
    
    **籌碼面 (主力吃貨痕跡)：**
    * 💰 **4. 外資連買 3 天**：外資連續三個交易日皆為買超，代表有長線資金默默佈局。
    * 🤝 **5. 法人今日同買**：外資與投信「今天」同步買超，代表兩大法人達成共識，可能為主升段發動訊號。
    """)

# 你的 CSV 雲端網址
CSV_URL = "https://raw.githubusercontent.com/hong-yi-05/MyStockBot/refs/heads/main/daily_stock_score.csv"

@st.cache_data(ttl=3600)
def load_data():
    try:
        return pd.read_csv(CSV_URL)
    except:
        return None

df = load_data()

if df is not None and not df.empty:
    update_time = df['更新日期'].iloc[0]
    st.success(f"📅 目前顯示資料日期：{update_time}")
    
    for score in [5, 4, 3, 2]:
        if score == 5: label = "🏆 S級極品 (5項條件全滿)"
        elif score == 4: label = "🔥 A級潛力 (滿足 4 項條件)"
        elif score == 3: label = "👀 B級觀察 (滿足 3 項條件)"
        else: label = "🌱 C級醞釀 (滿足 2 項條件)"
        
        sub_df = df[df['總分'] == score]
        if not sub_df.empty:
            st.subheader(label)
            st.dataframe(sub_df.drop(columns=['更新日期']), use_container_width=True)
else:
    st.info("⏳ 雲端機器人正在努力計算中，或今日無符合條件之股票。請稍後重新整理網頁。")
