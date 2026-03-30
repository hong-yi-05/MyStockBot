import streamlit as st
import pandas as pd

st.set_page_config(page_title="台股主力起漲監測", layout="wide")
st.title("🔥 雲端主力起漲評分系統 (10 條件版)")

with st.expander("📚 點我看本系統的 10 大選股條件說明"):
    st.markdown("""
    **✅ 絕對門檻：** 5 日平均成交量 > 1,000 張。
    **📊 技術面：** 1.均線糾結、2.極致量縮、3.帶量突破、6.KD金叉、7.站上20周線、8.跳空缺口。
    **💰 籌碼面：** 4.外資連買、5.法人同買。
    **🚀 進階面 (本機導入)：** 9.高融券軋空、10.營收年月雙增。
    """)

CSV_URL = "https://raw.githubusercontent.com/hong-yi-05/MyStockBot/refs/heads/main/daily_stock_score.csv"

@st.cache_data(ttl=60)
def load_data():
    try: return pd.read_csv(CSV_URL)
    except: return None

df = load_data()
if df is not None and not df.empty:
    st.success(f"📅 資料日期：{df['更新日期'].iloc[0]}")
    st.markdown("### 🏆 S級 (6分以上) | 🔥 A級 (4-5分) | 👀 B級 (3分)")
    st.dataframe(df.drop(columns=['更新日期']), use_container_width=True)
else:
    st.info("⏳ 待雲端計算完成後顯示...")
