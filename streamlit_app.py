import streamlit as st
import pandas as pd
import psycopg2
from docx import Document
from datetime import datetime
import os

TEMPLATE_PATH = "template.docx"
ACTS_DIR = "Акты"

st.set_page_config(page_title="Учёт ремонтов", layout="wide")

# Подключение к базе Supabase (PostgreSQL)
@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host="aws-0-eu-north-1.pooler.supabase.com",
        port="5432",
        dbname="postgres",
        user="postgres.njhjquehihrdauasqfvj",
        password="44238"
    )

conn = get_connection()

# Загрузка данных
@st.cache_data
def load_data():
    df = pd.read_sql("SELECT * FROM repairs", conn)
    return df.fillna("")

df = load_data()
st.title("📋 Учёт ремонтов")
st.dataframe(df, use_container_width=True)