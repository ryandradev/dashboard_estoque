import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Estoque", layout="wide")

# Estilo Dark Roxo
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    [data-testid="stMetricValue"] { color: #bf40bf !important; }
    .stButton>button { background-color: #6a0dad; color: white; border-radius: 8px; border: none; }
    h1, h2, h3 { color: #bf40bf; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    </style>
    """, unsafe_allow_html=True)

# Conexão Nuvem
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# SIDEBAR
st.sidebar.header("💜 Gerenciar Estoque")
with st.sidebar.form("novo_prod", clear_on_submit=True):
    nome = st.text_input("Produto")
    custo = st.number_input("Custo (R$)", min_value=0.0)
    margem = st.number_input("Margem (%)", min_value=0.0, value=30.0)
    qtd = st.number_input("Estoque Inicial", min_value=0)
    venda = st.number_input("Preço Venda (R$)", value=float(custo * (1 + margem/100)))
    
    if st.form_submit_button("Cadastrar na Nuvem"):
        if nome:
            novo = pd.DataFrame([{"Produto": nome, "Custo": custo, "Margem_%": margem, "Preco_Sugerido": custo*(1+margem/100), "Preco_Venda": venda, "Qtd_Estoque": qtd, "Vendas_Realizadas": 0}])
            df = pd.concat([df, novo], ignore_index=True)
            conn.update(data=df)
            st.cache_data.clear()
            st.rerun()

# REMOVER
st.sidebar.markdown("---")
prod_del = st.sidebar.selectbox("Excluir:", ["-"] + list(df['Produto'].unique()) if not df.empty else ["-"])
if st.sidebar.button("Apagar Permanentemente"):
    if prod_del != "-":
        df = df[df['Produto'] != prod_del]
        conn.update(data=df)
        st.cache_data.clear()
        st.rerun()

# MÉTRICAS
st.title("🚀 Painel Vendas Online")
if not df.empty:
    invest = (df['Custo'] * (df['Qtd_Estoque'] + df['Vendas_Realizadas'])).sum()
    receita = (df['Preco_Venda'] * df['Vendas_Realizadas']).sum()
    lucro = ((df['Preco_Venda'] - df['Custo']) * df['Vendas_Realizadas']).sum()
    saldo = receita - invest
else:
    invest = receita = lucro = saldo = 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("📦 Estoque", f"{int(df['Qtd_Estoque'].sum()) if not df.empty else 0}")
c2.metric("💰 Investimento", f"R$ {invest:.2f}")
c3.metric("📈 Lucro Bruto", f"R$ {lucro:.2f}")
c4.metric("⚖️ Saldo Real", f"R$ {saldo:.2f}")

# VENDAS
st.markdown("---")
col_v1, col_v2 = st.columns([2,1])
with col_v1:
    sel = st.selectbox("Vender item:", df['Produto'].unique() if not df.empty else ["-"])
with col_v2:
    st.write("##")
    if st.button("Confirmar Venda"):
        if not df.empty and sel in df['Produto'].values:
            idx = df[df['Produto'] == sel].index[0]
            if df.at[idx, 'Qtd_Estoque'] > 0:
                df.at[idx, 'Qtd_Estoque'] -= 1
                df.at[idx, 'Vendas_Realizadas'] += 1
                conn.update(data=df)
                st.cache_data.clear()
                st.toast("Venda registrada!")
                st.rerun()

st.subheader("📋 Tabela em Tempo Real")
st.dataframe(df, use_container_width=True)