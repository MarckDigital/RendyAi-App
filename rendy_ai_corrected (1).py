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
from typing import Dict, List, Optional, Tuple, Any
import plotly.graph_objects as go
import plotly.express as px
from dataclasses import dataclass, field
import warnings

warnings.filterwarnings('ignore')

# =================== CONFIGURAÇÕES E CONSTANTES ===================
st.set_page_config(
    page_title="Rendy AI - Plataforma de IA Agêntica para Investimentos",
    page_icon="🤖",
    layout="wide"
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Diretórios e Arquivos
DATA_DIR = 'data'
USUARIO_JSON = os.path.join(DATA_DIR, 'usuario.json')
HISTORICO_JSON = os.path.join(DATA_DIR, 'historico_interacoes.json')
os.makedirs(DATA_DIR, exist_ok=True) # Garante que o diretório 'data' existe

# Fuso Horário
FUSO_BR = pytz.timezone('America/Sao_Paulo')

# Lista de Tickers (reduzida para MVP para agilizar testes)
# Para produção, a lista original é preferível.
LISTA_TICKERS_IBOV = [
    'PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'ABEV3.SA',
    'B3SA3.SA', 'BBAS3.SA', 'SUZB3.SA', 'WEGE3.SA', 'BPAC11.SA'
]

# =================== CLASSES DE DADOS ===================

@dataclass
class AnaliseAtivo:
    """Estrutura para armazenar o resultado da análise de um ativo."""
    ticker: str
    nome_empresa: str = "N/A"
    preco_atual: float = 0.0
    mudanca_percentual_24h: float = 0.0
    volume_24h: float = 0.0
    tendencia_curto_prazo: str = "Indefinida"
    suporte: float = 0.0
    resistencia: float = 0.0
    volatilidade_recente: float = 0.0
    noticias_relevantes: List[str] = field(default_factory=list)
    score: float = 0.0
    recomendacao: str = "Manter"
    grafico_base64: Optional[str] = None # Para embeddings de imagem (futuro)

@dataclass
class PerfilUsuario:
    """Estrutura para armazenar o perfil do usuário."""
    nome: str = "Investidor"
    nivel_experiencia: str = "Iniciante"
    apetite_risco: str = "Moderado"
    objetivos: str = "Crescimento a longo prazo"
    capital_inicial: float = 1000.0

@dataclass
class InteracaoUsuario:
    """Estrutura para armazenar o histórico de interações."""
    timestamp: datetime
    pergunta: str
    resposta: str
    contexto: Dict[str, Any] = field(default_factory=dict)

# =================== PERSISTÊNCIA DE DADOS ===================

def carregar_perfil_usuario() -> PerfilUsuario:
    """Carrega o perfil do usuário do arquivo JSON ou retorna um perfil padrão."""
    if os.path.exists(USUARIO_JSON):
        try:
            with open(USUARIO_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return PerfilUsuario(**data)
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON do perfil do usuário: {e}. Usando perfil padrão.")
            return PerfilUsuario()
    return PerfilUsuario()

def salvar_perfil_usuario(perfil: PerfilUsuario):
    """Salva o perfil do usuário no arquivo JSON."""
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(USUARIO_JSON, 'w', encoding='utf-8') as f:
            json.dump(perfil.__dict__, f, ensure_ascii=False, indent=4)
    except IOError as e:
        logger.error(f"Erro ao salvar perfil do usuário: {e}")

def carregar_historico_interacoes() -> List[InteracaoUsuario]:
    """Carrega o histórico de interações do arquivo JSON."""
    if os.path.exists(HISTORICO_JSON):
        try:
            with open(HISTORICO_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                historico = []
                for item in data:
                    try:
                        item['timestamp'] = datetime.fromisoformat(item['timestamp']).replace(tzinfo=FUSO_BR)
                        historico.append(InteracaoUsuario(**item))
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Erro ao carregar item do histórico: {item}. Erro: {e}. Ignorando item.")
                return historico
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON do histórico: {e}. Retornando lista vazia.")
            return []
    return []

def adicionar_interacao_historico(interacao: InteracaoUsuario):
    """Adiciona uma nova interação ao histórico e salva."""
    historico = carregar_historico_interacoes()
    historico.append(interacao)
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(HISTORICO_JSON, 'w', encoding='utf-8') as f:
            # Converte datetime para string ISO formatável antes de salvar
            serializable_historico = [
                {k: v.isoformat() if isinstance(v, datetime) else v for k, v in item.__dict__.items()}
                for item in historico
            ]
            json.dump(serializable_historico, f, ensure_ascii=False, indent=4)
    except IOError as e:
        logger.error(f"Erro ao salvar histórico de interações: {e}")

# =================== AGENTES DA IA ===================

class AgenteBase:
    """Classe base para todos os agentes."""
    def __init__(self, nome: str):
        self.nome = nome
        logger.info(f"Agente {self.nome} inicializado.")

    def log_atividade(self, atividade: str):
        """Registra uma atividade do agente."""
        logger.info(f"[{self.nome}] {atividade}")

class AgenteFinanceiro(AgenteBase):
    """Agente responsável por coletar e analisar dados financeiros."""
    def __init__(self):
        super().__init__("Agente Financeiro")

    def _obter_dados_historicos(self, ticker: str, periodo: str = '1y') -> Optional[pd.DataFrame]:
        """Obtém dados históricos de um ativo usando yfinance."""
        try:
            self.log_atividade(f"Obtendo dados históricos para {ticker} ({periodo})...")
            ticker_yf = yf.Ticker(ticker)
            hist = ticker_yf.history(period=period)
            if hist.empty:
                logger.warning(f"Nenhum dado histórico encontrado para {ticker}.")
                return None
            return hist
        except Exception as e:
            logger.error(f"Erro ao obter dados históricos para {ticker}: {e}")
            return None

    def _calcular_indicadores_tecnicos(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos básicos (SMA, Volatilidade)."""
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['Volatilidade'] = df['Close'].pct_change().rolling(window=20).std() * (252**0.5) # Anualizada
        return df

    def _analisar_tendencia(self, df: pd.DataFrame) -> str:
        """Determina a tendência de curto prazo."""
        if df['Close'].iloc[-1] > df['SMA_20'].iloc[-1]:
            return "Alta"
        elif df['Close'].iloc[-1] < df['SMA_20'].iloc[-1]:
            return "Baixa"
        return "Consolidação"

    def _identificar_niveis_sr(self, df: pd.DataFrame) -> Tuple[float, float]:
        """Identifica níveis de suporte e resistência (simplificado)."""
        # Método simplificado: min/max do período recente
        periodo_recente = df['Close'].tail(30) # Últimos 30 dias
        suporte = periodo_recente.min()
        resistencia = periodo_recente.max()
        return suporte, resistencia

    def analisar_ativo(self, ticker: str) -> AnaliseAtivo:
        """Realiza uma análise completa de um ativo."""
        self.log_atividade(f"Iniciando análise para {ticker}")
        analise = AnaliseAtivo(ticker=ticker)

        ticker_info = yf.Ticker(ticker)
        info = ticker_info.info

        analise.nome_empresa = info.get('longName', 'Nome não disponível')
        analise.preco_atual = info.get('currentPrice', 0.0)

        # Tentativa de obter a mudança percentual e volume
        try:
            hist_1d = self._obter_dados_historicos(ticker, period='1d')
            if hist_1d is not None and not hist_1d.empty:
                if len(hist_1d) >= 2:
                    preco_abertura = hist_1d['Open'].iloc[0]
                    if preco_abertura != 0:
                        analise.mudanca_percentual_24h = ((analise.preco_atual - preco_abertura) / preco_abertura) * 100
                analise.volume_24h = hist_1d['Volume'].iloc[-1]
        except Exception as e:
            logger.warning(f"Não foi possível obter mudança percentual/volume para {ticker}: {e}")

        df_hist = self._obter_dados_historicos(ticker, period='6m') # Usar um período mais longo para análise técnica
        if df_hist is not None and not df_hist.empty:
            df_hist = self._calcular_indicadores_tecnicos(df_hist)
            analise.tendencia_curto_prazo = self._analisar_tendencia(df_hist)
            analise.suporte, analise.resistencia = self._identificar_niveis_sr(df_hist)
            analise.volatilidade_recente = df_hist['Volatilidade'].iloc[-1] if 'Volatilidade' in df_hist.columns else 0.0

        # Simulação de Notícias (poderia ser uma API real no futuro)
        analise.noticias_relevantes = [
            f"Notícia 1 sobre {analise.nome_empresa}",
            f"Notícia 2 sobre {analise.nome_empresa}"
        ]

        # Calcular Score (exemplo simples de lógica de pontuação)
        score = 0
        if analise.tendencia_curto_prazo == "Alta":
            score += 2
        elif analise.tendencia_curto_prazo == "Consolidação":
            score += 1

        if analise.mudanca_percentual_24h > 1: # Ganhos recentes
            score += 1
        if analise.mudanca_percentual_24h < -1: # Perdas recentes
            score -= 1

        # Exemplo: menos volatilidade pode ser um ponto positivo para alguns perfis
        if analise.volatilidade_recente < 0.3: # Arbitrário
             score += 0.5

        analise.score = score

        # Determinar recomendação com base no score
        if score >= 3:
            analise.recomendacao = "Compra Forte"
        elif score >= 1:
            analise.recomendacao = "Compra Moderada"
        elif score <= -1:
            analise.recomendacao = "Venda"
        else:
            analise.recomendacao = "Manter"

        self.log_atividade(f"Análise para {ticker} concluída. Score: {analise.score}, Recomendação: {analise.recomendacao}")
        return analise

class AgenteChat(AgenteBase):
    """Agente responsável por interagir com o usuário e fornecer respostas."""
    def __init__(self):
        super().__init__("Agente Chat")
        self.historico_interacoes: List[InteracaoUsuario] = carregar_historico_interacoes()
        self.perfil_usuario: PerfilUsuario = carregar_perfil_usuario()

    def gerar_resposta(self, pergunta: str, contexto: Optional[Dict[str, Any]] = None) -> str:
        """Gera uma resposta baseada na pergunta e contexto."""
        self.log_atividade(f"Gerando resposta para: '{pergunta}'")

        resposta_gerada = "Desculpe, não entendi sua pergunta. Poderia reformular?"
        contexto_da_interacao = contexto if contexto is not None else {}

        pergunta_lower = pergunta.lower()

        # Respostas baseadas em regras simples e contexto
        if "olá" in pergunta_lower or "oi" in pergunta_lower:
            resposta_gerada = f"Olá, {self.perfil_usuario.nome}! Como posso te ajudar com seus investimentos hoje?"
        elif "perfil" in pergunta_lower:
            resposta_gerada = (
                f"Seu perfil atual é:\n"
                f"- **Nome:** {self.perfil_usuario.nome}\n"
                f"- **Nível de Experiência:** {self.perfil_usuario.nivel_experiencia}\n"
                f"- **Apetite a Risco:** {self.perfil_usuario.apetite_risco}\n"
                f"- **Objetivos:** {self.perfil_usuario.objetivos}\n"
                f"- **Capital Inicial:** R${self.perfil_usuario.capital_inicial:,.2f}"
            )
        elif "oportunidades" in pergunta_lower:
            if "analises_oportunidades" in contexto_da_interacao and contexto_da_interacao["analises_oportunidades"]:
                respostas_oportunidades = ["Aqui estão algumas oportunidades que encontrei:\n"]
                for analise in contexto_da_interacao["analises_oportunidades"][:5]: # Mostrar top 5
                    respostas_oportunidades.append(
                        f"- **{analise.nome_empresa} ({analise.ticker}):** Preço R${analise.preco_atual:,.2f}, "
                        f"Mudança: {analise.mudanca_percentual_24h:.2f}%, Tendência: {analise.tendencia_curto_prazo}, "
                        f"Recomendação: {analise.recomendacao} (Score: {analise.score:.1f})"
                    )
                resposta_gerada = "\n".join(respostas_oportunidades)
            else:
                resposta_gerada = "Ainda não analisei o mercado em busca de oportunidades. Por favor, clique no botão 'Descobrir Oportunidades' na barra lateral."
        elif "ajuda" in pergunta_lower or "o que você pode fazer" in pergunta_lower:
            resposta_gerada = (
                "Eu sou a Rendy AI, sua assistente de investimentos! Posso:\n"
                "- **Analisar ativos:** Obter dados e indicadores de ações.\n"
                "- **Descobrir oportunidades:** Identificar ativos com bom potencial.\n"
                "- **Gerenciar seu perfil:** Configurar suas preferências de investimento.\n"
                "- **Responder suas perguntas:** Tentar te ajudar com dúvidas gerais sobre o mercado."
                "\n\nPara começar, você pode me perguntar sobre 'oportunidades' ou 'meu perfil'."
            )
        elif "analisar" in pergunta_lower and "ativo" in pergunta_lower:
            match = re.search(r'(?i)\b[A-Z]{4}\d?\.SA\b', pergunta) # Regex para tickers B3 (ex: PETR4.SA)
            if match:
                ticker_solicitado = match.group(0).upper()
                if "analises_oportunidades" in contexto_da_interacao:
                    analise_encontrada = next((a for a in contexto_da_interacao["analises_oportunidades"] if a.ticker == ticker_solicitado), None)
                    if analise_encontrada:
                        resposta_gerada = (
                            f"Detalhes para **{analise_encontrada.nome_empresa} ({analise_encontrada.ticker})**:\n"
                            f"- **Preço Atual:** R${analise_encontrada.preco_atual:,.2f}\n"
                            f"- **Mudança 24h:** {analise_encontrada.mudanca_percentual_24h:.2f}%\n"
                            f"- **Volume 24h:** R${analise_encontrada.volume_24h:,.2f}\n"
                            f"- **Tendência Curto Prazo:** {analise_encontrada.tendencia_curto_prazo}\n"
                            f"- **Suporte:** R${analise_encontrada.suporte:,.2f}\n"
                            f"- **Resistência:** R${analise_encontrada.resistencia:,.2f}\n"
                            f"- **Volatilidade Recente:** {analise_encontrada.volatilidade_recente:.2f}\n"
                            f"- **Recomendação:** {analise_encontrada.recomendacao} (Score: {analise_encontrada.score:.1f})"
                        )
                        if analise_encontrada.noticias_relevantes:
                            resposta_gerada += "\n- **Notícias Relevantes:** " + ", ".join(analise_encontrada.noticias_relevantes)
                    else:
                        resposta_gerada = f"Não encontrei detalhes recentes para o ativo {ticker_solicitado}. Tente descobrir oportunidades primeiro."
                else:
                    resposta_gerada = "Para analisar um ativo específico, por favor, me diga o ticker (ex: 'analisar PETR4.SA')."
            else:
                resposta_gerada = "Para analisar um ativo, preciso do ticker (ex: 'analisar PETR4.SA')."
        else:
            resposta_gerada = "Entendi. Sou uma IA focada em investimentos. Se tiver dúvidas sobre o mercado, me diga! Caso contrário, pergunte sobre 'oportunidades' ou 'perfil'."

        # Salvar interação
        nova_interacao = InteracaoUsuario(
            timestamp=datetime.now(FUSO_BR),
            pergunta=pergunta,
            resposta=resposta_gerada,
            contexto=contexto_da_interacao # Salva o contexto relevante
        )
        self.historico_interacoes.append(nova_interacao)
        adicionar_interacao_historico(nova_interacao)

        self.log_atividade(f"Resposta gerada: '{resposta_gerada[:50]}...'")
        return resposta_gerada

class RendyOrchestrator:
    """Orquestrador que coordena os diferentes agentes."""
    def __init__(self):
        self.finance_agent = AgenteFinanceiro()
        self.chat_agent = AgenteChat()
        logger.info("RendyOrchestrator inicializado.")

    def processar_solicitacao_chat(self, pergunta_usuario: str, contexto_chat: Optional[Dict[str, Any]] = None) -> str:
        """Processa uma solicitação do usuário através do agente de chat."""
        return self.chat_agent.generar_resposta(pergunta_usuario, contexto_chat)

# =================== CACHE E OTIMIZAÇÕES ===================

@st.cache_data(show_spinner="🔄 Analisando mercado...", ttl=timedelta(hours=4)) # Cache por 4 horas
def descobrir_oportunidades_cache(orchestrator: RendyOrchestrator) -> List[AnaliseAtivo]:
    """Versão cached da descoberta de oportunidades."""
    logger.info("Iniciando descoberta de oportunidades (pode usar cache).")
    analises = []

    for ticker in LISTA_TICKERS_IBOV:
        try:
            analise = orchestrator.finance_agent.analisar_ativo(ticker)
            if analise.preco_atual > 0: # Garante que o ativo tem um preço válido
                analises.append(analise)
        except Exception as e:
            logger.error(f"Erro ao analisar ativo {ticker}: {e}")
            # Continua para o próximo ticker mesmo que um falhe

    # Ordena por score e filtra para incluir apenas os de maior potencial
    analises_filtradas = sorted(analises, key=lambda x: x.score, reverse=True)

    logger.info(f"Descoberta de oportunidades concluída. Encontradas {len(analises_filtradas)} oportunidades.")
    return analises_filtradas

# =================== FUNÇÕES DE UTILIDADE PARA UI ===================

def exibir_analise_completa(analise: AnaliseAtivo):
    """Exibe os detalhes completos de uma análise de ativo em um expander."""
    with st.expander(f"Detalhes de {analise.nome_empresa} ({analise.ticker}) - Recomendação: **{analise.recomendacao}**"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Preço Atual", f"R${analise.preco_atual:,.2f}")
            st.metric("Mudança 24h", f"{analise.mudanca_percentual_24h:.2f}%")
            st.metric("Volume 24h", f"R${analise.volume_24h:,.2f}")
        with col2:
            st.metric("Tendência Curto Prazo", analise.tendencia_curto_prazo)
            st.metric("Suporte", f"R${analise.suporte:,.2f}")
            st.metric("Resistência", f"R${analise.resistencia:,.2f}")
        with col3:
            st.metric("Volatilidade Recente", f"{analise.volatilidade_recente:.2f}")
            st.metric("Score de Oportunidade", f"{analise.score:.1f}")
            st.metric("Recomendação", analise.recomendacao)

        st.markdown("---")
        st.subheader("Notícias Relevantes")
        if analise.noticias_relevantes:
            for noticia in analise.noticias_relevantes:
                st.markdown(f"- {noticia}")
        else:
            st.info("Nenhuma notícia relevante encontrada no momento (dados simulados).")

        # Opcional: Gerar um gráfico simples para o ativo
        df_hist = yf.Ticker(analise.ticker).history(period='3m')
        if not df_hist.empty:
            fig = go.Figure(data=[go.Candlestick(x=df_hist.index,
                                                open=df_hist['Open'],
                                                high=df_hist['High'],
                                                low=df_hist['Low'],
                                                close=df_hist['Close'])])
            fig.update_layout(title=f'Gráfico de Candlestick de {analise.ticker} (3 meses)',
                            xaxis_rangeslider_visible=False,
                            height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Não foi possível gerar o gráfico histórico para este ativo.")

def exibir_historico_chat():
    """Exibe o histórico de conversas do Streamlit."""
    st.subheader("Histórico de Conversas")
    historico = carregar_historico_interacoes()
    if historico:
        for i, interacao in enumerate(reversed(historico[-5:])): # Exibe as últimas 5 interações
            col_pergunta, col_resposta = st.columns([1, 4])
            with col_pergunta:
                st.markdown(f"**Você ({interacao.timestamp.strftime('%H:%M')}):**")
            with col_resposta:
                st.info(interacao.pergunta)

            col_ia, col_resposta_ia = st.columns([1, 4])
            with col_ia:
                st.markdown(f"**Rendy AI:**")
            with col_resposta_ia:
                st.success(interacao.resposta)
            st.markdown("---")
    else:
        st.info("Nenhuma interação anterior. Comece a conversar!")

def configurar_perfil_usuario_ui(perfil: PerfilUsuario):
    """Interface para configurar o perfil do usuário."""
    st.subheader("⚙️ Configurar Seu Perfil")
    with st.form("form_perfil_usuario"):
        novo_nome = st.text_input("Seu Nome", value=perfil.nome)
        novo_nivel = st.selectbox("Nível de Experiência",
                                  ["Iniciante", "Intermediário", "Avançado"],
                                  index=["Iniciante", "Intermediário", "Avançado"].index(perfil.nivel_experiencia))
        novo_apetite = st.selectbox("Apetite a Risco",
                                    ["Conservador", "Moderado", "Agressivo"],
                                    index=["Conservador", "Moderado", "Agressivo"].index(perfil.apetite_risco))
        novos_objetivos = st.text_area("Seus Objetivos de Investimento", value=perfil.objetivos)
        novo_capital = st.number_input("Capital Inicial (R$)", value=perfil.capital_inicial, min_value=0.0, format="%.2f")

        submitted = st.form_submit_button("Salvar Perfil")
        if submitted:
            perfil.nome = novo_nome
            perfil.nivel_experiencia = novo_nivel
            perfil.apetite_risco = novo_apetite
            perfil.objetivos = novos_objetivos
            perfil.capital_inicial = novo_capital
            salvar_perfil_usuario(perfil)
            st.success("Perfil atualizado com sucesso!")
            st.session_state.perfil_configurado = perfil # Atualiza o perfil na sessão
            st.rerun() # Recarrega a página para refletir as mudanças

# =================== MAIN ===================

def main():
    """Função principal da aplicação Streamlit."""
    orchestrator = RendyOrchestrator()

    # Inicializa o estado da sessão para armazenar o perfil e análises
    if 'perfil_configurado' not in st.session_state:
        st.session_state.perfil_configurado = carregar_perfil_usuario()
    if 'analises_oportunidades' not in st.session_state:
        st.session_state.analises_oportunidades = []
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    if 'chat_input_key' not in st.session_state:
        st.session_state.chat_input_key = 0 # Para resetar o input do chat

    st.sidebar.title("🤖 Rendy AI")
    st.sidebar.markdown("---")

    st.sidebar.header("🚀 Ações Rápidas")
    if st.sidebar.button("✨ Descobrir Oportunidades"):
        with st.spinner("Buscando e analisando oportunidades no mercado..."):
            st.session_state.analises_oportunidades = descobrir_oportunidades_cache(orchestrator)
        st.sidebar.success("Análise de oportunidades concluída!")

    st.sidebar.markdown("---")
    st.sidebar.header("👤 Seu Perfil")
    configurar_perfil_usuario_ui(st.session_state.perfil_configurado)
    st.sidebar.markdown("---")

    st.title("Bem-vindo(a) à Rendy AI! 🤖")
    st.write("Sua assistente de IA agêntica para investimentos. Explore as funcionalidades na barra lateral.")
    st.markdown("---")

    tab_chat, tab_oportunidades = st.tabs(["💬 Chat com Rendy AI", "📈 Oportunidades de Investimento"])

    with tab_chat:
        st.header("Converse com a Rendy AI")
        st.markdown("Faça suas perguntas sobre investimentos ou peça para analisar algo!")

        # Exibir histórico de mensagens do chat
        if st.session_state.chat_messages:
            for message in st.session_state.chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        # Input do chat
        prompt = st.chat_input("Pergunte algo...", key=f"chat_input_{st.session_state.chat_input_key}")
        if prompt:
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Rendy AI está pensando..."):
                    # Passa as análises recentes como contexto para o agente de chat
                    contexto_chat = {"analises_oportunidades": st.session_state.analises_oportunidades}
                    resposta_ai = orchestrator.processar_solicitacao_chat(prompt, contexto_chat)
                    st.markdown(resposta_ai)
                    st.session_state.chat_messages.append({"role": "assistant", "content": resposta_ai})

            # Incrementa a chave para limpar o input
            st.session_state.chat_input_key += 1
            st.experimental_rerun() # Recarrega para limpar o input

        exibir_historico_chat() # Exibe o histórico de interações salvo no arquivo

    with tab_oportunidades:
        st.header("Principais Oportunidades de Investimento")
        if st.session_state.analises_oportunidades:
            st.info(f"Última análise realizada em: {datetime.now(FUSO_BR).strftime('%d/%m/%Y %H:%M:%S')}")
            for analise in st.session_state.analises_oportunidades:
                exibir_analise_completa(analise)
        else:
            st.warning("Nenhuma oportunidade analisada ainda. Clique em '✨ Descobrir Oportunidades' na barra lateral para começar!")

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

    **Versão:** MVP 2.0 - Arquitetura Agêntica Refatorada
    **Última Atualização:** Junho 2025
    **Tecnologias:** Python, Streamlit, yfinance, Plotly, Pandas
    """)

if __name__ == "__main__":
    main()

