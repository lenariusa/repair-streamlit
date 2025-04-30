import streamlit as st
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd

# Растянуть страницу на всю ширину
st.set_page_config(layout="wide")

# Загрузка секретов
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

# Подключение к Supabase
supabase: Client = create_client(url, key)

# Получение данных
response = supabase.table("repairs").select("*").execute()
data = response.data

# Преобразуем в DataFrame
df = pd.DataFrame(data)

# Заголовок
st.title("📋 Таблица ремонтов")

if not df.empty:
    # Поиск
    search = st.text_input("🔍 Поиск по серийному номеру (serial1):")
    if search:
        df = df[df["serial1"].str.contains(search, case=False, na=False)]

    # Настройка таблицы
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, editable=False)
    gb.configure_side_bar()
    gb.configure_selection("single")
    gb.configure_grid_options(domLayout='autoHeight')  # автоматическая высота
    grid_options = gb.build()

    # Вывод таблицы на всю ширину
    AgGrid(
        df,
        gridOptions=grid_options,
        fit_columns_on_grid_load=True,
        theme="streamlit",
        allow_unsafe_jscode=True,
        reload_data=True,
        height=600,  # можно убрать или увеличить
    )
else:
    st.warning("Нет данных в таблице repairs.")
