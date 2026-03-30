import streamlit as st
import pandas as pd

st.set_page_config(page_title="台股主力起漲監測", layout="wide")
st.title("🔥 雲端主力起漲評分系統 (Pro版)")
st.markdown("🤖 本系統自動過濾 **5日均量小於 1000 張** 的冷門股，並從全市場精選起漲潛力股。")

# --- 完整 11 項條件說明書 ---
with st.expander("📚 點我看本系統的 11 大選股條件說明", expanded=False):
    st.markdown("""
    **✅ 絕對門檻：** 5 日平均成交量必須 > 1,000 張，確保流動性充足。
    
    **📊 技術面 (尋找蓄力與表態)：**
    * **1. 均線糾結**：5/10/20/60 日均線差距 < 5%，籌碼極度沉澱。
    * **2. 極致量縮**：近 5 日均量 < 近 20 日均量，浮額清洗完畢。
    * **3. 帶量突破**：漲幅 > 2% 且成交量大於 5 日均量 1.5 倍，站上所有均線。
    * **6. KD 黃金交叉**：K值由下往上突破D值，短線轉強訊號。
    * **7. 周線站上 MA20**：股價站上 100 日均線(約20周)，確保中長線趨勢偏多。
    * **8. 跳空缺口**：今日最低價大於昨日最高價，買盤極度強勢不回補。
    
    **💰 籌碼面 (主力吃貨痕跡)：**
    * **4. 外資連買 3 天**：外資連續三個交易日皆為買超。
    * **5. 法人今日同買**：外資與投信「今天」同步買超。
    
    **🚀 終極數據 (目前API擴充中，預設不給分)：**
    * *9. 高融券軋空*：融券餘額暴增，強迫空軍買回停損。
    * *10. 內部人大買*：董監事低檔增持或實施庫藏股。
    * *11. 營收年月雙增*：基本面由虧轉盈或創歷史新高。
    """)

# 你的 CSV 雲端網址
CSV_URL = "https://raw.githubusercontent.com/hong-yi-05/MyStockBot/refs/heads/main/daily_stock_score.csv"

@st.cache_data(ttl=60) # 改成 60 秒快取，方便你測試
def load_data():
    try:
        return pd.read_csv(CSV_URL)
    except:
        return None

df = load_data()

if df is not None and not df.empty:
    update_time = df['更新日期'].iloc[0]
    st.success(f"📅 目前顯示資料日期：{update_time}")
    
    # 由於滿分變高，重新定義等級
    st.markdown("### 🏆 S級極品 (符合 6~8 項條件) - 完美起漲點")
    df_s = df[df['總分'] >= 6]
    if not df_s.empty:
        st.dataframe(df_s.drop(columns=['更新日期']), use_container_width=True)
    else:
        st.info("今日無 S 級股票。")
        
    st.markdown("### 🔥 A級潛力 (符合 4~5 項條件) - 強勢表態股")
    df_a = df[(df['總分'] == 4) | (df['總分'] == 5)]
    if not df_a.empty:
        st.dataframe(df_a.drop(columns=['更新日期']), use_container_width=True)
    else:
        st.info("今日無 A 級股票。")
        
    st.markdown("### 👀 B級觀察 (符合 3 項條件) - 蓄勢待發")
    df_b = df[df['總分'] == 3]
    if not df_b.empty:
        st.dataframe(df_b.drop(columns=['更新日期']), use_container_width=True)
    else:
        st.info("今日無 B 級股票。")

else:
    st.info("⏳ 雲端機器人正在努力計算中，或今日無符合條件之股票。請稍後重新整理網頁。")
