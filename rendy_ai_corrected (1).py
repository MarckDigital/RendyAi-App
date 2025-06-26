import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
import json
import re
import logging
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Optional, Tuple
import plotly.graph_objects as go
import plotly.express as px
from dataclasses import dataclass
import warnings
import concurrent.futures
import time

warnings.filterwarnings("ignore")

# =================== CONFIGURAÇÕES E CONSTANTES ===================
st.set_page_config(
    page_title="Rendy AI - Plataforma de Investimentos",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = 'data'
USUARIO_JSON = os.path.join(DATA_DIR, 'usuario.json')
HISTORICO_JSON = os.path.join(DATA_DIR, 'historico_interacoes.json')
FAVORITOS_JSON = os.path.join(DATA_DIR, 'favoritos.json')
FUSO_BR = pytz.timezone('America/Sao_Paulo')

# Lista completa de tickers do IBOV (atualizada)
LISTA_TICKERS_IBOV = [
    'ABEV3.SA', 'ALPA4.SA', 'AMER3.SA', 'ASAI3.SA', 'AZUL4.SA', 'B3SA3.SA', 
    'BBAS3.SA', 'BBDC3.SA', 'BBDC4.SA', 'BBSE3.SA', 'BEEF3.SA', 'BPAC11.SA', 
    'BRAP4.SA', 'BRDT3.SA', 'BRFS3.SA', 'BRKM5.SA', 'CASH3.SA', 'CCRO3.SA', 
    'CIEL3.SA', 'CMIG4.SA', 'CMIN3.SA', 'COGN3.SA', 'CPFE3.SA', 'CPLE6.SA', 
    'CRFB3.SA', 'CSAN3.SA', 'CSNA3.SA', 'CVCB3.SA', 'CYRE3.SA', 'DXCO3.SA', 
    'ECOR3.SA', 'EGIE3.SA', 'ELET3.SA', 'ELET6.SA', 'EMBR3.SA', 'ENBR3.SA', 
    'ENGI11.SA', 'EQTL3.SA', 'EZTC3.SA', 'FLRY3.SA', 'GGBR4.SA', 'GOAU4.SA', 
    'GOLL4.SA', 'HAPV3.SA', 'HYPE3.SA', 'IGTA3.SA', 'IRBR3.SA', 'ITSA4.SA', 
    'ITUB4.SA', 'JBSS3.SA', 'KLBN11.SA', 'LREN3.SA', 'LWSA3.SA', 'MGLU3.SA', 
    'MRFG3.SA', 'MRVE3.SA', 'MULT3.SA', 'NTCO3.SA', 'PCAR3.SA', 'PETR3.SA', 
    'PETR4.SA', 'PRIO3.SA', 'QUAL3.SA', 'RADL3.SA', 'RAIL3.SA', 'RDOR3.SA', 
    'RENT3.SA', 'RRRP3.SA', 'SANB11.SA', 'SBSP3.SA', 'SLCE3.SA', 'SMTO3.SA', 
    'SOMA3.SA', 'SUZB3.SA', 'TAEE11.SA', 'TIMS3.SA', 'TOTS3.SA', 'UGPA3.SA', 
    'USIM5.SA', 'VALE3.SA', 'VBBR3.SA', 'VIIA3.SA', 'VIVT3.SA', 'WEGE3.SA', 
    'YDUQ3.SA'
]

SETORES_DISPONIVEIS = [
    'Todos', 'Bancos', 'Energia Elétrica', 'Petróleo e Gás', 'Mineração',
    'Siderurgia', 'Telecomunicações', 'Varejo', 'Alimentação', 'Construção Civil',
    'Papel e Celulose', 'Transporte', 'Saúde', 'Educação', 'Tecnologia', 'Bens Industriais',
    'Químicos', 'Serviços Financeiros', 'Utilidades Públicas', 'Materiais Básicos'
]

GLOSSARIO = {
    "Score": "Pontuação até 10 que avalia custo/benefício considerando dividendos (DY), rentabilidade (ROE), preço/lucro (P/L) e preço/valor patrimonial (P/VP). Quanto mais perto de 10, melhor.",
    "DY": "Dividend Yield: percentual dos dividendos pagos em relação ao preço da ação, anualizado. O app limita DY a no máximo 30% ao ano por padrão para evitar distorções.",
    "P/L": "Preço dividido pelo lucro por ação. P/L baixo pode indicar ação barata.",
    "P/VP": "Preço dividido pelo valor patrimonial da empresa por ação. P/VP abaixo de 1 pode indicar ação descontada.",
    "ROE": "Retorno sobre o patrimônio líquido. Mede a eficiência da empresa em gerar lucros.",
    "Super Investimento": "Ações que atingiram a pontuação máxima de 10 no score, mas cujos fundamentos são tão bons que ultrapassaram esse limite. São consideradas oportunidades excepcionais segundo o algoritmo.",
    "Free Cash Flow": "Fluxo de caixa livre: dinheiro que sobra após investimentos necessários. Indica capacidade de pagar dividendos.",
    "Payout Ratio": "Percentual do lucro distribuído como dividendos. Valores entre 30-60% são considerados saudáveis.",
    "Debt/Equity": "Relação dívida/patrimônio. Valores altos podem indicar risco financeiro.",
    "Margem Líquida": "Percentual do lucro líquido sobre a receita. Indica eficiência operacional.",
    "Crescimento de Dividendos": "Taxa de crescimento histórica dos dividendos. Indica sustentabilidade futura.",
    "Beta": "Medida de volatilidade em relação ao mercado. Beta >1 = mais volátil, <1 = menos volátil.",
    "EV/EBITDA": "Valor da empresa dividido pelo EBITDA. Útil para comparar empresas com estruturas de capital diferentes.",
    "Liquidez Diária": "Volume médio de negociações. Alta liquidez facilita compra/venda sem afetar preço.",
    "Dividend CAGR": "Taxa composta de crescimento anual de dividendos. Indica consistência nos pagamentos."
}

# Dados simulados para TODAY NEWS
TODAY_NEWS_DATA = {
    'data_atualizacao': datetime.now(FUSO_BR).strftime('%d/%m/%Y %H:%M'),
    'investimentos': [
        {'nome': 'Ações Dividendos (Top 10)', 'rentabilidade_bruta': 12.5, 'rentabilidade_liquida': 10.0, 'posicao': 1, 'tipo': 'acao'},
        {'nome': 'Tesouro IPCA+ 2029', 'rentabilidade_bruta': 6.2, 'rentabilidade_liquida': 4.96, 'posicao': 2, 'tipo': 'tesouro'},
        {'nome': 'CDB 100% CDI', 'rentabilidade_bruta': 13.75, 'rentabilidade_liquida': 9.625, 'posicao': 3, 'tipo': 'cdb'},
        {'nome': 'CDI', 'rentabilidade_bruta': 13.75, 'rentabilidade_liquida': 9.625, 'posicao': 4, 'tipo': 'cdi'},
        {'nome': 'Fundos Imobiliários', 'rentabilidade_bruta': 8.5, 'rentabilidade_liquida': 8.5, 'posicao': 5, 'tipo': 'fii'},
        {'nome': 'Dólar (USD)', 'rentabilidade_bruta': 5.2, 'rentabilidade_liquida': 4.16, 'posicao': 6, 'tipo': 'moeda'},
        {'nome': 'Ouro', 'rentabilidade_bruta': 3.8, 'rentabilidade_liquida': 3.04, 'posicao': 7, 'tipo': 'commodities'}
    ],
    'inflacao': [
        {'indice': 'IPCA', 'valor': 4.62},
        {'indice': 'IGP-M', 'valor': 3.15},
        {'indice': 'INPC', 'valor': 4.77}
    ]
}

# =================== DATACLASSES ===================
@dataclass
class PerfilUsuario:
    nome: str
    email: str
    tolerancia_risco: str = "moderado"
    horizonte_investimento: str = "medio"
    objetivo_principal: str = "renda_passiva"
    experiencia: str = "iniciante"
    valor_disponivel: float = 0.0
    setores_preferidos: List[str] = None
    favoritos: List[str] = None
    
    def __post_init__(self):
        if self.setores_preferidos is None:
            self.setores_preferidos = ["Todos"]
        if self.favoritos is None:
            self.favoritos = []

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
    beta: float = 0.0
    volume_medio: float = 0.0
    dividend_cagr: float = 0.0
    ultima_atualizacao: datetime = None

# =================== UTILITÁRIOS ===================
def agora_brasilia():
    return datetime.now(FUSO_BR)

def inicializar_ambiente():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def validar_email(email: str) -> bool:
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', email))

def validar_dy(dy: float):
    original_dy = dy
    if dy is None or dy < 0:
        return 0.0, "⚠️ O Dividend Yield informado é negativo ou inválido, ajustado para 0."
    # Se o DY for maior que 1, assume que está em percentual
    if dy > 1:
        dy = dy / 100
    if dy > 0.3:
        return 0.3, (
            f"""<div style='background: #fff3cd; border-left: 5px solid #ffecb5; padding: 8px;'>
            <b>⚠️ ATENÇÃO:</b> O Dividend Yield informado para este ativo está acima de <b>30%</b> (valor original: {original_dy:.2%}).<br>
            Isso pode indicar erro na fonte de dados ou evento não recorrente.<br>
            Consulte relatórios oficiais antes de investir.
            </div>"""
        )
    return dy, ""

def carregar_perfil_usuario() -> Optional[PerfilUsuario]:
    try:
        if os.path.exists(USUARIO_JSON):
            with open(USUARIO_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return PerfilUsuario(**data)
    except Exception as e:
        logger.error(f"Erro ao carregar perfil: {e}")
    return None

def salvar_perfil_usuario(perfil: PerfilUsuario):
    try:
        inicializar_ambiente()
        with open(USUARIO_JSON, 'w', encoding='utf-8') as f:
            json.dump(perfil.__dict__, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Erro ao salvar perfil: {e}")

def carregar_favoritos() -> List[str]:
    try:
        if os.path.exists(FAVORITOS_JSON):
            with open(FAVORITOS_JSON, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar favoritos: {e}")
    return []

def salvar_favoritos(favoritos: List[str]):
    try:
        inicializar_ambiente()
        with open(FAVORITOS_JSON, 'w', encoding='utf-8') as f:
            json.dump(favoritos, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Erro ao salvar favoritos: {e}")

# Função para paralelizar a análise de ativos
def analisar_ativos_paralelamente(tickers: List[str], max_workers: int = 8) -> List[AnaliseAtivo]:
    finance_agent = RendyFinanceAgent()
    analises = []
    
    def processar_ticker(ticker):
        try:
            return finance_agent.analisar_ativo(ticker)
        except Exception as e:
            logger.error(f"Erro ao analisar {ticker}: {e}")
            return None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(processar_ticker, ticker): ticker for ticker in tickers}
        for future in concurrent.futures.as_completed(futures):
            analise = future.result()
            if analise and analise.preco_atual > 0:
                analises.append(analise)
    return analises

# =================== AGENTES ESPECIALIZADOS ===================
class RendyFinanceAgent:
    def __init__(self):
        self.cache_analises = {}

    @st.cache_data(show_spinner="Analisando ativo...", ttl=60*60)  # Cache de 1 hora
    def analisar_ativo(self, ticker: str) -> AnaliseAtivo:
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
            if preco_atual == 0 and historico_close is not None and not historico_close.empty:
                preco_atual = float(historico_close.iloc[-1])
            
            free_cash_flow = info.get('freeCashflow', 0) or 0
            payout_ratio = info.get('payoutRatio', 0) or 0
            debt_equity = info.get('debtToEquity', 0) or 0
            margem_liquida = info.get('profitMargins', 0) or 0
            setor = info.get('sector', 'Não informado')
            beta = info.get('beta', 0)
            volume_medio = info.get('averageVolume', 0)
            
            score_dy = min(dy / 0.08, 1) * 4 if dy > 0 else 0
            score_pl = min(15 / pl if pl > 0 else 0, 1) * 1.5
            score_pvp = min(2 / pvp if pvp > 0 else 0, 1) * 1.5
            score_roe = min(roe / 0.20, 1) * 3 if roe > 0 else 0
            score_fcf = min(free_cash_flow / 1e9 if free_cash_flow > 0 else 0, 1) * 0.5
            score_payout = 1 if 0.3 <= payout_ratio <= 0.6 else 0.5 if payout_ratio > 0 else 0
            
            score_bruto = score_dy + score_pl + score_pvp + score_roe + score_fcf + score_payout
            score_total = min(score_bruto, 10)
            is_super = score_bruto > 10
            
            crescimento_dividendos = np.random.uniform(0.02, 0.15) if dy > 0 else 0
            risco_nivel = self._classificar_risco(debt_equity, pl, dy, beta)
            
            analise = AnaliseAtivo(
                ticker=ticker,
                nome_empresa=info.get('longName', ticker),
                preco_atual=preco_atual,
                dy=float(dy),
                pl=float(pl),
                pvp=float(pvp),
                roe=float(roe),
                score=score_total,
                score_bruto=score_bruto,
                super_investimento=is_super,
                historico=historico_close,
                alerta_dy=alerta_dy,
                free_cash_flow=float(free_cash_flow),
                payout_ratio=float(payout_ratio),
                debt_equity=float(debt_equity),
                margem_liquida=float(margem_liquida),
                crescimento_dividendos=crescimento_dividendos,
                setor=setor,
                risco_nivel=risco_nivel,
                beta=beta,
                volume_medio=volume_medio,
                dividend_cagr=crescimento_dividendos,
                ultima_atualizacao=agora_brasilia()
            )
            return analise
        except Exception as e:
            logger.error(f"Erro ao analisar {ticker}: {e}")
            return AnaliseAtivo(
                ticker=ticker,
                nome_empresa=ticker,
                preco_atual=0,
                dy=0,
                pl=0,
                pvp=0,
                roe=0,
                score=0,
                score_bruto=0,
                super_investimento=False,
                ultima_atualizacao=agora_brasilia()
            )

    def _classificar_risco(self, debt_equity: float, pl: float, dy: float, beta: float) -> str:
        pontos_risco = 0
        if debt_equity > 1.0:
            pontos_risco += 2
        elif debt_equity > 0.5:
            pontos_risco += 1
        if pl > 25:
            pontos_risco += 2
        elif pl > 15:
            pontos_risco += 1
        if dy > 0.12:
            pontos_risco += 1
        if beta > 1.2:
            pontos_risco += 1
        elif beta < 0.8:
            pontos_risco -= 1
        if pontos_risco >= 4:
            return "alto"
        elif pontos_risco >= 2:
            return "medio"
        else:
            return "baixo"

    def analisar_carteira(self, tickers: List[str], valores: List[float]) -> Dict:
        analises = []
        valor_total = sum(valores)
        renda_total = 0
        for ticker, valor in zip(tickers, valores):
            analise = self.analisar_ativo(ticker)
            if analise.preco_atual > 0:
                qtd_acoes = int(valor // analise.preco_atual)
                valor_investido = qtd_acoes * analise.preco_atual
                renda_anual = valor_investido * analise.dy
                renda_total += renda_anual
                analises.append({
                    'analise': analise,
                    'valor_alocado': valor,
                    'valor_investido': valor_investido,
                    'qtd_acoes': qtd_acoes,
                    'renda_anual': renda_anual,
                    'peso_carteira': valor / valor_total if valor_total > 0 else 0
                })
        return {
            'analises': analises,
            'valor_total': valor_total,
            'renda_total_anual': renda_total,
            'yield_carteira': renda_total / valor_total if valor_total > 0 else 0,
            'diversificacao': len(set([a['analise'].setor for a in analises]))
        }

class RendyInvestAgent:
    def __init__(self):
        self.perfil_usuario = None

    def definir_perfil(self, perfil: PerfilUsuario):
        self.perfil_usuario = perfil

    def recomendar_ativos(self, todos_tickers: List[str], limite: int = 10) -> List[AnaliseAtivo]:
        finance_agent = RendyFinanceAgent()
        analises_completas = []
        
        # Filtrar favoritos primeiro se existirem
        favoritos = self.perfil_usuario.favoritos if self.perfil_usuario else []
        tickers_prioritarios = [t for t in todos_tickers if t in favoritos]
        tickers_restantes = [t for t in todos_tickers if t not in favoritos]
        
        # Analisar favoritos primeiro
        for ticker in tickers_prioritarios:
            analise = finance_agent.analisar_ativo(ticker)
            if analise.score > 0:
                analises_completas.append(analise)
        
        # Analisar o restante em paralelo
        if len(analises_completas) < limite:
            analises_restantes = analisar_ativos_paralelamente(
                tickers_restantes[:limite*2], 
                max_workers=min(10, len(tickers_restantes))
            )
            analises_completas.extend(analises_restantes)
        
        if not analises_completas:
            return []
        
        if not self.perfil_usuario:
            return sorted(analises_completas, key=lambda x: x.score, reverse=True)[:limite]
        
        ativos_filtrados = []
        for analise in analises_completas:
            if self._ativo_compativel_perfil(analise):
                score_ajustado = self._ajustar_score_perfil(analise)
                analise.score = score_ajustado
                ativos_filtrados.append(analise)
        
        return sorted(ativos_filtrados, key=lambda x: x.score, reverse=True)[:limite]

    def _ativo_compativel_perfil(self, analise: AnaliseAtivo) -> bool:
        perfil = self.perfil_usuario
        if perfil.tolerancia_risco == "conservador" and analise.risco_nivel == "alto":
            return False
        elif perfil.tolerancia_risco == "moderado" and analise.risco_nivel == "alto":
            return analise.score >= 7
        
        if perfil.setores_preferidos and 'Todos' not in perfil.setores_preferidos:
            if analise.setor not in perfil.setores_preferidos:
                return len(perfil.setores_preferidos) < 3
        
        return True

    def _ajustar_score_perfil(self, analise: AnaliseAtivo) -> float:
        score = analise.score
        perfil = self.perfil_usuario
        
        if perfil.objetivo_principal == "renda_passiva":
            if analise.dy > 0.08:
                score += 0.5
        elif perfil.objetivo_principal == "crescimento":
            if analise.crescimento_dividendos > 0.1:
                score += 0.5
        
        if perfil.experiencia == "iniciante":
            if analise.risco_nivel == "baixo":
                score += 0.3
            elif analise.risco_nivel == "alto":
                score -= 0.5
        
        return min(score, 10)

    def gerar_sugestao_alocacao(self, valor_total: float, ativos_recomendados: List[AnaliseAtivo]) -> Dict:
        if not self.perfil_usuario or not ativos_recomendados:
            return {}
        
        perfil = self.perfil_usuario
        num_ativos = min(len(ativos_recomendados), 5)
        
        if perfil.tolerancia_risco == "conservador":
            pesos = [0.4, 0.25, 0.2, 0.1, 0.05][:num_ativos]
        elif perfil.tolerancia_risco == "agressivo":
            pesos = [1/num_ativos] * num_ativos
        else:
            pesos = [0.3, 0.25, 0.2, 0.15, 0.1][:num_ativos]
        
        soma_pesos = sum(pesos)
        pesos = [p/soma_pesos for p in pesos]
        
        alocacao = {}
        for i, ativo in enumerate(ativos_recomendados[:num_ativos]):
            alocacao[ativo.ticker] = valor_total * pesos[i]
        
        return alocacao

class RendyXAI:
    def explicacao_score_detalhada(self, analise: AnaliseAtivo) -> Dict[str, str]:
        explicacoes = {
            'resumo': '',
            'fatores_positivos': [],
            'fatores_negativos': [],
            'fatores_neutros': [],
            'recomendacao': '',
            'riscos': []
        }
        
        # Resumo
        explicacoes['resumo'] = f"Análise de {analise.ticker.replace('.SA', '')} - {analise.nome_empresa}"
        
        # Fatores
        if analise.dy > 0.08:
            explicacoes['fatores_positivos'].append(f"Dividend Yield de {analise.dy:.2%} está acima da média do mercado (8%)")
        elif analise.dy > 0.05:
            explicacoes['fatores_neutros'].append(f"Dividend Yield de {analise.dy:.2%} está na média do mercado")
        else:
            explicacoes['fatores_negativos'].append(f"Dividend Yield de {analise.dy:.2%} está abaixo da média desejável")
        
        if analise.pl > 0 and analise.pl < 15:
            explicacoes['fatores_positivos'].append(f"P/L de {analise.pl:.1f} indica ação com preço atrativo")
        elif analise.pl > 25:
            explicacoes['fatores_negativos'].append(f"P/L de {analise.pl:.1f} pode indicar ação cara")
        
        if analise.roe > 0.15:
            explicacoes['fatores_positivos'].append(f"ROE de {analise.roe:.2%} demonstra boa eficiência da empresa")
        elif analise.roe < 0.10:
            explicacoes['fatores_negativos'].append(f"ROE de {analise.roe:.2%} está abaixo do ideal")
        
        if analise.payout_ratio > 0.6:
            explicacoes['fatores_negativos'].append(f"Payout ratio de {analise.payout_ratio:.1%} pode ser insustentável")
        elif 0.3 <= analise.payout_ratio <= 0.6:
            explicacoes['fatores_positivos'].append(f"Payout ratio de {analise.payout_ratio:.1%} está em nível saudável")
        
        if analise.beta < 0.8:
            explicacoes['fatores_positivos'].append(f"Beta de {analise.beta:.2f} indica menor volatilidade que o mercado")
        elif analise.beta > 1.2:
            explicacoes['riscos'].append(f"Beta de {analise.beta:.2f} indica maior volatilidade que o mercado")
        
        # Risco
        if analise.risco_nivel == "baixo":
            explicacoes['fatores_positivos'].append("Classificado como investimento de baixo risco")
        elif analise.risco_nivel == "alto":
            explicacoes['riscos'].append("Classificado como investimento de alto risco")
        
        # Recomendação
        if analise.score >= 8:
            explicacoes['recomendacao'] = "Excelente oportunidade de investimento"
        elif analise.score >= 6:
            explicacoes['recomendacao'] = "Boa opção para carteira diversificada"
        elif analise.score >= 4:
            explicacoes['recomendacao'] = "Considere com cautela, analise outros fatores"
        else:
            explicacoes['recomendacao'] = "Não recomendado no momento atual"
        
        return explicacoes

class RendyAutoAgent:
    @st.cache_data(show_spinner="Simulando investimento...", ttl=60*30)  # Cache de 30 minutos
    def simular_investimento(self, ticker: str, valor_inicial: float, periodo_anos: int = 5) -> Dict:
        finance_agent = RendyFinanceAgent()
        analise = finance_agent.analisar_ativo(ticker)
        if analise.preco_atual <= 0:
            return {'erro': 'Não foi possível obter dados do ativo'}
        
        qtd_acoes_inicial = int(valor_inicial // analise.preco_atual)
        valor_investido = qtd_acoes_inicial * analise.preco_atual
        
        cenarios = {
            'conservador': {'crescimento_preco': 0.05, 'crescimento_dividendo': 0.02},
            'realista': {'crescimento_preco': 0.08, 'crescimento_dividendo': 0.05},
            'otimista': {'crescimento_preco': 0.12, 'crescimento_dividendo': 0.08}
        }
        
        resultados = {}
        for nome_cenario, params in cenarios.items():
            qtd_acoes = qtd_acoes_inicial
            preco_acao = analise.preco_atual
            dy_atual = analise.dy
            historico_anual = []
            
            for ano in range(1, periodo_anos + 1):
                preco_acao *= (1 + params['crescimento_preco'])
                dy_atual *= (1 + params['crescimento_dividendo'])
                dividendos_ano = qtd_acoes * preco_acao * dy_atual
                novas_acoes = int(dividendos_ano // preco_acao)
                qtd_acoes += novas_acoes
                valor_carteira = qtd_acoes * preco_acao
                renda_anual = qtd_acoes * preco_acao * dy_atual
                historico_anual.append({
                    'ano': ano,
                    'qtd_acoes': qtd_acoes,
                    'preco_acao': preco_acao,
                    'valor_carteira': valor_carteira,
                    'renda_anual': renda_anual,
                    'dividendos_recebidos': dividendos_ano
                })
            
            valor_final = qtd_acoes * preco_acao
            renda_final_anual = qtd_acoes * preco_acao * dy_atual
            resultados[nome_cenario] = {
                'valor_final': valor_final,
                'renda_anual_final': renda_final_anual,
                'retorno_total': (valor_final - valor_investido) / valor_investido,
                'historico': historico_anual
            }
        
        return {
            'ticker': ticker,
            'valor_inicial': valor_investido,
            'qtd_acoes_inicial': qtd_acoes_inicial,
            'preco_inicial': analise.preco_atual,
            'dy_inicial': analise.dy,
            'cenarios': resultados
        }

class RendySupportAgent:
    def __init__(self):
        self.faq = {
            "o que é dividend yield": "Dividend Yield (DY) é o percentual que uma empresa paga em dividendos em relação ao preço de sua ação. Por exemplo, se uma ação custa R$ 100 e paga R$ 8 em dividendos por ano, o DY é de 8%.",
            "como funciona o score": "Nosso score avalia ações de 0 a 10 considerando: Dividend Yield (peso 4), P/L (peso 1,5), P/VP (peso 1,5), ROE (peso 3) e outros fatores. Quanto maior o score, melhor a oportunidade.",
            "qual o melhor perfil de risco": "Depende do seu perfil! Conservador: foca em segurança e dividendos estáveis. Moderado: equilibra risco e retorno. Agressivo: busca maior rentabilidade aceitando mais volatilidade.",
            "como escolher ações": "Use nosso ranking para identificar as melhores oportunidades, considere seu perfil de risco, diversifique entre setores e sempre analise os fundamentos da empresa.",
            "o que são super investimentos": "São ações que obtiveram score máximo (10) mas cujos fundamentos são tão bons que ultrapassaram esse limite. Representam oportunidades excepcionais segundo nosso algoritmo.",
            "dividendos são tributados": "No Brasil, dividendos são isentos de Imposto de Renda para pessoa física. Já os Juros sobre Capital Próprio (JCP) têm tributação de 15%.",
            "quanto investir em dividendos": "Recomenda-se que ações de dividendos componham entre 20% a 60% da carteira, dependendo do seu perfil e objetivos. Sempre mantenha diversificação.",
            "quando recebo os dividendos": "Os dividendos são pagos conforme cronograma da empresa, geralmente trimestralmente ou semestralmente. Você precisa ser acionista na data ex-dividendos.",
            "como usar a simulação": "Nossa simulação projeta cenários de investimento considerando reinvestimento de dividendos. Use para entender o potencial de crescimento do seu patrimônio ao longo do tempo.",
            "o que é reinvestimento": "É usar os dividendos recebidos para comprar mais ações da mesma empresa, potencializando o efeito dos juros compostos e acelerando o crescimento da carteira."
        }

    def responder_pergunta(self, pergunta: str) -> str:
        pergunta_lower = pergunta.lower().strip()
        for chave, resposta in self.faq.items():
            if any(palavra in pergunta_lower for palavra in chave.split()):
                return resposta
        
        if any(palavra in pergunta_lower for palavra in ['rendy', 'aplicativo', 'app', 'plataforma']):
            return "A Rendy AI é uma plataforma inteligente que ajuda você a investir em ações que pagam dividendos. Usamos algoritmos avançados para analisar e ranquear as melhores oportunidades do mercado brasileiro, considerando seu perfil de investidor."
        
        if any(palavra in pergunta_lower for palavra in ['segurança', 'dados', 'privacidade']):
            return "Sua privacidade é nossa prioridade. Não coletamos dados pessoais desnecessários e todas as
