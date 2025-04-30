import streamlit as st
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd

# Растянуть страницу на всю ширину
st.set_page_config(layout="wide")

# Подключение к Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# Получение данных с кэшированием
@st.cache_data(ttl=600)
def load_data():
    repairs = supabase.table("repairs").select("*").execute().data
    users = supabase.table("users").select("id, full_name").execute().data
    return pd.DataFrame(repairs), pd.DataFrame(users)

df_repairs, df_users = load_data()

# Отладочный вывод
st.subheader("🔧 Исходные данные ремонтов:")
st.write(df_repairs.head(3))

st.subheader("👤 Исходные данные пользователей:")
st.write(df_users.head(3))

# Преобразование типов
df_repairs["user_id"] = df_repairs["user_id"].astype(str)
df_users["id"] = df_users["id"].astype(str)

# Объединение таблиц с явным удалением столбцов
if not df_repairs.empty and not df_users.empty:
    # Создаём копию перед merge
    df_merged = df_repairs.copy()
    
    # Выполняем merge
    df_merged = df_merged.merge(
        df_users, 
        left_on="user_id", 
        right_on="id", 
        how="left",
        suffixes=('', '_user')
    )
    
    # Удаляем ВСЕ технические столбцы
    cols_to_drop = ['id', 'user_id', 'id_user']
    df_merged = df_merged.drop(columns=[c for c in cols_to_drop if c in df_merged.columns])
    
    # Переименовываем
    df_merged = df_merged.rename(columns={"full_name": "ФИО"})
else:
    df_merged = df_repairs.copy()
    df_merged = df_merged.drop(columns=['id', 'user_id'], errors='ignore')

# Явно задаём порядок столбцов (без id и user_id)
desired_columns = [col for col in df_merged.columns if col not in ['id', 'user_id']]
df_merged = df_merged[desired_columns]

# Отладочный вывод
st.subheader("🔄 Результат после обработки:")
st.write(df_merged.head(3))

# Настройка AgGrid
gb = GridOptionsBuilder.from_dataframe(df_merged)
gb.configure_pagination(paginationAutoPageSize=True)
gb.configure_default_column(
    groupable=True,
    value=True,
    enableRowGroup=True,
    editable=False,
    suppressSizeToFit=True
)

# Явно скрываем технические столбцы
if 'id' in df_merged.columns:
    gb.configure_column('id', hide=True)
if 'user_id' in df_merged.columns:
    gb.configure_column('user_id', hide=True)

gb.configure_side_bar()
gb.configure_selection("single")
grid_options = gb.build()

# Вывод таблицы
st.title("📋 Итоговая таблица ремонтов")
AgGrid(
    df_merged,
    gridOptions=grid_options,
    fit_columns_on_grid_load=True,
    theme="streamlit",
    height=600,
    reload_data=True,
    key='repairs_grid'
)
