
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
    def analisar_ativo(_self, ticker: str) -> AnaliseAtivo:
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
            risco_nivel = _self._classificar_risco(debt_equity, pl, dy, beta)
            
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
    def simular_investimento(_self, ticker: str, valor_inicial: float, periodo_anos: int = 5) -> Dict:
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
            return "Sua privacidade é nossa prioridade. Não coletamos dados pessoais desnecessários e todas as informações são processadas localmente. Seus dados de perfil ficam armazenados apenas no seu dispositivo."
        
        if any(palavra in pergunta_lower for palavra in ['começar', 'iniciar', 'primeiro']):
            return "Para começar: 1) Preencha seu perfil de investidor, 2) Explore nosso ranking de ações, 3) Use a simulação para entender o potencial, 4) Monte sua carteira com nossa ajuda. Sempre invista apenas o que pode perder!"
        
        return "Desculpe, não encontrei uma resposta específica para sua pergunta. Tente perguntar sobre: dividend yield, score, perfil de risco, como escolher ações, super investimentos, tributação, simulação ou reinvestimento. Nossa equipe está sempre trabalhando para melhorar o atendimento!"
    
    def calcular_renda_objetivo(self, renda_mensal_desejada: float, dy_medio: float = 0.08) -> Dict:
        renda_anual = renda_mensal_desejada * 12
        capital_necessario = renda_anual / dy_medio
        return {
            'renda_mensal': renda_mensal_desejada,
            'renda_anual': renda_anual,
            'capital_necessario': capital_necessario,
            'dy_considerado': dy_medio
        }
    
    def calcular_aporte_necessario(self, capital_objetivo: float, capital_atual: float, 
                                 prazo_meses: int, rentabilidade_mensal: float = 0.008) -> Dict:
        if prazo_meses <= 0:
            return {'erro': 'Prazo deve ser maior que zero'}
        
        fv_capital_atual = capital_atual * ((1 + rentabilidade_mensal) ** prazo_meses)
        valor_restante = capital_objetivo - fv_capital_atual
        
        if valor_restante <= 0:
            aporte_mensal = 0
        else:
            fator = ((1 + rentabilidade_mensal) ** prazo_meses - 1) / rentabilidade_mensal
            aporte_mensal = valor_restante / fator
        
        return {
            'capital_objetivo': capital_objetivo,
            'capital_atual': capital_atual,
            'prazo_meses': prazo_meses,
            'aporte_mensal': aporte_mensal,
            'total_aportes': aporte_mensal * prazo_meses,
            'rentabilidade_mensal': rentabilidade_mensal
        }
    
    def gerar_dica_educacional(self, perfil: PerfilUsuario = None) -> str:
        dicas_gerais = [
            "💡 Dica: Diversifique sempre! Não coloque todos os ovos na mesma cesta.",
            "📚 Lembre-se: Dividend Yield muito alto pode ser uma armadilha. Analise a sustentabilidade.",
            "⏰ Paciência é fundamental: Investimentos em dividendos são para o longo prazo.",
            "🔍 Sempre verifique o Payout Ratio: entre 30-60% é considerado saudável.",
            "📈 Reinvestir dividendos potencializa o efeito dos juros compostos."
        ]
        
        if perfil and perfil.experiencia == "iniciante":
            dicas_iniciante = [
                "🎯 Para iniciantes: Comece com empresas conhecidas e setores que você entende.",
                "📖 Estude os fundamentos: ROE, P/L e P/VP são seus melhores amigos.",
                "💰 Comece pequeno: Invista valores que não farão falta no seu orçamento."
            ]
            return np.random.choice(dicas_iniciante)
        
        return np.random.choice(dicas_gerais)

class RendyComplianceAgent:
    def gerar_disclaimer(self) -> str:
        return """
        **⚠️ IMPORTANTE - DISCLAIMER DE INVESTIMENTOS**
        
        As informações fornecidas pela Rendy AI são apenas para fins educacionais e não constituem recomendação de investimento. • **Riscos**: Todo investimento envolve riscos, incluindo a possibilidade de perda do capital investido. • **Decisão Própria**: As decisões de investimento são de sua inteira responsabilidade. • **Consultoria**: Considere consultar um assessor de investimentos qualificado.
        • **Dados**: As informações podem conter erros ou estar desatualizadas. • **Tributação**: Consulte um contador sobre aspectos tributários.
        
        **A Rendy AI não se responsabiliza por perdas decorrentes do uso destas informações.**
        """
    
    def avaliar_risco_carteira(self, analises_carteira: List[Dict]) -> Dict:
        if not analises_carteira:
            return {'risco': 'indefinido', 'recomendacoes': []}
        
        riscos_altos = sum(1 for a in analises_carteira if a['analise'].risco_nivel == 'alto')
        total_ativos = len(analises_carteira)
        percentual_alto_risco = riscos_altos / total_ativos
        
        setores = set(a['analise'].setor for a in analises_carteira)
        diversificacao_setorial = len(setores)
        
        recomendacoes = []
        
        # Análise de concentração por setor
        setores_dist = {}
        for item in analises_carteira:
            setor = item['analise'].setor
            peso = item['peso_carteira']
            setores_dist[setor] = setores_dist.get(setor, 0) + peso
        
        for setor, peso in setores_dist.items():
            if peso > 0.4:
                recomendacoes.append(f"Concentração excessiva no setor {setor} ({peso*100:.1f}%)")
        
        # Análise de concentração por ativo
        for item in analises_carteira:
            if item['peso_carteira'] > 0.3:
                recomendacoes.append(
                    f"Concentração excessiva em {item['analise'].ticker.replace('.SA', '')} ({item['peso_carteira']*100:.1f}%)"
                )
        
        # Análise de risco geral da carteira
        if percentual_alto_risco > 0.3:
            risco_geral = "muito_alto"
            recomendacoes.append("Reduza a exposição a ativos de alto risco.")
        elif percentual_alto_risco > 0.1:
            risco_geral = "alto"
            recomendacoes.append("Considere reduzir a exposição a ativos de alto risco.")
        elif percentual_alto_risco == 0 and diversificacao_setorial >= 3:
            risco_geral = "baixo"
        else:
            risco_geral = "moderado"
            
        if diversificacao_setorial < 3 and total_ativos >= 3:
            recomendacoes.append("Melhore a diversificação setorial da sua carteira.")

        return {'risco': risco_geral, 'recomendacoes': list(set(recomendacoes))} # Remove duplicates
class RendyOrchestrator:
    def __init__(self):
        self.invest_agent = RendyInvestAgent()
        self.finance_agent = RendyFinanceAgent()
        self.auto_agent = RendyAutoAgent()
        self.xai_agent = RendyXAI()
        self.support_agent = RendySupportAgent()
        self.compliance_agent = RendyComplianceAgent()
        
        if 'carteira' not in st.session_state:
            st.session_state.carteira = []
        if 'historico_simulacao' not in st.session_state:
            st.session_state.historico_simulacao = []
        if 'perfil_usuario' not in st.session_state:
            st.session_state.perfil_usuario = carregar_perfil_usuario()

    def _salvar_interacao_historico(self, tipo: str, detalhes: str):
        historico = []
        if os.path.exists(HISTORICO_JSON):
            with open(HISTORICO_JSON, 'r', encoding='utf-8') as f:
                historico = json.load(f)
        
        historico.append({
            'timestamp': agora_brasilia().isoformat(),
            'tipo': tipo,
            'detalhes': detalhes
        })
        
        with open(HISTORICO_JSON, 'w', encoding='utf-8') as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)

    def aba_perfil_usuario(self):
        st.markdown("### 👤 Meu Perfil de Investidor")

        st.info("Preencha ou atualize seu perfil para receber recomendações mais personalizadas.")

        with st.form("form_perfil"):
            perfil = st.session_state.perfil_usuario
            
            nome = st.text_input("Nome", value=perfil.nome if perfil else "", key="perfil_nome")
            email = st.text_input("E-mail", value=perfil.email if perfil else "", key="perfil_email")
            
            tolerancia_risco = st.selectbox(
                "Qual sua tolerância a risco?",
                ["conservador", "moderado", "agressivo"],
                index=["conservador", "moderado", "agressivo"].index(perfil.tolerancia_risco) if perfil else 1,
                key="perfil_risco"
            )
            
            horizonte_investimento = st.selectbox(
                "Qual seu horizonte de investimento?",
                ["curto_prazo", "medio_prazo", "longo_prazo"],
                index=["curto_prazo", "medio_prazo", "longo_prazo"].index(perfil.horizonte_investimento) if perfil else 1,
                format_func=lambda x: x.replace('_', ' ').title(),
                key="perfil_horizonte"
            )
            
            objetivo_principal = st.selectbox(
                "Qual seu objetivo principal de investimento?",
                ["crescimento", "renda_passiva", "preservacao_capital"],
                index=["crescimento", "renda_passiva", "preservacao_capital"].index(perfil.objetivo_principal) if perfil else 1,
                format_func=lambda x: x.replace('_', ' ').title(),
                key="perfil_objetivo"
            )
            
            experiencia = st.selectbox(
                "Qual seu nível de experiência com investimentos?",
                ["iniciante", "intermediario", "avancado"],
                index=["iniciante", "intermediario", "avancado"].index(perfil.experiencia) if perfil else 0,
                key="perfil_experiencia"
            )
            
            valor_disponivel = st.number_input(
                "Valor disponível para investir (R$)",
                min_value=0.0,
                value=perfil.valor_disponivel if perfil else 0.0,
                step=100.0,
                format="%.2f",
                key="perfil_valor"
            )
            
            setores_preferidos = st.multiselect(
                "Setores de preferência (opcional)",
                SETORES_DISPONIVEIS,
                default=perfil.setores_preferidos if perfil else ["Todos"],
                key="perfil_setores"
            )

            submit_button = st.form_submit_button("Salvar Perfil")

            if submit_button:
                if not validar_email(email):
                    st.error("Por favor, insira um e-mail válido.")
                elif not nome.strip():
                    st.error("Por favor, insira seu nome.")
                else:
                    novo_perfil = PerfilUsuario(
                        nome=nome,
                        email=email,
                        tolerancia_risco=tolerancia_risco,
                        horizonte_investimento=horizonte_investimento,
                        objetivo_principal=objetivo_principal,
                        experiencia=experiencia,
                        valor_disponivel=valor_disponivel,
                        setores_preferidos=setores_preferidos
                    )
                    salvar_perfil_usuario(novo_perfil)
                    st.session_state.perfil_usuario = novo_perfil
                    self.invest_agent.definir_perfil(novo_perfil)
                    st.success("Perfil atualizado com sucesso!")
                    self._salvar_interacao_historico("perfil_atualizado", f"Perfil de {nome} atualizado.")

        st.markdown("---")
        st.markdown("#### 🎁 Dica Educacional")
        dica = self.support_agent.gerar_dica_educacional(st.session_state.perfil_usuario)
        st.info(dica)

    def aba_ranking_acoes(self):
        st.markdown("### 🏆 Ranking das Ações")
        st.info("Confira as ações com maior pontuação de acordo com nosso algoritmo.")

        perfil = carregar_perfil_usuario()
        if perfil:
            self.invest_agent.definir_perfil(perfil)
        else:
            st.warning("⚠️ Por favor, preencha seu perfil de investidor na aba 'Meu Perfil' para obter recomendações personalizadas.")

        st.markdown("---")
        st.markdown("#### 🔎 Filtrar Ações")
        col1, col2, col3 = st.columns(3)
        with col1:
            setor_selecionado = st.selectbox("Filtrar por Setor", SETORES_DISPONIVEIS)
        with col2:
            min_score = st.slider("Score Mínimo", 0, 10, 6)
        with col3:
            apenas_super_investimento = st.checkbox("Apenas Super Investimentos")
        
        if st.button("🔄 Atualizar Ranking", type="primary"):
            st.cache_data.clear() # Clear cache for fresh data
            st.rerun()

        st.markdown("---")
        st.markdown("#### 📊 Ações Ranqueadas")

        with st.spinner("Analisando ações... Isso pode levar alguns segundos."):
            recomendacoes = self.invest_agent.recomendar_ativos(LISTA_TICKERS_IBOV, limite=50) # Increased limit for filtering
            
            if setor_selecionado != "Todos":
                recomendacoes = [a for a in recomendacoes if a.setor == setor_selecionado]
            
            recomendacoes = [a for a in recomendacoes if a.score >= min_score]

            if apenas_super_investimento:
                recomendacoes = [a for a in recomendacoes if a.super_investimento]

            if not recomendacoes:
                st.warning("Nenhuma ação encontrada com os filtros selecionados.")
                return

            # Display results in a table
            data = []
            for analise in recomendacoes:
                data.append({
                    "Ticker": analise.ticker.replace('.SA', ''),
                    "Empresa": analise.nome_empresa,
                    "Preço Atual": f"R$ {analise.preco_atual:.2f}",
                    "Score": f"{analise.score:.1f} {'✨' if analise.super_investimento else ''}",
                    "DY": f"{analise.dy:.2%}",
                    "P/L": f"{analise.pl:.1f}",
                    "P/VP": f"{analise.pvp:.1f}",
                    "ROE": f"{analise.roe:.2%}",
                    "Setor": analise.setor,
                    "Risco": analise.risco_nivel.replace('_', ' ').title()
                })
            
            df_ranking = pd.DataFrame(data)
            st.dataframe(df_ranking, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("##### Detalhes e Ações")
            col_detail, col_add = st.columns([2, 1])

            with col_detail:
                selected_ticker = st.selectbox(
                    "Selecione uma ação para ver detalhes ou adicionar à carteira:",
                    [r['Ticker'] for r in data],
                    key="ranking_select_ticker"
                )
            
            if selected_ticker:
                analise_selecionada = next((a for a in recomendacoes if a.ticker.replace('.SA', '') == selected_ticker), None)
                if analise_selecionada:
                    st.markdown(f"###### Detalhes de {analise_selecionada.nome_empresa} ({selected_ticker})")
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.metric("Preço Atual", f"R$ {analise_selecionada.preco_atual:.2f}")
                        st.metric("Dividend Yield", f"{analise_selecionada.dy:.2%}")
                        st.metric("P/L", f"{analise_selecionada.pl:.1f}")
                        st.metric("P/VP", f"{analise_selecionada.pvp:.1f}")
                    with col_info2:
                        st.metric("ROE", f"{analise_selecionada.roe:.2%}")
                        st.metric("Score", f"{analise_selecionada.score:.1f}")
                        st.metric("Setor", analise_selecionada.setor)
                        st.metric("Risco", analise_selecionada.risco_nivel.replace('_', ' ').title())
                    
                    if analise_selecionada.alerta_dy:
                        st.markdown(analise_selecionada.alerta_dy, unsafe_allow_html=True)
                    
                    with st.expander("Ver explicação detalhada do Score"):
                        explicacao = self.xai_agent.explicacao_score_detalhada(analise_selecionada)
                        st.markdown(f"**Resumo:** {explicacao['resumo']}")
                        if explicacao['fatores_positivos']:
                            st.markdown("**Fatores Positivos:**")
                            for ponto in explicacao['fatores_positivos']:
                                st.markdown(f"• {ponto}")
                        if explicacao['fatores_negativos']:
                            st.markdown("**Fatores Negativos:**")
                            for ponto in explicacao['fatores_negativos']:
                                st.markdown(f"• {ponto}")
                        if explicacao['fatores_neutros']:
                            st.markdown("**Fatores Neutros:**")
                            for ponto in explicacao['fatores_neutros']:
                                st.markdown(f"• {ponto}")
                        if explicacao['riscos']:
                            st.markdown("**Riscos:**")
                            for ponto in explicacao['riscos']:
                                st.markdown(f"• {ponto}")
                        if explicacao['recomendacao']:
                            st.info(f"**Recomendação:** {explicacao['recomendacao']}")

                    with col_add:
                        st.markdown("###### Adicionar à Carteira")
                        valor_para_adicionar = st.number_input(
                            f"Valor para {selected_ticker} (R$)",
                            min_value=0.0, 
                            value=1000.0, 
                            step=100.0, 
                            format="%.2f",
                            key=f"valor_add_ranking_{selected_ticker}"
                        )
                        if st.button(f"➕ Adicionar {selected_ticker}", key=f"add_ranking_{selected_ticker}", type="primary"):
                            if valor_para_adicionar > 0:
                                # Ensure it's not already in the carteira or update existing one
                                found = False
                                for item in st.session_state.carteira:
                                    if item['Ativo'] == analise_selecionada.ticker:
                                        item['Quantidade'] += int(valor_para_adicionar // analise_selecionada.preco_atual)
                                        # Recalculate average price (simple average for now, could be weighted)
                                        item['Preço Médio'] = (item['Preço Médio'] + analise_selecionada.preco_atual) / 2
                                        item['Valor Alocado'] += valor_para_adicionar
                                        found = True
                                        break
                                if not found:
                                    st.session_state.carteira.append({
                                        'Ativo': analise_selecionada.ticker,
                                        'Nome': analise_selecionada.nome_empresa,
                                        'Quantidade': int(valor_para_adicionar // analise_selecionada.preco_atual),
                                        'Preço Médio': analise_selecionada.preco_atual,
                                        'Valor Alocado': valor_para_adicionar,
                                        'DY': analise_selecionada.dy,
                                        'Setor': analise_selecionada.setor
                                    })
                                st.success(f"{selected_ticker} adicionado/atualizado na carteira! Role para baixo para ver e gerenciar sua carteira atualizada.")
                                self._salvar_interacao_historico("acao_adicionada_ranking", f"Adicionou {selected_ticker} com valor {valor_para_adicionar}")
                                st.rerun()
                            else:
                                st.warning("Por favor, insira um valor maior que zero para adicionar à carteira.")

    def aba_simulacao_investimento(self):
        st.markdown("### 📈 Simulação de Investimento")
        st.info("Simule o potencial de crescimento dos seus investimentos ao longo do tempo, considerando o reinvestimento de dividendos.")

        col1, col2 = st.columns(2)
        with col1:
            ticker_simulacao = st.text_input("Ticker da Ação (ex: VALE3.SA)", key="sim_ticker").upper()
        with col2:
            valor_inicial_simulacao = st.number_input("Valor Inicial (R$)", min_value=10.0, value=1000.0, step=100.0, format="%.2f", key="sim_valor_inicial")
        
        periodo_anos = st.slider("Período de Simulação (anos)", 1, 30, 5, key="sim_periodo")

        if st.button("🚀 Iniciar Simulação", type="primary"):
            if ticker_simulacao:
                with st.spinner(f"Simulando {ticker_simulacao} por {periodo_anos} anos..."):
                    resultado_simulacao = self.auto_agent.simular_investimento(ticker_simulacao, valor_inicial_simulacao, periodo_anos)
                    
                    if 'erro' in resultado_simulacao:
                        st.error(f"Erro na simulação: {resultado_simulacao['erro']}")
                    else:
                        st.session_state.historico_simulacao.append(resultado_simulacao)
                        self._salvar_interacao_historico("simulacao_realizada", f"Simulou {ticker_simulacao} por {periodo_anos} anos.")
                        st.success(f"Simulação para {ticker_simulacao} concluída com sucesso! Role para baixo para ver e gerenciar sua carteira atualizada.")
                        st.rerun()
            else:
                st.warning("Por favor, insira o ticker da ação para simular.")

        st.markdown("---")
        st.markdown("#### 📜 Histórico de Simulações")

        if st.session_state.historico_simulacao:
            for idx, simulacao in enumerate(st.session_state.historico_simulacao):
                ticker = simulacao['ticker'].replace('.SA', '')
                st.markdown(f"##### Simulação para {ticker}")
                col_sim1, col_sim2, col_sim3 = st.columns(3)
                with col_sim1:
                    st.metric("Valor Inicial", f"R$ {simulacao['valor_inicial']:.2f}")
                with col_sim2:
                    st.metric("Preço Inicial da Ação", f"R$ {simulacao['preco_inicial']:.2f}")
                with col_sim3:
                    st.metric("DY Inicial da Ação", f"{simulacao['dy_inicial']:.2%}")

                st.markdown("###### Resultados por Cenário:")
                for cenario, dados in simulacao['cenarios'].items():
                    with st.expander(f"Cenário {cenario.replace('_', ' ').title()}"):
                        st.markdown(f"**Valor Final da Carteira:** R$ {dados['valor_final']:.2f}")
                        st.markdown(f"**Renda Anual Final:** R$ {dados['renda_anual_final']:.2f}")
                        st.markdown(f"**Retorno Total:** {dados['retorno_total']:.2%}")

                        df_historico = pd.DataFrame(dados['historico'])
                        df_historico.columns = [col.replace('_', ' ').title() for col in df_historico.columns]
                        st.dataframe(df_historico, use_container_width=True, hide_index=True)

                col_actions_sim = st.columns(2)
                with col_actions_sim[0]:
                    if st.button(f"➕ Adicionar {ticker} à Carteira (Sim.)", key=f"add_sim_{ticker}_{idx}", type="secondary"):
                        # Get the latest price for calculation (assuming realist scenario final price)
                        analise_atual = self.finance_agent.analisar_ativo(simulacao['ticker'])
                        if analise_atual.preco_atual > 0:
                            # Add initial simulated quantity to portfolio, or update if exists
                            found = False
                            for item in st.session_state.carteira:
                                if item['Ativo'] == simulacao['ticker']:
                                    item['Quantidade'] += simulacao['qtd_acoes_inicial']
                                    # Recalculate average price (simple average for now)
                                    item['Preço Médio'] = (item['Preço Médio'] + simulacao['preco_inicial']) / 2
                                    item['Valor Alocado'] += simulacao['valor_inicial']
                                    found = True
                                    break
                            if not found:
                                st.session_state.carteira.append({
                                    'Ativo': simulacao['ticker'],
                                    'Nome': analise_atual.nome_empresa,
                                    'Quantidade': simulacao['qtd_acoes_inicial'],
                                    'Preço Médio': simulacao['preco_inicial'],
                                    'Valor Alocado': simulacao['valor_inicial'],
                                    'DY': simulacao['dy_inicial'],
                                    'Setor': analise_atual.setor if analise_atual.setor != "Não informado" else "Diversos"
                                })
                            st.success(f"{ticker} (simulado) adicionado/atualizado à carteira! Role para baixo para ver e gerenciar sua carteira atualizada.")
                            self._salvar_interacao_historico("acao_adicionada_simulacao", f"Adicionou {ticker} (simulado) à carteira.")
                            st.rerun()
                        else:
                            st.error(f"Não foi possível adicionar {ticker} à carteira: não há dados de preço atual.")
                with col_actions_sim[1]:
                    if st.button(f"🗑️ Remover Simulação {ticker}", key=f"remove_sim_{ticker}_{idx}", type="secondary"):
                        st.session_state.historico_simulacao.pop(idx)
                        st.success(f"Simulação para {ticker} removida.")
                        self._salvar_interacao_historico("simulacao_removida", f"Removeu simulação de {ticker}.")
                        st.rerun()
                st.markdown("---")
        else:
            st.info("Nenhuma simulação realizada ainda. Comece uma acima!")
def aba_carteira_agentica(self):
        st.markdown("### 💼 Minha Carteira IA") 

        st.markdown("#### 🤖 Sugestões da IA") 

        col1, col2 = st.columns([2, 1]) 
        with col1: 
            st.info("Nossa IA pode sugerir ações baseadas no seu perfil de investidor.") 
        with col2: 
            if st.button("🎯 Gerar Sugestões", type="primary"): 
                with st.spinner("Analisando mercado e seu perfil..."): 
                    perfil = carregar_perfil_usuario() 
                    if perfil: 
                        self.invest_agent.definir_perfil(perfil) 
                        sugestoes = self.invest_agent.recomendar_ativos(LISTA_TICKERS_IBOV, limite=8) 
                        if sugestoes: 
                            st.markdown("##### ✨ Sugestões para Você:") 
                            for analise in sugestoes: 
                                col_sugestao1, col_sugestao2 = st.columns([3, 1]) 
                                with col_sugestao1: 
                                    st.markdown(f"**{analise.nome_empresa}** ({analise.ticker.replace('.SA', '')})") 
                                    st.write(f"Score: {analise.score:.1f} | DY: {analise.dy:.2%} | P/L: {analise.pl:.1f}") 
                                    if analise.alerta_dy: 
                                        st.markdown(analise.alerta_dy, unsafe_allow_html=True) 
                                with col_sugestao2: 
                                    valor_sugerido = st.number_input( 
                                        f"Valor para {analise.ticker.replace('.SA', '')} (R$)", 
                                        min_value=0.0, 
                                        value=500.0, 
                                        step=50.0, 
                                        format="%.2f", 
                                        key=f"valor_sugestao_{analise.ticker}" 
                                    ) 
                                    if st.button(f"+ Adicionar {analise.ticker.replace('.SA', '')}", key=f"add_sugestao_{analise.ticker}"): 
                                        if valor_sugerido > 0: 
                                            found = False 
                                            for item in st.session_state.carteira: 
                                                if item['Ativo'] == analise.ticker: 
                                                    item['Quantidade'] += int(valor_sugerido // analise.preco_atual) 
                                                    item['Preço Médio'] = (item['Preço Médio'] + analise.preco_atual) / 2 
                                                    item['Valor Alocado'] += valor_sugerido 
                                                    found = True 
                                                    break 
                                            if not found: 
                                                st.session_state.carteira.append({ 
                                                    'Ativo': analise.ticker, 
                                                    'Nome': analise.nome_empresa, 
                                                    'Quantidade': int(valor_sugerido // analise.preco_atual), 
                                                    'Preço Médio': analise.preco_atual, 
                                                    'Valor Alocado': valor_sugerido, 
                                                    'DY': analise.dy, 
                                                    'Setor': analise.setor 
                                                }) 
                                            st.success(f"{analise.ticker.replace('.SA', '')} adicionado/atualizado à carteira! Role para baixo para ver e gerenciar sua carteira atualizada.") 
                                            self._salvar_interacao_historico("acao_adicionada_sugestao", f"Adicionou {analise.ticker} sugerida com valor {valor_sugerido}") 
                                            st.rerun() 
                                        else: 
                                            st.warning("Por favor, insira um valor maior que zero para adicionar à carteira.") 
                                st.markdown("---") 
                        else: 
                            st.info("Não foi possível gerar sugestões com seu perfil atual. Tente ajustar suas preferências ou perfil.") 
                    else: 
                        st.warning("Para gerar sugestões, por favor, preencha seu perfil na aba 'Meu Perfil'.") 

        st.markdown("---") 
        st.markdown("#### ✍️ Adicionar Ação Manualmente") 
        col_manual1, col_manual2, col_manual3 = st.columns(3) 
        with col_manual1: 
            ticker_manual = st.text_input("Ticker (ex: ITUB4.SA)", key="manual_ticker").upper() 
        with col_manual2: 
            quantidade_manual = st.number_input("Quantidade", min_value=1, value=10, step=1, key="manual_qtd") 
        with col_manual3: 
            preco_medio_manual = st.number_input("Preço Médio (R$)", min_value=0.01, value=10.00, step=0.01, format="%.2f", key="manual_preco") 
        
        if st.button("➕ Adicionar Manualmente", type="primary", key="add_manual_btn"): 
            if ticker_manual and quantidade_manual > 0 and preco_medio_manual > 0: 
                analise_manual = self.finance_agent.analisar_ativo(ticker_manual) 
                if analise_manual.preco_atual > 0: 
                    found = False 
                    for item in st.session_state.carteira: 
                        if item['Ativo'] == ticker_manual: 
                            # Update existing entry
                            total_valor_antigo = item['Quantidade'] * item['Preço Médio'] 
                            total_valor_novo = quantidade_manual * preco_medio_manual 
                            nova_quantidade_total = item['Quantidade'] + quantidade_manual 
                            novo_preco_medio_calc = (total_valor_antigo + total_valor_novo) / nova_quantidade_total 
                            
                            item['Quantidade'] = nova_quantidade_total 
                            item['Preço Médio'] = novo_preco_medio_calc 
                            item['Valor Alocado'] += (quantidade_manual * preco_medio_manual) 
                            found = True 
                            break 
                    
                    if not found: 
                        st.session_state.carteira.append({ 
                            'Ativo': ticker_manual, 
                            'Nome': analise_manual.nome_empresa, 
                            'Quantidade': quantidade_manual, 
                            'Preço Médio': preco_medio_manual, 
                            'Valor Alocado': quantidade_manual * preco_medio_manual, 
                            'DY': analise_manual.dy, 
                            'Setor': analise_manual.setor 
                        }) 
                    st.success(f"{ticker_manual.replace('.SA', '')} adicionado/atualizado à carteira! Role para baixo para ver e gerenciar sua carteira atualizada.") 
                    self._salvar_interacao_historico("acao_adicionada_manual", f"Adicionou {ticker_manual} manualmente.") 
                    st.rerun() 
                else: 
                    st.error("Não foi possível obter dados para este ticker. Verifique se está correto.") 
            else: 
                st.warning("Preencha todos os campos para adicionar a ação manualmente.") 
        
        st.markdown("---") 
        st.markdown("#### 📊 Sua Carteira Atual") 

        if st.session_state.carteira: 
            df_carteira = pd.DataFrame(st.session_state.carteira) 
            df_carteira['Preço Atual'] = df_carteira['Ativo'].apply(lambda x: self.finance_agent.analisar_ativo(x).preco_atual) 
            df_carteira['Valor Atual'] = df_carteira['Quantidade'] * df_carteira['Preço Atual'] 
            df_carteira['Retorno'] = ((df_carteira['Valor Atual'] - df_carteira['Valor Alocado']) / df_carteira['Valor Alocado']).fillna(0) 

            df_carteira_display = df_carteira[[ 
                'Ativo', 'Nome', 'Quantidade', 'Preço Médio', 'Preço Atual', 
                'Valor Alocado', 'Valor Atual', 'Retorno', 'DY', 'Setor' 
            ]].copy() 

            df_carteira_display['Preço Médio'] = df_carteira_display['Preço Médio'].map('R$ {:.2f}'.format) 
            df_carteira_display['Preço Atual'] = df_carteira_display['Preço Atual'].map('R$ {:.2f}'.format) 
            df_carteira_display['Valor Alocado'] = df_carteira_display['Valor Alocado'].map('R$ {:.2f}'.format) 
            df_carteira_display['Valor Atual'] = df_carteira_display['Valor Atual'].map('R$ {:.2f}'.format) 
            df_carteira_display['Retorno'] = df_carteira_display['Retorno'].map('{:.2%}'.format) 
            df_carteira_display['DY'] = df_carteira_display['DY'].map('{:.2%}'.format) 
            
            st.dataframe( 
                df_carteira_display, 
                use_container_width=True, 
                hide_index=True, 
                column_config={ 
                    "Ativo": st.column_config.Column("Ativo", width="small"), 
                    "Nome": st.column_config.Column("Nome da Empresa", width="medium"), 
                    "Quantidade": st.column_config.NumberColumn("Quantidade", format="%d"), 
                    "Preço Médio": st.column_config.Column("Preço Médio"), 
                    "Preço Atual": st.column_config.Column("Preço Atual"), 
                    "Valor Alocado": st.column_config.Column("Valor Alocado"), 
                    "Valor Atual": st.column_config.Column("Valor Atual"), 
                    "Retorno": st.column_config.Column("Retorno"), 
                    "DY": st.column_config.Column("Dividend Yield"), 
                    "Setor": st.column_config.Column("Setor", width="small"), 
                } 
            ) 

            st.markdown("---") 
            st.markdown("##### Gerenciar Ações na Carteira") 

            # Function to remove asset
            def remover_ativo(ticker_to_remove):
                st.session_state.carteira = [item for item in st.session_state.carteira if item['Ativo'] != ticker_to_remove]
                st.success(f"{ticker_to_remove.replace('.SA', '')} removido da carteira.")
                self._salvar_interacao_historico("acao_removida_carteira", f"Removeu {ticker_to_remove} da carteira.")
                st.rerun()

            # Function to update asset
            def _atualizar_ativo_carteira(ticker_to_update, nova_quantidade, novo_preco_medio):
                for i, ativo in enumerate(st.session_state.carteira):
                    if ativo['Ativo'] == ticker_to_update:
                        if nova_quantidade is not None and nova_quantidade >= 0:
                            st.session_state.carteira[i]['Quantidade'] = nova_quantidade
                        if novo_preco_medio is not None and novo_preco_medio > 0:
                            st.session_state.carteira[i]['Preço Médio'] = novo_preco_medio
                            st.session_state.carteira[i]['Valor Alocado'] = nova_quantidade * novo_preco_medio
                        elif nova_quantidade is not None and nova_quantidade >= 0 and (novo_preco_medio is None or novo_preco_medio <= 0):
                             # If only quantity updated, re-calculate value based on current price if possible
                            current_price = self.finance_agent.analisar_ativo(ticker_to_update).preco_atual
                            if current_price > 0:
                                st.session_state.carteira[i]['Valor Alocado'] = nova_quantidade * current_price
                                st.session_state.carteira[i]['Preço Médio'] = current_price # Set average price to current if only quantity changed and no new avg price
                        
                        st.success(f"Ação {ticker_to_update.replace('.SA', '')} atualizada com sucesso na carteira!")
                        self._salvar_interacao_historico("acao_atualizada_carteira", f"Atualizou {ticker_to_update} na carteira.")
                        st.rerun()
                        return
                st.warning(f"Ação {ticker_to_update.replace('.SA', '')} não encontrada na carteira para atualização.")

            col_rem_upd1, col_rem_upd2 = st.columns(2)
            with col_rem_upd1:
                # Removal section
                st.markdown("###### 🗑️ Remover Ação")
                tickers_na_carteira = [item['Ativo'].replace('.SA', '') for item in st.session_state.carteira]
                ticker_para_remover = st.selectbox(
                    "Selecione a ação para remover:",
                    [""] + tickers_na_carteira,
                    key="remove_ticker_select"
                )
                if st.button("Remover Ação Selecionada", type="secondary", key="confirm_remove_btn"):
                    if ticker_para_remover:
                        remover_ativo(ticker_para_remover + '.SA')
                    else:
                        st.warning("Selecione uma ação para remover.")
            
            with col_rem_upd2:
                # Update section
                st.markdown("###### ✏️ Atualizar Ação")
                tickers_na_carteira_update = [item['Ativo'].replace('.SA', '') for item in st.session_state.carteira]
                ticker_para_atualizar = st.selectbox(
                    "Selecione a ação para atualizar:",
                    [""] + tickers_na_carteira_update,
                    key="update_ticker_select"
                )

                if ticker_para_atualizar:
                    current_item = next((item for item in st.session_state.carteira if item['Ativo'].replace('.SA', '') == ticker_para_atualizar), None)
                    if current_item:
                        nova_quantidade = st.number_input(
                            f"Nova Quantidade para {ticker_para_atualizar}",
                            min_value=0,
                            value=current_item['Quantidade'],
                            step=1,
                            key=f"nova_qtd_{ticker_para_atualizar}"
                        )
                        novo_preco_medio = st.number_input(
                            f"Novo Preço Médio para {ticker_para_atualizar} (R$)",
                            min_value=0.0,
                            value=current_item['Preço Médio'],
                            step=0.01,
                            format="%.2f",
                            key=f"novo_preco_medio_{ticker_para_atualizar}"
                        )
                        if st.button(f"Atualizar {ticker_para_atualizar}", type="primary", key="confirm_update_btn"):
                            _atualizar_ativo_carteira(ticker_para_atualizar + '.SA', nova_quantidade, novo_preco_medio)
                    else:
                        st.info("Selecione uma ação válida para atualizar.")
                else:
                    st.info("Selecione uma ação para atualizar sua quantidade ou preço médio.")

            st.markdown("---") 

            analise_carteira = self.finance_agent.analisar_carteira( 
                [item['Ativo'] for item in st.session_state.carteira], 
                [item['Valor Alocado'] for item in st.session_state.carteira] 
            ) 

            st.markdown("##### Visão Geral da Carteira") 
            col_resumo1, col_resumo2, col_resumo3 = st.columns(3) 
            with col_resumo1: 
                st.metric("Valor Total Investido", f"R$ {analise_carteira['valor_total']:.2f}") 
            with col_resumo2: 
                st.metric("Renda Anual Estimada", f"R$ {analise_carteira['renda_total_anual']:.2f}") 
            with col_resumo3: 
                st.metric("Yield da Carteira", f"{analise_carteira['yield_carteira']:.2%}") 

            st.markdown("---") 
            st.markdown("##### Análise de Diversificação") 
            
            # Gráfico de pizza de alocação por setor
            if analise_carteira['analises']: 
                setores_df = pd.DataFrame([ 
                    {'Setor': a['analise'].setor, 'Valor Alocado': a['valor_alocado']} 
                    for a in analise_carteira['analises'] 
                ]) 
                setores_agrupados = setores_df.groupby('Setor')['Valor Alocado'].sum().reset_index() 
                fig_setores = px.pie( 
                    setores_agrupados, 
                    values='Valor Alocado', 
                    names='Setor', 
                    title='Alocação por Setor', 
                    hole=0.3 
                ) 
                st.plotly_chart(fig_setores, use_container_width=True) 

            st.markdown("---") 
            st.markdown("##### ⚖️ Análise de Risco da Carteira") 
            col1, col2 = st.columns([1, 2]) 
            with col1: 
                # Certifica-se de que a variável 'avaliacao_risco' é calculada aqui para ser usada
                avaliacao_risco = self.compliance_agent.avaliar_risco_carteira(analise_carteira['analises'])
                risco_cores = {'baixo': '🟢', 'moderado': '🟡', 'alto': '🟠', 'muito_alto': '🔴', 'indefinido': '⚪'} 
                st.metric( 
                    "Nível de Risco", 
                    f"{risco_cores.get(avaliacao_risco['risco'], '⚪')} {avaliacao_risco['risco'].replace('_', ' ').title()}" 
                ) 
            with col2: 
                if avaliacao_risco['recomendacoes']: 
                    st.markdown("**Recomendações:**") 
                    for rec in avaliacao_risco['recomendacoes']: 
                        st.markdown(f"• {rec}") 
                else: 
                    st.success("✅ Sua carteira está bem balanceada!") 

            if st.button("🗑️ Limpar Carteira", type="secondary"): 
                st.session_state.carteira = [] 
                st.rerun() 
        else: 
            st.info("📝 Sua carteira está vazia. Adicione ações usando as sugestões da IA, manualmente ou importando de uma simulação!") 

    
        def aba_perguntas_frequentes(self):
        st.markdown("### ❓ Perguntas Frequentes e Ajuda")
        st.info("Encontre respostas para as perguntas mais comuns ou pergunte ao nosso assistente.")

        pergunta_usuario = st.text_input("Sua pergunta:", key="faq_pergunta")
        if st.button("Buscar Resposta", type="primary"):
            if pergunta_usuario:
                resposta = self.support_agent.responder_pergunta(pergunta_usuario)
                st.markdown("#### Resposta:")
                st.write(resposta)
                self._salvar_interacao_historico("faq_pergunta", f"Usuário perguntou: {pergunta_usuario}")
            else:
                st.warning("Por favor, digite sua pergunta.")

        st.markdown("---")
        st.markdown("#### 📖 Glossário de Termos")
        termo_selecionado = st.selectbox("Selecione um termo para explicação:", [""] + sorted(list(GLOSSARIO.keys())))
        if termo_selecionado:
            st.markdown(f"**{termo_selecionado}:** {GLOSSARIO[termo_selecionado]}")

        st.markdown("---")
        st.markdown("#### 🎯 Calcule seu Objetivo de Renda Passiva")
        col_renda1, col_renda2 = st.columns(2)
        with col_renda1:
            renda_mensal_desejada = st.number_input(
                "Renda Mensal Desejada (R$)",
                min_value=0.0,
                value=1000.0,
                step=100.0,
                format="%.2f",
                key="renda_desejada"
            )
        with col_renda2:
            dy_medio_considerado = st.slider(
                "Dividend Yield Médio Anual (%)",
                min_value=1.0,
                max_value=15.0,
                value=8.0,
                step=0.5,
                format="%.1f",
                key="dy_considerado"
            )
        
        if st.button("Calcular Capital Necessário", type="primary", key="calc_renda_btn"):
            if renda_mensal_desejada > 0 and dy_medio_considerado > 0:
                resultado_renda = self.support_agent.calcular_renda_objetivo(
                    renda_mensal_desejada, 
                    dy_medio_considerado / 100
                )
                st.markdown(f"""
                Para gerar uma renda passiva de **R$ {resultado_renda['renda_mensal']:.2f}** por mês (R$ {resultado_renda['renda_anual']:.2f} por ano),
                considerando um Dividend Yield médio de **{resultado_renda['dy_considerado']:.1%}**,
                você precisaria de um capital investido de aproximadamente **R$ {resultado_renda['capital_necessario']:.2f}**.
                """)
                self._salvar_interacao_historico("calculo_renda_passiva", f"Calculou renda passiva para {renda_mensal_desejada}")
            else:
                st.warning("Por favor, insira valores válidos.")

        st.markdown("---")
        st.markdown("#### 💰 Calcule seu Aporte Mensal para um Objetivo")
        col_aporte1, col_aporte2 = st.columns(2)
        with col_aporte1:
            capital_objetivo = st.number_input(
                "Capital Objetivo (R$)",
                min_value=0.0,
                value=100000.0,
                step=1000.0,
                format="%.2f",
                key="capital_objetivo"
            )
            capital_atual = st.number_input(
                "Capital Atual (R$)",
                min_value=0.0,
                value=0.0,
                step=100.0,
                format="%.2f",
                key="capital_atual"
            )
        with col_aporte2:
            prazo_anos_aporte = st.slider(
                "Prazo para atingir objetivo (anos)",
                min_value=1,
                max_value=30,
                value=10,
                step=1,
                key="prazo_aporte"
            )
            rentabilidade_anual_aporte = st.slider(
                "Rentabilidade Média Anual Esperada (%)",
                min_value=1.0,
                max_value=20.0,
                value=10.0,
                step=0.5,
                format="%.1f",
                key="rentabilidade_aporte"
            )
        
        if st.button("Calcular Aporte Mensal", type="primary", key="calc_aporte_btn"):
            if capital_objetivo >= 0 and prazo_anos_aporte > 0 and rentabilidade_anual_aporte >= 0:
                prazo_meses = prazo_anos_aporte * 12
                rentabilidade_mensal = (1 + rentabilidade_anual_aporte / 100) ** (1/12) - 1
                
                resultado_aporte = self.support_agent.calcular_aporte_necessario(
                    capital_objetivo,
                    capital_atual,
                    prazo_meses,
                    rentabilidade_mensal
                )
                
                if 'erro' in resultado_aporte:
                    st.error(f"Erro no cálculo: {resultado_aporte['erro']}")
                else:
                    st.markdown(f"""
                    Para atingir um capital de **R$ {resultado_aporte['capital_objetivo']:.2f}** em **{prazo_anos_aporte} anos**,
                    com um capital atual de **R$ {resultado_aporte['capital_atual']:.2f}** e uma rentabilidade média de **{rentabilidade_anual_aporte:.1f}% ao ano**,
                    você precisará realizar aportes mensais de aproximadamente **R$ {resultado_aporte['aporte_mensal']:.2f}**.
                    """)
                    if resultado_aporte['total_aportes'] > 0:
                        st.info(f"O total dos seus aportes seria de R$ {resultado_aporte['total_aportes']:.2f}.")
                    self._salvar_interacao_historico("calculo_aporte", f"Calculou aporte para objetivo {capital_objetivo} em {prazo_anos_aporte} anos.")
            else:
                st.warning("Por favor, insira valores válidos para o cálculo.")

        st.markdown("---")
        st.markdown("#### 🔒 Segurança e Privacidade")
        col_seg1, col_seg2 = st.columns(2)
        with col_seg1:
            st.markdown("##### Nosso Compromisso")
            st.markdown("""
            - Conformidade com LGPD
            - Dados criptografados
            - Armazenamento local seguro
            - Transparência algorítmica
            - Disclaimers de investimento
            """)
        with col_seg2:
            st.markdown("#### 🎓 Educação Financeira")
            st.markdown("""
            - Glossário completo
            - Dicas personalizadas
            - Assistente IA especializado
            - Simulações educativas
            - Alertas de risco
            """)
        
        st.markdown("---")
        st.markdown("#### 🔮 Roadmap Futuro")
        st.markdown("""
        - **🌐 Integração com Corretoras:** Execução automática de ordens
        - **📱 App Mobile:** Aplicativo nativo para iOS e Android
        - **🤝 Aprendizado Federado:** IA que aprende sem comprometer privacidade
        - **🌍 Expansão Internacional:** Mercados latino-americanos
        - **🔗 Blockchain Integration:** DeFi e tokenização de ativos
        - **🎙️ Interface por Voz:** Interação natural com assistente IA
        """)
        
        st.markdown("---")
        st.markdown("**Versão:** MVP 3.0 - Experiência Unificada  ")
        st.markdown("**Última Atualização:** Junho 2025  ")
        st.markdown("**Tecnologias:** Python, Streamlit, yfinance, Plotly, Pandas")

# =================== EXECUÇÃO PRINCIPAL ===================
if __name__ == "__main__":
    orchestrator = RendyOrchestrator()

    st.sidebar.title("Opções Rendy AI")
    st.sidebar.image("https://raw.githubusercontent.com/renyzeraa/Rendy-AI-Investment-Platform/main/src/Rendy_AI_Logo.png", use_column_width=True)
    st.sidebar.write("---")

    selected_aba = st.sidebar.radio(
        "Navegação",
        ["🏠 Início", "👤 Meu Perfil", "🏆 Ranking Ações", "📈 Simulação", "💼 Minha Carteira IA", "❓ Ajuda"],
        captions=["Visão geral", "Gerencie seu perfil", "Melhores oportunidades", "Projete seus ganhos", "Gerencie seus ativos", "Perguntas e suporte"]
    )

    st.sidebar.write("---")
    st.sidebar.markdown(orchestrator.compliance_agent.gerar_disclaimer())

    if selected_aba == "🏠 Início":
        st.markdown("### 🏠 Bem-vindo à Rendy AI - Sua Plataforma de Investimentos Inteligente!")
        st.info("Sua jornada para investimentos inteligentes e renda passiva começa aqui. Use a navegação lateral para explorar as funcionalidades.")

        st.markdown("---")
        st.markdown("#### 📊 Destaques do Mercado")
        news_data = TODAY_NEWS_DATA
        st.write(f"Dados atualizados em: {news_data['data_atualizacao']}")

        col_invest, col_inflacao = st.columns(2)
        with col_invest:
            st.markdown("##### Principais Investimentos (Bruto / Líquido)")
            for inv in news_data['investimentos']:
                if inv['tipo'] == 'acao':
                    st.markdown(f"**{inv['posicao']}º {inv['nome']}:** {inv['rentabilidade_bruta']:.2f}% / {inv['rentabilidade_liquida']:.2f}% (Rent. Anual)")
                else:
                    st.markdown(f"**{inv['posicao']}º {inv['nome']}:** {inv['rentabilidade_bruta']:.2f}% / {inv['rentabilidade_liquida']:.2f}% (Rent. Anual)")
        
        with col_inflacao:
            st.markdown("##### Inflação Recente (Últimos 12 meses)")
            for infl in news_data['inflacao']:
                st.markdown(f"**{infl['indice']}:** {infl['valor']:.2f}%")

        st.markdown("---")
        st.markdown("#### 💡 Por que a Rendy AI?")
        st.markdown("""
        A Rendy AI é sua parceira inteligente para construir uma carteira de investimentos focada em renda passiva com **dividendos**. Nossa plataforma utiliza **inteligência artificial** para:
        
        - **Analisar Ativos**: Varremos o mercado para encontrar as ações com os melhores fundamentos e potencial de dividendos.
        - **Recomendações Personalizadas**: Sugerimos ativos que se alinham ao seu perfil de risco e objetivos de investimento.
        - **Simulações de Longo Prazo**: Projete o crescimento do seu patrimônio com reinvestimento de dividendos.
        - **Gestão de Carteira Simplificada**: Mantenha o controle dos seus ativos e receba análises de risco.
        - **Educação Financeira**: Aprenda termos, estratégias e dicas para investir melhor.
        
        **Comece sua jornada para a liberdade financeira hoje!**
        """)

    elif selected_aba == "👤 Meu Perfil":
        orchestrator.aba_perfil_usuario()
    
    elif selected_aba == "🏆 Ranking Ações":
        orchestrator.aba_ranking_acoes()

    elif selected_aba == "📈 Simulação":
        orchestrator.aba_simulacao_investimento()

    elif selected_aba == "💼 Minha Carteira IA":
        orchestrator.aba_carteira_agentica()

    elif selected_aba == "❓ Ajuda":
        orchestrator.aba_perguntas_frequentes()
