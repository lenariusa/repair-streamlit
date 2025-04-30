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

# Выводим диагностику для проверки
st.subheader("📄 Исходные данные:")

st.write("🔧 Таблица repairs (ремонты):")
st.write(df_repairs)

st.write("👤 Таблица users (пользователи):")
st.write(df_users)

# Проверка типов данных для user_id и id
st.write("Тип user_id в таблице repairs:", df_repairs["user_id"].dtype)
st.write("Тип id в таблице users:", df_users["id"].dtype)

# Приводим типы к строкам (если нужно)
df_repairs["user_id"] = df_repairs["user_id"].astype(str)
df_users["id"] = df_users["id"].astype(str)

# Заменим user_id на full_name
if not df_repairs.empty and not df_users.empty:
    # Объединяем таблицы по user_id и id
    df_merged = df_repairs.merge(df_users, left_on="user_id", right_on="id", how="left")
    
    # Убираем лишние столбцы (id и user_id)
    columns_to_drop = ["id_x", "id_y", "user_id"]
    df_merged.drop(columns=[col for col in columns_to_drop if col in df_merged.columns], inplace=True)
    
    # Переименовываем столбец full_name в ФИО
    df_merged.rename(columns={"full_name": "ФИО"}, inplace=True)
else:
    df_merged = df_repairs.copy()  # fallback, если нет данных
    # Удаляем столбцы id и user_id, если они есть
    df_merged.drop(columns=["id", "user_id"], inplace=True, errors='ignore')

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

    # Вывод таблицы на всю ширину
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
