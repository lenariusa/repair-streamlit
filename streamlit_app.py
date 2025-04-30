import streamlit as st
import pandas as pd
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder

# Настроим кастомный CSS
st.markdown("""
    <style>
        .big-font {
            font-size: 30px;
            color: #333;
            text-align: center;
        }
        .table-container {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
        }
    </style>
""", unsafe_allow_html=True)

# Заголовок страницы
st.markdown('<p class="big-font">Программа для учета ремонтов</p>', unsafe_allow_html=True)

# Пример данных для таблицы
data = {
    "ID": [1, 2, 3],
    "Серийный номер": ["SN001", "SN002", "SN003"],
    "Тип ремонта": ["B", "C", "D"],
    "Статус": ["Готов", "В ожидании", "Готов"],
    "Клиент": ["loaner", "demo", "client"]
}

df = pd.DataFrame(data)

# Настройка GridOptions для Ag-Grid
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_column("ID", hide=True)
gb.configure_column("Серийный номер", width=150)
gb.configure_column("Тип ремонта", width=120)
gb.configure_column("Статус", cellStyle={'color': 'green', 'fontWeight': 'bold'})
grid_options = gb.build()

# Отображаем таблицу в Streamlit
st.markdown('<div class="table-container">', unsafe_allow_html=True)
AgGrid(df, gridOptions=grid_options, height=300)
st.markdown('</div>', unsafe_allow_html=True)

# Добавим кнопку
if st.button('Добавить запись'):
    st.write("Добавить новую запись!")
