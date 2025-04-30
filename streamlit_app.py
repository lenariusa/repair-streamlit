import streamlit as st
from supabase import create_client
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd

st.set_page_config(layout="wide", page_title="SonoScape - Управление ремонтами", page_icon="🔧")

# Стилизация страницы
st.markdown("""
<style>
body {
    background: linear-gradient(to right, #e8f0f7, #f5f9ff);
    font-family: 'Segoe UI', sans-serif;
}
[data-testid="stAppViewContainer"] {
    background-color: #f4f9ff;
}
</style>
""", unsafe_allow_html=True)

# Подключение к Supabase
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

    search_term = st.text_input("🔍 Поиск по серийному номеру:")
    if search_term and 'serial1' in df.columns:
        df = df[df['serial1'].str.contains(search_term, case=False, na=False)]

    # Добавляем столбец стилей
    def get_row_style(row):
        if row.get("status") == "Готов":
            return {"backgroundColor": "#d4edda"}
        elif row.get("status") == "В работе":
            return {"backgroundColor": "#fff3cd"}
        return {}

    # Применяем стили построчно
    styled_df = df.copy()
    styled_df["_style"] = [get_row_style(row) for _, row in df.iterrows()]

    # Настройки таблицы
    gb = GridOptionsBuilder.from_dataframe(styled_df.drop(columns=["_style"]))
    gb.configure_default_column(wrapText=True, autoHeight=True)
    grid_options = gb.build()

    # Добавляем стили
    grid_options["getRowStyle"] = {
        "function": """
        function(params) {
            if (params.data.status === 'Готов') {
                return {background: '#d4edda'};
            } else if (params.data.status === 'В работе') {
                return {background: '#fff3cd'};
            }
            return {};
        }
        """
    }

    AgGrid(
        styled_df.drop(columns=["_style"]),
        gridOptions=grid_options,
        theme="streamlit",
        fit_columns_on_grid_load=True,
        height=min(800, 35 * len(df) if len(df) > 0 else 400),
        key="main_table"
    )

    st.info(f"Всего записей: {len(df)}")

if __name__ == "__main__":
    main()
