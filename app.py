import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

# 1. CONFIGURAÇÃO E ESTILO DE ALTO NÍVEL
st.set_page_config(page_title="ERP Marketplace Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    [data-testid="stMetricValue"] { color: #bf40bf !important; font-weight: bold; }
    .stButton>button { 
        background: linear-gradient(45deg, #6a0dad, #bf40bf); 
        color: white; border-radius: 8px; border: none; font-weight: bold; transition: 0.3s; width: 100%;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0px 0px 15px #bf40bf; }
    h1, h2, h3 { color: #bf40bf; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stProgress > div > div > div > div { background-image: linear-gradient(to right, #6a0dad , #bf40bf); }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #bf40bf; }
    .stTabs [aria-selected="true"] { background-color: #bf40bf !important; color: white !important; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXÃO COM BANCO DE DADOS (GOOGLE SHEETS)
conn = st.connection("gsheets", type=GSheetsConnection)

def load_all_data():
    # Carrega Estoque
    estoque = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
    # Carrega Vendas com proteção
    try:
        vendas = conn.read(worksheet="Vendas", ttl=0).dropna(how="all")
    except:
        vendas = pd.DataFrame(columns=["Data", "Produto", "Custo", "Venda", "Lucro"])
    return estoque, vendas

df_estoque, df_vendas = load_all_data()

# 3. SIDEBAR - ENTRADA DE MERCADORIA
st.sidebar.title("💜 Gestão de Entrada")
with st.sidebar.form("form_cadastro", clear_on_submit=True):
    st.subheader("📦 Novo Lote")
    nome = st.text_input("Nome do Produto")
    custo = st.number_input("Custo Unitário (R$)", min_value=0.0, step=0.01)
    qtd = st.number_input("Quantidade Comprada", min_value=1, step=1)
    
    st.markdown("---")
    metodo = st.radio("Definição de Preço:", ["Margem Desejada (%)", "Preço Manual (R$)"])
    
    if metodo == "Margem Desejada (%)":
        margem_add = st.number_input("Quanto quer somar de margem? (%)", min_value=0.0, value=50.0)
        venda_calc = custo * (1 + margem_add/100)
        st.info(f"Preço de Venda será: R$ {venda_calc:.2f}")
        margem_final = margem_add
    else:
        venda_calc = st.number_input("Preço de Venda Final", min_value=0.0, step=0.01)
        margem_final = ((venda_calc - custo) / venda_calc * 100) if venda_calc > 0 else 0.0

    if st.form_submit_button("✅ CADASTRAR NO ESTOQUE"):
        if nome and venda_calc > 0:
            novo_item = pd.DataFrame([{
                "Produto": nome, "Custo": custo, "Margem_%": round(margem_final, 2),
                "Preco_Venda": venda_calc, "Qtd_Estoque": qtd, "Vendas_Realizadas": 0
            }])
            df_atualizado = pd.concat([df_estoque, novo_item], ignore_index=True)
            conn.update(worksheet="Página1", data=df_atualizado)
            st.cache_data.clear()
            st.success("Produto salvo na nuvem!")
            st.rerun()
        else:
            st.error("Preencha nome e valor corretamente.")

# 4. PAINEL PRINCIPAL
tab1, tab2, tab3, tab4 = st.tabs(["📊 DASHBOARD", "🛒 VENDER", "📦 ESTOQUE & EXTRATOS", "⚙️ CONFIGS"])

with tab1:
    st.title("🚀 Business Intelligence")
    if not df_vendas.empty:
        # Métricas de topo
        rec_total = df_vendas['Venda'].sum()
        lucro_total = df_vendas['Lucro'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Faturamento Total", f"R$ {rec_total:.2f}")
        c2.metric("Lucro Líquido", f"R$ {lucro_total:.2f}")
        c3.metric("Ticket Médio", f"R$ {df_vendas['Venda'].mean():.2f}")

        # Gráficos
        col_a, col_b = st.columns(2)
        with col_a:
            fig_evol = px.line(df_vendas, x="Data", y="Lucro", title="Evolução do Lucro", color_discrete_sequence=['#bf40bf'])
            st.plotly_chart(fig_evol, use_container_width=True)
        with col_b:
            lucro_prod = df_vendas.groupby("Produto")["Lucro"].sum().reset_index()
            fig_bar = px.bar(lucro_prod, x="Produto", y="Lucro", title="Lucro por Produto", color="Lucro", color_continuous_scale='Purples')
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Nenhuma venda registrada para gerar gráficos.")

with tab2:
    st.subheader("🛍️ Registrar Saída de Produto")
    if not df_estoque.empty:
        p_venda = st.selectbox("O que você vendeu?", df_estoque['Produto'].unique())
        if st.button("💰 CONFIRMAR VENDA"):
            idx = df_estoque[df_estoque['Produto'] == p_venda].index[0]
            if df_estoque.at[idx, 'Qtd_Estoque'] > 0:
                # Atualiza estoque localmente
                df_estoque.at[idx, 'Qtd_Estoque'] -= 1
                df_estoque.at[idx, 'Vendas_Realizadas'] += 1
                
                # Registra venda
                nova_venda = pd.DataFrame([{
                    "Data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Produto": p_venda,
                    "Custo": df_estoque.at[idx, 'Custo'],
                    "Venda": df_estoque.at[idx, 'Preco_Venda'],
                    "Lucro": df_estoque.at[idx, 'Preco_Venda'] - df_estoque.at[idx, 'Custo']
                }])
                
                conn.update(worksheet="Página1", data=df_estoque)
                conn.update(worksheet="Vendas", data=pd.concat([df_vendas, nova_venda], ignore_index=True))
                st.cache_data.clear()
                st.balloons()
                st.rerun()
            else:
                st.error("Produto sem estoque!")

with tab3:
    st.subheader("📂 Gerenciamento de Dados")
    
    # GERENCIAR ESTOQUE
    st.write("### 📦 Estoque Atual")
    if not df_estoque.empty:
        df_edit_est = df_estoque.copy()
        df_edit_est.insert(0, "Excluir", False)
        sel_est = st.data_editor(df_edit_est, use_container_width=True, hide_index=True, key="editor_estoque")
        if st.button("🗑️ Remover Produtos Selecionados"):
            indices = sel_est[sel_est["Excluir"] == False].index
            conn.update(worksheet="Página1", data=df_estoque.loc[indices])
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")
    
    # GERENCIAR VENDAS
    st.write("### 💸 Extrato de Vendas")
    if not df_vendas.empty:
        df_edit_ven = df_vendas.copy()
        df_edit_ven.insert(0, "Excluir", False)
        sel_ven = st.data_editor(df_edit_ven, use_container_width=True, hide_index=True, key="editor_vendas")
        if st.button("🗑️ Remover Vendas Selecionadas"):
            indices_v = sel_ven[sel_ven["Excluir"] == False].index
            conn.update(worksheet="Vendas", data=df_vendas.loc[indices_v])
            st.cache_data.clear()
            st.rerun()

with tab4:
    st.subheader("⚙️ Configurações & Segurança")
    
    meta = st.number_input("Definir Meta de Lucro (R$)", value=2000.0)
    if st.button("Salvar Meta"):
        st.session_state['meta_vendas'] = meta
        st.success("Meta atualizada!")

    st.markdown("---")
    st.write("#### ⚠️ Zona de Perigo")
    if st.button("🔥 LIMPAR TODO O SISTEMA (RESET)"):
        empty_est = pd.DataFrame(columns=["Produto", "Custo", "Margem_%", "Preco_Venda", "Qtd_Estoque", "Vendas_Realizadas"])
        empty_ven = pd.DataFrame(columns=["Data", "Produto", "Custo", "Venda", "Lucro"])
        conn.update(worksheet="Página1", data=empty_est)
        conn.update(worksheet="Vendas", data=empty_ven)
        st.cache_data.clear()
        st.rerun()