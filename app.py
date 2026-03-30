import streamlit as st
import pandas as pd

st.set_page_config(page_title="台股主力起漲監測", layout="wide")
st.title("🔥 雲端主力起漲評分系統 (10 條件版)")

with st.expander("📚 點我看本系統的 10 大選股條件說明", expanded=True):
    st.markdown("""
    **✅ 絕對門檻：** 5 日平均成交量必須 > 1,000 張。
    **📊 技術面：** 1.均線糾結、2.極致量縮、3.帶量突破、6.KD金叉、7.站上20周線、8.跳空缺口。
    **💰 籌碼面：** 4.外資連買3天、5.法人今日同買。
    **🚀 進階面 (本機導入)：** 🔥9.高融券軋空、🔥10.營收年月雙增。
    """)

CSV_URL = "https://raw.githubusercontent.com/hong-yi-05/MyStockBot/refs/heads/main/daily_stock_score.csv"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        return df
    except:
        return None

df = load_data()

if df is not None and not df.empty:
    st.success(f"📅 目前資料日期：{df['更新日期'].iloc[0]}")
    
    # 按照總分分區顯示
    st.markdown("### 🏆 S級極品 (6 分以上)")
    df_s = df[df['總分'] >= 6]
    st.dataframe(df_s.drop(columns=['更新日期']), use_container_width=True)
    
    st.markdown("### 🔥 A級潛力 (4-5 分)")
    df_a = df[(df['總分'] >= 4) & (df['總分'] <= 5)]
    st.dataframe(df_a.drop(columns=['更新日期']), use_container_width=True)
    
    st.markdown("### 👀 B級觀察 (3 分)")
    df_b = df[df['總分'] == 3]
    st.dataframe(df_b.drop(columns=['更新日期']), use_container_width=True)
else:
    st.info("⏳ 待雲端計算完成後顯示...")
