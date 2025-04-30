import streamlit as st
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd

# --- Настройка страницы (должен быть первым) ---
st.set_page_config(
    layout="wide",
    page_title="SonoScape - Управление ремонтами",
    page_icon="🔧"
)

# --- Стили для прокрутки ---
st.markdown("""
<style>
    .ag-theme-streamlit {
        height: 70vh !important;
        overflow-y: auto !important;
    }
    .ag-body-viewport {
        overflow-y: auto !important;
    }
    .ag-center-cols-viewport {
        overflow-y: auto !important;
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

# --- Основная функция ---
def main():
    # Заголовок
    st.title("📋 Таблица ремонтов SonoScape")
    
    # Загрузка данных
    df = load_data()
    
    # Удаление ненужных столбцов
    df = df.drop(columns=['id', 'user_id'], errors='ignore')
    
    # Поиск по серийному номеру
    search_term = st.text_input("🔍 Поиск по серийному номеру:", key="serial_search")
    
    if search_term and 'serial1' in df.columns:
        df = df[df['serial1'].str.contains(search_term, case=False, na=False)]
    
    # Настройка таблицы с фиксированной высотой
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationAutoPageSize=False)  # Отключаем встроенную пагинацию
    gb.configure_default_column(
        groupable=True,
        value=True,
        enableRowGroup=True,
        editable=False,
        wrapText=True,
        autoHeight=True
    )
    
    # Настройка высоты таблицы
    grid_options = gb.build()
    grid_options['alwaysShowVerticalScroll'] = True
    grid_options['suppressScrollOnNewData'] = True
    
    # Отображение таблицы с прокруткой
    AgGrid(
        df,
        gridOptions=grid_options,
        fit_columns_on_grid_load=True,
        theme="streamlit",
        height=600,  # Фиксированная высота контейнера
        custom_css={
            ".ag-root-wrapper": {"overflow-y": "auto"},
            ".ag-body-viewport": {"overflow-y": "auto"},
            ".ag-center-cols-viewport": {"overflow-y": "auto"}
        },
        key="main_table"
    )
    
    # Статус бар
    st.info(f"Всего записей: {len(df)}")

# Запуск приложения
if __name__ == "__main__":
    main()
