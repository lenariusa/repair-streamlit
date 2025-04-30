import streamlit as st
from supabase import create_client
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd

# --- Настройка страницы ---
st.set_page_config(layout="wide", page_title="SonoScape - Управление ремонтами", page_icon="🔧")

# --- Кастомные стили в стиле SonoScape ---
st.markdown("""
<style>
/* Фон с изображением */
[data-testid="stAppViewContainer"] {
    background-image: url("https://images.unsplash.com/photo-1581090700227-1e8e03b0d2fd?auto=format&fit=crop&w=1920&q=80");
    background-size: cover;
    background-position: center;
}

/* Полупрозрачный блок для контента */
[data-testid="stHeader"], .main, .block-container {
    background-color: rgba(255, 255, 255, 0.85);
    border-radius: 10px;
    padding: 1.5rem;
    backdrop-filter: blur(6px);
}

/* Шрифты и стили */
html, body, [class*="css"] {
    font-family: 'Segoe UI', sans-serif;
    color: #003366;
}

h1 {
    color: #003366;
    text-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

input, .stTextInput > div > div > input {
    border: 1px solid #cce0ff;
    border-radius: 8px;
    padding: 6px 10px;
    background-color: #f0f7ff;
}

/* Инфо-блок */
[data-testid="stMarkdownContainer"] .stAlert {
    background-color: #e0f0ff;
    border-left: 5px solid #007acc;
}

</style>
""", unsafe_allow_html=True)

# --- Подключение к Supabase ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# --- Загрузка данных ---
@st.cache_data(ttl=600)
def load_data():
    supabase = init_connection()
    repairs = supabase.table("repairs").select("*").execute()
    return pd.DataFrame(repairs.data)

# --- Основной код ---
def main():
    st.title("🔧 SonoScape — Управление ремонтами")

    df = load_data()
    df = df.drop(columns=['id', 'user_id'], errors='ignore')

    search_term = st.text_input("🔍 Поиск по серийному номеру:")
    if search_term and 'serial1' in df.columns:
        df = df[df['serial1'].str.contains(search_term, case=False, na=False)]

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(wrapText=True, autoHeight=True, resizable=True)
    grid_options = gb.build()

    AgGrid(
        df,
        gridOptions=grid_options,
        theme="streamlit",
        fit_columns_on_grid_load=True,
        height=min(800, 35 * len(df) if len(df) > 0 else 400),
        key="main_table"
    )

    st.info(f"Всего записей: {len(df)}")

if __name__ == "__main__":
    main()
