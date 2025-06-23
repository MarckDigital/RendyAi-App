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
warnings.filterwarnings('ignore')

# =================== CONFIGURAÇÕES E CONSTANTES ===================
st.set_page_config(
    page_title="Rendy AI - Plataforma de IA Agêntica para Investimentos",
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
    "Super Investimento": "Ações que atingiram a pontuação máxima de 10 no score, mas cujo valor bruto dos critérios ultrapassou esse limite. São consideradas oportunidades excepcionais segundo o algoritmo.",
    "Free Cash Flow": "Fluxo de caixa livre: dinheiro que sobra após investimentos necessários. Indica capacidade de pagar dividendos.",
    "Payout Ratio": "Percentual do lucro distribuído como dividendos. Valores entre 30-60% são considerados saudáveis.",
    "Debt/Equity": "Relação dívida/patrimônio. Valores altos podem indicar risco financeiro.",
    "Margem Líquida": "Percentual do lucro líquido sobre a receita. Indica eficiência operacional.",
    "Crescimento de Dividendos": "Taxa de crescimento histórica dos dividendos. Indica sustentabilidade futura."
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
    
    def recomendar_ativos(self, analises: List[AnaliseAtivo], limite: int = 10) -> List[AnaliseAtivo]:
        """Recomenda ativos baseado no perfil do usuário"""
        if not self.perfil_usuario:
            # Retorna top por score se não há perfil
            return sorted(analises, key=lambda x: x.score, reverse=True)[:limite]
        
        # Filtragem baseada no perfil
        ativos_filtrados = []
        
        for analise in analises:
            if self._ativo_compativel_perfil(analise):
                # Ajusta score baseado no perfil
                score_ajustado = self._ajustar_score_perfil(analise)
                analise.score = score_ajustado
                ativos_filtrados.append(analise)
        
        return sorted(ativos_filtrados, key=lambda x: x.score, reverse=True)[:limite]
    
    def _ativo_compativel_perfil(self, analise: AnaliseAtivo) -> bool:
        """Verifica se o ativo é compatível com o perfil do usuário"""
        perfil = self.perfil_usuario
        
        # Filtro por tolerância ao risco
        if perfil.tolerancia_risco == "conservador" and analise.risco_nivel == "alto":
            return False
        elif perfil.tolerancia_risco == "moderado" and analise.risco_nivel == "alto":
            return analise.score >= 7  # Só aceita se score for muito bom
        
        # Filtro por setores preferidos
        if perfil.setores_preferidos and analise.setor not in perfil.setores_preferidos:
            return len(perfil.setores_preferidos) < 3  # Flexibiliza se poucos setores
        
        return True
    
    def _ajustar_score_perfil(self, analise: AnaliseAtivo) -> float:
        """Ajusta o score baseado no perfil do usuário"""
        score = analise.score
        perfil = self.perfil_usuario
        
        # Ajuste por objetivo
        if perfil.objetivo_principal == "renda_passiva":
            if analise.dy > 0.08:
                score += 0.5
        elif perfil.objetivo_principal == "crescimento":
            if analise.crescimento_dividendos > 0.1:
                score += 0.5
        
        # Ajuste por experiência
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
        num_ativos = min(len(ativos_recomendados), 5)  # Máximo 5 ativos
        
        # Estratégia de alocação baseada no perfil
        if perfil.tolerancia_risco == "conservador":
            # Concentra mais nos melhores ativos
            pesos = [0.4, 0.25, 0.2, 0.1, 0.05][:num_ativos]
        elif perfil.tolerancia_risco == "agressivo":
            # Distribui mais uniformemente
            pesos = [1/num_ativos] * num_ativos
        else:  # moderado
            pesos = [0.3, 0.25, 0.2, 0.15, 0.1][:num_ativos]
        
        # Normaliza os pesos
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
        
        # Análise dos componentes do score
        if analise.dy > 0.08:
            explicacoes['fatores_positivos'].append(
                f"Dividend Yield de {analise.dy*100:.2f}% está acima do target de 8%"
            )
        elif analise.dy > 0.05:
            explicacoes['fatores_neutros'].append(
                f"Dividend Yield de {analise.dy*100:.2f}% está em nível moderado"
            )
        else:
            explicacoes['fatores_negativos'].append(
                f"Dividend Yield de {analise.dy*100:.2f}% está abaixo do esperado"
            )
        
        if analise.roe > 0.20:
            explicacoes['fatores_positivos'].append(
                f"ROE de {analise.roe*100:.2f}% indica alta eficiência na geração de lucros"
            )
        elif analise.roe > 0.15:
            explicacoes['fatores_neutros'].append(
                f"ROE de {analise.roe*100:.2f}% está em nível satisfatório"
            )
        else:
            explicacoes['fatores_negativos'].append(
                f"ROE de {analise.roe*100:.2f}% indica baixa eficiência"
            )
        
        if 0 < analise.pl < 10:
            explicacoes['fatores_positivos'].append(
                f"P/L de {analise.pl:.2f} sugere ação potencialmente subvalorizada"
            )
        elif 10 <= analise.pl <= 15:
            explicacoes['fatores_neutros'].append(
                f"P/L de {analise.pl:.2f} está em faixa razoável"
            )
        elif analise.pl > 15:
            explicacoes['fatores_negativos'].append(
                f"P/L de {analise.pl:.2f} pode indicar ação cara"
            )
        
        # Análise de riscos
        if analise.risco_nivel == "alto":
            explicacoes['riscos'].append("Classificado como alto risco devido a indicadores financeiros")
        if analise.debt_equity > 1.0:
            explicacoes['riscos'].append(f"Alta alavancagem (D/E: {analise.debt_equity:.2f})")
        if analise.dy > 0.15:
            explicacoes['riscos'].append("Dividend Yield muito alto pode indicar problemas na empresa")
        
        # Resumo e recomendação
        if analise.score >= 8:
            explicacoes['resumo'] = "Excelente oportunidade de investimento"
            explicacoes['recomendacao'] = "COMPRA FORTE - Ativo com fundamentos sólidos"
        elif analise.score >= 6:
            explicacoes['resumo'] = "Boa oportunidade com alguns pontos de atenção"
            explicacoes['recomendacao'] = "COMPRA - Considere para diversificação da carteira"
        elif analise.score >= 4:
            explicacoes['resumo'] = "Oportunidade moderada, requer análise adicional"
            explicacoes['recomendacao'] = "NEUTRO - Analise outros ativos antes de decidir"
        else:
            explicacoes['resumo'] = "Ativo com fundamentos fracos"
            explicacoes['recomendacao'] = "EVITAR - Procure alternativas melhores"
        
        return explicacoes
    
    def simular_cenarios(self, analise: AnaliseAtivo, valor_investimento: float) -> Dict:
        """Simula diferentes cenários de investimento"""
        cenarios = {}
        
        if analise.preco_atual > 0:
            qtd_acoes = int(valor_investimento // analise.preco_atual)
            valor_investido = qtd_acoes * analise.preco_atual
            
            # Cenário conservador (DY -20%)
            dy_conservador = analise.dy * 0.8
            renda_conservadora = valor_investido * dy_conservador
            
            # Cenário realista (DY atual)
            renda_realista = valor_investido * analise.dy
            
            # Cenário otimista (DY +20%)
            dy_otimista = analise.dy * 1.2
            renda_otimista = valor_investido * dy_otimista
            
            cenarios = {
                'conservador': {
                    'dy': dy_conservador,
                    'renda_anual': renda_conservadora,
                    'renda_mensal': renda_conservadora / 12
                },
                'realista': {
                    'dy': analise.dy,
                    'renda_anual': renda_realista,
                    'renda_mensal': renda_realista / 12
                },
                'otimista': {
                    'dy': dy_otimista,
                    'renda_anual': renda_otimista,
                    'renda_mensal': renda_otimista / 12
                }
            }
        
        return cenarios

class RendyAutoAgent:
    """Agente responsável pela automação de reinvestimento e operações"""
    
    def simular_reinvestimento(self, valor_inicial: float, dy_anual: float, anos: int = 10) -> Dict:
        """Simula o efeito do reinvestimento de dividendos ao longo do tempo"""
        resultados = {
            'anos': [],
            'valor_sem_reinvestimento': [],
            'valor_com_reinvestimento': [],
            'dividendos_acumulados': [],
            'diferenca_reinvestimento': []
        }
        
        valor_sem_reinv = valor_inicial
        valor_com_reinv = valor_inicial
        dividendos_acumulados = 0
        
        for ano in range(1, anos + 1):
            # Sem reinvestimento
            dividendos_ano_sem = valor_inicial * dy_anual
            dividendos_acumulados += dividendos_ano_sem
            
            # Com reinvestimento
            dividendos_ano_com = valor_com_reinv * dy_anual
            valor_com_reinv += dividendos_ano_com
            
            diferenca = valor_com_reinv - (valor_inicial + dividendos_acumulados)
            
            resultados['anos'].append(ano)
            resultados['valor_sem_reinvestimento'].append(valor_inicial + dividendos_acumulados)
            resultados['valor_com_reinvestimento'].append(valor_com_reinv)
            resultados['dividendos_acumulados'].append(dividendos_acumulados)
            resultados['diferenca_reinvestimento'].append(diferenca)
        
        return resultados
    
    def calcular_aporte_mensal_necessario(self, renda_objetivo: float, dy_medio: float) -> float:
        """Calcula o aporte mensal necessário para atingir uma renda objetivo"""
        if dy_medio <= 0:
            return 0
        
        # Valor total necessário para gerar a renda objetivo
        valor_necessario = renda_objetivo / dy_medio
        
        # Assumindo 5 anos para atingir o objetivo
        meses = 60
        aporte_mensal = valor_necessario / meses
        
        return aporte_mensal

class RendySupportAgent:
    """Agente responsável pelo suporte e conteúdo educacional"""
    
    def __init__(self):
        self.faq = {
            "Como funciona o score da Rendy AI?": 
                "O score combina 4 indicadores principais: Dividend Yield (peso 4), ROE (peso 3), P/L e P/VP (peso 1.5 cada). "
                "Também considera Free Cash Flow e Payout Ratio. O máximo é 10 pontos.",
            
            "O que é um 'Super Investimento'?": 
                "São ações que ultrapassaram 10 pontos no cálculo bruto do score, indicando fundamentos excepcionais "
                "segundo nossos critérios de análise.",
            
            "Como interpretar o Dividend Yield?": 
                "DY é o percentual de dividendos pagos sobre o preço da ação. Valores entre 6-12% são considerados "
                "atrativos, mas DY muito alto (>15%) pode indicar problemas na empresa.",
            
            "Qual a diferença entre P/L e P/VP?": 
                "P/L compara preço com lucro (quanto você paga por cada real de lucro). P/VP compara preço com "
                "patrimônio (valor contábil). Ambos baixos podem indicar ação barata.",
            
            "Como diversificar minha carteira?": 
                "Recomendamos investir em pelo menos 3-5 setores diferentes, não concentrar mais de 20% em uma "
                "única ação, e balancear entre ações de alto e baixo risco."
        }
    
    def responder_pergunta(self, pergunta: str) -> str:
        """Responde perguntas frequentes"""
        pergunta_lower = pergunta.lower()
        
        for faq_pergunta, resposta in self.faq.items():
            if any(palavra in pergunta_lower for palavra in faq_pergunta.lower().split()):
                return resposta
        
        return ("Desculpe, não encontrei uma resposta específica para sua pergunta. "
                "Consulte nosso glossário ou entre em contato conosco.")
    
    def gerar_dica_educacional(self, perfil: PerfilUsuario = None) -> str:
        """Gera dicas educacionais personalizadas"""
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
    """Agente responsável pela conformidade e gestão de riscos"""
    
    def avaliar_riscos_carteira(self, analises_carteira: List[Dict]) -> Dict:
        """Avalia os riscos de uma carteira"""
        if not analises_carteira:
            return {}
        
        riscos = {
            'concentracao_setor': False,
            'concentracao_ativo': False,
            'risco_alto_predominante': False,
            'dy_excessivo': False,
            'alertas': []
        }
        
        # Análise de concentração por setor
        setores = {}
        for item in analises_carteira:
            setor = item['analise'].setor
            peso = item['peso_carteira']
            setores[setor] = setores.get(setor, 0) + peso
        
        for setor, peso in setores.items():
            if peso > 0.4:  # Mais de 40% em um setor
                riscos['concentracao_setor'] = True
                riscos['alertas'].append(f"Concentração excessiva no setor {setor} ({peso*100:.1f}%)")
        
        # Análise de concentração por ativo
        for item in analises_carteira:
            if item['peso_carteira'] > 0.3:  # Mais de 30% em um ativo
                riscos['concentracao_ativo'] = True
                riscos['alertas'].append(
                    f"Concentração excessiva em {item['analise'].ticker} ({item['peso_carteira']*100:.1f}%)"
                )
        
        # Análise de risco geral
        ativos_alto_risco = sum(1 for item in analises_carteira 
                               if item['analise'].risco_nivel == "alto")
        if ativos_alto_risco > len(analises_carteira) * 0.5:
            riscos['risco_alto_predominante'] = True
            riscos['alertas'].append("Mais de 50% da carteira em ativos de alto risco")
        
        # Análise de DY excessivo
        dy_medio = np.mean([item['analise'].dy for item in analises_carteira])
        if dy_medio > 0.15:
            riscos['dy_excessivo'] = True
            riscos['alertas'].append(f"Dividend Yield médio muito alto ({dy_medio*100:.1f}%)")
        
        return riscos
    
    def gerar_disclaimer(self) -> str:
        """Gera disclaimer de conformidade"""
        return """
        ⚠️ **IMPORTANTE - DISCLAIMER DE INVESTIMENTOS**
        
        As informações fornecidas pela Rendy AI são apenas para fins educacionais e não constituem 
        recomendação de investimento. Rentabilidade passada não garante resultados futuros. 
        
        Sempre consulte um profissional qualificado antes de tomar decisões de investimento. 
        Investimentos em ações envolvem riscos de perda do capital investido.
        
        A Rendy AI não se responsabiliza por perdas decorrentes do uso das informações fornecidas.
        """

# =================== ORQUESTRADOR PRINCIPAL ===================

class RendyOrchestrator:
    """Orquestrador principal que coordena todos os agentes"""
    
    def __init__(self):
        self.finance_agent = RendyFinanceAgent()
        self.invest_agent = RendyInvestAgent()
        self.xai_agent = RendyXAI()
        self.auto_agent = RendyAutoAgent()
        self.support_agent = RendySupportAgent()
        self.compliance_agent = RendyComplianceAgent()
        
        self.inicializar_sessao()
    
    def inicializar_sessao(self):
        """Inicializa as variáveis de sessão"""
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
        """Salva interação do usuário para aprendizado futuro"""
        interacao = {
            'timestamp': agora_brasilia().isoformat(),
            'tipo': tipo,
            'dados': dados
        }
        st.session_state['historico_interacoes'].append(interacao)
        
        # Salva no arquivo (simulando persistência)
        try:
            with open(HISTORICO_JSON, 'w', encoding='utf-8') as f:
                json.dump(st.session_state['historico_interacoes'], f, 
                         ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"Erro ao salvar histórico: {e}")
    
    def run(self):
        """Executa a aplicação principal"""
        st.title("🤖 Rendy AI - Plataforma de IA Agêntica para Investimentos")
        st.markdown("*Sua assistente inteligente para investimentos em dividendos*")
        
        # Sidebar com perfil do usuário
        self.render_sidebar()
        
        # Tabs principais
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🎯 Simulação IA", "🏆 Ranking Inteligente", "💼 Carteira Agêntica", 
            "🤖 Assistente IA", "ℹ️ Sobre"
        ])
        
        with tab1:
            self.aba_simulacao_ia()
        with tab2:
            self.aba_ranking_inteligente()
        with tab3:
            self.aba_carteira_agentica()
        with tab4:
            self.aba_assistente_ia()
        with tab5:
            self.aba_sobre()
        
        # Footer com disclaimer
        st.markdown("---")
        with st.expander("⚠️ Disclaimer Legal"):
            st.markdown(self.compliance_agent.gerar_disclaimer())
    
    def render_sidebar(self):
        """Renderiza a sidebar com perfil do usuário"""
        st.sidebar.header("👤 Perfil do Investidor")
        
        # Formulário de perfil
        with st.sidebar.form("perfil_form"):
            nome = st.text_input("Nome", value=st.session_state.get('nome_usuario', ''))
            email = st.text_input("Email", value=st.session_state.get('email_usuario', ''))
            
            tolerancia_risco = st.selectbox(
                "Tolerância ao Risco",
                ["conservador", "moderado", "agressivo"],
                help="Define como você lida com volatilidade nos investimentos"
            )
            
            horizonte = st.selectbox(
                "Horizonte de Investimento",
                ["curto", "medio", "longo"],
                index=1,
                help="Curto: até 2 anos, Médio: 2-5 anos, Longo: 5+ anos"
            )
            
            objetivo = st.selectbox(
                "Objetivo Principal",
                ["renda_passiva", "crescimento", "preservacao"],
                help="Seu objetivo principal com os investimentos"
            )
            
            experiencia = st.selectbox(
                "Experiência em Investimentos",
                ["iniciante", "intermediario", "avancado"]
            )
            
            valor_disponivel = st.number_input(
                "Valor Disponível para Investir (R$)",
                min_value=0.0,
                value=10000.0,
                step=1000.0
            )
            
            submitted = st.form_submit_button("Atualizar Perfil")
            
            if submitted and nome and validar_email(email):
                perfil = PerfilUsuario(
                    nome=nome,
                    email=email,
                    tolerancia_risco=tolerancia_risco,
                    horizonte_investimento=horizonte,
                    objetivo_principal=objetivo,
                    experiencia=experiencia,
                    valor_disponivel=valor_disponivel
                )
                
                st.session_state['perfil_usuario'] = perfil
                st.session_state['nome_usuario'] = nome
                st.session_state['email_usuario'] = email
                
                self.invest_agent.definir_perfil(perfil)
                
                self.salvar_interacao('perfil_atualizado', {
                    'tolerancia_risco': tolerancia_risco,
                    'horizonte': horizonte,
                    'objetivo': objetivo,
                    'experiencia': experiencia
                })
                
                st.sidebar.success("Perfil atualizado com sucesso!")
        
        # Dica educacional personalizada
        if st.session_state['perfil_usuario']:
            st.sidebar.markdown("---")
            st.sidebar.markdown("💡 **Dica Personalizada**")
            dica = self.support_agent.gerar_dica_educacional(st.session_state['perfil_usuario'])
            st.sidebar.info(dica)
    
    def aba_simulacao_ia(self):
        """Aba de simulação com IA expandida"""
        st.header("🎯 Simulação Inteligente de Investimento")
        st.markdown("""
        Simule investimentos com análise expandida por IA, incluindo cenários futuros e 
        explicações detalhadas dos fatores que influenciam cada recomendação.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            ticker = st.selectbox(
                "Escolha uma ação para simular",
                options=LISTA_TICKERS_IBOV,
                help="Selecione uma empresa para análise detalhada"
            )
        
        with col2:
            valor_investimento = st.number_input(
                "Valor para investir (R$)",
                min_value=100.0,
                step=100.0,
                value=st.session_state['valor_simulacao'],
                help="Valor que pretende investir"
            )
            st.session_state['valor_simulacao'] = valor_investimento
        
        if st.button("🚀 Analisar com IA", type="primary", use_container_width=True):
            with st.spinner("🤖 IA analisando fundamentos..."):
                analise = self.finance_agent.analisar_ativo(ticker)
                st.session_state['analise_simulacao'] = analise
                
                self.salvar_interacao('simulacao', {
                    'ticker': ticker,
                    'valor': valor_investimento,
                    'score': analise.score
                })
        
        if st.session_state.get('analise_simulacao'):
            analise = st.session_state['analise_simulacao']
            
            if analise.preco_atual > 0:
                # Métricas principais
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric("Score IA", f"{analise.score:.1f}/10")
                with col2:
                    st.metric("Preço", f"R$ {analise.preco_atual:,.2f}")
                with col3:
                    st.metric("Div. Yield", f"{analise.dy*100:.2f}%")
                with col4:
                    st.metric("ROE", f"{analise.roe*100:.2f}%")
                with col5:
                    risco_color = {"baixo": "🟢", "medio": "🟡", "alto": "🔴"}
                    st.metric("Risco", f"{risco_color.get(analise.risco_nivel, '⚪')} {analise.risco_nivel.title()}")
                
                # Cálculos de investimento
                qtd_acoes = int(valor_investimento // analise.preco_atual)
                valor_investido = qtd_acoes * analise.preco_atual
                renda_anual = valor_investido * analise.dy
                
                if qtd_acoes > 0:
                    st.success(
                        f"💰 **Resultado:** Com R$ {valor_investimento:,.2f}, você pode comprar "
                        f"**{qtd_acoes} ação{'s' if qtd_acoes > 1 else ''}** e receber "
                        f"**R$ {renda_anual:,.2f}** por ano em dividendos "
                        f"(R$ {renda_anual/12:,.2f}/mês)"
                    )
                else:
                    st.warning(f"Valor insuficiente para comprar uma ação (preço: R$ {analise.preco_atual:,.2f})")
                
                # Explicação detalhada da IA
                st.markdown("### 🤖 Análise Detalhada da IA")
                explicacao = self.xai_agent.explicacao_score_detalhada(analise)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**✅ Fatores Positivos:**")
                    for fator in explicacao['fatores_positivos']:
                        st.markdown(f"• {fator}")
                    
                    if explicacao['fatores_neutros']:
                        st.markdown("**➖ Fatores Neutros:**")
                        for fator in explicacao['fatores_neutros']:
                            st.markdown(f"• {fator}")
                
                with col2:
                    if explicacao['fatores_negativos']:
                        st.markdown("**❌ Fatores Negativos:**")
                        for fator in explicacao['fatores_negativos']:
                            st.markdown(f"• {fator}")
                    
                    if explicacao['riscos']:
                        st.markdown("**⚠️ Riscos Identificados:**")
                        for risco in explicacao['riscos']:
                            st.markdown(f"• {risco}")
                
                # Recomendação da IA
                if analise.score >= 7:
                    st.success(f"🎯 **Recomendação IA:** {explicacao['recomendacao']}")
                elif analise.score >= 5:
                    st.info(f"🎯 **Recomendação IA:** {explicacao['recomendacao']}")
                else:
                    st.warning(f"🎯 **Recomendação IA:** {explicacao['recomendacao']}")
                
                # Simulação de cenários
                st.markdown("### 📊 Simulação de Cenários")
                cenarios = self.xai_agent.simular_cenarios(analise, valor_investimento)
                
                if cenarios:
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("**🐻 Cenário Conservador**")
                        st.metric("Renda Anual", f"R$ {cenarios['conservador']['renda_anual']:,.2f}")
                        st.metric("Renda Mensal", f"R$ {cenarios['conservador']['renda_mensal']:,.2f}")
                    
                    with col2:
                        st.markdown("**📈 Cenário Realista**")
                        st.metric("Renda Anual", f"R$ {cenarios['realista']['renda_anual']:,.2f}")
                        st.metric("Renda Mensal", f"R$ {cenarios['realista']['renda_mensal']:,.2f}")
                    
                    with col3:
                        st.markdown("**🚀 Cenário Otimista**")
                        st.metric("Renda Anual", f"R$ {cenarios['otimista']['renda_anual']:,.2f}")
                        st.metric("Renda Mensal", f"R$ {cenarios['otimista']['renda_mensal']:,.2f}")
                
                # Simulação de reinvestimento
                if analise.dy > 0:
                    st.markdown("### 🔄 Poder do Reinvestimento")
                    reinvestimento = self.auto_agent.simular_reinvestimento(valor_investido, analise.dy, 10)
                    
                    df_reinv = pd.DataFrame({
                        'Ano': reinvestimento['anos'],
                        'Sem Reinvestimento': reinvestimento['valor_sem_reinvestimento'],
                        'Com Reinvestimento': reinvestimento['valor_com_reinvestimento']
                    })
                    
                    fig = px.line(df_reinv, x='Ano', y=['Sem Reinvestimento', 'Com Reinvestimento'],
                                 title="Evolução do Patrimônio com e sem Reinvestimento")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    diferenca_10_anos = reinvestimento['diferenca_reinvestimento'][-1]
                    st.info(f"💡 **Impacto do Reinvestimento:** Em 10 anos, você teria "
                           f"R$ {diferenca_10_anos:,.2f} a mais reinvestindo os dividendos!")
    
    def aba_ranking_inteligente(self):
        """Aba de ranking com IA personalizada"""
        st.header("🏆 Ranking Inteligente de Oportunidades")
        st.markdown("Ranking personalizado baseado no seu perfil e análise avançada de IA")
        
        # Opções de filtro
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filtro_risco = st.selectbox(
                "Filtrar por Risco",
                ["todos", "baixo", "medio", "alto"],
                help="Filtra ativos por nível de risco"
            )
        
        with col2:
            filtro_dy_min = st.slider(
                "DY Mínimo (%)",
                0.0, 20.0, 5.0, 0.5,
                help="Dividend Yield mínimo desejado"
            ) / 100
        
        with col3:
            limite_resultados = st.selectbox(
                "Número de Resultados",
                [10, 20, 30, 50],
                help="Quantos ativos mostrar no ranking"
            )
        
        if st.button("🔍 Gerar Ranking Personalizado", type="primary"):
            with st.spinner("🤖 IA analisando mercado..."):
                # Análise de todos os ativos
                todas_analises = []
                progress_bar = st.progress(0)
                
                for i, ticker in enumerate(LISTA_TICKERS_IBOV):
                    analise = self.finance_agent.analisar_ativo(ticker)
                    if analise.preco_atual > 0:
                        todas_analises.append(analise)
                    progress_bar.progress((i + 1) / len(LISTA_TICKERS_IBOV))
                
                progress_bar.empty()
                
                # Aplicar filtros
                analises_filtradas = []
                for analise in todas_analises:
                    if filtro_risco != "todos" and analise.risco_nivel != filtro_risco:
                        continue
                    if analise.dy < filtro_dy_min:
                        continue
                    analises_filtradas.append(analise)
                
                # Personalização baseada no perfil
                if st.session_state['perfil_usuario']:
                    analises_recomendadas = self.invest_agent.recomendar_ativos(
                        analises_filtradas, limite_resultados
                    )
                else:
                    analises_recomendadas = sorted(
                        analises_filtradas, key=lambda x: x.score, reverse=True
                    )[:limite_resultados]
                
                # Exibir resultados
                if analises_recomendadas:
                    st.success(f"✅ Encontradas {len(analises_recomendadas)} oportunidades!")
                    
                    # Criar DataFrame para exibição
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
                            'Super': "🔥" if analise.super_investimento else ""
                        })
                    
                    df_ranking = pd.DataFrame(dados_ranking)
                    
                    # Configurar cores por risco
                    def color_risco(val):
                        if val == 'Baixo':
                            return 'background-color: #d4edda'
                        elif val == 'Alto':
                            return 'background-color: #f8d7da'
                        else:
                            return 'background-color: #fff3cd'
                    
                    st.dataframe(
                        df_ranking.style.applymap(color_risco, subset=['Risco']),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Análise da carteira sugerida
                    if st.session_state['perfil_usuario'] and len(analises_recomendadas) >= 3:
                        st.markdown("### 💼 Sugestão de Carteira Personalizada")
                        
                        valor_total = st.session_state['perfil_usuario'].valor_disponivel
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
                                        st.markdown(f"• {ticker}: R$ {valor:,.2f} ({percentual:.1f}%)")
                                
                                with col2:
                                    # Gráfico de alocação
                                    fig = px.pie(
                                        values=list(alocacao.values()),
                                        names=list(alocacao.keys()),
                                        title="Distribuição da Carteira"
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Nenhum ativo encontrado com os filtros aplicados. Tente ajustar os critérios.")
    
    def aba_carteira_agentica(self):
        """Aba de construção de carteira com IA"""
        st.header("💼 Carteira Agêntica Inteligente")
        st.markdown("Monte sua carteira com assistência de IA e análise de riscos automatizada")
        
        # Seleção de ativos
        col1, col2 = st.columns([2, 1])
        
        with col1:
            tickers_selecionados = st.multiselect(
                "Selecione os ativos para sua carteira:",
                LISTA_TICKERS_IBOV,
                default=[item.get('ticker', '') for item in st.session_state['carteira_em_montagem']],
                help="Escolha entre 3-10 ativos para diversificação adequada"
            )
        
        with col2:
            if st.button("🎯 Sugestão IA", help="IA sugere ativos baseado no seu perfil"):
                if st.session_state['perfil_usuario']:
                    with st.spinner("🤖 IA selecionando ativos..."):
                        # Análise rápida para sugestão
                        analises_sample = []
                        for ticker in LISTA_TICKERS_IBOV[:20]:  # Amostra para velocidade
                            analise = self.finance_agent.analisar_ativo(ticker)
                            if analise.preco_atual > 0:
                                analises_sample.append(analise)
                        
                        sugeridos = self.invest_agent.recomendar_ativos(analises_sample, 5)
                        tickers_selecionados = [a.ticker for a in sugeridos]
                        st.success("✅ Ativos sugeridos pela IA!")
                else:
                    st.warning("Configure seu perfil na barra lateral para receber sugestões personalizadas")
        
        if tickers_selecionados:
            st.markdown("### 💰 Definir Alocação")
            
            # Valor total disponível
            valor_total = st.number_input(
                "Valor Total para Investir (R$)",
                min_value=100.0,
                value=st.session_state['perfil_usuario'].valor_disponivel if st.session_state['perfil_usuario'] else 10000.0,
                step=1000.0
            )
            
            # Alocação por ativo
            alocacoes = {}
            col1, col2 = st.columns(2)
            
            for i, ticker in enumerate(tickers_selecionados):
                with col1 if i % 2 == 0 else col2:
                    percentual = st.slider(
                        f"{ticker}",
                        0.0, 50.0, 100.0/len(tickers_selecionados),
                        1.0,
                        key=f"alloc_{ticker}"
                    )
                    alocacoes[ticker] = (percentual / 100) * valor_total
            
            # Normalizar alocações se necessário
            soma_percentuais = sum(st.session_state[f"alloc_{ticker}"] for ticker in tickers_selecionados)
            if abs(soma_percentuais - 100) > 1:
                st.warning(f"⚠️ Soma dos percentuais: {soma_percentuais:.1f}% (recomendado: 100%)")
            
            if st.button("📊 Analisar Carteira", type="primary"):
                with st.spinner("🤖 IA analisando carteira..."):
                    # Análise da carteira
                    tickers_list = list(alocacoes.keys())
                    valores_list = list(alocacoes.values())
                    
                    analise_carteira = self.finance_agent.analisar_carteira(tickers_list, valores_list)
                    
                    if analise_carteira['analises']:
                        # Métricas da carteira
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Valor Total", f"R$ {analise_carteira['valor_total']:,.2f}")
                        with col2:
                            st.metric("Renda Anual", f"R$ {analise_carteira['renda_total_anual']:,.2f}")
                        with col3:
                            st.metric("Yield Carteira", f"{analise_carteira['yield_carteira']*100:.2f}%")
                        with col4:
                            st.metric("Setores", f"{analise_carteira['diversificacao']}")
                        
                        # Detalhes por ativo
                        st.markdown("### 📋 Detalhes da Carteira")
                        
                        dados_carteira = []
                        for item in analise_carteira['analises']:
                            analise = item['analise']
                            dados_carteira.append({
                                'Ticker': analise.ticker,
                                'Empresa': analise.nome_empresa[:25] + "..." if len(analise.nome_empresa) > 25 else analise.nome_empresa,
                                'Valor Alocado': f"R$ {item['valor_alocado']:,.2f}",
                                'Qtd Ações': item['qtd_acoes'],
                                'Renda Anual': f"R$ {item['renda_anual']:,.2f}",
                                'DY': f"{analise.dy*100:.2f}%",
                                'Score': f"{analise.score:.1f}",
                                'Risco': analise.risco_nivel.title(),
                                'Peso': f"{item['peso_carteira']*100:.1f}%"
                            })
                        
                        df_carteira = pd.DataFrame(dados_carteira)
                        st.dataframe(df_carteira, use_container_width=True, hide_index=True)
                        
                        # Análise de riscos
                        st.markdown("### ⚠️ Análise de Riscos")
                        riscos = self.compliance_agent.avaliar_riscos_carteira(analise_carteira['analises'])
                        
                        if riscos['alertas']:
                            for alerta in riscos['alertas']:
                                st.warning(f"⚠️ {alerta}")
                        else:
                            st.success("✅ Carteira bem diversificada, sem alertas de risco!")
                        
                        # Gráficos
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Distribuição por setor
                            setores_dist = {}
                            for item in analise_carteira['analises']:
                                setor = item['analise'].setor
                                setores_dist[setor] = setores_dist.get(setor, 0) + item['peso_carteira']
                            
                            if setores_dist:
                                fig_setores = px.pie(
                                    values=list(setores_dist.values()),
                                    names=list(setores_dist.keys()),
                                    title="Distribuição por Setor"
                                )
                                st.plotly_chart(fig_setores, use_container_width=True)
                        
                        with col2:
                            # Distribuição de risco
                            riscos_dist = {"baixo": 0, "medio": 0, "alto": 0}
                            for item in analise_carteira['analises']:
                                risco = item['analise'].risco_nivel
                                riscos_dist[risco] += item['peso_carteira']
                            
                            fig_riscos = px.bar(
                                x=list(riscos_dist.keys()),
                                y=list(riscos_dist.values()),
                                title="Distribuição de Risco",
                                color=list(riscos_dist.keys()),
                                color_discrete_map={
                                    "baixo": "green",
                                    "medio": "orange", 
                                    "alto": "red"
                                }
                            )
                            st.plotly_chart(fig_riscos, use_container_width=True)
                        
                        # Simulação de reinvestimento da carteira
                        if analise_carteira['yield_carteira'] > 0:
                            st.markdown("### 🔄 Projeção com Reinvestimento")
                            
                            reinv_carteira = self.auto_agent.simular_reinvestimento(
                                analise_carteira['valor_total'],
                                analise_carteira['yield_carteira'],
                                10
                            )
                            
                            df_proj = pd.DataFrame({
                                'Ano': reinv_carteira['anos'],
                                'Patrimônio': reinv_carteira['valor_com_reinvestimento'],
                                'Renda Anual': [analise_carteira['valor_total'] * analise_carteira['yield_carteira'] * ((1 + analise_carteira['yield_carteira']) ** ano) for ano in reinv_carteira['anos']]
                            })
                            
                            fig_proj = px.line(df_proj, x='Ano', y=['Patrimônio', 'Renda Anual'],
                                             title="Projeção de Patrimônio e Renda com Reinvestimento")
                            st.plotly_chart(fig_proj, use_container_width=True)
                            
                            valor_10_anos = reinv_carteira['valor_com_reinvestimento'][-1]
                            renda_10_anos = valor_10_anos * analise_carteira['yield_carteira']
                            
                            st.info(
                                f"💡 **Projeção 10 anos:** Patrimônio de R$ {valor_10_anos:,.2f} "
                                f"gerando R$ {renda_10_anos:,.2f}/ano (R$ {renda_10_anos/12:,.2f}/mês)"
                            )
        else:
            st.info("👆 Selecione pelo menos 3 ativos para começar a montar sua carteira")
    
    def aba_assistente_ia(self):
        """Aba do assistente de IA"""
        st.header("🤖 Assistente IA da Rendy")
        st.markdown("Tire suas dúvidas sobre investimentos com nossa IA especializada")
        
        # Chat interface
        if 'chat_history' not in st.session_state:
            st.session_state['chat_history'] = []
        
        # Perguntas sugeridas
        st.markdown("### 💬 Perguntas Frequentes")
        perguntas_sugeridas = [
            "Como funciona o score da Rendy AI?",
            "O que é um 'Super Investimento'?",
            "Como interpretar o Dividend Yield?",
            "Como diversificar minha carteira?",
            "Qual a diferença entre P/L e P/VP?"
        ]
        
        col1, col2 = st.columns(2)
        for i, pergunta in enumerate(perguntas_sugeridas):
            with col1 if i % 2 == 0 else col2:
                if st.button(pergunta, key=f"faq_{i}"):
                    resposta = self.support_agent.responder_pergunta(pergunta)
                    st.session_state['chat_history'].append({
                        'pergunta': pergunta,
                        'resposta': resposta,
                        'timestamp': agora_brasilia()
                    })
        
        # Input para pergunta personalizada
        st.markdown("### ✍️ Faça sua Pergunta")
        pergunta_usuario = st.text_input(
            "Digite sua pergunta sobre investimentos:",
            placeholder="Ex: Como calcular o retorno de uma carteira de dividendos?"
        )
        
        if st.button("Perguntar", type="primary") and pergunta_usuario:
            resposta = self.support_agent.responder_pergunta(pergunta_usuario)
            st.session_state['chat_history'].append({
                'pergunta': pergunta_usuario,
                'resposta': resposta,
                'timestamp': agora_brasilia()
            })
            
            self.salvar_interacao('pergunta_assistente', {
                'pergunta': pergunta_usuario,
                'resposta': resposta
            })
        
        # Histórico do chat
        if st.session_state['chat_history']:
            st.markdown("### 📝 Histórico de Conversas")
            
            for i, item in enumerate(reversed(st.session_state['chat_history'][-5:])):  # Últimas 5
                with st.expander(f"💬 {item['pergunta'][:50]}...", expanded=(i==0)):
                    st.markdown(f"**Pergunta:** {item['pergunta']}")
                    st.markdown(f"**Resposta:** {item['resposta']}")
                    st.caption(f"⏰ {item['timestamp'].strftime('%d/%m/%Y %H:%M')}")
        
        # Calculadoras úteis
        st.markdown("### 🧮 Calculadoras Úteis")
        
        tab1, tab2 = st.tabs(["💰 Renda Objetivo", "📈 Aporte Necessário"])
        
        with tab1:
            st.markdown("**Calcule quanto precisa investir para atingir uma renda mensal:**")
            
            col1, col2 = st.columns(2)
            with col1:
                renda_objetivo = st.number_input("Renda mensal desejada (R$)", min_value=100.0, value=1000.0, step=100.0)
            with col2:
                dy_esperado = st.slider("Dividend Yield esperado (%)", 3.0, 15.0, 8.0, 0.5) / 100
            
            if st.button("Calcular Investimento Necessário"):
                valor_necessario = (renda_objetivo * 12) / dy_esperado
                st.success(f"💡 **Resultado:** Você precisa investir R$ {valor_necessario:,.2f} "
                          f"para receber R$ {renda_objetivo:,.2f}/mês com DY de {dy_esperado*100:.1f}%")
        
        with tab2:
            st.markdown("**Calcule o aporte mensal necessário para atingir um objetivo:**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                renda_objetivo_2 = st.number_input("Renda mensal objetivo (R$)", min_value=100.0, value=2000.0, step=100.0, key="renda_obj_2")
            with col2:
                dy_esperado_2 = st.slider("DY esperado (%)", 3.0, 15.0, 8.0, 0.5, key="dy_esp_2") / 100
            with col3:
                prazo_anos = st.selectbox("Prazo (anos)", [3, 5, 10, 15, 20], index=2)
            
            if st.button("Calcular Aporte Mensal"):
                aporte_mensal = self.auto_agent.calcular_aporte_mensal_necessario(renda_objetivo_2, dy_esperado_2)
                aporte_ajustado = aporte_mensal / prazo_anos  # Simplificação para o MVP
                
                st.success(f"💡 **Resultado:** Aportando R$ {aporte_ajustado:,.2f}/mês por {prazo_anos} anos, "
                          f"você pode atingir uma renda de R$ {renda_objetivo_2:,.2f}/mês")
        
        # Glossário expandido
        st.markdown("### 📚 Glossário Completo")
        with st.expander("Ver todos os termos"):
            for termo, definicao in GLOSSARIO.items():
                st.markdown(f"**{termo}:** {definicao}")
    
    def aba_sobre(self):
        """Aba sobre a Rendy AI"""
        st.header("ℹ️ Sobre a Rendy AI")
        
        st.markdown("""
        ### 🤖 Plataforma de IA Agêntica para Investimentos
        
        A Rendy AI é uma fintech inovadora que utiliza **Inteligência Artificial Agêntica** 
        para democratizar o acesso a investimentos em ações pagadoras de dividendos no Brasil.
        
        #### 🎯 Nossa Missão
        Capacitar investidores iniciantes a construir patrimônio e renda passiva de forma 
        inteligente, automatizada e educativa.
        
        #### 🚀 Diferenciais Tecnológicos
        
        - **🧠 IA Agêntica Multi-Especializada:** Agentes especializados em análise fundamentalista, 
          personalização, explicabilidade, automação, suporte e conformidade
        - **🔍 Explainable AI (XAI):** Transparência total nas recomendações com explicações detalhadas
        - **🎯 Hiperpersonalização:** Recomendações adaptadas ao seu perfil e objetivos únicos
        - **🔒 Privacidade por Design:** Seus dados ficam seguros e privados
        - **📊 Análise Expandida:** Vai além do básico com métricas avançadas e análise de riscos
        - **🔄 Simulação de Cenários:** Projeta diferentes futuros para seus investimentos
        
        #### 🏗️ Arquitetura de Agentes
        
        Nossa plataforma é construída sobre uma arquitetura de agentes especializados:
        
        - **RendyFinanceAgent:** Análise fundamentalista e previsão de dividendos
        - **RendyInvestAgent:** Personalização e recomendações baseadas no seu perfil
        - **RendyXAI:** Explicações detalhadas e transparência das decisões
        - **RendyAutoAgent:** Simulação de reinvestimento e automação
        - **RendySupportAgent:** Assistente educacional e suporte
        - **RendyComplianceAgent:** Gestão de riscos e conformidade
        
        Todos coordenados pelo **RendyOrchestrator** que garante uma experiência integrada e inteligente.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            #### 📈 Metodologia de Score
            
            Nosso score proprietário combina:
            - **Dividend Yield (peso 4):** Potencial de renda passiva
            - **ROE (peso 3):** Eficiência da empresa
            - **P/L e P/VP (peso 1.5 cada):** Valuation atrativo
            - **Free Cash Flow (peso 0.5):** Sustentabilidade
            - **Payout Ratio (peso variável):** Política de dividendos
            
            **Score 8-10:** Excelente oportunidade  
            **Score 6-8:** Boa oportunidade  
            **Score 4-6:** Moderada, requer análise  
            **Score 0-4:** Evitar
            """)
        
        with col2:
            st.markdown("""
            #### 🛡️ Segurança e Conformidade
            
            - ✅ Conformidade com LGPD
            - ✅ Dados criptografados
            - ✅ Armazenamento local seguro
            - ✅ Transparência algorítmica
            - ✅ Disclaimers de investimento
            - ✅ Gestão de riscos automatizada
            
            #### 🎓 Educação Financeira
            
            - 📚 Glossário completo
            - 💡 Dicas personalizadas
            - 🤖 Assistente IA especializado
            - 📊 Simulações educativas
            - ⚠️ Alertas de risco
            """)
        
        st.markdown("---")
        
        # Estatísticas da sessão (simuladas para MVP)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Análises Realizadas", len(st.session_state.get('historico_interacoes', [])))
        with col2:
            st.metric("Agentes Ativos", "6")
        with col3:
            st.metric("Ativos Monitorados", len(LISTA_TICKERS_IBOV))
        with col4:
            perfil_config = "✅" if st.session_state.get('perfil_usuario') else "⚠️"
            st.metric("Perfil Configurado", perfil_config)
        
        st.markdown("---")
        st.markdown("""
        ### 🔮 Roadmap Futuro
        
        - **🌐 Integração com Corretoras:** Execução automática de ordens
        - **📱 App Mobile:** Aplicativo nativo para iOS e Android  
        - **🤝 Aprendizado Federado:** IA que aprende sem comprometer privacidade
        - **🌍 Expansão Internacional:** Mercados latino-americanos
        - **🔗 Blockchain Integration:** DeFi e tokenização de ativos
        - **🎙️ Interface por Voz:** Interação natural com assistente IA
        
        ---
        
        **Versão:** MVP 2.0 - Arquitetura Agêntica  
        **Última Atualização:** Dezembro 2024  
        **Tecnologias:** Python, Streamlit, yfinance, Plotly, Pandas
        """)

# =================== CACHE E OTIMIZAÇÕES ===================

@st.cache_data(show_spinner="🔄 Analisando mercado...")
def descobrir_oportunidades_cache():
    """Versão cached da descoberta de oportunidades"""
    orchestrator = RendyOrchestrator()
    analises = []
    
    for ticker in LISTA_TICKERS_IBOV:
        analise = orchestrator.finance_agent.analisar_ativo(ticker)
        if analise.preco_atual > 0:
            analises.append(analise)
    
    return sorted(analises, key=lambda x: x.score, reverse=True)

# =================== MAIN ===================

def main():
    """Função principal da aplicação"""
    orchestrator = RendyOrchestrator()
    orchestrator.run()

if __name__ == "__main__":
    main()

