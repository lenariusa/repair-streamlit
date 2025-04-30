import streamlit as st
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd

# --- Инициализация страницы (должен быть первым) ---
st.set_page_config(
    layout="wide",
    page_title="SonoScape - Управление ремонтами",
    page_icon="🔧"
)

# --- Инициализация соединения ---
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

# --- Основная функция приложения ---
def main():
    # Загрузка данных
    df = load_data()
    
    # Удаление ненужных столбцов
    columns_to_drop = ['id', 'user_id']
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])
    
    # Заголовок
    st.title("📋 Таблица ремонтов SonoScape")
    
    # Фильтры (уникальные ключи для каждого элемента)
    with st.expander("🔍 Фильтры", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            serial_filter = st.text_input("Серийный номер:", key="serial_filter")
        with col2:
            status_options = ["Все"] + (list(df['status'].unique()) if 'status' in df.columns else [])
            status_filter = st.selectbox("Статус:", status_options, key="status_filter")
        with col3:
            date_filter = st.date_input("Дата после:", key="date_filter")
            date_columns = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]
            date_column = st.selectbox("Столбец даты:", date_columns, key="date_column") if date_columns else None
    
    # Применение фильтров
    if not df.empty:
        if serial_filter and 'serial1' in df.columns:
            df = df[df['serial1'].str.contains(serial_filter, case=False, na=False)]
        
        if status_filter != "Все" and 'status' in df.columns:
            df = df[df['status'] == status_filter]
        
        if date_filter and date_column:
            try:
                df = df[pd.to_datetime(df[date_column]) >= pd.to_datetime(date_filter)]
            except Exception as e:
                st.warning(f"Ошибка фильтрации даты: {e}")
    
    # Настройка таблицы
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_default_column(
        groupable=True,
        value=True,
        enableRowGroup=True,
        editable=False,
        filterable=True
    )
    
    # Скрытие технических столбцов
    for col in columns_to_drop:
        if col in df.columns:
            gb.configure_column(col, hide=True)
    
    # Отображение таблицы
    AgGrid(
        df,
        gridOptions=gb.build(),
        fit_columns_on_grid_load=True,
        theme="streamlit",
        height=600,
        reload_data=True,
        key="repairs_table"
    )
    
    # Статус бар
    st.info(f"Всего записей: {len(df)} | Последнее обновление: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")

# Запуск приложения
if __name__ == "__main__":
    main()
