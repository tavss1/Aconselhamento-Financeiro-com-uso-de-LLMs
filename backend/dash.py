# Teste de visualização
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

df = pd.read_csv("C:/Users/Bruno/OneDrive/Área de Trabalho/Aconselhamento-Financeiro-com-uso-de-LLMs/backend/extrato_categorizados_final.csv")
df["date"] = pd.to_datetime(df["date"])
df["date"] = df["date"].dt.date  
df = df[df["Categoria"]!="Receitas"]
df = df.dropna(subset=['Categoria'])

def filter_date(df, dia, selected_categories):
    df_filtered = df.copy()
    
    if dia != "Todos os dias":
        df_filtered = df_filtered[df_filtered['date'] == dia]
    
    # Aplica filtro de categorias
    if selected_categories:
        df_filtered = df_filtered[df_filtered['Categoria'].isin(selected_categories)]

    return df_filtered

# Título do Dashboard
st.title("Dashboard de Finanças Pessoais")

# Filtros de date
st.sidebar.header("Filtros")

available_dias = ["Todos os dias"] + sorted(df["date"].unique().tolist())
dia = st.sidebar.selectbox("Filtrar por Dia", available_dias)

# Filtro de categoria
categories = df["Categoria"].unique().tolist()
selected_categories = st.sidebar.multiselect("Filtrar por Categorias", categories, default=categories)

df_filtered = filter_date(df, dia, selected_categories)


# ====================
c1, c2 = st.columns([0.6, 0.4])

# c1.subheader("Tabela de Finanças Filtradas")
c1.dataframe(df_filtered)
 

# c2.subheader("Distribuição de Categorias")
category_distribution = df_filtered.groupby("Categoria")["amount"].sum().reset_index()
fig = px.pie(category_distribution, values='amount', names='Categoria', 
            title='Distribuição por Categoria', hole=0.3
                )
c2.plotly_chart(fig, use_container_width=True)