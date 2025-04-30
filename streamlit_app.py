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

# --- Стили для непрерывной прокрутки ---
st.markdown("""
<style>
    .ag-root-wrapper {
        height: 70vh !important;
        min-height: 400px !important;
    }
    .ag-body-viewport-wrapper {
        overflow-y: auto !important;
    }
    .ag-center-cols-viewport {
        overflow-y: visible !important;
        height: auto !important;
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

def main():
    st.title("📋 Таблица ремонтов SonoScape")
    
    df = load_data()
    df = df.drop(columns=['id', 'user_id'], errors='ignore')
    
    search_term = st.text_input("🔍 Поиск по серийному номеру:", key="serial_search")
    if search_term and 'serial1' in df.columns:
        df = df[df['serial1'].str.contains(search_term, case=False, na=False)]
    
    # Настройка таблицы с непрерывной прокруткой
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(enabled=False)  # Отключаем пагинацию полностью
    gb.configure_default_column(
        flex=1,
        wrapText=True,
        autoHeight=True
    )
    
    # Дополнительные настройки для непрерывной прокрутки
    grid_options = gb.build()
    grid_options["suppressScrollOnNewData"] = True
    grid_options["alwaysShowVerticalScroll"] = True
    grid_options["domLayout"] = "autoHeight"
    
    
    AgGrid(
        df,
        gridOptions=grid_options,
        fit_columns_on_grid_load=True,
        theme="streamlit",
        height=height,
        custom_css={
            ".ag-root-wrapper": {"overflow-y": "auto", "border": "none"},
            ".ag-body-viewport": {"overflow-y": "auto", "height": "auto"},
            ".ag-center-cols-viewport": {"overflow-y": "visible"}
        },
        key="main_table"
    )
    
    st.info(f"Всего записей: {len(df)}")

if __name__ == "__main__":
    main()
