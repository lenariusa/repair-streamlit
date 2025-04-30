import streamlit as st
from supabase import create_client
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd
import base64

# --- Настройка страницы ---
st.set_page_config(
    layout="wide", 
    page_title="SonoScape Future - Управление ремонтами", 
    page_icon="🔧",
    initial_sidebar_state="expanded"
)

# --- Кастомные стили в стиле SonoScape Future ---
def set_background(image_url):
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("{image_url}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Футуристичный фон (можно заменить на собственное изображение SonoScape)
set_background("https://images.unsplash.com/photo-1620712943543-bcc4688e7485?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=1920&q=80")

st.markdown("""
<style>
/* Основные стили */
[data-testid="stAppViewContainer"], .main, .block-container {
    background-color: rgba(0, 20, 40, 0.85) !important;
    color: #ffffff !important;
    border-radius: 15px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(0, 150, 255, 0.3);
    box-shadow: 0 8px 32px rgba(0, 80, 150, 0.3);
}

/* Заголовки */
h1, h2, h3, h4, h5, h6 {
    color: #00a0ff !important;
    font-weight: 600 !important;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

/* Текст */
[class*="css"], p, div {
    color: #e0f0ff !important;
}

/* Поля ввода */
.stTextInput>div>div>input, .stSelectbox>div>div>select {
    background-color: rgba(0, 40, 80, 0.7) !important;
    color: white !important;
    border: 1px solid #007acc !important;
    border-radius: 8px !important;
}

/* Кнопки */
.stButton>button {
    background-color: #007acc !important;
    color: white !important;
    border-radius: 8px !important;
    border: none !important;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
    transition: all 0.3s ease;
}

.stButton>button:hover {
    background-color: #00a0ff !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 120, 255, 0.3);
}

/* Таблицы */
.ag-theme-streamlit {
    --ag-background-color: rgba(0, 30, 60, 0.7) !important;
    --ag-foreground-color: #e0f0ff !important;
    --ag-border-color: rgba(0, 150, 255, 0.3) !important;
}

/* Инфо-блоки */
.stAlert {
    background-color: rgba(0, 80, 160, 0.5) !important;
    border-left: 5px solid #00a0ff !important;
}

/* Сайдбар */
[data-testid="stSidebar"] {
    background-color: rgba(0, 20, 40, 0.9) !important;
    border-right: 1px solid rgba(0, 150, 255, 0.2) !important;
}

/* Хедер */
[data-testid="stHeader"] {
    background-color: rgba(0, 0, 0, 0.3) !important;
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
    # Логотип и заголовок
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("https://via.placeholder.com/150x50/007ACC/FFFFFF?text=SonoScape", width=150)
    with col2:
        st.title("Управление ремонтами оборудования")

    # Поиск и фильтры в сайдбаре
    with st.sidebar:
        st.header("🔍 Фильтры")
        search_term = st.text_input("Поиск по серийному номеру:")
        status_filter = st.selectbox(
            "Статус ремонта",
            ["Все", "В работе", "Завершен", "Ожидает запчастей"]
        )
        st.markdown("---")
        st.markdown("**SonoScape Future**")
        st.markdown("v2.0.1")

    # Загрузка данных
    df = load_data()
    df = df.drop(columns=['id', 'user_id'], errors='ignore')

    # Применение фильтров
    if search_term and 'serial1' in df.columns:
        df = df[df['serial1'].str.contains(search_term, case=False, na=False)]
    
    if status_filter != "Все" and 'status' in df.columns:
        df = df[df['status'] == status_filter]

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
        key="main_table",
        custom_css={
            ".ag-header-cell-label": {"color": "#00a0ff"},
            ".ag-row-hover": {"background-color": "rgba(0, 160, 255, 0.1) !important"}
        }
    )

    # Статистика
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Всего записей", len(df))
    with col2:
        st.metric("В работе", len(df[df['status'] == "В работе"]) if 'status' in df.columns else "N/A")
    with col3:
        st.metric("Завершено", len(df[df['status'] == "Завершен"]) if 'status' in df.columns else "N/A")

if __name__ == "__main__":
    main()
