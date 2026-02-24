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
        color: white; border-radius: 10px; border: none; font-weight: bold; transition: 0.3s; width: 100%;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0px 0px 15px #bf40bf; }
    h1, h2, h3 { color: #bf40bf; }
    .stProgress > div > div > div > div { background-image: linear-gradient(to right, #6a0dad , #bf40bf); }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #bf40bf; }
    .stTabs [aria-selected="true"] { background-color: #bf40bf; color: white; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXÃO NUVEM
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    estoque = conn.read(worksheet="Página1", ttl=0)
    try:
        vendas_hist = conn.read(worksheet="Vendas", ttl=0)
    except:
        vendas_hist = pd.DataFrame(columns=["Data", "Produto", "Custo", "Venda", "Lucro"])
    return estoque, vendas_hist

df_estoque, df_vendas = get_data()

# 3. SIDEBAR (CADASTRO FLEXÍVEL)
st.sidebar.title("💜 Entrada de Estoque")
with st.sidebar.form("novo_prod", clear_on_submit=True):
    nome = st.text_input("Nome do Produto")
    custo = st.number_input("Custo Unitário (R$)", min_value=0.0, step=0.01)
    qtd = st.number_input("Quantidade Comprada", min_value=1, step=1)
    
    st.markdown("---")
    usar_margem = st.checkbox("Usar margem automática?", value=False)
    
    if usar_margem:
        margem_input = st.number_input("Margem (%)", min_value=0.0, value=30.0)
        venda_final = float(custo * (1 + margem_input/100))
        st.info(f"Preço sugerido: R$ {venda_final:.2f}")
    else:
        venda_final = st.number_input("Preço de Venda Manual (R$)", min_value=0.0, step=0.01)
        # Calcula a margem real baseada no que o usuário digitou
        if venda_final > 0:
            margem_input = ((venda_final - custo) / venda_final) * 100
        else:
            margem_input = 0.0

    if st.form_submit_button("✅ CADASTRAR PRODUTO"):
        if nome and (venda_final > 0):
            novo = pd.DataFrame([{
                "Produto": nome, 
                "Custo": custo, 
                "Margem_%": round(margem_input, 2), 
                "Preco_Venda": venda_final, 
                "Qtd_Estoque": qtd, 
                "Vendas_Realizadas": 0
            }])
            df_estoque = pd.concat([df_estoque, novo], ignore_index=True)
            conn.update(worksheet="Página1", data=df_estoque)
            st.cache_data.clear()
            st.success(f"{nome} adicionado!")
            st.rerun()
        else:
            st.error("Preencha o nome e o preço de venda!")

# 4. DASHBOARD E EXTRATOS
tab1, tab2, tab3, tab4 = st.tabs(["📊 DASHBOARD", "🛒 VENDER", "📜 EXTRATOS", "⚙️ CONFIG"])

with tab1:
    if not df_estoque.empty:
        invest_total = (df_estoque['Custo'] * (df_estoque['Qtd_Estoque'] + df_estoque['Vendas_Realizadas'])).sum()
        receita_total = (df_estoque['Preco_Venda'] * df_estoque['Vendas_Realizadas']).sum()
        lucro_realizado = df_vendas['Lucro'].sum() if not df_vendas.empty else 0.0
        saldo_geral = receita_total - invest_total
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Peças em Estoque", f"{int(df_estoque['Qtd_Estoque'].sum())}")
        c2.metric("💸 Investimento Total", f"R$ {invest_total:.2f}")
        c3.metric("📈 Lucro Realizado", f"R$ {lucro_realizado:.2f}")
        c4.metric("⚖️ Saldo do Negócio", f"R$ {saldo_geral:.2f}")

        st.markdown("---")
        meta_valor = st.session_state.get('meta_vendas', 2000.0)
        progresso = min(lucro_realizado / meta_valor, 1.0) if meta_valor > 0 else 0
        st.subheader(f"🎯 Meta de Lucro: R$ {meta_valor:.2f}")
        st.progress(progresso)
        st.caption(f"Progresso: {progresso*100:.1f}%")
    else:
        st.info("Nenhum dado disponível.")

with tab2:
    st.subheader("🛍️ Registrar Venda")
    if not df_estoque.empty:
        prod_sel = st.selectbox("Selecione o produto:", df_estoque['Produto'].unique())
        if st.button("💰 CONFIRMAR VENDA"):
            idx = df_estoque[df_estoque['Produto'] == prod_sel].index[0]
            if df_estoque.at[idx, 'Qtd_Estoque'] > 0:
                df_estoque.at[idx, 'Qtd_Estoque'] -= 1
                df_estoque.at[idx, 'Vendas_Realizadas'] += 1
                
                nova_venda = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Produto": prod_sel,
                    "Custo": df_estoque.at[idx, 'Custo'],
                    "Venda": df_estoque.at[idx, 'Preco_Venda'],
                    "Lucro": df_estoque.at[idx, 'Preco_Venda'] - df_estoque.at[idx, 'Custo']
                }])
                df_vendas = pd.concat([df_vendas, nova_venda], ignore_index=True)
                
                conn.update(worksheet="Página1", data=df_estoque)
                conn.update(worksheet="Vendas", data=df_vendas)
                st.cache_data.clear()
                st.balloons()
                st.rerun()

with tab3:
    st.subheader("📦 Extrato de Estoque & Margens")
    if not df_estoque.empty:
        # Tabela bonitona com a margem real de cada item
        df_show = df_estoque.copy()
        df_show['Margem Real %'] = ((df_show['Preco_Venda'] - df_show['Custo']) / df_show['Preco_Venda'] * 100).map("{:.2f}%".format)
        st.dataframe(df_show[['Produto', 'Custo', 'Preco_Venda', 'Margem Real %', 'Qtd_Estoque']], use_container_width=True)
    
    st.markdown("---")
    st.subheader("💸 Histórico de Vendas")
    if not df_vendas.empty:
        st.dataframe(df_vendas.sort_index(ascending=False), use_container_width=True)

with tab4:
    st.subheader("⚙️ Configurações")
    nova_meta = st.number_input("Nova Meta de Lucro (R$)", value=st.session_state.get('meta_vendas', 2000.0))
    if st.button("Salvar Meta"):
        st.session_state['meta_vendas'] = nova_meta
        st.success("Meta atualizada!")
    
    st.markdown("---")
    st.subheader("🗑️ Remover Produto")
    p_del = st.selectbox("Escolha um produto para apagar:", ["-"] + list(df_estoque['Produto'].unique()))
    if st.button("Excluir Definitivamente"):
        if p_del != "-":
            df_estoque = df_estoque[df_estoque['Produto'] != p_del]
            conn.update(worksheet="Página1", data=df_estoque)
            st.cache_data.clear()
            st.rerun()