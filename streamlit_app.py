import streamlit as st
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd

# --- Настройка страницы ---
st.set_page_config(
    layout="wide",
    page_title="SonoScape - Управление ремонтами",
    page_icon="🔧"
)

# --- Стили для таблицы ---
st.markdown("""
<style>
    .ag-root-wrapper {
        height: 70vh !important;
        min-height: 400px !important;
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
    df = pd.DataFrame(repairs.data)
    return df

def main():
    st.title("📋 Таблица ремонтов SonoScape")

    df = load_data()

    # Удаление колонок id и user_id
    df = df.drop(columns=["id", "user_id"], errors="ignore")

    # Поиск по серийному номеру
    search_term = st.text_input("🔍 Поиск по серийному номеру:", key="serial_search")
    if search_term and 'serial1' in df.columns:
        df = df[df['serial1'].str.contains(search_term, case=False, na=False)]

    # Настройка таблицы
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(enabled=False)
    gb.configure_default_column(flex=1, wrapText=True, autoHeight=True)

    grid_options = gb.build()
    grid_options["suppressScrollOnNewData"] = True
    grid_options["alwaysShowVerticalScroll"] = True
    grid_options["domLayout"] = "autoHeight"

    table_height = min(800, 35 * len(df) if len(df) > 0 else 400)

    AgGrid(
        df,
        gridOptions=grid_options,
        fit_columns_on_grid_load=True,
        theme="streamlit",
        height=table_height,
        allow_unsafe_jscode=True,
        reload_data=True,
        key="main_table"
    )

    st.info(f"Всего записей: {len(df)}")

if __name__ == "__main__":
    main()
