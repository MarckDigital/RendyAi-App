import streamlit as st
import yfinance as yf
import pandas as pd
import time
from typing import Dict, List, Optional
import json
import os
from datetime import datetime
import logging
import re

# ============================================================================
# CONFIGURAÇÕES GERAIS E CONSTANTES
# ============================================================================

st.set_page_config(
    page_title="Rendy AI - Sua Jornada de Investimentos",
    page_icon="🤖",
    layout="centered"
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = 'data'
USUARIO_JSON = os.path.join(DATA_DIR, 'usuario.json')

# Glossário financeiro
GLOSSARIO_FINANCEIRO = {
    "Score": "Uma pontuação de 0 a 10 que avalia o custo/benefício de uma ação para investidores de dividendos. Combina preço justo (P/L, P/VP), rentabilidade (ROE) e dividendos (DY).",
    "DY": "Dividend Yield. Mede os dividendos pagos nos últimos 12 meses em relação ao preço da ação. É o principal indicador para renda passiva.",
    "P/L": "Preço sobre Lucro. Indica quanto o mercado paga pelos lucros da empresa. Um P/L baixo pode sugerir que a ação está barata.",
    "P/VP": "Preço sobre Valor Patrimonial. Compara o preço da ação com o valor patrimonial da empresa. P/VP abaixo de 1 pode indicar que a ação está descontada.",
    "ROE": "Return on Equity. Mede a capacidade da empresa de gerar lucro. Um ROE alto é um sinal de boa rentabilidade."
}

LISTA_TICKERS_IBOV_SIMPLIFICADA = [
    "ITSA4.SA", "PETR4.SA", "VALE3.SA", "BBAS3.SA", "BBDC4.SA", 
    "TAEE11.SA", "EGIE3.SA", "BBSE3.SA", "TRPL4.SA", "CPLE6.SA", 
    "CMIG4.SA", "SANB11.SA"
]

# ============================================================================
# FUNÇÕES DE UTILIDADE (GESTÃO DE DADOS E SESSÃO)
# ============================================================================

def inicializar_ambiente():
    """Cria o diretório de dados se não existir"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def salvar_dados_usuario(dados: Dict):
    """Salva os dados do usuário em arquivo JSON"""
    try:
        inicializar_ambiente()
        with open(USUARIO_JSON, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
        logger.info(f"Dados do usuário salvos em {USUARIO_JSON}")
    except Exception as e:
        logger.error(f"Erro ao salvar dados do usuário: {e}")
        st.error("Erro ao salvar dados do usuário")

def carregar_dados_usuario() -> Dict:
    """Carrega os dados do usuário do arquivo JSON"""
    try:
        if os.path.exists(USUARIO_JSON):
            with open(USUARIO_JSON, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar dados do usuário: {e}")
    return {}

def inicializar_sessao():
    """Inicializa as variáveis de sessão"""
    if 'step' not in st.session_state:
        st.session_state.step = "welcome"
    if 'dashboard_view' not in st.session_state:
        st.session_state.dashboard_view = 'simulacao'
    if 'carteira_em_montagem' not in st.session_state:
        st.session_state.carteira_em_montagem = []
    if 'carteira_salva' not in st.session_state:
        st.session_state.carteira_salva = carregar_dados_usuario().get('carteira_salva', [])
    if 'nome_usuario' not in st.session_state:
        st.session_state.nome_usuario = ""
    if 'analise_cache' not in st.session_state:
        st.session_state.analise_cache = None
    if 'valor_a_investir_simulacao' not in st.session_state:
        st.session_state.valor_a_investir_simulacao = 10000.0

# ============================================================================
# CLASSES DOS AGENTES DE IA
# ============================================================================

class RendyInvestAgent:
    """Agente responsável por gerenciar o perfil do usuário"""
    
    def obter_perfil_usuario(self) -> Dict:
        """Obtém o perfil do usuário"""
        user_data = carregar_dados_usuario()
        valor_definido_na_ui = st.session_state.get('valor_a_investir_simulacao', 10000.0)
        
        return {
            'nome': user_data.get('nome', 'Investidor(a)'),
            'email': user_data.get('email', ''),
            'valor_total_disponivel': valor_definido_na_ui
        }

class RendyFinanceAgent:
    """Agente responsável por análises financeiras"""
    
    def analisar_ativo(self, ticker: str) -> Dict:
        """Analisa um ativo específico"""
        try:
            logger.info(f"Analisando ticker: {ticker}")
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            
            # Busca dados históricos
            historico = ticker_obj.history(period="1y")
            historico_close = historico['Close'] if not historico.empty else None
            
            # Extrai métricas financeiras
            dy = info.get('dividendYield', 0) or 0
            pl = info.get('trailingPE', 0) or 0
            pvp = info.get('priceToBook', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            preco_atual = info.get('currentPrice', 0) or info.get('regularMarketPrice', 0) or 0
            
            # Se preço atual ainda for 0, tenta pegar do histórico
            if preco_atual == 0 and historico_close is not None and not historico_close.empty:
                preco_atual = float(historico_close.iloc[-1])
            
            # Calcula score refinado
            # Pesos: DY=4, ROE=3, P/L=1.5, P/VP=1.5
            score_dy = min(dy / 0.08, 1) * 4 if dy > 0 else 0  # Normalizado por um DY "ótimo" de 8%
            score_pl = min(15 / pl if pl > 0 else 0, 1) * 1.5
            score_pvp = min(2 / pvp if pvp > 0 else 0, 1) * 1.5  # P/VP até 2 ainda pode ser ok
            score_roe = min(roe / 0.20, 1) * 3 if roe > 0 else 0  # Normalizado por um ROE "excelente" de 20%
            score_total = min(score_dy + score_pl + score_pvp + score_roe, 10)
            
            return {
                "ticker": ticker,
                "nome_empresa": info.get('longName', 'N/A'),
                "setor": info.get('sector', 'N/A'),
                "preco_atual": preco_atual,
                "dy": dy,
                "pl": pl,
                "pvp": pvp,
                "roe": roe,
                "score": score_total,
                "historico": historico_close
            }
            
        except Exception as e:
            logger.error(f"Erro ao analisar o ticker {ticker}: {e}")
            return {"ticker": ticker, "error": str(e)}

class RendyXaiAgent:
    """Agente responsável por apresentar análises e relatórios"""
    
    def apresentar_relatorio_visual(self, analise: Dict, perfil: Dict):
        """Apresenta relatório visual da análise"""
        if analise.get("error"):
            st.error(f"Não foi possível obter os dados para {analise['ticker']}. Tente outro ativo.")
            return
        
        # Tratamento de casos especiais para exibição
        if analise['dy'] > 0:
            dy_text = f"{analise['dy'] * 100:.2f}%"
            dy_help = GLOSSARIO_FINANCEIRO['DY']
        else:
            dy_text = "Não Paga"
            dy_help = "Esta empresa não distribuiu dividendos recentemente."
        
        if analise['pl'] > 0:
            pl_text = f"{analise['pl']:.2f}"
        else:
            pl_text = "N/A (Prejuízo)"
        
        st.subheader(f"Análise para {analise['nome_empresa']} ({analise['ticker']})")
        
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Score Rendy AI", f"{analise['score']:.1f}/10", 
                   help=GLOSSARIO_FINANCEIRO['Score'])
        col2.metric("Dividend Yield", dy_text, help=dy_help)
        col3.metric("Preço/Lucro (P/L)", pl_text, help=GLOSSARIO_FINANCEIRO['P/L'])
        col4.metric("Preço da Ação", f"R$ {analise['preco_atual']:.2f}")
        
        # Simulação de investimento
        valor_simulado = perfil['valor_total_disponivel']
        if analise['preco_atual'] > 0:
            qtd_acoes = int(valor_simulado / analise['preco_atual'])
            ganho_anual_projetado = valor_simulado * analise['dy']
            
            st.success(
                f"Com **R$ {valor_simulado:,.2f}**, você poderia comprar **{qtd_acoes}** "
                f"ações e ter uma projeção de renda passiva de **R$ {ganho_anual_projetado:,.2f}** no próximo ano."
            )
        else:
            st.warning("Não foi possível calcular a simulação devido ao preço indisponível.")
        
        # Gráfico histórico
        st.subheader("Desempenho da Ação no Último Ano")
        if analise.get('historico') is not None and not analise['historico'].empty:
            st.line_chart(analise['historico'], use_container_width=True)
        else:
            st.warning("Não foi possível carregar o histórico de cotações para este ativo.")
        
        # Análise comparativa
        with st.expander("🆚 Comparar com outro ativo"):
            lista_comparacao = [t for t in LISTA_TICKERS_IBOV_SIMPLIFICADA if t != analise['ticker']]
            ticker_comparacao = st.selectbox(
                "Selecione um ativo para comparar:",
                options=lista_comparacao,
                key=f"comp_{analise['ticker']}"
            )
            
            if ticker_comparacao:
                finance_agent_comp = RendyFinanceAgent()
                analise_comp = finance_agent_comp.analisar_ativo(ticker_comparacao)
                
                if not analise_comp.get("error"):
                    st.write(f"Comparando **{analise['ticker']}** vs **{analise_comp['ticker']}**")
                    
                    # Tabela de comparação
                    dados_tabela = {
                        'Métrica': ['Score', 'Div. Yield', 'P/L', 'ROE', 'Preço'],
                        analise['ticker']: [
                            f"{analise['score']:.1f}/10",
                            f"{analise['dy']*100:.2f}%",
                            f"{analise['pl']:.2f}" if analise['pl'] > 0 else "N/A",
                            f"{analise['roe']*100:.2f}%",
                            f"R$ {analise['preco_atual']:.2f}"
                        ],
                        analise_comp['ticker']: [
                            f"{analise_comp['score']:.1f}/10",
                            f"{analise_comp['dy']*100:.2f}%",
                            f"{analise_comp['pl']:.2f}" if analise_comp['pl'] > 0 else "N/A",
                            f"{analise_comp['roe']*100:.2f}%",
                            f"R$ {analise_comp['preco_atual']:.2f}"
                        ]
                    }
                    df_comp = pd.DataFrame(dados_tabela)
                    st.dataframe(df_comp, use_container_width=True, hide_index=True)
                else:
                    st.error(f"Não foi possível carregar dados para {ticker_comparacao}")
        
        st.divider()
        
        # Botão para adicionar à carteira
        if analise['ticker'] not in [item['ticker'] for item in st.session_state.carteira_em_montagem]:
            if len(st.session_state.carteira_em_montagem) < 10:
                if st.button("➕ Adicionar à Minha Carteira", key=f"add_{analise['ticker']}"):
                    st.session_state.carteira_em_montagem.append({'ticker': analise['ticker']})
                    st.toast(f"{analise['ticker']} adicionado com sucesso!", icon="✅")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("Você atingiu o limite de 10 ações na sua carteira em montagem.")
        else:
            st.info("Esta ação já está na sua carteira em montagem.")
    
    def analisar_carteira_completa(self, carteira_alocada: List[Dict], finance_agent: RendyFinanceAgent) -> Dict:
        """Analisa a carteira completa do usuário"""
        total_investido = 0
        renda_passiva_anual_total = 0
        
        for item in carteira_alocada:
            valor_alocado = item.get('valor_alocado', 0)
            if valor_alocado > 0:
                analise = finance_agent.analisar_ativo(item['ticker'])
                if not analise.get("error"):
                    total_investido += valor_alocado
                    renda_passiva_anual_total += valor_alocado * analise['dy']
        
        dy_medio_ponderado = (renda_passiva_anual_total / total_investido) if total_investido > 0 else 0
        
        return {
            "total_investido": total_investido,
            "renda_passiva_anual_total": renda_passiva_anual_total,
            "dy_medio_ponderado": dy_medio_ponderado
        }

# ============================================================================
# TELAS DA APLICAÇÃO
# ============================================================================

def tela_dashboard():
    """Tela principal do dashboard"""
    st.title(f"Olá, {st.session_state.nome_usuario}! 👋")
    
    # Passo 1: Simulação
    st.header("Passo 1: Simule seu Investimento")
    st.markdown("Descubra o potencial de uma ação. Selecione um ativo, defina o valor e veja uma projeção clara dos seus ganhos.")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        ticker_selecionado = st.selectbox("Selecione um ativo:", LISTA_TICKERS_IBOV_SIMPLIFICADA)
    with col2:
        st.session_state.valor_a_investir_simulacao = st.number_input(
            "Valor para simular (R$):",
            min_value=100.0,
            value=st.session_state.valor_a_investir_simulacao,
            step=100.0
        )
    
    if st.button("📊 Gerar Simulação", use_container_width=True, type="primary"):
        invest_agent = RendyInvestAgent()
        finance_agent = RendyFinanceAgent()
        
        with st.spinner(f"Analisando {ticker_selecionado}..."):
            perfil = invest_agent.obter_perfil_usuario()
            analise = finance_agent.analisar_ativo(ticker_selecionado)
            st.session_state.analise_cache = (analise, perfil)
    
    # Exibe análise se disponível
    if st.session_state.get('analise_cache'):
        analise, perfil = st.session_state.analise_cache
        xai_agent = RendyXaiAgent()
        xai_agent.apresentar_relatorio_visual(analise, perfil)
    
    st.divider()
    
    # Passo 2: Montagem da carteira
    if st.session_state.carteira_em_montagem:
        st.header("Passo 2: Monte sua Carteira de Renda Passiva")
        st.markdown("Revise sua lista de ações pré-selecionadas e avance para definir a alocação de recursos.")
        
        for i, item in enumerate(st.session_state.carteira_em_montagem):
            col1, col2 = st.columns([4, 1])
            col1.info(f"**{i+1}. {item['ticker']}**")
            if col2.button("❌ Remover", key=f"remove_{item['ticker']}", use_container_width=True):
                st.session_state.carteira_em_montagem.pop(i)
                st.rerun()
        
        if st.button("Definir Alocação de Recursos ➔", use_container_width=True):
            st.session_state.dashboard_view = 'alocacao'
            st.rerun()
    
    # Passo 3: Alocação
    if st.session_state.dashboard_view == 'alocacao':
        st.header("Passo 3: Defina sua Alocação")
        st.markdown("Distribua o seu capital entre as ações escolhidas.")
        
        with st.form("alocacao_form"):
            alocacoes = []
            for item in st.session_state.carteira_em_montagem:
                valor_alocado = st.number_input(
                    f"Valor para **{item['ticker']}** (R$)",
                    min_value=0.0,
                    key=f"aloc_{item['ticker']}"
                )
                alocacoes.append({'ticker': item['ticker'], 'valor_alocado': valor_alocado})
            
            if st.form_submit_button("✔ Analisar Minha Carteira Completa"):
                total_alocado = sum(item['valor_alocado'] for item in alocacoes)
                valor_disponivel = RendyInvestAgent().obter_perfil_usuario()['valor_total_disponivel']
                
                if total_alocado > valor_disponivel:
                    st.error(f"O valor total alocado (R$ {total_alocado:,.2f}) não pode exceder o seu valor de simulação (R$ {valor_disponivel:,.2f}).")
                else:
                    st.session_state.carteira_alocada = alocacoes
                    st.session_state.dashboard_view = 'resumo'
                    st.rerun()
    
    # Passo 4: Resumo
    if st.session_state.dashboard_view == 'resumo':
        st.header("Resumo do Seu Plano de Investimentos")
        
        finance_agent = RendyFinanceAgent()
        xai_agent = RendyXaiAgent()
        
        with st.spinner("Calculando o potencial da sua carteira..."):
            resumo_carteira = xai_agent.analisar_carteira_completa(st.session_state.carteira_alocada, finance_agent)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Investido", f"R$ {resumo_carteira['total_investido']:,.2f}")
        col2.metric("Renda Anual Estimada", f"R$ {resumo_carteira['renda_passiva_anual_total']:,.2f}")
        col3.metric("Dividend Yield Médio", f"{resumo_carteira['dy_medio_ponderado'] * 100:.2f}%")
        
        st.info("Este é o potencial da sua carteira com base nos dados atuais. Lembre-se que o mercado é volátil.")
        
        if st.button("Confirmar e Salvar Plano", type="primary", use_container_width=True):
            dados_usuario = carregar_dados_usuario()
            dados_usuario['carteira_salva'] = st.session_state.carteira_alocada
            salvar_dados_usuario(dados_usuario)
            
            st.session_state.carteira_salva = st.session_state.carteira_alocada
            st.session_state.carteira_em_montagem = []
            st.session_state.dashboard_view = 'simulacao'
            st.session_state.analise_cache = None
            
            st.success("Seu plano de investimentos foi salvo com sucesso!")
            st.balloons()
            time.sleep(3)
            st.rerun()

def tela_welcome():
    """Tela de boas-vindas e login"""
    st.title("Bem-vindo(a) ao Rendy AI 🤖")
    st.markdown("Faça seu login ou cadastro para acessar seu dashboard.")
    
    nome = st.text_input("Seu nome:")
    email = st.text_input("Seu email:")
    
    if st.button("Acessar Dashboard", type="primary"):
        if nome and email:
            # Validação básica de email
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                st.error("Por favor, insira um email válido.")
                return
            
            salvar_dados_usuario({'nome': nome, 'email': email, 'carteira_salva': []})
            st.session_state.step = 'dashboard'
            st.session_state.nome_usuario = nome.split(' ')[0]
            st.rerun()
        else:
            st.error("Por favor, preencha nome e email.")

# ============================================================================
# FLUXO PRINCIPAL DA APLICAÇÃO
# ============================================================================

def main():
    """Função principal da aplicação"""
    try:
        inicializar_sessao()
        
        # Verifica se há usuário logado
        if os.path.exists(USUARIO_JSON) and (not st.session_state.nome_usuario):
            user_data = carregar_dados_usuario()
            if user_data and user_data.get('nome'):
                st.session_state.step = 'dashboard'
                st.session_state.nome_usuario = user_data.get('nome', '').split(' ')[0]
        
        # Navegação entre telas
        if st.session_state.step == "dashboard":
            tela_dashboard()
        else:
            tela_welcome()
            
    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado na aplicação: {e}")
              st.error("Ocorreu um erro inesperado. Por favor, recarregue a página.")

if __name__ == "__main__":
    main()