import streamlit as st
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd

# Настройка страницы
st.set_page_config(layout="wide")

# Подключение к Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# Получение только данных о ремонтах
@st.cache_data(ttl=600)
def load_repairs():
    return pd.DataFrame(supabase.table("repairs").select("*").execute().data)

df = load_repairs()

# Удаляем ненужные столбцы
columns_to_drop = ['id', 'user_id']
df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])

# Настройка AgGrid с явным скрытием столбцов
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_pagination(paginationAutoPageSize=True)
gb.configure_default_column(
    groupable=True,
    value=True,
    enableRowGroup=True,
    editable=False
)

# Явно скрываем столбцы, если они вдруг остались
for col in columns_to_drop:
    if col in df.columns:
        gb.configure_column(col, hide=True)

grid_options = gb.build()

# Вывод таблицы
st.title("📋 Таблица ремонтов")
AgGrid(
    df,
    gridOptions=grid_options,
    fit_columns_on_grid_load=True,
    theme="streamlit",
    height=600,
    reload_data=True
)
