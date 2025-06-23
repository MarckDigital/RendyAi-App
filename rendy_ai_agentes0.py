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
warnings.filterwarnings("ignore")

# =================== CONFIGURAÇÕES E CONSTANTES ===================
st.set_page_config(
    page_title="Rendy AI - Plataforma de Investimentos",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
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

SETORES_DISPONIVEIS = [
    'Todos', 'Bancos', 'Energia Elétrica', 'Petróleo e Gás', 'Mineração',
    'Siderurgia', 'Telecomunicações', 'Varejo', 'Alimentação', 'Construção Civil',
    'Papel e Celulose', 'Transporte', 'Saúde', 'Educação', 'Tecnologia'
]

GLOSSARIO = {
    "Score": "Pontuação até 10 que avalia custo/benefício considerando dividendos (DY), rentabilidade (ROE), preço/lucro (P/L) e preço/valor patrimonial (P/VP). Quanto mais perto de 10, melhor.",
    "DY": "Dividend Yield: percentual dos dividendos pagos em relação ao preço da ação, anualizado. O app limita DY a no máximo 30% ao ano por padrão para evitar distorções.",
    "P/L": "Preço dividido pelo lucro por ação. P/L baixo pode indicar ação barata.",
    "P/VP": "Preço dividido pelo valor patrimonial da empresa por ação. P/VP abaixo de 1 pode indicar ação descontada.",
    "ROE": "Retorno sobre o patrimônio líquido. Mede a eficiência da empresa em gerar lucros.",
    "Super Investimento": "Ações que atingiram a pontuação máxima de 10 no score, mas cujo valor bruto dos critérios ultrapassou esse limite. São consideradas oportunidades excepcionais segundo o algoritmo.",
    "Free Cash Flow": "Fluxo de caixa livre: dinheiro que sobra após investimentos necessários. Indica capacidade de pagar dividendos.",
    "Payout Ratio": "Percentual do lucro distribuído como dividendos. Valores entre 30-60% são considerados saudáveis.",
    "Debt/Equity": "Relação dívida/patrimônio. Valores altos podem indicar risco financeiro.",
    "Margem Líquida": "Percentual do lucro líquido sobre a receita. Indica eficiência operacional.",
    "Crescimento de Dividendos": "Taxa de crescimento histórica dos dividendos. Indica sustentabilidade futura."
}

# Dados simulados para TODAY NEWS (em ambiente real, seria obtido via APIs)
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
    tolerancia_risco: str = "moderado"  # conservador, moderado, agressivo
    horizonte_investimento: str = "medio"  # curto, medio, longo
    objetivo_principal: str = "renda_passiva"  # renda_passiva, crescimento, preservacao
    experiencia: str = "iniciante"  # iniciante, intermediario, avancado
    valor_disponivel: float = 0.0
    setores_preferidos: List[str] = None
    
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
    # Novos campos expandidos
    free_cash_flow: float = 0.0
    payout_ratio: float = 0.0
    debt_equity: float = 0.0
    margem_liquida: float = 0.0
    crescimento_dividendos: float = 0.0
    setor: str = ""
    risco_nivel: str = "medio"
    recomendacao: str = ""

# =================== UTILITÁRIOS ===================
def agora_brasilia():
    return datetime.now(FUSO_BR)

def inicializar_ambiente():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def validar_email(email: str) -> bool:
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', email))

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

def carregar_perfil_usuario() -> Optional[PerfilUsuario]:
    """Carrega o perfil do usuário do arquivo JSON"""
    try:
        if os.path.exists(USUARIO_JSON):
            with open(USUARIO_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return PerfilUsuario(**data)
    except Exception as e:
        logger.error(f"Erro ao carregar perfil: {e}")
    return None

def salvar_perfil_usuario(perfil: PerfilUsuario):
    """Salva o perfil do usuário no arquivo JSON"""
    try:
        inicializar_ambiente()
        with open(USUARIO_JSON, 'w', encoding='utf-8') as f:
            json.dump(perfil.__dict__, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Erro ao salvar perfil: {e}")

# =================== AGENTES ESPECIALIZADOS ===================

class RendyFinanceAgent:
    """Agente responsável pela análise fundamentalista e previsão de dividendos"""
    
    def __init__(self):
        self.cache_analises = {}
    
    def analisar_ativo(self, ticker: str) -> AnaliseAtivo:
        """Análise fundamentalista expandida de um ativo"""
        try:
            # Cache simples para evitar múltiplas chamadas
            if ticker in self.cache_analises:
                return self.cache_analises[ticker]
            
            acao = yf.Ticker(ticker)
            info = acao.info
            historico = acao.history(period="1y")
            historico_close = historico['Close'] if not historico.empty else None
            
            # Dados básicos
            dy_raw = info.get('dividendYield', 0) or 0
            dy, alerta_dy = validar_dy(float(dy_raw))
            pl = info.get('trailingPE', 0) or 0
            pvp = info.get('priceToBook', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            preco_atual = info.get('currentPrice', 0) or info.get('regularMarketPrice', 0) or 0
            
            if preco_atual == 0 and historico_close is not None and not historico_close.empty:
                preco_atual = float(historico_close.iloc[-1])
            
            # Dados expandidos
            free_cash_flow = info.get('freeCashflow', 0) or 0
            payout_ratio = info.get('payoutRatio', 0) or 0
            debt_equity = info.get('debtToEquity', 0) or 0
            margem_liquida = info.get('profitMargins', 0) or 0
            setor = info.get('sector', 'Não informado')
            
            # Cálculo do score expandido
            score_dy = min(dy / 0.08, 1) * 4 if dy > 0 else 0
            score_pl = min(15 / pl if pl > 0 else 0, 1) * 1.5
            score_pvp = min(2 / pvp if pvp > 0 else 0, 1) * 1.5
            score_roe = min(roe / 0.20, 1) * 3 if roe > 0 else 0
            
            # Novos componentes do score
            score_fcf = min(free_cash_flow / 1e9 if free_cash_flow > 0 else 0, 1) * 0.5
            score_payout = 1 if 0.3 <= payout_ratio <= 0.6 else 0.5 if payout_ratio > 0 else 0
            
            score_bruto = score_dy + score_pl + score_pvp + score_roe + score_fcf + score_payout
            score_total = min(score_bruto, 10)
            is_super = score_bruto > 10
            
            # Simulação de crescimento de dividendos (mockado para MVP)
            crescimento_dividendos = np.random.uniform(0.02, 0.15) if dy > 0 else 0
            
            # Classificação de risco
            risco_nivel = self._classificar_risco(debt_equity, pl, dy)
            
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
                risco_nivel=risco_nivel
            )
            
            self.cache_analises[ticker] = analise
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
                super_investimento=False
            )
    
    def _classificar_risco(self, debt_equity: float, pl: float, dy: float) -> str:
        """Classifica o nível de risco do ativo"""
        pontos_risco = 0
        
        if debt_equity > 1.0:
            pontos_risco += 2
        elif debt_equity > 0.5:
            pontos_risco += 1
            
        if pl > 25:
            pontos_risco += 2
        elif pl > 15:
            pontos_risco += 1
            
        if dy > 0.12:  # DY muito alto pode indicar risco
            pontos_risco += 1
            
        if pontos_risco >= 4:
            return "alto"
        elif pontos_risco >= 2:
            return "medio"
        else:
            return "baixo"
    
    def analisar_carteira(self, tickers: List[str], valores: List[float]) -> Dict:
        """Análise de uma carteira de ativos"""
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
    """Agente responsável pela personalização e recomendações"""
    
    def __init__(self):
        self.perfil_usuario = None
    
    def definir_perfil(self, perfil: PerfilUsuario):
        """Define o perfil do usuário para personalização"""
        self.perfil_usuario = perfil
    
    def recomendar_ativos(self, todos_tickers: List[str], limite: int = 10) -> List[AnaliseAtivo]:
        """Recomenda ativos baseado no perfil do usuário"""
        finance_agent = RendyFinanceAgent()
        analises_completas = []
        for ticker in todos_tickers:
            analise = finance_agent.analisar_ativo(ticker)
            if analise.score > 0:
                analises_completas.append(analise)

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
        """Verifica se o ativo é compatível com o perfil do usuário"""
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
        """Ajusta o score baseado no perfil do usuário"""
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
        """Gera sugestão de alocação baseada no perfil"""
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
    """Agente responsável pela explicabilidade e transparência das decisões"""
    
    def explicacao_score_detalhada(self, analise: AnaliseAtivo) -> Dict[str, str]:
        """Gera explicação detalhada do score de um ativo"""
        explicacoes = {
            'resumo': '',
            'fatores_positivos': [],
            'fatores_negativos': [],
            'fatores_neutros': [],
            'recomendacao': '',
            'riscos': []
        }
        
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
        
        if analise.risco_nivel == "baixo":
            explicacoes['fatores_positivos'].append("Classificado como investimento de baixo risco")
        elif analise.risco_nivel == "alto":
            explicacoes['riscos'].append("Classificado como investimento de alto risco")
        
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
    """Agente responsável por simulações e automação"""
    
    def simular_investimento(self, ticker: str, valor_inicial: float, periodo_anos: int = 5) -> Dict:
        """Simula investimento com reinvestimento de dividendos"""
        finance_agent = RendyFinanceAgent()
        analise = finance_agent.analisar_ativo(ticker)
        
        if analise.preco_atual <= 0:
            return {'erro': 'Não foi possível obter dados do ativo'}
        
        qtd_acoes_inicial = int(valor_inicial // analise.preco_atual)
        valor_investido = qtd_acoes_inicial * analise.preco_atual
        
        # Simulação de cenários
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
                # Crescimento do preço da ação
                preco_acao *= (1 + params['crescimento_preco'])
                
                # Crescimento do dividend yield
                dy_atual *= (1 + params['crescimento_dividendo'])
                
                # Dividendos recebidos no ano
                dividendos_ano = qtd_acoes * preco_acao * dy_atual
                
                # Reinvestimento dos dividendos
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
    """Agente de suporte e educação financeira"""
    
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
        """Responde perguntas sobre investimentos e o aplicativo"""
        pergunta_lower = pergunta.lower().strip()
        
        # Busca por palavras-chave na pergunta
        for chave, resposta in self.faq.items():
            if any(palavra in pergunta_lower for palavra in chave.split()):
                return resposta
        
        # Respostas específicas sobre o aplicativo
        if any(palavra in pergunta_lower for palavra in ['rendy', 'aplicativo', 'app', 'plataforma']):
            return "A Rendy AI é uma plataforma inteligente que ajuda você a investir em ações que pagam dividendos. Usamos algoritmos avançados para analisar e ranquear as melhores oportunidades do mercado brasileiro, considerando seu perfil de investidor."
        
        if any(palavra in pergunta_lower for palavra in ['segurança', 'dados', 'privacidade']):
            return "Sua privacidade é nossa prioridade. Não coletamos dados pessoais desnecessários e todas as informações são processadas localmente. Seus dados de perfil ficam armazenados apenas no seu dispositivo."
        
        if any(palavra in pergunta_lower for palavra in ['começar', 'iniciar', 'primeiro']):
            return "Para começar: 1) Preencha seu perfil de investidor, 2) Explore nosso ranking de ações, 3) Use a simulação para entender o potencial, 4) Monte sua carteira com nossa ajuda. Sempre invista apenas o que pode perder!"
        
        # Resposta padrão
        return "Desculpe, não encontrei uma resposta específica para sua pergunta. Tente perguntar sobre: dividend yield, score, perfil de risco, como escolher ações, super investimentos, tributação, simulação ou reinvestimento. Nossa equipe está sempre trabalhando para melhorar o atendimento!"
    
    def calcular_renda_objetivo(self, renda_mensal_desejada: float, dy_medio: float = 0.08) -> Dict:
        """Calcula quanto investir para atingir renda mensal desejada"""
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
        """Calcula aporte mensal necessário para atingir objetivo"""
        if prazo_meses <= 0:
            return {'erro': 'Prazo deve ser maior que zero'}
        
        # Fórmula de valor futuro com aportes mensais
        fv_capital_atual = capital_atual * ((1 + rentabilidade_mensal) ** prazo_meses)
        valor_restante = capital_objetivo - fv_capital_atual
        
        if valor_restante <= 0:
            aporte_mensal = 0
        else:
            # PMT = FV / [((1+r)^n - 1) / r]
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

class RendyComplianceAgent:
    """Agente de conformidade e gestão de riscos"""
    
    def gerar_disclaimer(self) -> str:
        """Gera disclaimer de conformidade"""
        return """
        **⚠️ IMPORTANTE - DISCLAIMER DE INVESTIMENTOS**
        
        As informações fornecidas pela Rendy AI são apenas para fins educacionais e não constituem recomendação de investimento. 
        
        • **Riscos**: Todo investimento envolve riscos, incluindo a possibilidade de perda do capital investido.
        • **Decisão Própria**: As decisões de investimento são de sua inteira responsabilidade.
        • **Consultoria**: Considere consultar um assessor de investimentos qualificado.
        • **Dados**: As informações podem conter erros ou estar desatualizadas.
        • **Tributação**: Consulte um contador sobre aspectos tributários.
        
        **A Rendy AI não se responsabiliza por perdas decorrentes do uso destas informações.**
        """
    
    def avaliar_risco_carteira(self, analises_carteira: List[Dict]) -> Dict:
        """Avalia o risco geral da carteira"""
        if not analises_carteira:
            return {'risco': 'indefinido', 'recomendacoes': []}
        
        riscos_altos = sum(1 for a in analises_carteira if a['analise'].risco_nivel == 'alto')
        total_ativos = len(analises_carteira)
        percentual_alto_risco = riscos_altos / total_ativos
        
        setores = set(a['analise'].setor for a in analises_carteira)
        diversificacao_setorial = len(setores)
        
        recomendacoes = []
        
        if percentual_alto_risco > 0.5:
            recomendacoes.append("Carteira com muitos ativos de alto risco. Considere rebalancear.")
        
        if diversificacao_setorial < 3:
            recomendacoes.append("Baixa diversificação setorial. Considere incluir ativos de outros setores.")
        
        if total_ativos < 5:
            recomendacoes.append("Carteira com poucos ativos. Considere diversificar mais.")
        
        if percentual_alto_risco > 0.7:
            nivel_risco = 'muito_alto'
        elif percentual_alto_risco > 0.4:
            nivel_risco = 'alto'
        elif percentual_alto_risco > 0.2:
            nivel_risco = 'moderado'
        else:
            nivel_risco = 'baixo'
        
        return {
            'risco': nivel_risco,
            'percentual_alto_risco': percentual_alto_risco,
            'diversificacao_setorial': diversificacao_setorial,
            'recomendacoes': recomendacoes
        }

class RendyOrchestrator:
    """Orquestrador principal que coordena todos os agentes"""
    
    def __init__(self):
        self.finance_agent = RendyFinanceAgent()
        self.invest_agent = RendyInvestAgent()
        self.xai_agent = RendyXAI()
        self.auto_agent = RendyAutoAgent()
        self.support_agent = RendySupportAgent()
        self.compliance_agent = RendyComplianceAgent()
        
        # Estado da sessão
        if 'carteira' not in st.session_state:
            st.session_state.carteira = []
        if 'simulacao_cache' not in st.session_state:
            st.session_state.simulacao_cache = {}
        if 'perfil_completo' not in st.session_state:
            st.session_state.perfil_completo = False
        if 'mostrar_boas_vindas' not in st.session_state:
            st.session_state.mostrar_boas_vindas = True
    
    def run(self):
        """Executa a aplicação principal"""
        inicializar_ambiente()
        
        # Verifica se o perfil está completo
        perfil = carregar_perfil_usuario()
        if perfil:
            st.session_state.perfil_completo = True
            st.session_state.mostrar_boas_vindas = False
            self.invest_agent.definir_perfil(perfil)
        
        # Tela de boas-vindas
        if st.session_state.mostrar_boas_vindas and not st.session_state.perfil_completo:
            self.tela_boas_vindas()
            return
        
        # Tela de perfil obrigatório
        if not st.session_state.perfil_completo:
            self.tela_perfil_obrigatorio()
            return
        
        # Interface principal
        self.interface_principal()
    
    def tela_boas_vindas(self):
        """Tela de boas-vindas com informações de privacidade"""
        st.markdown("""
        <div style='text-align: center; padding: 2rem;'>
            <h1>🤖 Bem-vindo à Rendy AI</h1>
            <h2>Plataforma de Investimentos</h2>
            <h3 style='color: #666;'>Sua assistente inteligente para investimentos em dividendos no Brasil</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            ### 🔒 Sua Privacidade é Nossa Prioridade
            
            **Compromisso com a Segurança:**
            • **Não coletamos dados pessoais** desnecessários
            • **Processamento local** - suas informações ficam no seu dispositivo
            • **Sem compartilhamento** de dados com terceiros
            • **Conformidade com a LGPD** - Lei Geral de Proteção de Dados
            
            ### 🎯 O que Oferecemos
            
            • **Ranking Inteligente** de ações que pagam dividendos
            • **Simulações avançadas** de investimento
            • **Carteira personalizada** baseada no seu perfil
            • **Assistente IA** para suas dúvidas sobre investimentos
            
            ### ⚠️ Importante
            
            Esta plataforma é para fins **educacionais e informativos**. Não constitui recomendação de investimento. 
            Sempre consulte um profissional qualificado antes de investir.
            """)
            
            st.markdown("---")
            
            if st.button("🚀 Começar Agora", type="primary", use_container_width=True):
                st.session_state.mostrar_boas_vindas = False
                st.rerun()
    
    def tela_perfil_obrigatorio(self):
        """Tela obrigatória para preenchimento do perfil"""
        st.markdown("""
        <div style='text-align: center; padding: 1rem;'>
            <h2>📋 Complete Seu Perfil de Investidor</h2>
            <p style='color: #666;'>Para oferecer recomendações personalizadas, precisamos conhecer seu perfil.</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("perfil_usuario"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome Completo*", placeholder="Seu nome")
                email = st.text_input("E-mail*", placeholder="seu@email.com")
                
                tolerancia_risco = st.selectbox(
                    "Tolerância ao Risco*",
                    ["conservador", "moderado", "agressivo"],
                    format_func=lambda x: {
                        "conservador": "Conservador - Priorizo segurança",
                        "moderado": "Moderado - Equilibro risco e retorno", 
                        "agressivo": "Agressivo - Aceito mais risco por maior retorno"
                    }[x]
                )
                
                horizonte = st.selectbox(
                    "Horizonte de Investimento*",
                    ["curto", "medio", "longo"],
                    format_func=lambda x: {
                        "curto": "Curto prazo (até 2 anos)",
                        "medio": "Médio prazo (2 a 5 anos)",
                        "longo": "Longo prazo (mais de 5 anos)"
                    }[x]
                )
            
            with col2:
                objetivo = st.selectbox(
                    "Objetivo Principal*",
                    ["renda_passiva", "crescimento", "preservacao"],
                    format_func=lambda x: {
                        "renda_passiva": "Gerar renda passiva",
                        "crescimento": "Crescimento do patrimônio",
                        "preservacao": "Preservação do capital"
                    }[x]
                )
                
                experiencia = st.selectbox(
                    "Experiência em Investimentos*",
                    ["iniciante", "intermediario", "avancado"],
                    format_func=lambda x: {
                        "iniciante": "Iniciante - Pouca experiência",
                        "intermediario": "Intermediário - Alguma experiência",
                        "avancado": "Avançado - Muita experiência"
                    }[x]
                )
                
                valor_disponivel = st.number_input(
                    "Valor Disponível para Investir (R$)",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    help="Valor aproximado que pretende investir"
                )
                
                setores = st.multiselect(
                    "Setores Preferidos (Opcional)",
                    SETORES_DISPONIVEIS,
                    help="Deixe em branco ou selecione 'Todos' para não ter preferência"
                )
            
            submitted = st.form_submit_button("✅ Salvar Perfil e Continuar", type="primary", use_container_width=True)
            
            if submitted:
                if not nome or not email:
                    st.error("Por favor, preencha nome e e-mail.")
                elif not validar_email(email):
                    st.error("Por favor, insira um e-mail válido.")
                else:
                    perfil = PerfilUsuario(
                        nome=nome,
                        email=email,
                        tolerancia_risco=tolerancia_risco,
                        horizonte_investimento=horizonte,
                        objetivo_principal=objetivo,
                        experiencia=experiencia,
                        valor_disponivel=valor_disponivel,
                        setores_preferidos=setores if setores else ["Todos"]
                    )
                    
                    salvar_perfil_usuario(perfil)
                    self.invest_agent.definir_perfil(perfil)
                    st.session_state.perfil_completo = True
                    
                    st.success("✅ Perfil salvo com sucesso! Redirecionando...")
                    st.rerun()
    
    def interface_principal(self):
        """Interface principal da aplicação"""
        # Header
        st.markdown("""
        <div style='text-align: center; padding: 1rem; background: linear-gradient(90deg, #1f4e79, #2d5aa0); color: white; margin-bottom: 2rem; border-radius: 10px;'>
            <h1>🤖 Rendy AI - Plataforma de Investimentos</h1>
            <p style='margin: 0; font-size: 1.1em;'>Sua assistente inteligente para investimentos em dividendos no Brasil</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Navegação por abas
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Ranking Inteligente", 
            "🎯 Simulação IA", 
            "💼 Carteira Agêntica", 
            "🤖 Assistente IA", 
            "👤 Perfil", 
            "📚 Glossário"
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
    
    def aba_ranking_inteligente(self):
        """Aba do ranking inteligente com TODAY NEWS"""
        st.markdown("### 🏆 Ranking Inteligente de Ações")
        
        # Explicação do algoritmo
        with st.expander("ℹ️ Como Funciona Nosso Algoritmo", expanded=False):
            st.markdown("""
            **Nosso algoritmo proprietário analisa:**
            
            • **Dividend Yield (DY)** - Peso 4: Percentual de dividendos pagos
            • **Preço/Lucro (P/L)** - Peso 1,5: Indica se a ação está cara ou barata
            • **Preço/Valor Patrimonial (P/VP)** - Peso 1,5: Relação entre preço e valor contábil
            • **Return on Equity (ROE)** - Peso 3: Eficiência da empresa em gerar lucros
            • **Fluxo de Caixa Livre** - Peso 0,5: Capacidade de gerar caixa
            • **Payout Ratio** - Peso variável: Sustentabilidade dos dividendos
            
            **📈 Universo Analisado:** Analisamos as principais ações do Ibovespa, descartando automaticamente 
            empresas que não pagam dividendos ou têm histórico muito ruim nesta área.
            
            **🎯 Score:** Cada ação recebe uma nota de 0 a 10. Ações com fundamentos excepcionais 
            podem ser classificadas como "Super Investimentos".
            """)
        
        # Vantagens dos dividendos
        with st.expander("💰 Por que Investir em Ações de Dividendos?", expanded=False):
            st.markdown("""
            **Vantagens dos Investimentos em Dividendos:**
            
            ✅ **Renda Passiva Regular:** Receba pagamentos periódicos sem vender suas ações
            
            ✅ **Isenção de IR:** Dividendos são isentos de Imposto de Renda para pessoa física
            
            ✅ **Proteção contra Inflação:** Empresas sólidas tendem a reajustar dividendos
            
            ✅ **Juros Compostos:** Reinvestindo dividendos, você acelera o crescimento patrimonial
            
            ✅ **Empresas Maduras:** Geralmente são empresas consolidadas e menos voláteis
            
            ✅ **Flexibilidade:** Você pode usar a renda ou reinvestir conforme sua estratégia
            
            **Comparado a outros investimentos:**
            • **Poupança/CDB:** Dividendos podem superar a renda fixa no longo prazo
            • **Fundos Imobiliários:** Ações oferecem maior potencial de crescimento
            • **Tesouro Direto:** Dividendos não têm prazo de vencimento
            """)
        
        # TODAY NEWS - Panorama de Investimentos
        st.markdown("### 📰 TODAY NEWS - Panorama de Investimentos")
        st.caption(f"Última atualização: {TODAY_NEWS_DATA['data_atualizacao']}")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("#### 📊 Ranking de Rentabilidade Anualizada")
            
            df_investimentos = pd.DataFrame(TODAY_NEWS_DATA['investimentos'])
            df_investimentos = df_investimentos.sort_values('rentabilidade_liquida', ascending=False)
            
            # Criar gráfico de barras
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                name='Rentabilidade Bruta',
                x=df_investimentos['nome'],
                y=df_investimentos['rentabilidade_bruta'],
                marker_color='lightblue',
                text=[f"{x:.1f}%" for x in df_investimentos['rentabilidade_bruta']],
                textposition='auto'
            ))
            
            fig.add_trace(go.Bar(
                name='Rentabilidade Líquida',
                x=df_investimentos['nome'],
                y=df_investimentos['rentabilidade_liquida'],
                marker_color='darkblue',
                text=[f"{x:.1f}%" for x in df_investimentos['rentabilidade_liquida']],
                textposition='auto'
            ))
            
            fig.update_layout(
                title="Comparativo de Rentabilidades (% ao ano)",
                xaxis_title="Tipo de Investimento",
                yaxis_title="Rentabilidade (%)",
                barmode='group',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### 📈 Índices de Inflação")
            
            for inflacao in TODAY_NEWS_DATA['inflacao']:
                delta_color = "normal" if inflacao['valor'] < 5 else "inverse"
                st.metric(
                    label=inflacao['indice'],
                    value=f"{inflacao['valor']:.2f}%",
                    delta=f"Meta: 3,25%",
                    delta_color=delta_color
                )
            
            st.markdown("#### 🏅 Top 3 Investimentos")
            for i, inv in enumerate(df_investimentos.head(3).to_dict('records')):
                emoji = ["🥇", "🥈", "🥉"][i]
                st.markdown(f"""
                **{emoji} {inv['nome']}**  
                Líquido: {inv['rentabilidade_liquida']:.1f}%
                """)
        
        # Ranking de ações
        st.markdown("---")
        st.markdown("### 🎯 Ranking de Ações por Score")
        
        with st.spinner("Analisando ações do mercado..."):
            # Análise das ações
            analises = []
            progress_bar = st.progress(0)
            
            for i, ticker in enumerate(LISTA_TICKERS_IBOV[:20]):  # Limita a 20 para performance
                analise = self.finance_agent.analisar_ativo(ticker)
                if analise.score > 0:
                    analises.append(analise)
                progress_bar.progress((i + 1) / 20)
            
            progress_bar.empty()
            
            # Ordena por score
            analises.sort(key=lambda x: x.score, reverse=True)
            
            # Exibe o ranking
            for i, analise in enumerate(analises[:10]):
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([1, 3, 2, 2, 2])
                    
                    with col1:
                        st.markdown(f"**#{i+1}**")
                    
                    with col2:
                        emoji = "⭐" if analise.super_investimento else "📈"
                        st.markdown(f"**{emoji} {analise.ticker.replace('.SA', '')}**")
                        st.caption(analise.nome_empresa[:30] + "..." if len(analise.nome_empresa) > 30 else analise.nome_empresa)
                    
                    with col3:
                        score_color = "🟢" if analise.score >= 7 else "🟡" if analise.score >= 5 else "🔴"
                        st.metric("Score", f"{analise.score:.1f}/10", delta=score_color)
                    
                    with col4:
                        st.metric("DY", f"{analise.dy:.2%}")
                        st.metric("P/L", f"{analise.pl:.1f}" if analise.pl > 0 else "N/A")
                    
                    with col5:
                        risco_emoji = {"baixo": "🟢", "medio": "🟡", "alto": "🔴"}[analise.risco_nivel]
                        st.metric("Risco", f"{risco_emoji} {analise.risco_nivel.title()}")
                        st.metric("Preço", f"R$ {analise.preco_atual:.2f}")
                    
                    if analise.alerta_dy:
                        st.warning(analise.alerta_dy, icon="⚠️")
                    
                    st.markdown("---")
        
        # Disclaimer
        st.markdown(self.compliance_agent.gerar_disclaimer())
    
    def aba_simulacao_ia(self):
        """Aba de simulação com IA"""
        st.markdown("### 🎯 Simulação Inteligente de Investimentos")
        st.markdown("Simule o crescimento do seu investimento com reinvestimento automático de dividendos.")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            ticker_input = st.text_input(
                "Código da Ação",
                value="ITUB4.SA",
                help="Digite o código da ação (ex: PETR4.SA, VALE3.SA)"
            ).upper()
            
            valor_inicial = st.number_input(
                "Valor Inicial (R$)",
                min_value=100.0,
                value=10000.0,
                step=1000.0
            )
        
        with col2:
            periodo_anos = st.slider(
                "Período (anos)",
                min_value=1,
                max_value=20,
                value=5
            )
            
            simular = st.button("🚀 Simular Investimento", type="primary")
        
        if simular and ticker_input:
            with st.spinner("Processando simulação..."):
                resultado = self.auto_agent.simular_investimento(ticker_input, valor_inicial, periodo_anos)
                
                if 'erro' in resultado:
                    st.error(resultado['erro'])
                else:
                    st.session_state.simulacao_cache[ticker_input] = resultado
                    
                    # Informações básicas
                    st.success(f"✅ Simulação concluída para {resultado['ticker'].replace('.SA', '')}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Valor Investido", f"R$ {resultado['valor_inicial']:,.2f}")
                    with col2:
                        st.metric("Ações Iniciais", f"{resultado['qtd_acoes_inicial']:,}")
                    with col3:
                        st.metric("DY Inicial", f"{resultado['dy_inicial']:.2%}")
                    
                    # Resultados por cenário
                    st.markdown("#### 📊 Resultados por Cenário")
                    
                    cenarios_data = []
                    for nome, dados in resultado['cenarios'].items():
                        cenarios_data.append({
                            'Cenário': nome.title(),
                            'Valor Final': f"R$ {dados['valor_final']:,.2f}",
                            'Renda Anual': f"R$ {dados['renda_anual_final']:,.2f}",
                            'Retorno Total': f"{dados['retorno_total']:.1%}"
                        })
                    
                    df_cenarios = pd.DataFrame(cenarios_data)
                    st.dataframe(df_cenarios, use_container_width=True)
                    
                    # Gráfico de evolução
                    st.markdown("#### 📈 Evolução do Patrimônio")
                    
                    fig = go.Figure()
                    
                    for nome, dados in resultado['cenarios'].items():
                        anos = [h['ano'] for h in dados['historico']]
                        valores = [h['valor_carteira'] for h in dados['historico']]
                        
                        fig.add_trace(go.Scatter(
                            x=anos,
                            y=valores,
                            mode='lines+markers',
                            name=nome.title(),
                            line=dict(width=3)
                        ))
                    
                    fig.update_layout(
                        title="Evolução do Valor da Carteira",
                        xaxis_title="Anos",
                        yaxis_title="Valor (R$)",
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Botão para adicionar à carteira
                    st.markdown("#### 💼 Adicionar à Carteira")
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.info("Gostou da simulação? Adicione esta ação à sua carteira para análise detalhada.")
                    
                    with col2:
                        if st.button("➕ Adicionar à Carteira", key="add_simulacao"):
                            # Adiciona à carteira
                            nova_acao = {
                                'ticker': ticker_input,
                                'valor': valor_inicial
                            }
                            
                            # Verifica se já existe
                            existe = any(acao['ticker'] == ticker_input for acao in st.session_state.carteira)
                            
                            if not existe:
                                st.session_state.carteira.append(nova_acao)
                                st.success(f"✅ {ticker_input.replace('.SA', '')} adicionada à carteira!")
                                st.rerun()
                            else:
                                st.warning("Esta ação já está na sua carteira.")
        
        # Mostra simulação em cache se existir
        if st.session_state.simulacao_cache:
            st.markdown("---")
            st.markdown("#### 📋 Simulações Recentes")
            
            for ticker, resultado in st.session_state.simulacao_cache.items():
                with st.expander(f"📊 {ticker.replace('.SA', '')} - Última Simulação"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        melhor_cenario = max(resultado['cenarios'].items(), key=lambda x: x[1]['valor_final'])
                        st.metric(
                            "Melhor Cenário",
                            melhor_cenario[0].title(),
                            f"R$ {melhor_cenario[1]['valor_final']:,.2f}"
                        )
                    
                    with col2:
                        pior_cenario = min(resultado['cenarios'].items(), key=lambda x: x[1]['valor_final'])
                        st.metric(
                            "Cenário Conservador",
                            pior_cenario[0].title(),
                            f"R$ {pior_cenario[1]['valor_final']:,.2f}"
                        )
                    
                    with col3:
                        if st.button(f"🗑️ Limpar", key=f"clear_{ticker}"):
                            del st.session_state.simulacao_cache[ticker]
                            st.rerun()
    
    def aba_carteira_agentica(self):
        """Aba da carteira agêntica melhorada"""
        st.markdown("### 💼 Carteira Agêntica")
        st.markdown("Monte sua carteira de dividendos com a ajuda da nossa IA.")
        
        # Seção de sugestões da IA
        st.markdown("#### 🤖 Sugestões da IA")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info("Nossa IA pode sugerir ações baseadas no seu perfil de investidor. Clique no botão ao lado para receber recomendações personalizadas.")
        
        with col2:
            if st.button("🎯 Gerar Sugestões", type="primary"):
                with st.spinner("Analisando mercado e seu perfil..."):
                    perfil = carregar_perfil_usuario()
                    if perfil:
                        self.invest_agent.definir_perfil(perfil)
                    
                    sugestoes = self.invest_agent.recomendar_ativos(LISTA_TICKERS_IBOV, limite=8)
                    
                    if sugestoes:
                        st.markdown("##### 📋 Ações Recomendadas para Você")
                        
                        for i, analise in enumerate(sugestoes):
                            with st.container():
                                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                                
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
                                    
                                    if st.button("➕", key=f"add_sug_{analise.ticker}", help="Adicionar à carteira"):
                                        nova_acao = {
                                            'ticker': analise.ticker,
                                            'valor': valor_sugerido
                                        }
                                        
                                        # Verifica se já existe
                                        existe = any(acao['ticker'] == analise.ticker for acao in st.session_state.carteira)
                                        
                                        if not existe:
                                            st.session_state.carteira.append(nova_acao)
                                            st.success(f"✅ {analise.ticker.replace('.SA', '')} adicionada!")
                                            st.rerun()
                                        else:
                                            st.warning("Já está na carteira")
                                
                                st.markdown("---")
        
        # Seção de adição manual
        st.markdown("#### ✋ Adicionar Manualmente")
        
        with st.form("adicionar_acao"):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                ticker_manual = st.text_input(
                    "Código da Ação",
                    placeholder="Ex: PETR4.SA",
                    help="Digite o código completo da ação"
                ).upper()
            
            with col2:
                valor_manual = st.number_input(
                    "Valor a Investir (R$)",
                    min_value=0.0,
                    value=1000.0,
                    step=100.0
                )
            
            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                adicionar_manual = st.form_submit_button("➕ Adicionar", type="primary")
            
            if adicionar_manual and ticker_manual:
                # Verifica se já existe
                existe = any(acao['ticker'] == ticker_manual for acao in st.session_state.carteira)
                
                if not existe:
                    nova_acao = {
                        'ticker': ticker_manual,
                        'valor': valor_manual
                    }
                    st.session_state.carteira.append(nova_acao)
                    st.success(f"✅ {ticker_manual.replace('.SA', '')} adicionada à carteira!")
                    st.rerun()
                else:
                    st.warning("Esta ação já está na sua carteira.")
        
        # Exibição da carteira atual
        if st.session_state.carteira:
            st.markdown("---")
            st.markdown("#### 📊 Sua Carteira Atual")
            
            # Análise da carteira
            tickers = [acao['ticker'] for acao in st.session_state.carteira]
            valores = [acao['valor'] for acao in st.session_state.carteira]
            
            with st.spinner("Analisando sua carteira..."):
                analise_carteira = self.finance_agent.analisar_carteira(tickers, valores)
                
                # Métricas gerais
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Valor Total", f"R$ {analise_carteira['valor_total']:,.2f}")
                
                with col2:
                    st.metric("Renda Anual", f"R$ {analise_carteira['renda_total_anual']:,.2f}")
                
                with col3:
                    st.metric("Yield da Carteira", f"{analise_carteira['yield_carteira']:.2%}")
                
                with col4:
                    st.metric("Diversificação", f"{analise_carteira['diversificacao']} setores")
                
                # Detalhes por ação
                st.markdown("##### 📋 Detalhes por Ação")
                
                for i, item in enumerate(analise_carteira['analises']):
                    analise = item['analise']
                    
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
                        
                        with col1:
                            emoji = "⭐" if analise.super_investimento else "📈"
                            st.markdown(f"**{emoji} {analise.ticker.replace('.SA', '')}**")
                            st.caption(f"Peso: {item['peso_carteira']:.1%}")
                        
                        with col2:
                            st.metric("Valor Alocado", f"R$ {item['valor_alocado']:,.2f}")
                            st.metric("Qtd. Ações", f"{item['qtd_acoes']:,}")
                        
                        with col3:
                            st.metric("Score", f"{analise.score:.1f}/10")
                            st.metric("DY", f"{analise.dy:.2%}")
                        
                        with col4:
                            st.metric("Renda Anual", f"R$ {item['renda_anual']:,.2f}")
                            risco_emoji = {"baixo": "🟢", "medio": "🟡", "alto": "🔴"}[analise.risco_nivel]
                            st.markdown(f"Risco: {risco_emoji}")
                        
                        with col5:
                            if st.button("🗑️", key=f"remove_{i}", help="Remover da carteira"):
                                st.session_state.carteira.pop(i)
                                st.rerun()
                        
                        # Explicação XAI
                        with st.expander(f"🔍 Por que {analise.ticker.replace('.SA', '')}?"):
                            explicacao = self.xai_agent.explicacao_score_detalhada(analise)
                            
                            if explicacao['fatores_positivos']:
                                st.markdown("**✅ Pontos Positivos:**")
                                for ponto in explicacao['fatores_positivos']:
                                    st.markdown(f"• {ponto}")
                            
                            if explicacao['fatores_negativos']:
                                st.markdown("**❌ Pontos de Atenção:**")
                                for ponto in explicacao['fatores_negativos']:
                                    st.markdown(f"• {ponto}")
                            
                            if explicacao['recomendacao']:
                                st.info(f"**Recomendação:** {explicacao['recomendacao']}")
                        
                        st.markdown("---")
                
                # Análise de risco da carteira
                avaliacao_risco = self.compliance_agent.avaliar_risco_carteira(analise_carteira['analises'])
                
                st.markdown("##### ⚖️ Análise de Risco da Carteira")
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    risco_cores = {
                        'baixo': '🟢',
                        'moderado': '🟡', 
                        'alto': '🟠',
                        'muito_alto': '🔴'
                    }
                    st.metric(
                        "Nível de Risco",
                        f"{risco_cores[avaliacao_risco['risco']]} {avaliacao_risco['risco'].replace('_', ' ').title()}"
                    )
                
                with col2:
                    if avaliacao_risco['recomendacoes']:
                        st.markdown("**Recomendações:**")
                        for rec in avaliacao_risco['recomendacoes']:
                            st.markdown(f"• {rec}")
                    else:
                        st.success("✅ Sua carteira está bem balanceada!")
                
                # Botão para limpar carteira
                if st.button("🗑️ Limpar Carteira", type="secondary"):
                    st.session_state.carteira = []
                    st.rerun()
        
        else:
            st.info("📝 Sua carteira está vazia. Adicione algumas ações para começar a análise!")
        
        # Disclaimer
        st.markdown("---")
        st.markdown(self.compliance_agent.gerar_disclaimer())
    
    def aba_assistente_ia(self):
        """Aba do assistente IA melhorada"""
        st.markdown("### 🤖 Assistente IA")
        st.markdown("Tire suas dúvidas sobre investimentos em dividendos e sobre a plataforma.")
        
        # Chat interface
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        # Exibe histórico do chat
        for i, (pergunta, resposta) in enumerate(st.session_state.chat_history):
            with st.container():
                st.markdown(f"**👤 Você:** {pergunta}")
                st.markdown(f"**🤖 Rendy AI:** {resposta}")
                st.markdown("---")
        
        # Input para nova pergunta
        pergunta = st.text_input(
            "Faça sua pergunta:",
            placeholder="Ex: Como funciona o dividend yield?",
            key="chat_input"
        )
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
            enviar = st.button("📤 Enviar", type="primary")
        
        if enviar and pergunta:
            resposta = self.support_agent.responder_pergunta(pergunta)
            st.session_state.chat_history.append((pergunta, resposta))
            st.rerun()
        
        # Perguntas frequentes
        st.markdown("---")
        st.markdown("#### ❓ Perguntas Frequentes")
        
        perguntas_freq = [
            "O que é dividend yield?",
            "Como funciona o score?",
            "Qual o melhor perfil de risco?",
            "Como escolher ações?",
            "O que são super investimentos?",
            "Dividendos são tributados?",
            "Quanto investir em dividendos?",
            "Como usar a simulação?"
        ]
        
        col1, col2 = st.columns(2)
        
        for i, pergunta_freq in enumerate(perguntas_freq):
            col = col1 if i % 2 == 0 else col2
            
            with col:
                if st.button(f"💬 {pergunta_freq}", key=f"faq_{i}"):
                    resposta = self.support_agent.responder_pergunta(pergunta_freq)
                    st.session_state.chat_history.append((pergunta_freq, resposta))
                    st.rerun()
        
        # Calculadoras úteis
        st.markdown("---")
        st.markdown("#### 🧮 Calculadoras Úteis")
        
        tab1, tab2 = st.tabs(["💰 Renda Objetivo", "📈 Aporte Necessário"])
        
        with tab1:
            st.markdown("##### Calcule quanto investir para atingir sua renda mensal desejada")
            
            col1, col2 = st.columns(2)
            
            with col1:
                renda_desejada = st.number_input(
                    "Renda Mensal Desejada (R$)",
                    min_value=100.0,
                    value=3000.0,
                    step=100.0
                )
                
                dy_medio = st.slider(
                    "Dividend Yield Médio Esperado",
                    min_value=0.04,
                    max_value=0.15,
                    value=0.08,
                    format="%.1%"
                )
            
            with col2:
                if st.button("🧮 Calcular Capital Necessário"):
                    resultado = self.support_agent.calcular_renda_objetivo(renda_desejada, dy_medio)
                    
                    st.success(f"""
                    **Resultado:**
                    
                    • **Renda mensal desejada:** R$ {resultado['renda_mensal']:,.2f}
                    • **Renda anual:** R$ {resultado['renda_anual']:,.2f}
                    • **Capital necessário:** R$ {resultado['capital_necessario']:,.2f}
                    • **DY considerado:** {resultado['dy_considerado']:.1%}
                    """)
        
        with tab2:
            st.markdown("##### Calcule quanto aportar mensalmente para atingir seu objetivo")
            
            col1, col2 = st.columns(2)
            
            with col1:
                capital_objetivo = st.number_input(
                    "Capital Objetivo (R$)",
                    min_value=1000.0,
                    value=100000.0,
                    step=1000.0
                )
                
                capital_atual = st.number_input(
                    "Capital Atual (R$)",
                    min_value=0.0,
                    value=10000.0,
                    step=1000.0
                )
                
                prazo_meses = st.number_input(
                    "Prazo (meses)",
                    min_value=1,
                    value=60,
                    step=1
                )
            
            with col2:
                if st.button("🧮 Calcular Aporte Mensal"):
                    resultado = self.support_agent.calcular_aporte_necessario(
                        capital_objetivo, capital_atual, prazo_meses
                    )
                    
                    if 'erro' in resultado:
                        st.error(resultado['erro'])
                    else:
                        st.success(f"""
                        **Resultado:**
                        
                        • **Aporte mensal necessário:** R$ {resultado['aporte_mensal']:,.2f}
                        • **Total de aportes:** R$ {resultado['total_aportes']:,.2f}
                        • **Prazo:** {resultado['prazo_meses']} meses
                        • **Rentabilidade considerada:** {resultado['rentabilidade_mensal']:.1%} ao mês
                        """)
        
        # Botão para limpar histórico
        if st.session_state.chat_history:
            st.markdown("---")
            if st.button("🗑️ Limpar Histórico do Chat"):
                st.session_state.chat_history = []
                st.rerun()
    
    def aba_perfil_usuario(self):
        """Aba do perfil do usuário"""
        st.markdown("### 👤 Perfil do Investidor")
        
        perfil = carregar_perfil_usuario()
        
        if perfil:
            st.success("✅ Perfil configurado com sucesso!")
            
            # Exibe informações atuais
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📋 Informações Pessoais")
                st.info(f"**Nome:** {perfil.nome}")
                st.info(f"**E-mail:** {perfil.email}")
                st.info(f"**Valor Disponível:** R$ {perfil.valor_disponivel:,.2f}")
            
            with col2:
                st.markdown("#### 🎯 Perfil de Investimento")
                st.info(f"**Tolerância ao Risco:** {perfil.tolerancia_risco.title()}")
                st.info(f"**Horizonte:** {perfil.horizonte_investimento.title()} prazo")
                st.info(f"**Objetivo:** {perfil.objetivo_principal.replace('_', ' ').title()}")
                st.info(f"**Experiência:** {perfil.experiencia.title()}")
            
            if perfil.setores_preferidos:
                st.markdown("#### 🏭 Setores Preferidos")
                setores_str = ", ".join(perfil.setores_preferidos)
                st.info(setores_str)
            
            # Formulário para atualizar
            st.markdown("---")
            st.markdown("#### ✏️ Atualizar Perfil")
            
            with st.form("atualizar_perfil"):
                col1, col2 = st.columns(2)
                
                with col1:
                    novo_nome = st.text_input("Nome Completo", value=perfil.nome)
                    novo_email = st.text_input("E-mail", value=perfil.email)
                    
                    nova_tolerancia = st.selectbox(
                        "Tolerância ao Risco",
                        ["conservador", "moderado", "agressivo"],
                        index=["conservador", "moderado", "agressivo"].index(perfil.tolerancia_risco),
                        format_func=lambda x: {
                            "conservador": "Conservador - Priorizo segurança",
                            "moderado": "Moderado - Equilibro risco e retorno", 
                            "agressivo": "Agressivo - Aceito mais risco por maior retorno"
                        }[x]
                    )
                    
                    novo_horizonte = st.selectbox(
                        "Horizonte de Investimento",
                        ["curto", "medio", "longo"],
                        index=["curto", "medio", "longo"].index(perfil.horizonte_investimento),
                        format_func=lambda x: {
                            "curto": "Curto prazo (até 2 anos)",
                            "medio": "Médio prazo (2 a 5 anos)",
                            "longo": "Longo prazo (mais de 5 anos)"
                        }[x]
                    )
                
                with col2:
                    novo_objetivo = st.selectbox(
                        "Objetivo Principal",
                        ["renda_passiva", "crescimento", "preservacao"],
                        index=["renda_passiva", "crescimento", "preservacao"].index(perfil.objetivo_principal),
                        format_func=lambda x: {
                            "renda_passiva": "Gerar renda passiva",
                            "crescimento": "Crescimento do patrimônio",
                            "preservacao": "Preservação do capital"
                        }[x]
                    )
                    
                    nova_experiencia = st.selectbox(
                        "Experiência em Investimentos",
                        ["iniciante", "intermediario", "avancado"],
                        index=["iniciante", "intermediario", "avancado"].index(perfil.experiencia),
                        format_func=lambda x: {
                            "iniciante": "Iniciante - Pouca experiência",
                            "intermediario": "Intermediário - Alguma experiência",
                            "avancado": "Avançado - Muita experiência"
                        }[x]
                    )
                    
                    novo_valor = st.number_input(
                        "Valor Disponível para Investir (R$)",
                        min_value=0.0,
                        value=float(perfil.valor_disponivel),
                        step=1000.0
                    )
                    
                    novos_setores = st.multiselect(
                        "Setores Preferidos",
                        SETORES_DISPONIVEIS,
                        default=perfil.setores_preferidos
                    )
                
                atualizar = st.form_submit_button("💾 Atualizar Perfil", type="primary")
                
                if atualizar:
                    if not novo_nome or not novo_email:
                        st.error("Por favor, preencha nome e e-mail.")
                    elif not validar_email(novo_email):
                        st.error("Por favor, insira um e-mail válido.")
                    else:
                        novo_perfil = PerfilUsuario(
                            nome=novo_nome,
                            email=novo_email,
                            tolerancia_risco=nova_tolerancia,
                            horizonte_investimento=novo_horizonte,
                            objetivo_principal=novo_objetivo,
                            experiencia=nova_experiencia,
                            valor_disponivel=novo_valor,
                            setores_preferidos=novos_setores if novos_setores else ["Todos"]
                        )
                        
                        salvar_perfil_usuario(novo_perfil)
                        self.invest_agent.definir_perfil(novo_perfil)
                        
                        st.success("✅ Perfil atualizado com sucesso!")
                        st.rerun()
        
        else:
            st.error("❌ Perfil não encontrado. Por favor, configure seu perfil.")
    
    def aba_glossario(self):
        """Aba do glossário"""
        st.markdown("### 📚 Glossário de Investimentos")
        st.markdown("Entenda os principais termos utilizados na plataforma.")
        
        # Busca no glossário
        busca = st.text_input("🔍 Buscar termo:", placeholder="Digite um termo para buscar...")
        
        # Filtra termos se houver busca
        termos_filtrados = GLOSSARIO
        if busca:
            termos_filtrados = {
                k: v for k, v in GLOSSARIO.items() 
                if busca.lower() in k.lower() or busca.lower() in v.lower()
            }
        
        # Exibe termos
        for termo, definicao in termos_filtrados.items():
            with st.expander(f"📖 {termo}"):
                st.markdown(definicao)
        
        if busca and not termos_filtrados:
            st.warning("🔍 Nenhum termo encontrado. Tente uma busca diferente.")
        
        # Termos adicionais
        st.markdown("---")
        st.markdown("#### 💡 Dicas Importantes")
        
        st.info("""
        **📈 Lembre-se:**
        • Diversifique sempre seus investimentos
        • Invista apenas o que pode perder
        • Estude antes de investir
        • Mantenha disciplina e foco no longo prazo
        • Reinvista os dividendos para potencializar ganhos
        """)
        
        st.warning("""
        **⚠️ Atenção:**
        • Rentabilidade passada não garante resultados futuros
        • Todo investimento envolve riscos
        • Consulte sempre um profissional qualificado
        • Mantenha-se atualizado sobre o mercado
        """)

# =================== EXECUÇÃO PRINCIPAL ===================
if __name__ == "__main__":
    orchestrator = RendyOrchestrator()
    orchestrator.run()

