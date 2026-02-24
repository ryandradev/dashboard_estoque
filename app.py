import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. CONFIGURAÇÃO E ESTILO
st.set_page_config(page_title="Gestão VIP Marketplace", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    [data-testid="stMetricValue"] { color: #bf40bf !important; font-weight: bold; }
    .stButton>button { 
        background: linear-gradient(45deg, #6a0dad, #bf40bf); 
        color: white; border-radius: 10px; border: none; font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0px 0px 15px #bf40bf; }
    h1, h2, h3 { color: #bf40bf; font-family: 'Trebuchet MS'; }
    .stProgress > div > div > div > div { background-color: #bf40bf; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #bf40bf; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONEXÃO NUVEM
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl=0)

# 3. SIDEBAR
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3081/3081559.png", width=80)
st.sidebar.title("Menu de Gestão")

with st.sidebar.form("novo_prod", clear_on_submit=True):
    st.subheader("📦 Comprar p/ Estoque")
    nome = st.text_input("Nome do Produto")
    custo = st.number_input("Custo de Compra (R$)", min_value=0.0)
    margem = st.number_input("Margem Alvo (%)", min_value=0.0, value=30.0)
    qtd = st.number_input("Quantidade", min_value=1)
    venda = st.number_input("Preço de Venda (R$)", value=float(custo * (1 + margem/100)))
    
    if st.form_submit_button("Finalizar Compra"):
        if nome:
            novo = pd.DataFrame([{
                "Produto": nome, "Custo": custo, "Margem_%": margem, 
                "Preco_Sugerido": custo*(1+margem/100), "Preco_Venda": venda, 
                "Qtd_Estoque": qtd, "Vendas_Realizadas": 0,
                "Data_Ultima_Acao": datetime.now().strftime("%d/%m/%Y %H:%M")
            }])
            df = pd.concat([df, novo], ignore_index=True)
            conn.update(data=df)
            st.cache_data.clear()
            st.rerun()

st.sidebar.markdown("---")
if not df.empty:
    prod_del = st.sidebar.selectbox("Remover Produto:", ["-"] + list(df['Produto'].unique()))
    if st.sidebar.button("🗑️ Excluir Item"):
        if prod_del != "-":
            df = df[df['Produto'] != prod_del]
            conn.update(data=df)
            st.cache_data.clear()
            st.rerun()

# 4. CORPO PRINCIPAL COM ABAS
tab1, tab2 = st.tabs(["📊 Dashboard Principal", "📜 Extrato Detalhado"])

with tab1:
    st.title("🚀 Business Intelligence - Marketplace")
    
    if not df.empty:
        # Cálculos
        invest_total = (df['Custo'] * (df['Qtd_Estoque'] + df['Vendas_Realizadas'])).sum()
        receita_total = (df['Preco_Venda'] * df['Vendas_Realizadas']).sum()
        lucro_bruto = ((df['Preco_Venda'] - df['Custo']) * df['Vendas_Realizadas']).sum()
        saldo = receita_total - invest_total
        estoque_total = int(df['Qtd_Estoque'].sum())
        
        # Linha 1: Métricas Principais
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Estoque Atual", f"{estoque_total} un")
        c2.metric("💸 Investimento", f"R$ {invest_total:.2f}")
        c3.metric("💰 Lucro Acumulado", f"R$ {lucro_bruto:.2f}")
        
        color = "normal" if saldo >= 0 else "inverse"
        c4.metric("⚖️ Saldo (Break-even)", f"R$ {saldo:.2f}", delta=f"{saldo:.2f}", delta_color=color)

        # Meta Visual Bonitona
        st.markdown("### 🎯 Meta de Lucro")
        meta_lucro = st.number_input("Ajustar Meta (R$)", value=2000.0, step=100.0)
        progresso = min(lucro_bruto / meta_lucro, 1.0) if meta_lucro > 0 else 0
        
        col_meta, col_texto = st.columns([4, 1])
        with col_meta:
            st.progress(progresso)
        with col_texto:
            st.write(f"**{progresso*100:.1f}% batida**")

        st.markdown("---")
        
        # Registro de Venda Rápida
        st.subheader("🛒 Registrar Nova Venda")
        cv1, cv2 = st.columns([3, 1])
        with cv1:
            sel = st.selectbox("Selecione o produto que saiu:", df['Produto'].unique())
        with cv2:
            st.write("##")
            if st.button("💰 CONFIRMAR VENDA"):
                idx = df[df['Produto'] == sel].index[0]
                if df.at[idx, 'Qtd_Estoque'] > 0:
                    df.at[idx, 'Qtd_Estoque'] -= 1
                    df.at[idx, 'Vendas_Realizadas'] += 1
                    df.at[idx, 'Data_Ultima_Acao'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                    conn.update(data=df)
                    st.cache_data.clear()
                    st.toast(f"Sucesso! Venda de {sel} registrada.")
                    st.rerun()
                else:
                    st.error("Estoque zerado!")
    else:
        st.info("Cadastre seu primeiro produto na barra lateral para começar!")

with tab2:
    st.subheader("📜 Histórico e Detalhes do Estoque")
    if not df.empty:
        # Criando colunas extras para o extrato
        extrato_df = df.copy()
        extrato_df['Valor p/ Recuperar'] = (extrato_df['Custo'] * extrato_df['Qtd_Estoque'])
        extrato_df['Lucro Esperado (Restante)'] = (extrato_df['Preco_Venda'] - extrato_df['Custo']) * extrato_df['Qtd_Estoque']
        
        st.write("Abaixo você vê quanto cada produto ainda tem para te dar de lucro:")
        st.dataframe(
            extrato_df.style.format({
                "Custo": "R$ {:.2f}", 
                "Preco_Venda": "R$ {:.2f}", 
                "Valor p/ Recuperar": "R$ {:.2f}",
                "Lucro Esperado (Restante)": "R$ {:.2f}"
            }), 
            use_container_width=True
        )
        
        st.download_button(
            label="📥 Baixar Relatório CSV",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name='meu_estoque.csv',
            mime='text/csv',
        )
    else:
        st.warning("Nenhum dado para exibir no extrato.")