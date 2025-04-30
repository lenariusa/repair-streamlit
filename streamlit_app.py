import streamlit as st
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd

# Растянуть страницу на всю ширину
st.set_page_config(layout="wide")

# Подключение к Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Получение данных
repairs_data = supabase.table("repairs").select("*").execute().data
users_data = supabase.table("users").select("id, full_name").execute().data

# Преобразуем в DataFrame
df_repairs = pd.DataFrame(repairs_data)
df_users = pd.DataFrame(users_data)

# Заменим user_id на full_name
if not df_repairs.empty and not df_users.empty:
    df_merged = df_repairs.merge(df_users, left_on="user_id", right_on="id", how="left")
    df_merged.drop(columns=["id_x", "user_id", "id_y"], inplace=True)
    df_merged.rename(columns={"full_name": "ФИО"}, inplace=True)
else:
    df_merged = df_repairs

# Заголовок
st.title("📋 Таблица ремонтов")

# Фильтр по серийному номеру
if not df_merged.empty:
    search = st.text_input("🔍 Поиск по серийному номеру (serial1):")
    if search:
        df_merged = df_merged[df_merged["serial1"].str.contains(search, case=False, na=False)]

    # Настройка таблицы
    gb = GridOptionsBuilder.from_dataframe(df_merged)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, editable=False)
    gb.configure_side_bar()
    gb.configure_selection("single")
    gb.configure_grid_options(domLayout='autoHeight')
    grid_options = gb.build()

    # Вывод таблицы
    AgGrid(
        df_merged,
        gridOptions=grid_options,
        fit_columns_on_grid_load=True,
        theme="streamlit",
        allow_unsafe_jscode=True,
        reload_data=True,
        height=600,
    )
else:
    st.warning("Нет данных для отображения.")
