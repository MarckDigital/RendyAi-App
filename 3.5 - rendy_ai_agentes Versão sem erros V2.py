# rendy_ai_unificado.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import json
import re
import logging
from datetime import datetime
import pytz
from typing import Dict, List, Optional
import plotly.express as px
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# ========== CONFIG & CONSTANTES ==========
st.set_page_config(
    page_title="Rendy AI - Plataforma Inteligente de Investimentos",
    page_icon="🤖",
    layout="wide"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = 'data'
USUARIO_JSON = os.path.join(DATA_DIR, 'usuario.json')
HISTORICO_JSON = os.path.join(DATA_DIR, 'historico_interacoes.json')
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
    "Score": "Pontuação até 10 que avalia custo/benefício considerando dividendos (DY), rentabilidade (ROE), preço/lucro (P/L) e preço/valor patrimonial (P/VP). Quanto mais perto de 10, melhor.",
    "DY": "Dividend Yield: percentual dos dividendos pagos em relação ao preço da ação, anualizado. O app limita DY a no máximo 30% ao ano por padrão para evitar distorções.",
    "P/L": "Preço dividido pelo lucro por ação. P/L baixo pode indicar ação barata.",
    "P/VP": "Preço dividido pelo valor patrimonial da empresa por ação. P/VP abaixo de 1 pode indicar ação descontada.",
    "ROE": "Retorno sobre o patrimônio líquido. Mede a eficiência da empresa em gerar lucros.",
    "Super Investimento": "Ações que atingiram a pontuação máxima de 10 no score, mas cujo valor bruto dos critérios ultrapassou esse limite. São consideradas oportunidades excepcionais segundo a metodologia da Rendy.",
    "Free Cash Flow": "Fluxo de caixa livre: dinheiro que sobra após investimentos necessários. Indica capacidade de pagar dividendos.",
    "Payout Ratio": "Percentual do lucro distribuído como dividendos. Valores entre 30-60% são considerados saudáveis.",
    "Debt/Equity": "Relação dívida/patrimônio. Valores altos podem indicar risco financeiro.",
    "Margem Líquida": "Percentual do lucro líquido sobre a receita. Indica eficiência operacional.",
    "Crescimento de Dividendos": "Taxa de crescimento histórica dos dividendos. Indica sustentabilidade futura."
}

# ========== DATACLASSES ==========
@dataclass
class PerfilUsuario:
    nome: str
    email: str
    tolerancia_risco: str = "moderado"
    horizonte_investimento: str = "medio"
    objetivo_principal: str = "renda_passiva"
    experiencia: str = "iniciante"
    valor_disponivel: float = 0.0
    setores_preferidos: Optional[List[str]] = None
    def __post_init__(self):
        if self.setores_preferidos is None:
            self.setores_preferidos = []

@dataclass
class AnaliseAtivo:
    ticker: str
    nome_empresa: str
    preco_atual: float
    dy: float
    pl: float
    pvp: float
    roe: float
    score: float
    score_bruto: float
    super_investimento: bool
    historico: Optional[pd.Series] = None
    alerta_dy: str = ""
    free_cash_flow: float = 0.0
    payout_ratio: float = 0.0
    debt_equity: float = 0.0
    margem_liquida: float = 0.0
    crescimento_dividendos: float = 0.0
    setor: str = ""
    risco_nivel: str = "medio"
    recomendacao: str = ""

# ========== UTILITÁRIOS ==========
def agora_brasilia():
    return datetime.now(FUSO_BR)

def inicializar_ambiente():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def validar_email(email: str) -> bool:
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', email))

def validar_dy(dy: float):
    if dy is None or dy < 0:
        return 0.0, "⚠️ O Dividend Yield informado é negativo ou inválido, ajustado para 0."
    if dy > 1:
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

# ========== AGENTES ==========
# (Cole aqui todas as classes RendyFinanceAgent, RendyInvestAgent, RendyXAI, RendyAutoAgent, RendySupportAgent, RendyComplianceAgent exatamente como no arquivo modular V0.py)

# ========== ORQUESTRADOR ==========
class RendyOrchestrator:
    def __init__(self):
        self.finance_agent = RendyFinanceAgent()
        self.invest_agent = RendyInvestAgent()
        self.xai_agent = RendyXAI()
        self.auto_agent = RendyAutoAgent()
        self.support_agent = RendySupportAgent()
        self.compliance_agent = RendyComplianceAgent()
        self.inicializar_sessao()
    def inicializar_sessao(self):
        inicializar_ambiente()
        if 'perfil_usuario' not in st.session_state:
            st.session_state['perfil_usuario'] = None
        if 'carteira_em_montagem' not in st.session_state:
            st.session_state['carteira_em_montagem'] = []
        if 'valor_simulacao' not in st.session_state:
            st.session_state['valor_simulacao'] = 5000.0
        if 'analise_simulacao' not in st.session_state:
            st.session_state['analise_simulacao'] = None
        if 'historico_interacoes' not in st.session_state:
            st.session_state['historico_interacoes'] = []
    def salvar_interacao(self, tipo: str, dados: Dict):
        interacao = {
            'timestamp': agora_brasilia().isoformat(),
            'tipo': tipo,
            'dados': dados
        }
        st.session_state['historico_interacoes'].append(interacao)
        try:
            with open(HISTORICO_JSON, 'w', encoding='utf-8') as f:
                json.dump(st.session_state['historico_interacoes'], f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"Erro ao salvar histórico: {e}")
    def run(self):
        st.title("🤖 Rendy AI - Plataforma Inteligente de Investimentos")
        st.markdown("*Assistente didática e personalizada para iniciantes em dividendos!*")
        self.render_sidebar()
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🎯 Simulação IA", "🏆 Ranking Inteligente", "💼 Carteira", "🤖 Assistente IA", "ℹ️ Sobre"
        ])
        with tab1: self.aba_simulacao_ia()
        with tab2: self.aba_ranking_inteligente()
        with tab3: self.aba_carteira_agentica()
        with tab4: self.aba_assistente_ia()
        with tab5: self.aba_sobre()
        st.markdown("---")
        with st.expander("⚠️ Disclaimer Legal"):
            st.markdown(self.compliance_agent.gerar_disclaimer())
    # (Colar aqui os métodos render_sidebar, aba_simulacao_ia, aba_ranking_inteligente, aba_carteira_agentica, aba_assistente_ia, aba_sobre do código modular, adaptando para manter toda a experiência educativa do base!)
    # (Garanta que todas as telas, FAQ, glossário, calculadoras, histórico, simulações, XAI, gráficos, dicas, filtros, etc. estão presentes e funcionais!)

# ========== CACHE ==========
@st.cache_data(show_spinner="🔄 Analisando mercado...")
def descobrir_oportunidades_cache():
    orchestrator = RendyOrchestrator()
    analises = []
    for ticker in LISTA_TICKERS_IBOV:
        analise = orchestrator.finance_agent.analisar_ativo(ticker)
        if analise.preco_atual > 0:
            analises.append(analise)
    return sorted(analises, key=lambda x: x.score, reverse=True)

# ========== MAIN ==========
def main():
    orchestrator = RendyOrchestrator()
    orchestrator.run()

if __name__ == "__main__":
    main()
