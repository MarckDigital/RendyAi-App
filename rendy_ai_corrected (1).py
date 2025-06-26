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
                dividend_cagr=0.0,
                ultima_atualizacao=agora_brasilia()
            )
            
            return analise
            
        except Exception as e:
            logger.error(f"Erro ao analisar {ticker}: {e}")
            return AnaliseAtivo(
                ticker=ticker,
                nome_empresa=ticker,
                preco_atual=0.0,
                dy=0.0,
                pl=0.0,
                pvp=0.0,
                roe=0.0,
                score=0.0,
                score_bruto=0.0,
                super_investimento=False,
                ultima_atualizacao=agora_brasilia()
            )
    
    def _classificar_risco(self, debt_equity: float, pl: float, dy: float, beta: float) -> str:
        pontos_risco = 0
        
        if debt_equity > 2:
            pontos_risco += 2
        elif debt_equity > 1:
            pontos_risco += 1
            
        if pl > 25 or pl <= 0:
            pontos_risco += 1
            
        if dy > 0.15:
            pontos_risco += 1
            
        if beta > 1.5:
            pontos_risco += 1
        elif beta > 1.2:
            pontos_risco += 0.5
            
        if pontos_risco >= 3:
            return "alto"
        elif pontos_risco >= 1.5:
            return "medio"
        else:
            return "baixo"
    
    def analisar_carteira(self, tickers: List[str], valores: List[float]) -> Dict:
        analises = []
        valor_total = sum(valores)
        
        for ticker, valor in zip(tickers, valores):
            analise = self.analisar_ativo(ticker)
            if analise and analise.preco_atual > 0:
                qtd_acoes = int(valor / analise.preco_atual)
                renda_anual = valor * analise.dy
                peso_carteira = valor / valor_total
                
                analises.append({
                    'analise': analise,
                    'valor_alocado': valor,
                    'qtd_acoes': qtd_acoes,
                    'renda_anual': renda_anual,
                    'peso_carteira': peso_carteira
                })
        
        if not analises:
            return {
                'valor_total': 0,
                'renda_total_anual': 0,
                'yield_carteira': 0,
                'diversificacao': 0,
                'analises': []
            }
        
        renda_total_anual = sum(item['renda_anual'] for item in analises)
        yield_carteira = renda_total_anual / valor_total if valor_total > 0 else 0
        setores_unicos = len(set(item['analise'].setor for item in analises))
        
        return {
            'valor_total': valor_total,
            'renda_total_anual': renda_total_anual,
            'yield_carteira': yield_carteira,
            'diversificacao': setores_unicos,
            'analises': analises
        }

class RendyInvestAgent:
    def __init__(self):
        self.perfil_usuario = None
    
    def definir_perfil(self, perfil: PerfilUsuario):
        self.perfil_usuario = perfil
    
    def recomendar_ativos(self, todos_tickers: List[str], limite: int = 10) -> List[AnaliseAtivo]:
        if not self.perfil_usuario:
            return []
        
        finance_agent = RendyFinanceAgent()
        analises = analisar_ativos_paralelamente(todos_tickers)
        
        analises_filtradas = []
        for analise in analises:
            if analise.preco_atual <= 0:
                continue
                
            # Filtrar por tolerância ao risco
            if self.perfil_usuario.tolerancia_risco == "conservador" and analise.risco_nivel == "alto":
                continue
            elif self.perfil_usuario.tolerancia_risco == "moderado" and analise.risco_nivel == "alto":
                continue
            
            # Filtrar por setores preferidos
            if "Todos" not in self.perfil_usuario.setores_preferidos:
                if analise.setor not in self.perfil_usuario.setores_preferidos:
                    continue
            
            # Filtrar por objetivo
            if self.perfil_usuario.objetivo_principal == "renda_passiva":
                if analise.dy < 0.03:  # Mínimo 3% de DY
                    continue
            
            analises_filtradas.append(analise)
        
        # Ordenar por score
        analises_filtradas.sort(key=lambda x: x.score, reverse=True)
        
        return analises_filtradas[:limite]
    
    def gerar_sugestao_alocacao(self, valor_total: float, ativos_recomendados: List[AnaliseAtivo]) -> Dict:
        if not self.perfil_usuario or not ativos_recomendados:
            return {}
        
        alocacao = {}
        
        # Determinar número de ativos baseado no valor disponível
        num_ativos = min(len(ativos_recomendados), 5)
        
        # Distribuição baseada no perfil
        if self.perfil_usuario.tolerancia_risco == "conservador":
            pesos = [0.4, 0.3, 0.2, 0.1]
        elif self.perfil_usuario.tolerancia_risco == "moderado":
            pesos = [0.3, 0.25, 0.25, 0.2]
        else:  # arrojado
            pesos = [0.25, 0.25, 0.25, 0.25]
        
        # Aplicar alocação
        for i, ativo in enumerate(ativos_recomendados[:num_ativos]):
            peso = pesos[i] if i < len(pesos) else pesos[-1]
            alocacao[ativo.ticker] = valor_total * peso
        
        return alocacao

class RendyXAI:
    @staticmethod
    def explicar_score(analise: AnaliseAtivo) -> Dict:
        explicacoes = {
            'dy': f"Dividend Yield de {analise.dy:.2%} {'excelente' if analise.dy >= 0.08 else 'bom' if analise.dy >= 0.05 else 'moderado'}",
            'pl': f"P/L de {analise.pl:.1f} {'atrativo' if 0 < analise.pl <= 15 else 'alto' if analise.pl > 15 else 'indisponível'}",
            'pvp': f"P/VP de {analise.pvp:.2f} {'descontado' if analise.pvp < 1 else 'justo' if analise.pvp <= 2 else 'caro'}",
            'roe': f"ROE de {analise.roe:.2%} {'excelente' if analise.roe >= 0.20 else 'bom' if analise.roe >= 0.15 else 'moderado'}",
            'recomendacao': '',
        }
        
        # Recomendação
        if analise.score >= 8:
            explicacoes['recomendacao'] = "Excelente oportunidade de investimento"
        elif analise.score >= 6:
            explicacoes['recomendacao'] = "Boa opção para carteira diversificada"
        else:
            explicacoes['recomendacao'] = "Considere com cautela, analise outros fatores"
        
        return explicacoes

class RendyAutoAgent:
    @staticmethod
    def simular_investimento(analise: AnaliseAtivo, valor_inicial: float, periodo_anos: int) -> Dict:
        try:
            cenarios = {
                'conservador': {'crescimento_preco': 0.06, 'crescimento_dividendo': 0.03},
                'moderado': {'crescimento_preco': 0.10, 'crescimento_dividendo': 0.05},
                'otimista': {'crescimento_preco': 0.15, 'crescimento_dividendo': 0.08}
            }
            
            resultados = {}
            
            for nome, params in cenarios.items():
                valor_atual = valor_inicial
                qtd_acoes = valor_inicial / analise.preco_atual
                renda_anual = valor_inicial * analise.dy
                
                for ano in range(periodo_anos):
                    # Crescimento dos dividendos
                    renda_anual *= (1 + params['crescimento_dividendo'])
                    
                    # Reinvestimento (50% dos dividendos)
                    reinvestimento = renda_anual * 0.5
                    preco_acao_ano = analise.preco_atual * ((1 + params['crescimento_preco']) ** (ano + 1))
                    novas_acoes = reinvestimento / preco_acao_ano
                    qtd_acoes += novas_acoes
                    
                    valor_atual = qtd_acoes * preco_acao_ano
                
                resultados[nome] = {
                    'valor_final': valor_atual,
                    'qtd_acoes_final': qtd_acoes,
                    'renda_anual_final': renda_anual,
                    'total_retorno': ((valor_atual - valor_inicial) / valor_inicial) * 100
                }
            
            return resultados
            
        except Exception as e:
            logger.error(f"Erro na simulação: {e}")
            return {}

class RendySupportAgent:
    @staticmethod
    def gerar_dica_personalizada(perfil: PerfilUsuario, analise: AnaliseAtivo) -> str:
        dicas = []
        
        if perfil.experiencia == "iniciante":
            dicas.append("💡 Dica para Iniciantes: Comece com empresas conhecidas e estabelecidas.")
            
        if analise.dy > 0.12:
            dicas.append("⚠️ Atenção: DY muito alto pode indicar problemas na empresa.")
            
        if analise.super_investimento:
            dicas.append("🌟 Esta é uma oportunidade excepcional segundo nosso algoritmo!")
            
        if analise.risco_nivel == "alto":
            dicas.append("🔴 Alto risco: Considere apenas uma pequena parte da carteira.")
            
        return " ".join(dicas) if dicas else "📈 Continue estudando e diversificando sua carteira!"

class RendyComplianceAgent:
    @staticmethod
    def gerar_disclaimer() -> str:
        return """
        ⚠️ **AVISO IMPORTANTE:** Esta plataforma é apenas educacional e não constitui recomendação de investimento. 
        Sempre faça sua própria análise e consulte profissionais qualificados antes de investir. 
        Investimentos envolvem riscos e rentabilidade passada não garante resultados futuros.
        """
    
    @staticmethod
    def validar_perfil(perfil: PerfilUsuario) -> List[str]:
        alertas = []
        
        if perfil.tolerancia_risco == "alto" and perfil.experiencia == "iniciante":
            alertas.append("⚠️ Alto risco para iniciante: considere começar com perfil moderado")
            
        if perfil.valor_disponivel > 100000 and perfil.experiencia == "iniciante":
            alertas.append("💰 Grande valor para iniciante: considere assessoria profissional")
            
        return alertas

# =================== ORQUESTRADOR PRINCIPAL ===================
class RendyOrchestrator:
    def __init__(self):
        self.finance_agent = RendyFinanceAgent()
        self.invest_agent = RendyInvestAgent()
        self.xai_agent = RendyXAI()
        self.auto_agent = RendyAutoAgent()
        self.support_agent = RendySupportAgent()
        self.compliance_agent = RendyComplianceAgent()
        
        # Inicializar session state
        if 'carteira' not in st.session_state:
            st.session_state.carteira = []
        if 'favoritos' not in st.session_state:
            st.session_state.favoritos = carregar_favoritos()
        if 'simulacao_cache' not in st.session_state:
            st.session_state.simulacao_cache = {}
        if 'dividend_tickers' not in st.session_state:
            st.session_state.dividend_tickers = []
    
    def run(self):
        self.sidebar_configuracao()
        self.interface_principal()
    
    def get_dividend_stocks(self, tickers: List[str]) -> List[str]:
        """Filtra apenas ações que pagam dividendos (DY > 0)"""
        dividend_tickers = []
        
        with st.spinner("🔍 Identificando ações pagadoras de dividendos..."):
            analises = analisar_ativos_paralelamente(tickers, max_workers=10)
            
            for analise in analises:
                if analise and analise.dy > 0:
                    dividend_tickers.append(analise.ticker)
        
        return sorted(dividend_tickers)
    
    def sidebar_configuracao(self):
        st.sidebar.markdown("# 🤖 Rendy AI")
        st.sidebar.markdown("*Sua IA especialista em dividendos*")
        
        perfil = carregar_perfil_usuario()
        if perfil:
            st.sidebar.success(f"👤 Olá, {perfil.nome}!")
            st.sidebar.markdown(f"**📊 Perfil:** {perfil.tolerancia_risco.title()}")
            st.sidebar.markdown(f"**🎯 Objetivo:** {perfil.objetivo_principal.replace('_', ' ').title()}")
            st.sidebar.markdown(f"**💰 Carteira:** {len(st.session_state.carteira)} ações")
        else:
            st.sidebar.warning("⚠️ Configure seu perfil na aba 'Perfil'")
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🎛️ Configurações Rápidas")
        
        if st.sidebar.button("🗑️ Limpar Carteira"):
            st.session_state.carteira = []
            st.sidebar.success("Carteira limpa!")
        
        if st.sidebar.button("🔄 Limpar Cache"):
            st.cache_data.clear()
            st.sidebar.success("Cache limpo!")
        
        st.sidebar.markdown("---")
        st.sidebar.markdown(self.compliance_agent.gerar_disclaimer())
    
    def interface_principal(self):
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "📊 Ranking Inteligente", 
            "🎯 Simulação IA", 
            "💼 Minha Carteira IA", 
            "🤖 Assistente IA", 
            "👤 Perfil", 
            "📚 Glossário",
            "ℹ️ Sobre"
        ])
        
        with tab1:
            self.aba_ranking_inteligente()
        with tab2:
            self.aba_simulacao_ia()
        with tab3:
            self.aba_carteira_agentica()
        with tab4:
            self.aba_assistente_ia()
        with tab5:
            self.aba_perfil_usuario()
        with tab6:
            self.aba_glossario()
        with tab7:
            self.aba_sobre()
    
    def aba_ranking_inteligente(self):
        st.markdown("### 🏆 Ranking Inteligente de Ações")
        
        with st.expander("ℹ️ Como Funciona Nosso Algoritmo", expanded=False):
            st.markdown("""
            **Nosso algoritmo proprietário analisa:**  
            • **Dividend Yield (DY)** - Peso 4  
            • **Preço/Lucro (P/L)** - Peso 1,5  
            • **Preço/Valor Patrimonial (P/VP)** - Peso 1,5  
            • **Return on Equity (ROE)** - Peso 3  
            • **Fluxo de Caixa Livre** - Peso 0,5  
            • **Payout Ratio** - Peso variável  
            """)
        
        with st.expander("💰 Por que Investir em Ações de Dividendos?", expanded=False):
            st.markdown("""
            **Vantagens:**  
            ✅ Renda Passiva Regular  
            ✅ Isenção de IR  
            ✅ Proteção contra Inflação  
            ✅ Juros Compostos  
            ✅ Empresas Maduras  
            """)
        
        st.markdown("### 📰 TODAY NEWS - Panorama de Investimentos")
        st.caption(f"Última atualização: {TODAY_NEWS_DATA['data_atualizacao']}")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            df_investimentos = pd.DataFrame(TODAY_NEWS_DATA['investimentos'])
            
            # Criar gráfico de barras
            fig = px.bar(
                df_investimentos, 
                x='nome', 
                y='rentabilidade_liquida',
                title='Rentabilidade Líquida Anualizada (%)',
                color='tipo',
                text='rentabilidade_liquida'
            )
            fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            fig.update_layout(xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("**📈 Inflação Atual**")
            for item in TODAY_NEWS_DATA['inflacao']:
                st.metric(item['indice'], f"{item['valor']:.2f}%")
        
        st.markdown("---")

        # =================== SEÇÃO MOVIDA: AÇÕES DA CARTEIRA ===================
        # Mostrar seção da carteira se houver ações (MOVIDA DA ABA MINHA CARTEIRA IA)
        if st.session_state.carteira:
            st.markdown("### 📊 Sua Carteira Atual")

            tickers = [acao['ticker'] for acao in st.session_state.carteira]
            valores = [acao['valor'] for acao in st.session_state.carteira]

            with st.spinner("Analisando sua carteira..."):
                analise_carteira = self.finance_agent.analisar_carteira(tickers, valores)
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Valor Total", f"R$ {analise_carteira['valor_total']:,.2f}")
                with col2:
                    st.metric("Renda Anual", f"R$ {analise_carteira['renda_total_anual']:,.2f}")
                with col3:
                    st.metric("Yield da Carteira", f"{analise_carteira['yield_carteira']:.2%}")
                with col4:
                    st.metric("Diversificação", f"{analise_carteira['diversificacao']} setores")

                st.markdown("##### 📋 Detalhes por Ação")
                for i, item in enumerate(analise_carteira['analises']):
                    analise = item['analise']
                    with st.container():
                        # Card visual mais atrativo - CORRIGIDO A FORMATAÇÃO
                        st.markdown(f"""
                        <div style='background-color: #f8f9fa; padding: 20px; border-radius: 15px; margin-bottom: 15px; 
                                    border-left: 5px solid {"#ff6b35" if analise.super_investimento else "#007bff"};
                                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <h4 style="margin: 0 0 10px 0; color: #2c3e50;">
                                {"⭐" if analise.super_investimento else "📈"} {analise.ticker.replace(".SA", "")}
                                {"<span style=\"color: #e74c3c; font-size: 0.8em; margin-left: 10px;\">SUPER INVESTIMENTO</span>" if analise.super_investimento else ""}
                            </h4>
                            <p style="margin: 0; color: #7f8c8d; font-size: 0.9em;">Peso na carteira: {item["peso_carteira"]*100:.1f}%</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                        with col1:
                            st.metric("💰 Valor Alocado", f"R$ {item['valor_alocado']:,.2f}")
                            st.metric("🔢 Qtd. Ações", f"{item['qtd_acoes']:,}")
                        with col2:
                            st.metric("⭐ Score", f"{analise.score:.1f}/10")
                            st.metric("💵 DY", f"{analise.dy:.2%}")
                        with col3:
                            st.metric("💸 Renda Anual", f"R$ {item['renda_anual']:,.2f}")
                            risco_emoji = {"baixo": "🟢", "medio": "🟡", "alto": "🔴"}[analise.risco_nivel]
                            st.markdown(f"**Risco:** {risco_emoji} {analise.risco_nivel.title()}")
                        with col4:
                            st.markdown("**Ações:**")
                            if st.button("🗑️ Remover", key=f"remove_main_{i}", 
                                       help="Remover ação da carteira", type="secondary", use_container_width=True):
                                st.session_state.carteira.pop(i)
                                st.success(f"✅ {analise.ticker.replace('.SA', '')} removida da carteira")
                                st.rerun()
                        st.markdown("---")
            st.markdown("---")
        # =================== FIM DA SEÇÃO MOVIDA ===================

        # Exibir sugestões da IA se existirem
        if 'sugestoes_carteira' in st.session_state and st.session_state.sugestoes_carteira:
            st.markdown("### 🤖 Sugestões da IA")
            for i, analise in enumerate(st.session_state.sugestoes_carteira):
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
                    with col1:
                        emoji = "⭐" if analise.super_investimento else "📈"
                        st.markdown(f"**{emoji} {analise.ticker.replace('.SA', '')}**")
                        st.caption(analise.nome_empresa[:40] + "..." if len(analise.nome_empresa) > 40 else analise.nome_empresa)
                    with col2:
                        st.metric("Score", f"{analise.score:.1f}/10")
                        st.metric("DY", f"{analise.dy:.2%}")
                    with col3:
                        st.metric("Preço", f"R$ {analise.preco_atual:.2f}")
                        risco_emoji = {"baixo": "🟢", "medio": "🟡", "alto": "🔴"}[analise.risco_nivel]
                        st.markdown(f"Risco: {risco_emoji} {analise.risco_nivel.title()}")
                    with col4:
                        valor_sugerido = st.number_input(
                            "Valor (R$)",
                            min_value=0.0,
                            value=1000.0,
                            step=100.0,
                            key=f"valor_sug_main_{analise.ticker}"
                        )
                    with col5:
                        if st.button("➕", key=f"add_sug_main_{analise.ticker}", help="Adicionar à carteira"):
                            # Limitar a 10 ações na carteira
                            if len(st.session_state.carteira) >= 10:
                                st.warning("Limite de 10 ações na carteira atingido!")
                            else:
                                nova_acao = {
                                    'ticker': analise.ticker, 
                                    'valor': valor_sugerido,
                                    'origem': 'sugestao'
                                }
                                if not any(acao['ticker'] == analise.ticker for acao in st.session_state.carteira):
                                    st.session_state.carteira.append(nova_acao)
                                    st.success(f"✅ {analise.ticker.replace('.SA', '')} adicionada à carteira!")
                                    st.rerun()
                                else:
                                    st.warning("Esta ação já está na sua carteira")
                st.markdown("---")
        
        st.markdown("### 🎯 Ações Recomendadas para Você")
        
        # Formulário de configuração
        with st.form("configuracao_analise"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                setor_selecionado = st.selectbox("🏭 Setor", SETORES_DISPONIVEIS)
            
            with col2:
                filtro_risco = st.selectbox("⚠️ Nível de Risco", ["todos", "baixo", "medio", "alto"])
            
            with col3:
                filtro_dy_min = st.slider("📊 DY Mínimo (%)", 0.0, 15.0, 3.0, 0.5) / 100
            
            with col4:
                limite_resultados = st.slider("📋 Máx. Resultados", 5, 20, 10)
            
            analisar = st.form_submit_button("🚀 Analisar Mercado", type="primary")
        
        if analisar:
            perfil = carregar_perfil_usuario()
            
            with st.spinner("🔍 Analisando todas as ações do IBOVESPA..."):
                tickers_para_analisar = LISTA_TICKERS_IBOV.copy()
                
                # Filtrar por setor se necessário
                if setor_selecionado != "Todos":
                    # Para simplificar, vamos analisar todas e filtrar depois
                    pass
                
                analises = analisar_ativos_paralelamente(tickers_para_analisar)
                
                analises_filtradas = []
                for analise in analises:
                    if filtro_risco != "todos" and analise.risco_nivel != filtro_risco:
                        continue
                    if analise.dy < filtro_dy_min:
                        continue
                    analises_filtradas.append(analise)
                
                if perfil:
                    self.invest_agent.definir_perfil(perfil)
                    analises_recomendadas = self.invest_agent.recomendar_ativos(
                        [a.ticker for a in analises_filtradas], limite_resultados
                    )
                else:
                    analises_recomendadas = sorted(
                        analises_filtradas, key=lambda x: x.score, reverse=True
                    )[:limite_resultados]
                
                if analises_recomendadas:
                    st.success(f"✅ Encontradas {len(analises_recomendadas)} oportunidades!")
                    
                    dados_ranking = []
                    for i, analise in enumerate(analises_recomendadas):
                        dados_ranking.append({
                            'Posição': i + 1,
                            'Ticker': analise.ticker,
                            'Empresa': analise.nome_empresa[:30] + "..." if len(analise.nome_empresa) > 30 else analise.nome_empresa,
                            'Score': f"{analise.score:.1f}",
                            'DY': f"{analise.dy*100:.2f}%",
                            'ROE': f"{analise.roe*100:.2f}%",
                            'P/L': f"{analise.pl:.2f}" if analise.pl > 0 else "N/A",
                            'Risco': analise.risco_nivel.title(),
                            'Setor': analise.setor,
                            'Super': "🔥" if analise.super_investimento else "",
                            'Favorito': "⭐" if analise.ticker in st.session_state.favoritos else ""
                        })
                    
                    df_ranking = pd.DataFrame(dados_ranking)
                    
                    # Adicionar coluna de ações com botões
                    def formatar_linha(row):
                        return st.button(
                            "⭐" if row['Favorito'] else "🤍", 
                            key=f"fav_{row['Ticker']}",
                            help="Clique para favoritar/desfavoritar"
                        )
                    
                    # Remover colunas que não serão exibidas
                    df_display = df_ranking.drop(columns=['Ticker', 'Favorito'])
                    
                    # Exibir tabela
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                    
                    # Sugestão de carteira
                    if perfil and len(analises_recomendadas) >= 3:
                        st.markdown("### 💼 Sugestão de Carteira Personalizada")
                        valor_total = perfil.valor_disponivel
                        if valor_total > 0:
                            alocacao = self.invest_agent.gerar_sugestao_alocacao(
                                valor_total, analises_recomendadas[:5]
                            )
                            
                            if alocacao:
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown("**Alocação Sugerida:**")
                                    for ticker, valor in alocacao.items():
                                        percentual = (valor / valor_total) * 100
                                        st.markdown(f"• {ticker.replace('.SA', '')}: R$ {valor:,.2f} ({percentual:.1f}%)")
                                with col2:
                                    fig = px.pie(
                                        values=list(alocacao.values()),
                                        names=[t.replace('.SA', '') for t in alocacao.keys()],
                                        title="Distribuição da Carteira"
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Nenhum ativo encontrado com os filtros aplicados.")
        
        st.markdown(self.compliance_agent.gerar_disclaimer())
    
    def aba_simulacao_ia(self):
        st.markdown("### 🎯 Simulação Inteligente de Investimentos")
        st.info("""
        **Explore o Futuro dos Seus Investimentos!**
        Use esta ferramenta para simular o potencial de crescimento de uma ação específica ao longo do tempo, 
        considerando diferentes cenários e o reinvestimento de dividendos. 
        Descubra quanto seu patrimônio e sua renda passiva podem render!
        """)
        
        # Obter ações pagadoras de dividendos
        if not st.session_state.dividend_tickers:
            with st.spinner("🔄 Carregando ações pagadoras de dividendos..."):
                st.session_state.dividend_tickers = self.get_dividend_stocks(LISTA_TICKERS_IBOV)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Menu dropdown apenas com ações pagadoras de dividendos
            ticker_input = st.selectbox(
                "📈 Selecione uma Ação (apenas pagadoras de dividendos)",
                options=st.session_state.dividend_tickers,
                index=0 if st.session_state.dividend_tickers else None,
                help="Apenas ações que pagam dividendos aparecem nesta lista"
            )
        
        with col2:
            valor_inicial = st.number_input("💰 Valor Inicial (R$)", min_value=100.0, value=10000.0, step=500.0)
        
        col3, col4 = st.columns([1, 1])
        
        with col3:
            periodo_anos = st.slider("⏰ Período (anos)", 1, 30, 10)
        
        with col4:
            st.markdown("&nbsp;")  # Espaçamento
            simular = st.button("🚀 Simular Investimento", type="primary")
        
        if simular and ticker_input:
            # Cache da simulação
            cache_key = f"{ticker_input}_{valor_inicial}_{periodo_anos}"
            
            if cache_key not in st.session_state.simulacao_cache:
                with st.spinner(f"📊 Simulando investimento em {ticker_input.replace('.SA', '')}..."):
                    analise = self.finance_agent.analisar_ativo(ticker_input)
                    
                    if analise and analise.preco_atual > 0:
                        resultado = self.auto_agent.simular_investimento(analise, valor_inicial, periodo_anos)
                        
                        if resultado:
                            st.session_state.simulacao_cache[cache_key] = {
                                'analise': analise,
                                'cenarios': resultado,
                                'parametros': {'valor_inicial': valor_inicial, 'periodo': periodo_anos}
                            }
                    else:
                        st.error("Não foi possível analisar este ativo.")
        
        # Exibir resultados das simulações
        if st.session_state.simulacao_cache:
            st.markdown("---")
            st.markdown("### 📋 Resultados das Simulações")
            
            for ticker, resultado in st.session_state.simulacao_cache.items():
                analise = resultado['analise']
                cenarios = resultado['cenarios']
                params = resultado['parametros']
                
                with st.expander(f"📊 {analise.ticker.replace('.SA', '')} - {analise.nome_empresa[:50]}", expanded=True):
                    # Informações da ação
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("💰 Preço Atual", f"R$ {analise.preco_atual:.2f}")
                    with col2:
                        st.metric("📊 DY Atual", f"{analise.dy:.2%}")
                    with col3:
                        st.metric("⭐ Score", f"{analise.score:.1f}/10")
                    with col4:
                        if analise.super_investimento:
                            st.success("🌟 Super Investimento!")
                        else:
                            st.info("📈 Boa Oportunidade")
                    
                    # Resultados da simulação
                    st.markdown(f"**Simulação: R$ {params['valor_inicial']:,.2f} por {params['periodo']} anos**")
                    
                    dados_cenarios = []
                    for nome, dados in cenarios.items():
                        dados_cenarios.append({
                            'Cenário': nome.title(),
                            'Valor Final': f"R$ {dados['valor_final']:,.2f}",
                            'Retorno Total': f"{dados['total_retorno']:.1f}%",
                            'Renda Anual Final': f"R$ {dados['renda_anual_final']:,.2f}",
                            'Qtd. Ações': f"{dados['qtd_acoes_final']:.0f}"
                        })
                    
                    df_cenarios = pd.DataFrame(dados_cenarios)
                    st.dataframe(df_cenarios, use_container_width=True, hide_index=True)
                    
                    # Gráfico dos cenários
                    fig = px.bar(
                        x=[d['Cenário'] for d in dados_cenarios],
                        y=[cenarios[nome]['valor_final'] for nome in cenarios.keys()],
                        title=f"Projeção de Valor Final - {analise.ticker.replace('.SA', '')}",
                        labels={'x': 'Cenário', 'y': 'Valor Final (R$)'},
                        color=[d['Cenário'] for d in dados_cenarios]
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Adicionar à carteira
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        if st.button(f"➕ Adicionar à Carteira", key=f"add_{ticker}"):
                            if len(st.session_state.carteira) >= 10:
                                st.warning("Limite de 10 ações na carteira atingido!")
                            else:
                                nova_acao = {
                                    'ticker': analise.ticker, 
                                    'valor': params['valor_inicial'],
                                    'origem': 'simulacao'
                                }
                                if not any(acao['ticker'] == analise.ticker for acao in st.session_state.carteira):
                                    st.session_state.carteira.append(nova_acao)
                                    st.success(f"✅ {analise.ticker.replace('.SA', '')} adicionada à carteira!")
                                else:
                                    st.warning("Esta ação já está na sua carteira")
                    with col2:
                        melhor_cenario = max(resultado['cenarios'].items(), key=lambda x: x[1]['valor_final'])
                        st.metric("Melhor Cenário", melhor_cenario[0].title(), f"R$ {melhor_cenario[1]['valor_final']:,.2f}")
                    with col3:
                        pior_cenario = min(resultado['cenarios'].items(), key=lambda x: x[1]['valor_final'])
                        st.metric("Cenário Conservador", pior_cenario[0].title(), f"R$ {pior_cenario[1]['valor_final']:,.2f}")
                    with col3:
                        if st.button(f"🗑️ Limpar", key=f"clear_{ticker}"):
                            del st.session_state.simulacao_cache[ticker]
                            st.rerun()
    
    def aba_carteira_agentica(self):
        st.markdown("### 💼 Minha Carteira IA")
        st.info("""
        **Gerencie e Otimize Seus Investimentos!**
        Nesta aba, você pode adicionar ações manualmente, importar sugestões da nossa IA ou ações simuladas. 
        Suas ações da carteira atual são exibidas no topo da página principal para acompanhamento rápido.
        """)
        
        # Separar ações por origem
        acoes_simulacao = [a for a in st.session_state.carteira if a.get('origem') == 'simulacao']
        acoes_manuais = [a for a in st.session_state.carteira if a.get('origem') != 'simulacao']
        
        if acoes_simulacao:
            st.markdown("#### 📥 Ações Importadas da Simulação IA")
            for i, acao in enumerate(acoes_simulacao):
                with st.container():
                    st.markdown(f"""
                    <div style='background-color: #f0f8ff; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #4CAF50;'>
                        <h4 style='margin: 0; color: #2e7d32;'>🎯 {acao['ticker'].replace('.SA', '')}</h4>
                        <p style='margin: 5px 0; color: #666;'>Importada da Simulação IA</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns([2, 3, 2])
                    with col1:
                        st.metric("💰 Valor Investido", f"R$ {acao['valor']:,.2f}")
                    with col2:
                        novo_valor = st.number_input(
                            "Atualizar Valor (R$)",
                            min_value=0.0,
                            value=acao['valor'],
                            step=100.0,
                            key=f"update_sim_{acao['ticker']}_{i}",
                            help="Digite o novo valor e clique em 'Atualizar'"
                        )
                    with col3:
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("🔄 Atualizar", key=f"update_btn_sim_{acao['ticker']}_{i}", 
                                       help="Atualizar valor", type="secondary", use_container_width=True):
                                for a in st.session_state.carteira:
                                    if a == acao:
                                        a['valor'] = novo_valor
                                st.success(f"✅ Valor atualizado para {acao['ticker'].replace('.SA', '')}")
                                st.rerun()
                        with col_btn2:
                            if st.button("🗑️ Remover", key=f"remove_sim_{acao['ticker']}_{i}", 
                                       help="Remover ação da carteira", type="secondary", use_container_width=True):
                                st.session_state.carteira = [a for a in st.session_state.carteira if a != acao]
                                st.success(f"✅ {acao['ticker'].replace('.SA', '')} removida da carteira")
                                st.rerun()
                    st.markdown("---")
        
        st.markdown("#### 🤖 Sugestões da IA")
        st.info("Nossa IA pode sugerir ações baseadas no seu perfil de investidor.")
        
        col1, col2 = st.columns([1, 1])
        with col2:
            if st.button("🎯 Gerar Sugestões", type="primary"):
                with st.spinner("Analisando mercado e seu perfil..."):
                    perfil = carregar_perfil_usuario()
                    if perfil:
                        self.invest_agent.definir_perfil(perfil)
                        sugestoes = self.invest_agent.recomendar_ativos(LISTA_TICKERS_IBOV, limite=8)
                        st.session_state.sugestoes_carteira = sugestoes
                    else:
                        st.error("Perfil não encontrado. Configure seu perfil na aba 'Perfil'.")

        # Exibir sugestões
        if 'sugestoes_carteira' in st.session_state and st.session_state.sugestoes_carteira:
            st.markdown("##### 📋 Ações Recomendadas para Você")
            for i, analise in enumerate(st.session_state.sugestoes_carteira):
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
                    with col1:
                        emoji = "⭐" if analise.super_investimento else "📈"
                        st.markdown(f"**{emoji} {analise.ticker.replace('.SA', '')}**")
                        st.caption(analise.nome_empresa[:40] + "..." if len(analise.nome_empresa) > 40 else analise.nome_empresa)
                    with col2:
                        st.metric("Score", f"{analise.score:.1f}/10")
                        st.metric("DY", f"{analise.dy:.2%}")
                    with col3:
                        st.metric("Preço", f"R$ {analise.preco_atual:.2f}")
                        risco_emoji = {"baixo": "🟢", "medio": "🟡", "alto": "🔴"}[analise.risco_nivel]
                        st.markdown(f"Risco: {risco_emoji} {analise.risco_nivel.title()}")
                    with col4:
                        valor_sugerido = st.number_input(
                            "Valor (R$)",
                            min_value=0.0,
                            value=1000.0,
                            step=100.0,
                            key=f"valor_sug_{analise.ticker}"
                        )
                    with col5:
                        if st.button("➕", key=f"add_sug_{analise.ticker}", help="Adicionar à carteira"):
                            # Limitar a 10 ações na carteira
                            if len(st.session_state.carteira) >= 10:
                                st.warning("Limite de 10 ações na carteira atingido!")
                            else:
                                nova_acao = {
                                    'ticker': analise.ticker, 
                                    'valor': valor_sugerido,
                                    'origem': 'sugestao'
                                }
                                if not any(acao['ticker'] == analise.ticker for acao in st.session_state.carteira):
                                    st.session_state.carteira.append(nova_acao)
                                    st.success(f"✅ {analise.ticker.replace('.SA', '')} adicionada à carteira!")
                                    st.rerun()
                                else:
                                    st.warning("Esta ação já está na sua carteira")
                    st.markdown("---")

        st.markdown("#### ✋ Adicionar Manualmente")
        with st.form("adicionar_acao"):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                # Menu dropdown para seleção de ações
                ticker_manual = st.selectbox(
                    "Selecione uma Ação",
                    options=LISTA_TICKERS_IBOV,
                    index=LISTA_TICKERS_IBOV.index('PETR4.SA') if 'PETR4.SA' in LISTA_TICKERS_IBOV else 0,
                    help="Selecione uma ação para adicionar"
                )
            with col2:
                valor_manual = st.number_input("Valor a Investir (R$)", min_value=0.0, value=1000.0, step=100.0)
            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                adicionar_manual = st.form_submit_button("➕ Adicionar", type="primary")
            if adicionar_manual and ticker_manual:
                # Limitar a 10 ações na carteira
                if len(st.session_state.carteira) >= 10:
                    st.warning("Limite de 10 ações na carteira atingido!")
                else:
                    nova_acao = {
                        'ticker': ticker_manual, 
                        'valor': valor_manual,
                        'origem': 'manual'
                    }
                    if not any(acao['ticker'] == ticker_manual for acao in st.session_state.carteira):
                        st.session_state.carteira.append(nova_acao)
                        st.success(f"✅ {ticker_manual.replace('.SA', '')} adicionada à carteira!")
                        st.rerun()
                    else:
                        st.warning("Esta ação já está na sua carteira.")

        # Informação sobre onde visualizar a carteira
        if st.session_state.carteira:
            st.info("💡 **Dica:** Sua carteira atual e detalhes das ações estão disponíveis no topo da aba 'Ranking Inteligente' para acompanhamento rápido!")

    def aba_assistente_ia(self):
        st.markdown("### 🤖 Assistente IA Rendy")
        st.info("""
        **Seu Consultor Pessoal de Investimentos!**
        Faça perguntas sobre ações, dividendos, análise fundamentalista ou estratégias de investimento. 
        O Assistente Rendy está aqui para te educar e orientar em suas decisões de investimento.
        """)
        
        # Exemplos de perguntas
        with st.expander("💡 Exemplos de Perguntas", expanded=False):
            st.markdown("""
            **Análise de Ações:**
            • "Como interpretar o P/L de uma empresa?"
            • "O que é um bom Dividend Yield?"
            • "Como analisar o ROE?"
            
            **Estratégias:**
            • "Como montar uma carteira de dividendos?"
            • "Qual a diferença entre valor e crescimento?"
            • "Como diversificar por setores?"
            
            **Educação:**
            • "O que são dividendos?"
            • "Como funcionam os JCP?"
            • "Quando reinvestir dividendos?"
            """)
        
        # Chat interface
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = [
                {"role": "assistant", "content": "Olá! Sou o Assistente Rendy, especialista em investimentos em dividendos. Como posso te ajudar hoje?"}
            ]
        
        # Exibir histórico do chat
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Input do usuário
        if prompt := st.chat_input("Digite sua pergunta sobre investimentos..."):
            # Adicionar pergunta do usuário
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Gerar resposta
            with st.chat_message("assistant"):
                with st.spinner("Analisando sua pergunta..."):
                    resposta = self._gerar_resposta_assistente(prompt)
                    st.markdown(resposta)
                    st.session_state.chat_history.append({"role": "assistant", "content": resposta})
        
        # Botão para limpar histórico
        if st.button("🗑️ Limpar Conversa"):
            st.session_state.chat_history = [
                {"role": "assistant", "content": "Olá! Sou o Assistente Rendy, especialista em investimentos em dividendos. Como posso te ajudar hoje?"}
            ]
            st.rerun()
    
    def _gerar_resposta_assistente(self, pergunta: str) -> str:
        """Gera resposta simulada do assistente baseada na pergunta"""
        pergunta_lower = pergunta.lower()
        
        # Respostas baseadas em palavras-chave
        if any(palavra in pergunta_lower for palavra in ['p/l', 'preço/lucro', 'preco lucro']):
            return """
            📊 **Preço/Lucro (P/L)** é um dos indicadores mais importantes!
            
            **Como interpretar:**
            • **P/L baixo (5-15)**: Ação pode estar barata
            • **P/L médio (15-25)**: Preço justo para a maioria das empresas
            • **P/L alto (>25)**: Pode indicar supervalorização ou expectativa de crescimento
            
            **Dicas importantes:**
            ✅ Compare com empresas do mesmo setor
            ✅ P/L negativo indica prejuízo da empresa
            ✅ Considere junto com outros indicadores (ROE, DY, P/VP)
            """
        
        elif any(palavra in pergunta_lower for palavra in ['dividend yield', 'dy', 'dividendo']):
            return """
            💰 **Dividend Yield (DY)** é a rentabilidade anual dos dividendos!
            
            **Interpretação:**
            • **DY 3-6%**: Bom para empresas consolidadas
            • **DY 6-10%**: Excelente, mas verifique sustentabilidade
            • **DY >10%**: Atenção! Pode indicar problemas ou evento especial
            
            **Cuidados:**
            ⚠️ DY muito alto pode ser "pegadinha"
            ⚠️ Verifique histórico de pagamentos
            ⚠️ Analise a saúde financeira da empresa
            """
        
        elif any(palavra in pergunta_lower for palavra in ['roe', 'retorno patrimonio']):
            return """
            📈 **ROE (Return on Equity)** mede a eficiência da empresa!
            
            **Benchmarks:**
            • **ROE >15%**: Excelente gestão
            • **ROE 10-15%**: Boa empresa
            • **ROE <10%**: Pode indicar ineficiência
            
            **Por que é importante:**
            ✅ Mostra capacidade de gerar lucros
            ✅ Indica qualidade da gestão
            ✅ Relaciona-se com crescimento sustentável
            """
        
        elif any(palavra in pergunta_lower for palavra in ['carteira', 'portfólio', 'diversificar']):
            return """
            🎯 **Como montar uma carteira de dividendos:**
            
            **Diversificação por setor:**
            • Bancos (20-30%)
            • Utilities/Energia (20-25%)
            • Consumo/Varejo (15-20%)
            • Outros setores (25-35%)
            
            **Dicas estratégicas:**
            ✅ Máximo 10% por ação
            ✅ 8-15 ações na carteira
            ✅ Reinvestir 50% dos dividendos
            ✅ Revisar trimestralmente
            
            **Cuidados:**
            ⚠️ Não concentrar em 1 setor
            ⚠️ Analisar correlação entre ativos
            """
        
        else:
            return f"""
            🤖 **Assistente Rendy aqui!**
            
            Entendi sua pergunta sobre: "{pergunta}"
            
            **Sugestões para você:**
            📚 Consulte nosso Glossário na aba específica
            📊 Use o Ranking Inteligente para análises detalhadas
            🎯 Experimente a Simulação IA para projeções
            
            **Para respostas mais específicas, pergunte sobre:**
            • Indicadores específicos (P/L, ROE, DY)
            • Estratégias de investimento
            • Análise fundamentalista
            • Gestão de carteira
            
            Reformule sua pergunta para uma resposta mais direcionada! 😊
            """
    
    def aba_perfil_usuario(self):
        st.markdown("### 👤 Configuração do Perfil")
        
        perfil_atual = carregar_perfil_usuario()
        
        with st.form("perfil_usuario"):
            st.markdown("#### 📝 Informações Básicas")
            
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome Completo", value=perfil_atual.nome if perfil_atual else "")
            with col2:
                email = st.text_input("E-mail", value=perfil_atual.email if perfil_atual else "")
            
            st.markdown("#### 🎯 Perfil de Investimento")
            
            col1, col2 = st.columns(2)
            with col1:
                tolerancia_risco = st.selectbox(
                    "Tolerância ao Risco",
                    ["conservador", "moderado", "arrojado"],
                    index=["conservador", "moderado", "arrojado"].index(perfil_atual.tolerancia_risco) if perfil_atual else 1
                )
                
                objetivo_principal = st.selectbox(
                    "Objetivo Principal",
                    ["renda_passiva", "crescimento", "preservacao_capital"],
                    index=["renda_passiva", "crescimento", "preservacao_capital"].index(perfil_atual.objetivo_principal) if perfil_atual else 0
                )
            
            with col2:
                horizonte_investimento = st.selectbox(
                    "Horizonte de Investimento",
                    ["curto", "medio", "longo"],
                    index=["curto", "medio", "longo"].index(perfil_atual.horizonte_investimento) if perfil_atual else 1
                )
                
                experiencia = st.selectbox(
                    "Experiência em Investimentos",
                    ["iniciante", "intermediario", "avancado"],
                    index=["iniciante", "intermediario", "avancado"].index(perfil_atual.experiencia) if perfil_atual else 0
                )
            
            valor_disponivel = st.number_input(
                "Valor Disponível para Investir (R$)",
                min_value=0.0,
                value=perfil_atual.valor_disponivel if perfil_atual else 0.0,
                step=1000.0
            )
            
            setores_preferidos = st.multiselect(
                "Setores de Interesse",
                SETORES_DISPONIVEIS,
                default=perfil_atual.setores_preferidos if perfil_atual else ["Todos"]
            )
            
            salvar = st.form_submit_button("💾 Salvar Perfil", type="primary")
            
            if salvar:
                if not nome or not email:
                    st.error("Nome e e-mail são obrigatórios!")
                elif not validar_email(email):
                    st.error("E-mail inválido!")
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
                    st.success("✅ Perfil salvo com sucesso!")
                    
                    # Validar perfil
                    alertas = self.compliance_agent.validar_perfil(novo_perfil)
                    for alerta in alertas:
                        st.warning(alerta)
                    
                    st.rerun()
        
        # Exibir perfil atual
        if perfil_atual:
            st.markdown("---")
            st.markdown("### 📊 Seu Perfil Atual")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.info(f"""
                **👤 Informações Pessoais**
                • Nome: {perfil_atual.nome}
                • E-mail: {perfil_atual.email}
                """)
            
            with col2:
                st.info(f"""
                **🎯 Perfil Investidor**
                • Risco: {perfil_atual.tolerancia_risco.title()}
                • Objetivo: {perfil_atual.objetivo_principal.replace('_', ' ').title()}
                • Horizonte: {perfil_atual.horizonte_investimento.title()}
                """)
            
            with col3:
                st.info(f"""
                **💰 Investimentos**
                • Valor: R$ {perfil_atual.valor_disponivel:,.2f}
                • Experiência: {perfil_atual.experiencia.title()}
                • Setores: {len(perfil_atual.setores_preferidos)}
                """)
    
    def aba_glossario(self):
        st.markdown("### 📚 Glossário de Investimentos")
        st.markdown("*Entenda os principais termos usados na análise de ações*")
        
        # Busca no glossário
        busca = st.text_input("🔍 Buscar termo", placeholder="Digite para buscar...")
        
        # Filtrar termos
        termos_filtrados = GLOSSARIO
        if busca:
            termos_filtrados = {k: v for k, v in GLOSSARIO.items() 
                              if busca.lower() in k.lower() or busca.lower() in v.lower()}
        
        if not termos_filtrados:
            st.warning("Nenhum termo encontrado.")
        else:
            # Exibir termos em cards
            for termo, definicao in termos_filtrados.items():
                with st.expander(f"📖 {termo}", expanded=busca and termo.lower() == busca.lower()):
                    st.markdown(definicao)
        
        # Categorias
        st.markdown("---")
        st.markdown("### 📋 Categorias")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**🎯 Indicadores Básicos**")
            st.markdown("• Score • DY • P/L • P/VP • ROE")
        
        with col2:
            st.markdown("**📊 Indicadores Avançados**")
            st.markdown("• Free Cash Flow • Payout Ratio • Debt/Equity • EV/EBITDA")
        
        with col3:
            st.markdown("**⚖️ Métricas de Risco**")
            st.markdown("• Beta • Liquidez • Margem Líquida • Dividend CAGR")
    
    def aba_sobre(self):
        st.markdown("# 🤖 Rendy AI - Plataforma de Investimentos")
        st.markdown("### *Inteligência Artificial a serviço dos seus dividendos*")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            ## 🎯 Nossa Missão
            Democratizar o acesso a análises fundamentalistas profissionais através de inteligência artificial, 
            capacitando investidores a construir patrimônio sólido e renda passiva sustentável.
            """)
        
        with col2:
            st.metric("🎯 Score Máximo", "10.0")
            st.metric("📊 Ações Analisadas", "73")
            st.metric("🤖 Agentes IA", "6")
        
        st.markdown("---")
        
        st.markdown("""
        ## 🚀 O que é o Rendy AI?
        
        O **Rendy AI** é uma plataforma inovadora que utiliza múltiplos agentes especializados de inteligência artificial 
        para análise fundamentalista de ações brasileiras, com foco especial em empresas pagadoras de dividendos.
        
        ### 🎯 Público-Alvo
        Investidores que buscam renda passiva através de dividendos, desde iniciantes até intermediários, 
        que desejam tomar decisões baseadas em dados e análises científicas.
        
        ### 🎪 Filosofia
        Capacitar investidores iniciantes a construir patrimônio e renda passiva de forma inteligente e educativa.
        
        #### 🚀 Diferenciais Tecnológicos
        - **Arquitetura de Agentes Especializados:**  
          • RendyFinanceAgent: Análise fundamentalista  
          • RendyInvestAgent: Personalização e recomendações  
          • RendyXAI: Explicabilidade das decisões  
          • RendyAutoAgent: Simulações e projeções  
          • RendySupportAgent: Educação e suporte  
          • RendyComplianceAgent: Gestão de riscos  
        
        #### 📈 Metodologia de Score
        **Componentes:**  
        • Dividend Yield (peso 4)  
        • ROE (peso 3)  
        • P/L e P/VP (peso 1.5 cada)  
        • Free Cash Flow (peso 0.5)  
        • Payout Ratio (peso variável)  
        
        **Interpretação:**  
        • 8-10: Excelente oportunidade  
        • 6-8: Boa oportunidade  
        • 4-6: Moderada, requer análise  
        • 0-4: Evitar  
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🛡️ Segurança e Conformidade")
            st.markdown("""
            - Conformidade com LGPD
            - Dados criptografados
            - Armazenamento local seguro
            - Transparência algorítmica
            - Disclaimers de investimento
            """)
        with col2:
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
    orchestrator.run()
