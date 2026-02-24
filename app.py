import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import plotly.express as px

# 1. CONFIGURAÇÃO E ESTILO
st.set_page_config(page_title="ERP Marketplace Pro v2", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    [data-testid="stMetricValue"] { color: #bf40bf !important; font-weight: bold; }
    .stButton>button { 
        background: linear-gradient(45deg, #6a0dad, #bf40bf); 
        color: white; border-radius: 8px; border: none; transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0px 0px 10px #bf40bf; }
    h1, h2, h3 { color: #bf40bf; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #bf40bf; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXÃO NUVEM
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    estoque = conn.read(worksheet="Página1", ttl=0).dropna(how="all")
    try:
        vendas = conn.read(worksheet="Vendas", ttl=0).dropna(how="all")
    except:
        vendas = pd.DataFrame(columns=["Data", "Produto", "Custo", "Venda", "Lucro"])
    return estoque, vendas

df_estoque, df_vendas = get_data()

# 3. SIDEBAR - CADASTRO COM MARGEM DINÂMICA
st.sidebar.title("🚀 Gestão de Entrada")
with st.sidebar.form("novo_prod", clear_on_submit=True):
    nome = st.text_input("Nome do Produto")
    custo = st.number_input("Custo Unitário (R$)", min_value=0.0, step=0.01)
    qtd = st.number_input("Quantidade em Estoque", min_value=1, step=1)
    
    st.markdown("---")
    tipo_preco = st.radio("Precificação", ["Margem Desejada (%)", "Preço Manual (R$)"])
    
    if tipo_preco == "Margem Desejada (%)":
        # ESPAÇO PARA DEFINIR A MARGEM QUE VOCÊ DESEJA ADICIONAR
        margem_input = st.number_input("Quanto de margem quer somar? (%)", min_value=0.0, value=50.0)
        venda_final = custo * (1 + margem_input/100)
        st.caption(f"Preço final calculado: R$ {venda_final:.2f}")
    else:
        venda_final = st.number_input("Preço de Venda Final", min_value=0.0, step=0.01)
        margem_input = ((venda_final - custo) / venda_final * 100) if venda_final > 0 else 0.0

    if st.form_submit_button("CADASTRAR NO SISTEMA"):
        if nome and venda_final > 0:
            novo = pd.DataFrame([{
                "Produto": nome, "Custo": custo, "Margem_%": round(margem_input, 2),
                "Preco_Venda": venda_final, "Qtd_Estoque": qtd, "Vendas_Realizadas": 0
            }])
            df_atualizado = pd.concat([df_estoque, novo], ignore_index=True)
            conn.update(worksheet="Página1", data=df_atualizado)
            st.cache_data.clear()
            st.rerun()

# 4. CORPO PRINCIPAL
tab1, tab2, tab3, tab4 = st.tabs(["📊 DASHBOARD", "🛒 VENDER", "📦 ESTOQUE & VENDAS", "⚙️ CONFIGURAÇÕES"])

with tab1:
    if not df_vendas.empty:
        total_vendas = df_vendas['Venda'].sum()
        total_lucro = df_vendas['Lucro'].sum()
        ticket_medio = df_vendas['Venda'].mean()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Receita Total", f"R$ {total_vendas:.2f}")
        c2.metric("Lucro Líquido", f"R$ {total_lucro:.2f}")
        c3.metric("Ticket Médio", f"R$ {ticket_medio:.2f}")
        
        # Gráficos Profissionais
        col_esq, col_dir = st.columns(2)
        fig_lucro = px.line(df_vendas, x="Data", y="Lucro", title="Evolução do Lucro no Tempo", color_discrete_sequence=['#bf40bf'])
        col_esq.plotly_chart(fig_lucro, use_container_width=True)
        
        fig_prod = px.bar(df_vendas.groupby("Produto")["Lucro"].sum().reset_index(), x="Produto", y="Lucro", title="Lucro por Produto", color="Lucro")
        col_dir.plotly_chart(fig_prod, use_container_width=True)
    else:
        st.info("Aguardando as primeiras vendas para gerar gráficos.")

with tab2:
    st.subheader("Registrar Saída")
    if not df_estoque.empty:
        p_venda = st.selectbox("Produto vendido:", df_estoque['Produto'].unique())
        if st.button("Confirmar Venda"):
            idx = df_estoque[df_estoque['Produto'] == p_venda].index[0]
            if df_estoque.at[idx, 'Qtd_Estoque'] > 0:
                df_estoque.at[idx, 'Qtd_Estoque'] -= 1
                df_estoque.at[idx, 'Vendas_Realizadas'] += 1
                nova_venda = pd.DataFrame([{
                    "Data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Produto": p_venda,
                    "Custo": df_estoque.at[idx, 'Custo'],
                    "Venda": df_estoque.at[idx, 'Preco_Venda'],
                    "Lucro": df_estoque.at[idx, 'Preco_Venda'] - df_estoque.at[idx, 'Custo']
                }])
                conn.update(worksheet="Página1", data=df_estoque)
                conn.update(worksheet="Vendas", data=pd.concat([df_vendas, nova_venda]))
                st.cache_data.clear()
                st.rerun()

with tab3:
    st.subheader("Gerenciamento de Dados")
    
    # SEÇÃO ESTOQUE
    st.write("### 📦 Estoque Atual")
    if not df_estoque.empty:
        # Checkbox para deletar produtos
        df_exp = df_estoque.copy()
        df_exp.insert(0, "Selecionar", False)
        edited_estoque = st.data_editor(df_exp, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Excluir Produtos Selecionados"):
            indices_para_manter = edited_estoque[edited_estoque["Selecionar"] == False].index
            df_final = df_estoque.loc[indices_para_manter]
            conn.update(worksheet="Página1", data=df_final)
            st.cache_data.clear()
            st.rerun()
            
    st.markdown("---")
    
    # SEÇÃO VENDAS
    st.write("### 💸 Histórico de Vendas")
    if not df_vendas.empty:
        df_v_exp = df_vendas.copy()
        df_v_exp.insert(0, "Selecionar", False)
        edited_vendas = st.data_editor(df_v_exp, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Excluir Vendas Selecionadas"):
            indices_v_manter = edited_vendas[edited_vendas["Selecionar"] == False].index
            df_v_final = df_vendas.loc[indices_v_manter]
            conn.update(worksheet="Vendas", data=df_v_final)
            st.cache_data.clear()
            st.rerun()

with tab4:
    st.subheader("🛠️ Painel de Controle Avançado")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("#### Metas")
        nova_meta = st.number_input("Meta de Lucro Mensal (R$)", value=2000.0)
        if st.button("Atualizar Meta"):
            st.session_state['meta'] = nova_meta
            st.success("Meta Salva!")

    with col2:
        st.write("#### Limpeza de Dados")
        if st.button("⚠️ RESETAR TODO O SISTEMA"):
            # Cria dataframes vazios com cabeçalhos
            empty_est = pd.DataFrame(columns=["Produto", "Custo", "Margem_%", "Preco_Venda", "Qtd_Estoque", "Vendas_Realizadas"])
            empty_ven = pd.DataFrame(columns=["Data", "Produto", "Custo", "Venda", "Lucro"])
            conn.update(worksheet="Página1", data=empty_est)
            conn.update(worksheet="Vendas", data=empty_ven)
            st.cache_data.clear()
            st.rerun()

    st.write("#### 📈 Análise de Margem por Custo")
    if not df_estoque.empty:
        fig_scatter = px.scatter(df_estoque, x="Custo", y="Margem_%", size="Qtd_Estoque", hover_name="Produto", title="Relação Custo vs Margem (%)")
        st.plotly_chart(fig_scatter, use_container_width=True)