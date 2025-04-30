import streamlit as st
from supabase import create_client
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd

# --- Настройка страницы ---
st.set_page_config(layout="wide", page_title="SonoScape - Управление ремонтами", page_icon="🔧")

# --- Стили в стиле SonoScape ---
st.markdown("""
<style>
body {
    background: linear-gradient(to right, #e6f2ff, #f8fcff);
    font-family: 'Segoe UI', sans-serif;
}
[data-testid="stAppViewContainer"] {
    background-color: #f7fbff;
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
    st.title("📋 Таблица ремонтов SonoScape")

    df = load_data()
    df = df.drop(columns=['id', 'user_id'], errors='ignore')

    search_term = st.text_input("🔍 Поиск по серийному номеру:")
    if search_term and 'serial1' in df.columns:
        df = df[df['serial1'].str.contains(search_term, case=False, na=False)]

    # Добавляем столбец с цветом фона (опционально)
    def get_status_style(status):
        if status == "Готов":
            return {"backgroundColor": "#d4edda"}
        elif status == "В работе":
            return {"backgroundColor": "#fff3cd"}
        return {}

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(wrapText=True, autoHeight=True, resizable=True)

    # Пример: применить стиль к колонке "status"
    if "status" in df.columns:
        gb.configure_column(
            "status",
            cellStyle=lambda params: get_status_style(params["value"])
        )

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
