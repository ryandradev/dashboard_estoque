import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. CONFIGURAÇÃO E ESTILO
st.set_page_config(page_title="Gestão Marketplace Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    [data-testid="stMetricValue"] { color: #bf40bf !important; font-weight: bold; }
    .stButton>button { 
        background: linear-gradient(45deg, #6a0dad, #bf40bf); 
        color: white; border-radius: 10px; border: none; font-weight: bold; transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0px 0px 15px #bf40bf; }
    h1, h2, h3 { color: #bf40bf; }
    .stProgress > div > div > div > div { background-color: #bf40bf; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #bf40bf; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXÃO NUVEM
conn = st.connection("gsheets", type=GSheetsConnection)

# Função para carregar dados das duas abas
def get_data():
    estoque = conn.read(worksheet="Página1", ttl=0)
    try:
        vendas_hist = conn.read(worksheet="Vendas", ttl=0)
    except:
        vendas_hist = pd.DataFrame(columns=["Data", "Produto", "Custo", "Venda", "Lucro"])
    return estoque, vendas_hist

df_estoque, df_vendas = get_data()

# 3. SIDEBAR (COMPRAS)
st.sidebar.title("💜 Compras/Estoque")
with st.sidebar.form("novo_prod", clear_on_submit=True):
    nome = st.text_input("Nome do Produto")
    custo = st.number_input("Custo de Compra (R$)", min_value=0.0)
    margem = st.number_input("Margem (%)", min_value=0.0, value=30.0)
    qtd = st.number_input("Quantidade", min_value=1)
    venda_sug = float(custo * (1 + margem/100))
    venda_final = st.number_input("Preço de Venda Final (R$)", value=venda_sug)
    
    if st.form_submit_button("Cadastrar Compra"):
        if nome:
            novo = pd.DataFrame([{"Produto": nome, "Custo": custo, "Margem_%": margem, "Preco_Sugerido": venda_sug, "Preco_Venda": venda_final, "Qtd_Estoque": qtd, "Vendas_Realizadas": 0}])
            df_estoque = pd.concat([df_estoque, novo], ignore_index=True)
            conn.update(worksheet="Página1", data=df_estoque)
            st.cache_data.clear()
            st.rerun()

# 4. CORPO PRINCIPAL
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "💰 Registrar Venda", "📜 Extrato de Vendas"])

with tab1:
    st.title("🚀 Business Intelligence")
    if not df_estoque.empty:
        invest = (df_estoque['Custo'] * (df_estoque['Qtd_Estoque'] + df_estoque['Vendas_Realizadas'])).sum()
        receita = (df_estoque['Preco_Venda'] * df_estoque['Vendas_Realizadas']).sum()
        lucro_total = (df_vendas['Lucro'].sum()) if not df_vendas.empty else 0
        saldo = receita - invest
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Itens no Estoque", f"{int(df_estoque['Qtd_Estoque'].sum())}")
        c2.metric("💸 Investimento Total", f"R$ {invest:.2f}")
        c3.metric("📈 Lucro Realizado", f"R$ {lucro_total:.2f}")
        c4.metric("⚖️ Saldo Atual", f"R$ {saldo:.2f}", delta_color="normal")

        st.markdown("### 🎯 Meta de Lucro")
        meta = st.slider("Sua Meta", 100, 10000, 2000)
        prog = min(lucro_total/meta, 1.0) if meta > 0 else 0
        st.progress(prog)
        st.write(f"Você atingiu **{prog*100:.1f}%** da sua meta!")
    else:
        st.info("Aguardando dados...")

with tab2:
    st.subheader("🛒 Nova Venda")
    if not df_estoque.empty:
        prod_sel = st.selectbox("O que você vendeu?", df_estoque['Produto'].unique())
        if st.button("💰 CONFIRMAR VENDA"):
            idx = df_estoque[df_estoque['Produto'] == prod_sel].index[0]
            if df_estoque.at[idx, 'Qtd_Estoque'] > 0:
                # Atualiza Estoque
                df_estoque.at[idx, 'Qtd_Estoque'] -= 1
                df_estoque.at[idx, 'Vendas_Realizadas'] += 1
                
                # Registra no Extrato de Vendas
                nova_venda = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Produto": prod_sel,
                    "Custo": df_estoque.at[idx, 'Custo'],
                    "Venda": df_estoque.at[idx, 'Preco_Venda'],
                    "Lucro": df_estoque.at[idx, 'Preco_Venda'] - df_estoque.at[idx, 'Custo']
                }])
                df_vendas = pd.concat([df_vendas, nova_venda], ignore_index=True)
                
                # Salva ambos no Google Sheets
                conn.update(worksheet="Página1", data=df_estoque)
                conn.update(worksheet="Vendas", data=df_vendas)
                
                st.cache_data.clear()
                st.balloons()
                st.rerun()
    else:
        st.warning("Sem produtos cadastrados.")

with tab3:
    st.subheader("📜 Extrato Geral de Vendas")
    if not df_vendas.empty:
        st.write("Histórico detalhado de cada venda realizada:")
        # Inverte a ordem para mostrar as mais recentes primeiro
        st.dataframe(df_vendas.sort_index(ascending=False), use_container_width=True)
        
        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            st.info(f"Ticket Médio: R$ {df_vendas['Venda'].mean():.2f}")
        with col_ex2:
            st.success(f"Maior Lucro Único: R$ {df_vendas['Lucro'].max():.2f}")
    else:
        st.write("Nenhuma venda registrada ainda. Bora vender!")

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Limpar Erros (Reset Cache)"):
    st.cache_data.clear()
    st.rerun()