import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. CONFIGURAÇÃO E ESTILO (ROXO DARK)
st.set_page_config(page_title="Dashboard Cloud Vendas", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    [data-testid="stMetricValue"] { color: #bf40bf !important; }
    .stButton>button { background-color: #6a0dad; color: white; border-radius: 8px; width: 100%; }
    h1, h2, h3 { color: #bf40bf; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXÃO COM GOOGLE SHEETS
# O link da planilha deve ser colocado no arquivo de segredos do Streamlit Cloud
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(ttl="0") # ttl=0 força o recarregamento dos dados reais

df = load_data()

# 3. SIDEBAR: CADASTRO E REMOÇÃO
st.sidebar.header("💜 Gerenciar Nuvem")

with st.sidebar.form("form_cadastro", clear_on_submit=True):
    st.subheader("Novo Produto")
    nome = st.text_input("Nome do Produto")
    custo = st.number_input("Custo Unitário (R$)", min_value=0.0, format="%.2f")
    margem = st.number_input("Margem (%)", min_value=0.0, value=30.0)
    qtd = st.number_input("Qtd Inicial", min_value=0)
    venda = st.number_input("Preço de Venda (R$)", value=float(custo * (1 + margem/100)))
    
    if st.form_submit_button("Salvar na Nuvem"):
        if nome:
            novo_item = pd.DataFrame([{
                "Produto": nome, "Custo": custo, "Margem_%": margem, 
                "Preco_Sugerido": custo*(1+margem/100), "Preco_Venda": venda, 
                "Qtd_Estoque": qtd, "Vendas_Realizadas": 0
            }])
            updated_df = pd.concat([df, novo_item], ignore_index=True)
            conn.update(data=updated_df)
            st.cache_data.clear()
            st.rerun()

st.sidebar.markdown("---")
prod_del = st.sidebar.selectbox("Excluir Item:", ["-"] + list(df['Produto'].unique()) if not df.empty else ["-"])
if st.sidebar.button("Excluir do Banco"):
    if prod_del != "-":
        updated_df = df[df['Produto'] != prod_del]
        conn.update(data=updated_df)
        st.cache_data.clear()
        st.rerun()

# 4. CÁLCULOS
if not df.empty:
    invest_total = (df['Custo'] * (df['Qtd_Estoque'] + df['Vendas_Realizadas'])).sum()
    receita_total = (df['Preco_Venda'] * df['Vendas_Realizadas']).sum()
    lucro_bruto = ((df['Preco_Venda'] - df['Custo']) * df['Vendas_Realizadas']).sum()
    saldo_recup = receita_total - invest_total
else:
    invest_total = receita_total = lucro_bruto = saldo_recup = 0.0

# 5. DASHBOARD
st.title("🚀 Vendas Marketplace (Nuvem)")

c1, c2, c3, c4 = st.columns(4)
c1.metric("📦 Estoque", f"{int(df['Qtd_Estoque'].sum()) if not df.empty else 0} un")
c2.metric("💰 Investimento", f"R$ {invest_total:.2f}")
c3.metric("📈 Lucro Bruto", f"R$ {lucro_bruto:.2f}")
c4.metric("⚖️ Saldo Real", f"R$ {saldo_recup:.2f}")

st.markdown("---")

# 6. REGISTRO DE VENDAS
cv1, cv2 = st.columns([2, 1])
with cv1:
    prod_sel = st.selectbox("Registrar Venda:", df['Produto'].unique() if not df.empty else ["-"])
with cv2:
    st.write("##")
    if st.button("Confirmar Venda (+1)"):
        if not df.empty and prod_sel in df['Produto'].values:
            idx = df[df['Produto'] == prod_sel].index[0]
            if df.at[idx, 'Qtd_Estoque'] > 0:
                df.loc[idx, 'Qtd_Estoque'] -= 1
                df.loc[idx, 'Vendas_Realizadas'] += 1
                conn.update(data=df)
                st.cache_data.clear()
                st.toast(f"Venda de {prod_sel} salva!")
                st.rerun()

st.subheader("📋 Tabela Online")
st.dataframe(df, width=2000)