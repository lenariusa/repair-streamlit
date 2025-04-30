import streamlit as st
from supabase import create_client
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd

# --- Настройка страницы ---
st.set_page_config(
    layout="wide", 
    page_title="SonoScape - Управление ремонтами", 
    page_icon="🔧",
    initial_sidebar_state="expanded"
)

# --- Встроенные логотипы в base64 ---
def get_logo_base64(logo_type="main"):
    logos = {
        "main": "iVBORw0KGgoAAAANSUhEUgAAAMgAAAAyCAYAAAAZUZThAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAFkSURBVHgB7dixbcMwEAXQs0T6D5zBg7t0SJXKQ7p08OQhXTp48pAqGQJkCGDgA7IsiZQoUqQo8T0gkEiCxAcQlETyAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADwP9q2XQ3DcNq27XQcx9U4jqt5nlfjOK7meV7N87yapmk1TdNqHMfVMAyrvu9Xfd+vuq5bdV236rpu1bbtqm3bVdM0q6ZpVnVdr6qqWlVVtSrLclUUxaqiKFZ5nq+yLFtlabrK0nSVpukqSZJVEserOI5XURS9xXG8iqLoLYqiVRiGqzAMV2EYrsIwXIVhuArDcBUEwSoIglUQBKsgCFZBEKyCIFgFQbAKgmAVBMEqCIJVEASrIAhWQRCsgiBYBUGwCoJgFQTBKgiCVRAEqyAIVkEQrIIgWAVBsAqCYBUEwSoIglUQBKsgCFZBEKyCIFgFQbAKgmAVBMEqCIJVEASrIAhWQRCsgiBYBUGwCoJgFQTBKgiCVRAEqyAIVkEQrIIgWAVBsAqCYBUEwSoIglUQBKsgCFZBEKyCIFgFQbAKgmAVBMEqCIJVEASrIAhWQRCsgiBYBUGwCoJgFQTBKgiCVRAEqyAIVkEQrP4A0eYp9VjT0XQAAAAASUVORK5CYII=",
        "header": "iVBORw0KGgoAAAANSUhEUgAAAJYAAAAyCAYAAAC+jCIaAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAIiSURBVHgB7doxTsMwFAXQs8T9D5zBg7t0SJXKQ7p08OQhXTp48pAqGQJkCGDgA7IsiZQoUqQo8T0gkEiCxAcQlETyAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADwP9q2XQ3DcNq27XQcx9U4jqt5nlfjOK7meV7N87yapmk1TdNqHMfVMAyrvu9Xfd+vuq5bdV236rpu1bbtqm3bVdM0q6ZpVnVdr6qqWlVVtSrLclUUxaqiKFZ5nq+yLFtlabrK0nSVpukqSZJVEcerOI5XURS9xXG8iqLoLYqiVRiGqzAMV2EYrsIwXIVhuArDcBWE4SoIw1UQhqsgDFdBGK6CMFwFYbgKwnAVhOEqCMNVEIarIAxXQRiugjBcBWG4CsJwFYThKgjDVRCGqyAMV0EYroIwXAVhuArCcBWE4SoIw1UQhqsgDFdBGK6CMFwFYbgKwnAVhOEqCMNVEIarIAxXQRiugjBcBWG4CsJwFYThKgjDVRCGqyAMV0EYroIwXAVhuArCcBWE4SoIw1UQhqsgDFdBGK6CMFwFYbgKwnAVhOEqCMNVEIarIAxXQRiugjBcBWG4CsJwFYThKgjDVRCGqyAMV0EYroIwXAVhuArCcBWE4SoIw1UQhqsgDFdBGK6CMFwFYbgKwnAVhOEqCMNVEIarIAxXQRiugjBcBWG4CsJwFYThKgjDVRCGqyAMV0EYroIwXAVhuArCcBWE4SoIw1UQhqsgDFdBGK6CMFwFYbgKwnAVhOEqCMNVEIarIAxXQRiugjBcBWG4CsJwFYThKgjDVRCGqyAMV0EYroIwXAVhuArCcBWE4SoIw1UQhqsgDFdBGK6CMFwFYbgKwnAVhOEqCMNVEIarIAxXQRiugjBcBWG4CsJwFYThKgjDVRCGqyAMV0EYroIwXAVhuArCcBWE4SoIw1UQhqsgDFdBGK6CMFwFYbgKwnAVhOEqCMNVEIarIAxXQRiugjBcBWG4CsJwFYThKgjDVRCGqyAMV0EYroIwXAVhuArCcBWE4SoIw1UQhqsgDFdBGK6CMFwFYbgKwnAVhOEqCMNVEIarIAxXQRiugjBcBWG4CsJwFYThKgjDVRCGqyAMV0EYroIwXAVhuArCcBWE4SoIw1UQhqsgDFdBGK6CMFwFYbgKwnAVhOEqiP8BfQHlY2yqQZQAAAAASUVORK5CYII="
    }
    return logos.get(logo_type, "")

# --- Кастомные стили ---
st.markdown(f"""
<style>
/* Основные стили */
[data-testid="stAppViewContainer"] {{
    background-color: #f8f9fa;
}}

/* Логотип в заголовке */
.header-logo {{
    height: 50px;
    margin-right: 15px;
}}

/* Контейнеры контента */
.main, .block-container, [data-testid="stHorizontalBlock"] {{
    background-color: white;
    border-radius: 8px;
    padding: 2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 2rem;
}}

/* Заголовки */
h1, h2, h3 {{
    color: #005b9f;
    font-family: 'Arial', sans-serif;
    font-weight: 600;
    margin-bottom: 1rem;
}}

h1 {{
    font-size: 28px;
    border-bottom: 2px solid #e0e0e0;
    padding-bottom: 0.5rem;
}}

/* Остальные стили остаются как в предыдущем варианте */
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
    # Заголовок с логотипом
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("https://www.sonoscape.com.cn/static/images/logo.png", width=150)
    with col2:
        st.title("Управление ремонтами")
        
        """, unsafe_allow_html=True)

    # Фильтры вверху страницы
    with st.container():
        st.markdown('<div class="filter-container">', unsafe_allow_html=True)
        search_term = st.text_input("🔍 Поиск по серийному номеру:", key="search_input")
        st.markdown('</div>', unsafe_allow_html=True)

    # Загрузка данных
    df = load_data()
    df = df.drop(columns=['id', 'user_id'], errors='ignore')

    # Применение фильтров
    if search_term and 'serial1' in df.columns:
        df = df[df['serial1'].str.contains(search_term, case=False, na=False)]

    # Настройка таблицы
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        wrapText=True,
        autoHeight=True,
        resizable=True,
        sortable=True,
        filter=True
    )
    gb.configure_grid_options(domLayout='normal')
    grid_options = gb.build()

    # Отображение таблицы
    AgGrid(
        df,
        gridOptions=grid_options,
        theme="streamlit",
        fit_columns_on_grid_load=True,
        height=min(800, 35 * len(df) if len(df) > 0 else 400),
        key="main_table"
    )

    # Статистика
    st.markdown("### Статистика ремонтов")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Всего записей", len(df))
    with col2:
        in_progress = len(df[df['status'] == "В работе"]) if 'status' in df.columns else 0
        st.metric("В работе", in_progress)
    with col3:
        ready = len(df[df['status'] == "Готов"]) if 'status' in df.columns else 0
        st.metric("Готово", ready)

if __name__ == "__main__":
    main()
