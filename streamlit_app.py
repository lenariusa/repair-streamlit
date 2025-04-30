import streamlit as st
from supabase import create_client
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.shared import JsCode
import pandas as pd

# --- Настройка страницы ---
st.set_page_config(
    layout="wide",
    page_title="SonoScape - Управление ремонтами",
    page_icon="🔧"
)

# --- Стили в стиле SonoScape ---
st.markdown("""
<style>
body {
    background: linear-gradient(to right, #e8f0f7, #f5f9ff);
    font-family: 'Segoe UI', sans-serif;
}
h1 {
    color: #003f7f;
}
[data-testid="stAppViewContainer"] {
    background-color: #f4f9ff;
}
</style>
""", unsafe_allow_html=True)

# --- Подключение к Supabase ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

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

    # Настройка таблицы
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(wrapText=True, autoHeight=True)
    gb.configure_pagination(enabled=False)
    grid_options = gb.build()

    # Добавляем JS-код для стилизации строк
    row_style = JsCode("""
    function(params) {
        if (params.data.status === 'Готов') {
            return {'background': '#d4edda'};
        } else if (params.data.status === 'В работе') {
            return {'background': '#fff3cd'};
        }
        return {};
    }
    """)
    grid_options["getRowStyle"] = row_style

    AgGrid(
        df,
        gridOptions=grid_options,
        fit_columns_on_grid_load=True,
        theme="streamlit",
        height=min(800, 35 * len(df) if len(df) > 0 else 400),
        key="main_table"
    )

    st.info(f"Всего записей: {len(df)}")

if __name__ == "__main__":
    main()
