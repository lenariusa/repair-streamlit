import streamlit as st
from supabase import create_client
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd
import base64

# --- Настройки страницы ---
st.set_page_config(
    layout="wide",
    page_title="SonoScape - Управление ремонтами",
    page_icon="🔧",
    initial_sidebar_state="expanded"
)

# --- Установка фонового изображения ---
def set_background(image_path):
    with open(image_path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode()
    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:image/png;base64,{encoded}");
            background-size: cover;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

set_background("A_digital_illustration_showcases_a_futuristic_medi.png")  # Название файла

# --- Кастомные стили SonoScape ---
st.markdown("""
<style>
/* Общий фон контейнеров */
.block-container {
    background-color: rgba(255, 255, 255, 0.85);
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 0 20px rgba(0,0,0,0.2);
    margin-top: 2rem;
}

/* Заголовки и шрифт */
h1, h2, h3 {
    color: #0073a7;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 600;
}

h1 {
    font-size: 30px;
    border-bottom: 2px solid #dcdcdc;
    padding-bottom: 0.5rem;
}

label, .stTextInput > div > div > input {
    font-family: 'Segoe UI', sans-serif;
    font-size: 16px;
}

/* Метрика */
[data-testid="stMetricValue"] {
    color: #0073a7;
}

/* Поисковая строка */
input[type="text"] {
    background-color: #ffffff;
    border-radius: 8px;
    padding: 8px;
}

/* Логотип */
.header-logo {
    height: 60px;
    margin-bottom: 10px;
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

# --- Основной интерфейс ---
def main():
    # Верхний блок с логотипом и заголовком
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image("https://www.sonoscape.com.cn/static/images/logo.png", width=130)
    with col2:
        st.title("Управление ремонтами SonoScape")

    # Фильтр поиска
    with st.container():
        st.markdown("### 🔍 Поиск")
        search_term = st.text_input("Введите серийный номер", key="search_input")

    # Загрузка данных
    df = load_data()
    df = df.drop(columns=['id', 'user_id'], errors='ignore')

    if search_term and 'serial1' in df.columns:
        df = df[df['serial1'].str.contains(search_term, case=False, na=False)]

    # Отображение таблицы
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        wrapText=True,
        autoHeight=True,
        resizable=True,
        sortable=True,
        filter=True
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

    # Статистика
    st.markdown("### 📊 Статистика")
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
