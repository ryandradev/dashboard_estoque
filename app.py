import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

# 1. CONFIGURAÇÃO E ESTILO
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
    h1, h2, h3 { color: #bf40bf; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #bf40bf; }
    .stTabs [aria-selected="true"] { background-color: #bf40bf !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXÃO
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    estoque = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
    try:
        vendas = conn.read(worksheet="Vendas", ttl=0).dropna(how="all")
    except:
        vendas = pd.DataFrame(columns=["Data", "Produto", "Custo", "Venda", "Lucro"])
    return estoque, vendas

df_estoque, df_vendas = load_data()

# 3. SIDEBAR - CADASTRO (CORRIGIDO)
st.sidebar.title("🚀 Gestão de Entrada")

# Fora do form para permitir atualização dinâmica de cálculos
nome = st.sidebar.text_input("Nome do Produto")
custo = st.sidebar.number_input("Custo Unitário (R$)", min_value=0.0, step=0.01)
qtd = st.sidebar.number_input("Quantidade em Estoque", min_value=1, step=1)

st.sidebar.markdown("---")
metodo = st.sidebar.radio("Como quer definir o preço?", ["Margem Desejada (%)", "Preço Manual (R$)"])

venda_final = 0.0
margem_final = 0.0

if metodo == "Margem Desejada (%)":
    margem_input = st.sidebar.number_input("Margem que deseja adicionar (%)", min_value=0.0, value=50.0)
    venda_final = custo * (1 + margem_input/100)
    st.sidebar.write(f"💰 **Preço de Venda: R$ {venda_final:.2f}**")
    margem_final = margem_input
else:
    venda_final = st.sidebar.number_input("Digite o Preço de Venda (R$)", min_value=0.0, step=0.01)
    if venda_final > 0:
        margem_final = ((venda_final - custo) / venda_final) * 100
        st.sidebar.write(f"📈 **Margem Resultante: {margem_final:.2f}%**")

# Botão de cadastro isolado
if st.sidebar.button("✅ CADASTRAR PRODUTO"):
    if nome and venda_final > 0:
        novo_item = pd.DataFrame([{
            "Produto": nome, "Custo": custo, "Margem_%": round(margem_final, 2),
            "Preco_Venda": round(venda_final, 2), "Qtd_Estoque": qtd, "Vendas_Realizadas": 0
        }])
        df_atualizado = pd.concat([df_estoque, novo_item], ignore_index=True)
        conn.update(worksheet="Página1", data=df_atualizado)
        st.cache_data.clear()
        st.success("Salvo com sucesso!")
        st.rerun()
    else:
        st.sidebar.error("Preencha os dados corretamente!")

# 4. DASHBOARD
tab1, tab2, tab3, tab4 = st.tabs(["📊 DASHBOARD", "🛒 VENDER", "📦 ESTOQUE & EXTRATOS", "⚙️ CONFIGS"])

with tab1:
    st.title("🚀 Business Intelligence")
    if not df_vendas.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Receita Total", f"R$ {df_vendas['Venda'].sum():.2f}")
        c2.metric("Lucro Líquido", f"R$ {df_vendas['Lucro'].sum():.2f}")
        c3.metric("Vendas (Qtd)", len(df_vendas))

        col_a, col_b = st.columns(2)
        with col_a:
            fig_evol = px.line(df_vendas, x="Data", y="Lucro", title="Evolução do Lucro", color_discrete_sequence=['#bf40bf'])
            st.plotly_chart(fig_evol, use_container_width=True)
        with col_b:
            lucro_prod = df_vendas.groupby("Produto")["Lucro"].sum().reset_index()
            fig_bar = px.bar(lucro_prod, x="Produto", y="Lucro", title="Lucro por Produto", color="Lucro", color_continuous_scale='Purples')
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Sem vendas registradas.")

with tab2:
    st.subheader("🛍️ Registrar Venda")
    if not df_estoque.empty:
        p_sel = st.selectbox("Escolha o produto:", df_estoque['Produto'].unique())
        if st.button("💰 CONFIRMAR VENDA"):
            idx = df_estoque[df_estoque['Produto'] == p_sel].index[0]
            if df_estoque.at[idx, 'Qtd_Estoque'] > 0:
                df_estoque.at[idx, 'Qtd_Estoque'] -= 1
                df_estoque.at[idx, 'Vendas_Realizadas'] += 1
                
                nova_venda = pd.DataFrame([{
                    "Data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Produto": p_sel, "Custo": df_estoque.at[idx, 'Custo'],
                    "Venda": df_estoque.at[idx, 'Preco_Venda'],
                    "Lucro": df_estoque.at[idx, 'Preco_Venda'] - df_estoque.at[idx, 'Custo']
                }])
                conn.update(worksheet="Página1", data=df_estoque)
                conn.update(worksheet="Vendas", data=pd.concat([df_vendas, nova_venda], ignore_index=True))
                st.cache_data.clear()
                st.balloons()
                st.rerun()

with tab3:
    st.subheader("📂 Gerenciamento de Estoque e Vendas")
    
    # ESTOQUE COM OPÇÃO DE EXCLUIR
    st.write("### 📦 Itens em Estoque")
    if not df_estoque.empty:
        df_edit_est = df_estoque.copy()
        df_edit_est.insert(0, "Selecionar para Excluir", False)
        sel_est = st.data_editor(df_edit_est, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Remover Produtos Selecionados"):
            manter = sel_est[sel_est["Selecionar para Excluir"] == False].index
            df_final = df_estoque.loc[manter]
            conn.update(worksheet="Página1", data=df_final)
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")
    
    # VENDAS COM OPÇÃO DE EXCLUIR
    st.write("### 💸 Histórico de Vendas")
    if not df_vendas.empty:
        df_edit_ven = df_vendas.copy()
        df_edit_ven.insert(0, "Selecionar para Excluir", False)
        sel_ven = st.data_editor(df_edit_ven, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Remover Vendas Selecionadas"):
            manter_v = sel_ven[sel_ven["Selecionar para Excluir"] == False].index
            df_final_v = df_vendas.loc[manter_v]
            conn.update(worksheet="Vendas", data=df_final_v)
            st.cache_data.clear()
            st.rerun()

with tab4:
    st.subheader("⚙️ Configurações Profissionais")
    st.write("#### 🎯 Meta de Lucro")
    meta = st.number_input("Meta Mensal (R$)", value=2000.0)
    
    st.markdown("---")
    st.write("#### ⚠️ Reset Total")
    if st.button("🔥 APAGAR TUDO E RECOMEÇAR"):
        e_est = pd.DataFrame(columns=["Produto", "Custo", "Margem_%", "Preco_Venda", "Qtd_Estoque", "Vendas_Realizadas"])
        e_ven = pd.DataFrame(columns=["Data", "Produto", "Custo", "Venda", "Lucro"])
        conn.update(worksheet="Página1", data=e_est)
        conn.update(worksheet="Vendas", data=e_ven)
        st.cache_data.clear()
        st.rerun()