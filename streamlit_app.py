import streamlit as st
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd

# --- ДОЛЖЕН БЫТЬ ПЕРВЫМ ВЫЗОВОМ ---
st.set_page_config(
    layout="wide",
    page_title="SonoScape",
    page_icon="🔧"
)

# --- Настройка стиля под SonoScape ---
st.markdown("""
<style>
    /* Основные цвета SonoScape */
    :root {
        --sonoscape-blue: #005BAA;
        --sonoscape-orange: #FF6B00;
    }
    
    /* Стиль заголовка */
    .stTitle {
        color: var(--sonoscape-blue) !important;
        border-bottom: 2px solid var(--sonoscape-orange);
        padding-bottom: 10px;
    }
    
    /* Стиль кнопок и интерактивных элементов */
    .stButton>button {
        background-color: var(--sonoscape-blue) !important;
        color: white !important;
    }
    
    /* Стиль таблицы */
    .ag-theme-streamlit {
        font-family: Arial, sans-serif;
    }
    
    .ag-header-cell {
        background-color: var(--sonoscape-blue) !important;
        color: white !important;
    }
    
    /* Полоса прокрутки */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--sonoscape-blue);
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--sonoscape-orange);
    }
    
    /* Контейнер с фиксированной высотой и прокруткой */
    .fixed-container {
        height: 70vh;
        overflow-y: auto;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- Подключение к Supabase ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- Загрузка данных ---
@st.cache_data(ttl=600)
def load_repairs():
    return pd.DataFrame(supabase.table("repairs").select("*").execute().data)

df = load_repairs()

# --- Удаление ненужных столбцов ---
columns_to_drop = ['id', 'user_id']
df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])

# --- Заголовок с логотипом ---
col1, col2 = st.columns([1, 6])
with col1:
    st.image("https://www.sonoscape.com/images/logo.png", width=100)  # Замените на реальный URL логотипа
with col2:
    st.markdown("<h1 class='stTitle'>SonoScape - Система учёта ремонтов</h1>", unsafe_allow_html=True)

# --- Фильтры ---
with st.expander("🔍 Фильтры", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        serial_filter = st.text_input("Серийный номер:")
    with col2:
        status_filter = st.selectbox("Статус:", ["Все"] + list(df['status'].unique()))
    with col3:
        date_filter = st.date_input("Дата после:")

# --- Применение фильтров ---
if serial_filter:
    df = df[df['serial1'].str.contains(serial_filter, case=False, na=False)]
if status_filter != "Все":
    df = df[df['status'] == status_filter]
if date_filter:
    df = df[pd.to_datetime(df['date']) >= pd.to_datetime(date_filter)]

# --- Настройка AgGrid ---
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_pagination(paginationAutoPageSize=True)
gb.configure_default_column(
    groupable=True,
    value=True,
    enableRowGroup=True,
    editable=False,
    filterable=True
)

# Явное скрытие столбцов
for col in columns_to_drop:
    if col in df.columns:
        gb.configure_column(col, hide=True)

grid_options = gb.build()

# --- Отображение таблицы с прокруткой ---
st.markdown("<div class='fixed-container'>", unsafe_allow_html=True)
AgGrid(
    df,
    gridOptions=grid_options,
    fit_columns_on_grid_load=False,
    theme="streamlit",
    height=500,
    reload_data=True,
    custom_css={
        ".ag-root-wrapper": {"border": "1px solid var(--sonoscape-blue)"},
        ".ag-header": {"background-color": "var(--sonoscape-blue)"},
        ".ag-header-cell": {"color": "white !important"}
    }
)
st.markdown("</div>", unsafe_allow_html=True)

# --- Статус бар внизу ---
st.markdown(f"""
<div style="background-color: var(--sonoscape-blue); color: white; padding: 10px; border-radius: 5px; margin-top: 20px;">
    Всего записей: <strong>{len(df)}</strong> | Последнее обновление: <strong>{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}</strong>
</div>
""", unsafe_allow_html=True)
