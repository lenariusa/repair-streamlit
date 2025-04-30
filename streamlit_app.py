import streamlit as st
from supabase import create_client, Client

# Получение секретов из streamlit
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

# Создание клиента Supabase
supabase: Client = create_client(url, key)

# Получение данных из таблицы "repairs"
response = supabase.table("repairs").select("*").execute()
data = response.data

# Вывод данных в Streamlit
st.write("Данные из Supabase:")
st.write(data)
