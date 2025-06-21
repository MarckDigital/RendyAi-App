import streamlit as st
import yfinance as yf
import pandas as pd
import os
import json
import re
import logging
from datetime import datetime
import pytz

# =================== CONFIGURAÇÕES E CONSTANTES ===================
st.set_page_config(
    page_title="Rendy AI - Assessor de Investimentos",
    page_icon="🤖",
    layout="centered"
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = 'data'
USUARIO_JSON = os.path.join(DATA_DIR, 'usuario.json')
FUSO_BR = pytz.timezone('America/Sao_Paulo')

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
    "DY": "Dividend Yield: percentual dos dividendos pagos em relação ao preço da ação, anualizado. O app limita DY a no máximo 30% ao ano por padrão para evitar distorções.",
    "P/L": "Preço dividido pelo lucro por ação. P/L baixo pode indicar ação barata.",
    "P/VP": "Preço dividido pelo valor patrimonial da empresa por ação. P/VP abaixo de 1 pode indicar ação descontada.",
    "ROE": "Retorno sobre o patrimônio líquido. Mede a eficiência da empresa em gerar lucros.",
    "Super Investimento": "Ações que atingiram a pontuação máxima de 10 no score, mas cujo valor bruto dos critérios ultrapassou esse limite. São consideradas oportunidades excepcionais segundo o algoritmo."
}

# =================== UTILITÁRIOS E SESSÃO ===================
def agora_brasilia():
    return datetime.now(FUSO_BR)

def inicializar_ambiente():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def salvar_usuario(nome: str, email: str):
    inicializar_ambiente()
    dados = {'nome': nome, 'email': email, 'data_cadastro': agora_brasilia().isoformat()}
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

def validar_dy(dy: float):
    """Valida e ajusta o Dividend Yield, limitando valores anormais."""
    if dy is None or dy < 0:
        return 0.0, "⚠️ O Dividend Yield informado é negativo ou inválido, ajustado para 0."
    if dy > 1:  # Provavelmente veio em percentual, corrija para proporção
        dy = dy / 100
    if dy > 0.3:
        return 0.3, (
            """<div style='background: #fff3cd; border-left: 5px solid #ffecb5; padding: 8px;'>
            <b>⚠️ ATENÇÃO:</b> O Dividend Yield informado para este ativo está acima de <b>30%</b>.<br>
            Isso pode indicar erro na fonte de dados ou evento não recorrente.<br>
            Consulte relatórios oficiais antes de investir.
            </div>"""
        )
    return dy, ""

# =================== AGENTES E ANÁLISE DE AÇÕES ===================
class RendyFinanceAgent:
    def analisar_ativo(self, ticker: str) -> dict:
        try:
            acao = yf.Ticker(ticker)
            info = acao.info
            historico = acao.history(period="1y")
            historico_close = historico['Close'] if not historico.empty else None
            dy_raw = info.get('dividendYield', 0) or 0
            dy, alerta_dy = validar_dy(float(dy_raw))
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
            score_bruto = score_dy + score_pl + score_pvp + score_roe
            score_total = min(score_bruto, 10)
            is_super = score_bruto > 10
            return {
                "ticker": ticker,
                "nome_empresa": info.get('longName', ticker),
                "preco_atual": preco_atual,
                "dy": float(dy),
                "pl": float(pl),
                "pvp": float(pvp),
                "roe": float(roe),
                "score": score_total,
                "score_bruto": score_bruto,
                "super_investimento": is_super,
                "historico": historico_close,
                "alerta_dy": alerta_dy
            }
        except Exception as e:
            logger.error(f"Erro ao analisar {ticker}: {e}")
            return {"ticker": ticker, "error": str(e)}

    def descobrir_oportunidades(self):
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

# =================== UI EXPLICATIVA ===================
def tooltip(texto):
    return f"ℹ️ <span style='color:gray;font-size:0.95em'>{texto}</span>"

def render_explicacao_campos():
    st.markdown("#### O que significa cada indicador?")
    for key, desc in GLOSSARIO.items():
        st.markdown(f"- **{key}**: {desc}")

# =================== ABAS PRINCIPAIS ===================
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
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Score", f"{analise['score']:.1f}/10", help=GLOSSARIO["Score"])
            col2.metric("Preço Atual", f"R$ {preco:,.2f}")
            col3.metric("Div. Yield", f"{dy*100:.2f}%", help=GLOSSARIO["DY"])
            col4.metric("P/L", f"{analise['pl']:.2f}", help=GLOSSARIO["P/L"])
            col5.metric("ROE", f"{roe*100:.2f}%", help=GLOSSARIO["ROE"])

            # Mensagem destacada, pluralização e didática (CORRIGIDO AQUI)
            if qtd == 0:
                st.warning(f"Com o valor de R$ {valor:,.2f}, não é possível adquirir nenhuma ação de {analise['nome_empresa']} ao preço atual.")
            else:
                st.markdown(
                    f"""
                    <div style='background: #d4edda; border-left: 5px solid #28a745; padding: 8px; border-radius: 4px;'>
                    <b>Parabéns!</b> Com seu investimento de <b>R$ {valor:,.2f}</b>, você pode adquirir <b>{qtd} ação{'s' if qtd > 1 else ''}</b>.<br>
                    Sua renda passiva anual estimada em dividendos será de <b style='color:green'>R$ {renda:,.2f}</b>.<br>
                    <span style='font-size: 0.95em;'>O cálculo utiliza o Dividend Yield anualizado mais recente disponível. Resultados passados não garantem retornos futuros.</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # Alerta amigável se DY estiver fora do padrão
            if analise.get("alerta_dy"):
                st.markdown(analise["alerta_dy"], unsafe_allow_html=True)

            # SUPER INVESTIMENTO
            if analise.get('super_investimento'):
                st.info("🔥 Esta ação é classificada como SUPER INVESTIMENTO pelo algoritmo! (i) "
                        "A pontuação bruta dela ultrapassa 10, ou seja, é ainda mais diferenciada segundo nossos critérios. "
                        + tooltip(GLOSSARIO["Super Investimento"]))

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
    df['Preço Atual'] = df['preco_atual'].apply(lambda x: f"R$ {x:,.2f}" if x > 0 else "N/A")
    df['Div. Yield'] = df['dy'].apply(lambda x: f"{x*100:.2f}%" if x > 0 else "N/A")
    df['P/L'] = df['pl'].apply(lambda x: f"{x:.2f}" if x > 0 else "N/A")
    df['ROE'] = df['roe'].apply(lambda x: f"{x*100:.2f}%" if x > 0 else "N/A")
    df['Super Investimento'] = df['super_investimento'].apply(lambda x: '🔥' if x else '')

    st.dataframe(
        df[['ticker', 'nome_empresa', 'Preço Atual', 'score', 'Div. Yield', 'P/L', 'ROE', 'Super Investimento']].rename(
            columns={
                'ticker':'Ticker', 
                'nome_empresa':'Empresa', 
                'score':'Score',
                'Super Investimento': f"Super Investimento {tooltip(GLOSSARIO['Super Investimento'])}"
            }),
        hide_index=True, use_container_width=True,
        column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=10, format='%.1f')}
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
            preco = analise.get('preco_atual', 0.0)
            renda = item['valor_alocado'] * dy
            renda_total += renda
            linhas.append({
                "Ticker": item['ticker'],
                "Preço Atual": f"R$ {preco:,.2f}" if preco > 0 else "N/A",
                "Valor Investido": f"R$ {item['valor_alocado']:,.2f}",
                "DY": f"{dy*100:.2f}%",
                "Renda Passiva": f"R$ {renda:,.2f}",
                "Super Investimento": "🔥" if analise.get('super_investimento') else ""
            })
        st.subheader("Resumo da Carteira")
        st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
        st.success(f"Total investido: R$ {total_investido:,.2f} | Renda passiva anual estimada: R$ {renda_total:,.2f}")
        if total_investido > 0:
            st.info(f"Dividend Yield médio da carteira: {renda_total / total_investido * 100:.2f}%")
        if any(linha["Super Investimento"] for linha in linhas):
            st.markdown(tooltip(GLOSSARIO["Super Investimento"]), unsafe_allow_html=True)
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

# =================== MAIN ===================
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
