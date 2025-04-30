import streamlit as st
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd

# Загрузка секретов
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

# Подключение к Supabase
supabase: Client = create_client(url, key)

# Получение данных из Supabase
response = supabase.table("repairs").select("*").execute()
data = response.data

# Преобразуем в DataFrame
df = pd.DataFrame(data)

# Заголовок
st.title("📋 Таблица ремонтов")

# Проверим, есть ли данные
if not df.empty:
    # Поиск по серийному номеру
    search = st.text_input("🔍 Поиск по серийному номеру (serial1):")
    if search:
        df = df[df["serial1"].str.contains(search, case=False, na=False)]

    # Настройка AgGrid
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationAutoPageSize=True)  # Автоматическая пагинация
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, editable=False)
    gb.configure_side_bar()  # Панель настроек справа
    gb.configure_selection("single")
    grid_options = gb.build()

    # Вывод таблицы
    AgGrid(
        df,
        gridOptions=grid_options,
        enable_enterprise_modules=False,
        fit_columns_on_grid_load=True,
        theme="streamlit",  # темы: "streamlit", "light", "dark", "blue", "fresh"
        allow_unsafe_jscode=True,
        reload_data=True,
    )
else:
    st.warning("Нет данных в таблице repairs.")
