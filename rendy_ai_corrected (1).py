import streamlit as st
import yfinance as yf
import pandas as pd
import os
import json
import re
import logging
from datetime import datetime
from typing import Dict, List

# ========== CONFIGURAÇÕES E CONSTANTES ==========
st.set_page_config(
    page_title="Rendy AI - Assessor de Investimentos",
    page_icon="🤖",
    layout="centered"
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = 'data'
USUARIO_JSON = os.path.join(DATA_DIR, 'usuario.json')
LISTA_TICKERS_IBOV = [
    'ABEV3.SA', 'B3SA3.SA', 'BBAS3.SA', 'BBDC4.SA', 'BBSE3.SA', 'BRAP4.SA',
    'BRFS3.SA', 'BRKM5.SA', 'CCRO3.SA', 'CIEL3.SA', 'CMIG4.SA', 'CPLE6.SA',
    'CSAN3.SA', 'CSNA3.SA', 'CYRE3.SA', 'ECOR3.SA', 'EGIE3.SA', 'ELET3.SA',
    'EMBR3.SA', 'ENBR3.SA', 'EQTL3.SA', 'GGBR4.SA', 'GOAU4.SA', 'HAPV3.SA',
    'HYPE3.SA', 'ITSA4.SA', 'ITUB4.SA', 'JBSS3.SA', 'LREN3.SA', 'MGLU3.SA',
    'MRFG3.SA', 'MRVE3.SA', 'MULT3.SA', 'NTCO3.SA', 'PCAR3.SA', 'PETR3.SA',
    'PETR4.SA', 'PRIO3.SA', 'RADL3.SA', 'RAIL3.SA', 'RENT3.SA', 'SANB11.SA',
    'SBSP3.SA', 'SUZB3.SA', 'TAEE11.SA', 'UGPA3.SA', 'USIM5.SA', 'VALE3.SA',
    'VIVT3.SA', 'WEGE3.SA', 'YDUQ3.SA'
]
GLOSSARIO = {
    "Score": "Pontuação de até 10 que avalia custo/benefício considerando dividendos (DY), rentabilidade (ROE), preço/lucro (P/L) e preço/valor patrimonial (P/VP). Quanto mais perto de 10, melhor.",
    "DY": "Dividend Yield: percentual dos dividendos pagos em relação ao preço da ação, anualizado.",
    "P/L": "Preço dividido pelo lucro por ação. P/L baixo pode indicar ação barata.",
    "P/VP": "Preço dividido pelo valor patrimonial da empresa por ação. P/VP abaixo de 1 pode indicar ação descontada.",
    "ROE": "Retorno sobre o patrimônio líquido. Mede a eficiência da empresa em gerar lucros.",
}

# ========== UTILITÁRIOS E SESSÃO ==========
def inicializar_ambiente():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def salvar_usuario(nome: str, email: str):
    inicializar_ambiente()
    dados = {'nome': nome, 'email': email, 'data_cadastro': datetime.now().isoformat()}
    with open(USUARIO_JSON, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    st.session_state['nome_usuario'] = nome
    st.session_state['email_usuario'] = email

def carregar_usuario():
    if os.path.exists(USUARIO_JSON):
        with open(USUARIO_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def validar_email(email: str) -> bool:
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', email))

def inicializar_sessao():
    if 'nome_usuario' not in st.session_state:
        user = carregar_usuario()
        st.session_state['nome_usuario'] = user.get('nome', '')
        st.session_state['email_usuario'] = user.get('email', '')
    if 'carteira_em_montagem' not in st.session_state:
        st.session_state['carteira_em_montagem'] = []
    if 'valor_simulacao' not in st.session_state:
        st.session_state['valor_simulacao'] = 5000.0
    if 'analise_simulacao' not in st.session_state:
        st.session_state['analise_simulacao'] = None
    if 'lista_alocada' not in st.session_state:
        st.session_state['lista_alocada'] = []

# ========== AGENTES E ANÁLISE DE AÇÕES ==========
class RendyFinanceAgent:
    def analisar_ativo(self, ticker: str) -> Dict:
        try:
            acao = yf.Ticker(ticker)
            info = acao.info
            historico = acao.history(period="1y")
            historico_close = historico['Close'] if not historico.empty else None
            dy = info.get('dividendYield', 0) or 0
            pl = info.get('trailingPE', 0) or 0
            pvp = info.get('priceToBook', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            preco_atual = info.get('currentPrice', 0) or info.get('regularMarketPrice', 0) or 0
            if preco_atual == 0 and historico_close is not None and hasattr(historico_close, 'iloc') and not historico_close.empty:
                preco_atual = float(historico_close.iloc[-1])
            score_dy = min(dy / 0.08, 1) * 4 if dy > 0 else 0
            score_pl = min(15 / pl if pl > 0 else 0, 1) * 1.5
            score_pvp = min(2 / pvp if pvp > 0 else 0, 1) * 1.5
            score_roe = min(roe / 0.20, 1) * 3 if roe > 0 else 0
            score_total = min(score_dy + score_pl + score_pvp + score_roe, 10)
            return {
                "ticker": ticker,
                "nome_empresa": info.get('longName', ticker),
                "preco_atual": preco_atual,
                "dy": float(dy),
                "pl": float(pl),
                "pvp": float(pvp),
                "roe": float(roe),
                "score": score_total,
                "historico": historico_close
            }
        except Exception as e:
            logger.error(f"Erro ao analisar {ticker}: {e}")
            return {"ticker": ticker, "error": str(e)}

    def descobrir_oportunidades(self) -> List[Dict]:
        resultados = []
        progress_bar = st.progress(0, "Analisando todo o mercado para você!")
        for i, ticker in enumerate(LISTA_TICKERS_IBOV):
            resultado = self.analisar_ativo(ticker)
            if 'error' not in resultado and resultado.get('preco_atual', 0) > 0:
                resultados.append(resultado)
            progress = min((i + 1) / len(LISTA_TICKERS_IBOV), 1.0)
            progress_bar.progress(progress, f"Pesquisando {ticker}...")
        progress_bar.empty()
        return sorted(resultados, key=lambda x: x.get('score', 0), reverse=True)

# ========== UI EXPLICATIVA ==========
def tooltip(texto):
    return f"ℹ️ <span style='color:gray;font-size:0.95em'>{texto}</span>"

def render_explicacao_campos():
    st.markdown("#### O que significa cada indicador?")
    for key, desc in GLOSSARIO.items():
        st.markdown(f"- **{key}**: {desc}")

# ========== ABAS ==========
def aba_simulacao():
    st.header("🎯 Simulação Personalizada de Investimento")
    st.markdown("""
    Aqui você simula um investimento real, escolhendo uma ação e um valor para investir.  
    <br>
    <b>O objetivo:</b> Mostrar de forma didática quanto de renda passiva anual é possível conquistar e como cada métrica impacta sua decisão!
    """, unsafe_allow_html=True)
    st.info("Dica: Use o simulador para experimentar valores e ações. Clique nos (i) para entender cada campo.")

    col1, col2 = st.columns(2)
    with col1:
        ticker = st.selectbox("Escolha uma ação para simular", options=LISTA_TICKERS_IBOV,
                              help="Selecione uma empresa da bolsa para a simulação.")
    with col2:
        st.session_state['valor_simulacao'] = st.number_input(
            "Quanto deseja investir? (R$)",
            min_value=100.0, step=100.0, value=st.session_state['valor_simulacao'],
            help="Digite o valor que pretende investir nesta simulação."
        )

    if st.button("Simular meu investimento 🚀", type="primary", use_container_width=True):
        agent = RendyFinanceAgent()
        with st.spinner("Analisando sua simulação..."):
            st.session_state['analise_simulacao'] = agent.analisar_ativo(ticker)

    if st.session_state.get('analise_simulacao'):
        analise = st.session_state['analise_simulacao']
        if analise.get("error"):
            st.error(f"Erro ao analisar: {analise['error']}")
        else:
            st.subheader(f"Resultado para {analise['nome_empresa']} ({analise['ticker']})")
            valor = st.session_state['valor_simulacao']
            preco = analise["preco_atual"]
            dy = analise["dy"]
            roe = analise["roe"]
            qtd = int(valor // preco) if preco > 0 else 0
            investido = qtd * preco
            renda = investido * dy
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Score", f"{analise['score']:.1f}/10", help=GLOSSARIO["Score"])
            col2.metric("Div. Yield", f"{dy*100:.2f}%", help=GLOSSARIO["DY"])
            col3.metric("P/L", f"{analise['pl']:.2f}", help=GLOSSARIO["P/L"])
            col4.metric("ROE", f"{roe*100:.2f}%", help=GLOSSARIO["ROE"])
            st.success(
                f"Com **R$ {valor:,.2f}** você compraria **{qtd} ações** e teria uma renda passiva anual estimada de **R$ {renda:,.2f}**."
            )
            if analise.get('historico') is not None and hasattr(analise['historico'], 'empty') and not analise['historico'].empty:
                st.markdown("##### Evolução do Preço nos Últimos 12 Meses")
                st.line_chart(analise['historico'])
            render_explicacao_campos()

def aba_ranking():
    st.header("🏆 Ranking de Oportunidades do Mercado")
    st.markdown("""
    Aqui você encontra as melhores oportunidades do momento, segundo o algoritmo do Rendy!
    <br>
    <b>Como interpretar?</b> O Score combina potencial de dividendos, valorização e preço justo.
    <br>
    Dica: Passe o mouse sobre cada coluna para entender os indicadores e clique em uma ação para simular.
    """, unsafe_allow_html=True)
    agent = RendyFinanceAgent()
    oportunidades = agent.descobrir_oportunidades()
    if not oportunidades:
        st.error("Não foi possível carregar o ranking agora. Tente novamente.")
        return
    df = pd.DataFrame(oportunidades)
    df['Div. Yield'] = df['dy'].apply(lambda x: f"{x*100:.2f}%" if x > 0 else "N/A")
    df['P/L'] = df['pl'].apply(lambda x: f"{x:.2f}" if x > 0 else "N/A")
    df['ROE'] = df['roe'].apply(lambda x: f"{x*100:.2f}%" if x > 0 else "N/A")
    st.dataframe(
        df[['ticker', 'nome_empresa', 'score', 'Div. Yield', 'P/L', 'ROE']].rename(
            columns={'ticker':'Ticker', 'nome_empresa':'Empresa', 'score':'Score'}),
        hide_index=True, use_container_width=True,
        column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=10, format="%.1f")}
    )
    render_explicacao_campos()

def aba_carteira():
    st.header("💼 Monte sua Carteira de Renda Passiva")
    st.markdown("""
    <b>Objetivo:</b> Aqui você pode montar sua carteira de ações escolhidas, distribuir seu capital e ver a projeção de renda passiva total.
    <br>
    Dica: Selecione várias ações, defina quanto investir em cada uma e veja o resultado combinado!
    """, unsafe_allow_html=True)
    if 'lista_alocada' not in st.session_state:
        st.session_state['lista_alocada'] = []
    tickers_add = st.multiselect(
        "Selecione as ações para sua carteira:",
        LISTA_TICKERS_IBOV,
        default=[a['ticker'] for a in st.session_state['carteira_em_montagem']]
    )
    if st.button("Adicionar à Carteira", use_container_width=True):
        st.session_state['carteira_em_montagem'] = [{'ticker': t} for t in tickers_add]
        st.success("Ações adicionadas! Agora defina a alocação para cada uma.")

    total = 0
    alocacoes = []
    st.markdown(tooltip("Defina quanto deseja investir em cada ação. Diversificação pode diminuir riscos!"), unsafe_allow_html=True)
    for item in st.session_state['carteira_em_montagem']:
        val = st.number_input(
            f"Valor para {item['ticker']}:",
            min_value=0.0,
            key=f"aloc_{item['ticker']}"
        )
        alocacoes.append({'ticker': item['ticker'], 'valor_alocado': val})
        total += val

    if st.button("Analisar Carteira", type="primary", use_container_width=True):
        st.session_state['lista_alocada'] = alocacoes

    if st.session_state.get('lista_alocada'):
        agent = RendyFinanceAgent()
        total_investido = sum(a['valor_alocado'] for a in st.session_state['lista_alocada'])
        renda_total = 0
        linhas = []
        for item in st.session_state['lista_alocada']:
            analise = agent.analisar_ativo(item['ticker'])
            dy = float(analise['dy']) if analise.get('dy') else 0.0
            renda = item['valor_alocado'] * dy
            renda_total += renda
            linhas.append({
                "Ticker": item['ticker'],
                "Valor Investido": f"R$ {item['valor_alocado']:,.2f}",
                "DY": f"{dy*100:.2f}%",
                "Renda Passiva": f"R$ {renda:,.2f}"
            })
        st.subheader("Resumo da Carteira")
        st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
        st.success(f"Total investido: R$ {total_investido:,.2f} | Renda passiva anual estimada: R$ {renda_total:,.2f}")
        if total_investido > 0:
            st.info(f"Dividend Yield médio da carteira: {renda_total / total_investido * 100:.2f}%")
        render_explicacao_campos()

def aba_sobre():
    st.header("ℹ️ Sobre o Rendy AI & Glossário")
    st.markdown("""
    O Rendy AI é seu assessor virtual para investimentos inteligentes e didáticos, pronto para ajudar você a:
    - Entender indicadores de investimento de modo simples e prático
    - Simular oportunidades antes de investir
    - Montar sua carteira de renda passiva
    - Aprender a analisar oportunidades do mercado

    <b>Glossário:</b>
    """, unsafe_allow_html=True)
    for k, v in GLOSSARIO.items():
        st.markdown(f"- **{k}**: {v}")

# ========== MAIN ==========
def main():
    inicializar_sessao()
    st.title("🤖 Rendy AI - Assessor de Investimentos")
    st.markdown(
        "<span style='color:#666;'>Navegue pelas abas abaixo para simular, aprender e investir com inteligência. O app vai te orientar em cada passo!</span>",
        unsafe_allow_html=True
    )

    # Cadastro rápido se necessário
    if not st.session_state['nome_usuario']:
        with st.form("cadastro"):
            st.subheader("Primeiro, cadastre-se para uma experiência personalizada!")
            nome = st.text_input("Seu nome")
            email = st.text_input("Seu melhor email")
            submitted = st.form_submit_button("Entrar no Rendy AI")
            if submitted:
                if not nome.strip() or not validar_email(email):
                    st.error("Por favor, preencha nome e email válidos!")
                    return
                salvar_usuario(nome.strip(), email.strip())
                st.success(f"Bem-vindo, {nome.split()[0]}! Agora navegue nas abas.")
                st.rerun()
        return

    tabs = st.tabs([
        "🏆 Ranking de Mercado",
        "🎯 Simulação Personalizada",
        "💼 Montar Carteira",
        "ℹ️ Sobre & Glossário"
    ])
    with tabs[0]: aba_ranking()
    with tabs[1]: aba_simulacao()
    with tabs[2]: aba_carteira()
    with tabs[3]: aba_sobre()

if __name__ == "__main__":
    main()