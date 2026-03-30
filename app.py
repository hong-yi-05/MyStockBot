import streamlit as st
import pandas as pd

# 網頁標題
st.set_page_config(page_title="台股主力起漲監測", layout="wide")
st.title("🔥 雲端主力起漲評分系統")
st.markdown("🤖 本系統由雲端機器人自動分析，手機可直接查看。")

# 你的雲端資料路徑
CSV_URL = "https://raw.githubusercontent.com/hong-yi-05/MyStockBot/refs/heads/main/daily_stock_score.csv"

@st.cache_data(ttl=3600)
def load_data():
    try:
        return pd.read_csv(CSV_URL)
    except:
        return None

df = load_data()

if df is not None:
    update_time = df['更新日期'].iloc[0]
    st.success(f"📅 資料日期：{update_time}")
    
    # 分層顯示
    for score in [5, 4, 3, 2]:
        if score == 5: label = "🏆 S級 (5分)"
        elif score == 4: label = "🔥 A級 (4分)"
        else: label = f"👀 B級 ({score}分)"
        
        sub_df = df[df['總分'] == score]
        if not sub_df.empty:
            st.subheader(label)
            st.dataframe(sub_df.drop(columns=['更新日期']), use_container_width=True)
else:
    st.error("讀取資料失敗，請確認 GitHub 上的 CSV 檔是否存在。")
