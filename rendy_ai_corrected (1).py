import streamlit as st
import yfinance as yf
import pandas as pd
import time
from typing import Dict, List, Optional
import json
import os
from datetime import datetime
import logging

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA E LOGGING
# ==============================================================================
st.set_page_config(
    page_title="Rendy AI - Assessor de Investimentos",
    page_icon="🤖",
    layout="centered"
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# SISTEMA DE PERSISTÊNCIA DE DADOS (Sem alterações)
# ==============================================================================
def salvar_usuario(nome: str, email: str) -> bool:
    try:
        if not nome or not email: return False
        if not os.path.exists('data'): os.makedirs('data')
        usuario_data = {
            'nome': nome.strip(), 'email': email.strip().lower(),
            'data_cadastro': datetime.now().isoformat(), 'perfil_risco': 'Moderado',
            'objetivo_principal': 'Aumentar Renda Passiva'
        }
        with open('data/usuario.json', 'w', encoding='utf-8') as f:
            json.dump(usuario_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Usuário {nome} salvo com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar dados do usuário: {e}")
        return False

def carregar_usuario() -> Optional[Dict]:
    try:
        if os.path.exists('data/usuario.json'):
            with open('data/usuario.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.error(f"Erro ao carregar dados do usuário: {e}")
        return None

def validar_email(email: str) -> bool:
    if not email or '@' not in email or '.' not in email: return False
    parts = email.split('@')
    if len(parts) != 2 or not parts[0] or not parts[1]: return False
    domain_parts = parts[1].split('.')
    if len(domain_parts) < 2 or not all(part for part in domain_parts): return False
    return True

# ==============================================================================
# SISTEMA DE NAVEGAÇÃO (Sem alterações)
# ==============================================================================
def inicializar_sessao():
    if 'step' not in st.session_state:
        usuario_existente = carregar_usuario()
        if usuario_existente:
            st.session_state.step = "main_app"
            st.session_state.user_name = usuario_existente['nome']
            st.session_state.user_email = usuario_existente['email']
        else:
            st.session_state.step = "welcome"
    
    default_values = {'ver_todos': False, 'valor_investir': 5000.0, 'user_name': '', 'user_email': ''}
    for key, value in default_values.items():
        if key not in st.session_state: st.session_state[key] = value

# ==============================================================================
# AGENTES DE IA (CLASSES DE ANÁLISE)
# ==============================================================================

class RendyInvestAgent: # (Sem alterações)
    def obter_perfil_usuario(self) -> Dict:
        usuario_data = carregar_usuario()
        perfil = {
            'user_id': st.session_state.get('user_email', 'user_123'),
            'nome': st.session_state.get('user_name', 'Usuário'),
            'perfil_risco': usuario_data.get('perfil_risco', 'Moderado') if usuario_data else 'Moderado',
            'objetivo_principal': usuario_data.get('objetivo_principal', 'Aumentar Renda Passiva') if usuario_data else 'Aumentar Renda Passiva',
            'valor_disponivel': st.session_state.get('valor_investir', 5000.00)
        }
        return perfil

class RendyFinanceAgent: # (Sem alterações)
    def _calcular_score_custo_beneficio(self, dados: Dict) -> float:
        try:
            score = 0
            dy = dados.get('dividend_yield', 0)
            if isinstance(dy, (int, float)) and dy > 0: score += dy * 15
            roe = dados.get('roe', 0)
            if isinstance(roe, (int, float)) and roe > 0: score += roe * 10
            pl = dados.get('p_l', 0)
            if isinstance(pl, (int, float)) and pl > 0: score += (1 / pl) * 5
            pvp = dados.get('p_vp', 0)
            if isinstance(pvp, (int, float)) and pvp > 0: score += (1 / pvp) * 5
            return round(max(score, 0), 2)
        except Exception: return 0.0

    def analisar_ativo(self, ticker: str) -> Dict:
        if not ticker or not isinstance(ticker, str): return {'erro': 'Ticker inválido'}
        try:
            acao = yf.Ticker(ticker.strip().upper())
            info = acao.info
            if not info or 'longName' not in info or not info.get('longName'):
                return {'erro': f"Dados insuficientes para '{ticker}'."}
            
            def get_numeric(key: str, default: float = 0.0) -> float:
                val = info.get(key, default)
                return float(val) if val is not None else default
            
            dados = {
                'ticker': ticker, 'nome_empresa': info.get('longName', 'N/A'),
                'preco_atual': get_numeric('currentPrice') or get_numeric('regularMarketPrice'),
                'dividend_yield': get_numeric('dividendYield'), 'p_l': get_numeric('trailingPE'),
                'p_vp': get_numeric('priceToBook'), 'roe': get_numeric('returnOnEquity'),
            }
            if dados['dividend_yield'] > 1: dados['dividend_yield'] /= 100
            if dados['roe'] > 1: dados['roe'] /= 100
            dados['score'] = self._calcular_score_custo_beneficio(dados)
            return dados
        except Exception as e:
            return {'erro': f"Erro ao buscar dados para {ticker}: {e}"}

    def descobrir_oportunidades(self) -> List[Dict]:
        tickers_ibov = [
            'ABEV3.SA', 'B3SA3.SA', 'BBAS3.SA', 'BBDC4.SA', 'BBSE3.SA', 'BRAP4.SA', 
            'BRFS3.SA', 'BRKM5.SA', 'CCRO3.SA', 'CIEL3.SA', 'CMIG4.SA', 'CPLE6.SA',
            'CSAN3.SA', 'CSNA3.SA', 'CYRE3.SA', 'ECOR3.SA', 'EGIE3.SA', 'ELET3.SA', 
            'EMBR3.SA', 'ENBR3.SA', 'EQTL3.SA', 'GGBR4.SA', 'GOAU4.SA', 'HAPV3.SA', 
            'HYPE3.SA', 'ITSA4.SA', 'ITUB4.SA', 'JBSS3.SA', 'LREN3.SA',
            'MGLU3.SA', 'MRFG3.SA', 'MRVE3.SA', 'MULT3.SA', 'NTCO3.SA', 'PCAR3.SA', 
            'PETR3.SA', 'PETR4.SA', 'PRIO3.SA', 'RADL3.SA', 'RAIL3.SA', 'RENT3.SA', 
            'SANB11.SA', 'SBSP3.SA', 'SUZB3.SA', 'TAEE11.SA', 'UGPA3.SA', 'USIM5.SA',
            'VALE3.SA', 'VIVT3.SA', 'WEGE3.SA', 'YDUQ3.SA'
        ]
        resultados = []
        progress_bar = st.progress(0, "Analisando o mercado para você...")
        for i, ticker in enumerate(tickers_ibov):
            resultado = self.analisar_ativo(ticker)
            if 'erro' not in resultado and resultado.get('preco_atual', 0) > 0:
                resultados.append(resultado)
            progress_bar.progress((i + 1) / len(tickers_ibov), f"Analisando {ticker}...")
        progress_bar.empty()
        return sorted(resultados, key=lambda x: x.get('score', 0), reverse=True)

class RendyXaiAgent:
    """Agente responsável por explicações, projeções e recomendações"""
    
    def _gerar_recomendacao(self, score: float) -> str:
        if not isinstance(score, (int, float)): score = 0
        if score >= 7: return "🟢 **OPORTUNIDADE EXCELENTE** - Esta ação apresenta indicadores muito favoráveis para dividendos e valorização."
        elif score >= 5: return "🟡 **BOA OPORTUNIDADE** - Esta ação tem potencial interessante, mas analise outros fatores antes de investir."
        elif score >= 3: return "🟠 **OPORTUNIDADE MODERADA** - Esta ação pode ser considerada, mas há opções potencialmente melhores no mercado."
        else: return "🔴 **CAUTELA RECOMENDADA** - Esta ação apresenta indicadores menos favoráveis. Considere outras alternativas."

    def apresentar_relatorio_visual(self, analise_ativo: Dict, perfil_usuario: Dict):
        """Gera um relatório visual interativo com Streamlit"""
        if 'erro' in analise_ativo:
            st.error(f"❌ **Não foi possível gerar um relatório:** {analise_ativo['erro']}")
            return

        try:
            nome_usuario = perfil_usuario.get('nome', 'Investidor').split(' ')[0]
            valor_investir = float(perfil_usuario.get('valor_disponivel', 0))
            preco_acao = float(analise_ativo.get('preco_atual', 0))
            dy = float(analise_ativo.get('dividend_yield', 0))
            roe = float(analise_ativo.get('roe', 0))
        except (ValueError, TypeError):
            st.error("❌ **Erro:** Dados numéricos inválidos para gerar projeção.")
            return

        if valor_investir <= 0 or preco_acao <= 0:
            st.warning("Dados insuficientes para gerar projeção (valor ou preço da ação inválidos).")
            return
        
        qtd_acoes = int(valor_investir / preco_acao)
        valor_investido_real = qtd_acoes * preco_acao
        renda_passiva_anual = valor_investido_real * dy
        
        st.subheader(f"📊 Relatório Personalizado para {nome_usuario}")
        st.markdown(f"### {analise_ativo.get('nome_empresa', 'N/A')} ({analise_ativo.get('ticker', 'N/A')})")

        st.markdown("#### 🎯 Suas Projeções para 1 Ano")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Renda Passiva Anual", f"R$ {renda_passiva_anual:,.2f}", f"{dy*100:.2f}% a.a.")
        with col2:
            st.metric("📈 Valor Investido", f"R$ {valor_investido_real:,.2f}", f"{qtd_acoes} ações")
        with col3:
            st.metric("💎 Potencial de Valorização", f"{roe*100:.2f}%", "Baseado no ROE")

        st.markdown("#### 💡 Recomendação Rendy AI")
        st.markdown(self._gerar_recomendacao(analise_ativo.get('score', 0)))

        with st.expander("🔍 Ver Análise Técnica Detalhada (Score, P/L, ROE...)"):
            score = analise_ativo.get('score', 0)
            pl = analise_ativo.get('p_l', 0)
            pvp = analise_ativo.get('p_vp', 0)

            st.write(f"**Score Custo/Benefício: {score:.1f} / 10**")
            st.progress(score / 10)

            if dy > 0: st.success(f"- **Dividend Yield {dy*100:.2f}%:** Bom potencial de renda passiva.")
            else: st.warning("- **Dividend Yield:** Dado não disponível ou a empresa não paga dividendos.")
            
            if pl > 0:
                if pl <= 15: st.success(f"- **P/L {pl:.2f}:** Potencialmente subvalorizada (bom).")
                else: st.warning(f"- **P/L {pl:.2f}:** Preço pode estar elevado.")
            else: st.info("- **P/L:** Dado não disponível.")

            if roe > 0: st.success(f"- **ROE {roe*100:.2f}%:** Boa capacidade de gerar lucro.")
            else: st.warning("- **ROE:** Dado não disponível.")
            
            if pvp > 0:
                if pvp <= 1.5: st.success(f"- **P/VP {pvp:.2f}:** Pode ser uma boa oportunidade de valor.")
                else: st.warning(f"- **P/VP {pvp:.2f}:** Preço acima do valor patrimonial.")
            else: st.info("- **P/VP:** Dado não disponível.")

        st.caption(f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}")
        st.warning("Aviso: Esta análise é educacional e baseada em dados históricos, não sendo uma garantia de resultados futuros. Sempre diversifique seus investimentos.")

# ==============================================================================
# ORQUESTRAÇÃO E CACHE (Função de análise um pouco alterada para usar barra de progresso)
# ==============================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def rodar_analise_de_mercado():
    finance_agent = RendyFinanceAgent()
    resultados = finance_agent.descobrir_oportunidades()
    return resultados

# ==============================================================================
# TELAS DO APLICATIVO (Telas de Onboarding sem alterações)
# ==============================================================================
def tela_boas_vindas():
    st.markdown("🤖", unsafe_allow_html=True)
    st.title("Olá! Eu sou o Rendy.AI 🤖")
    st.markdown("### Seu assistente de investimentos pessoal...")
    nome_usuario = st.text_input("Para começarmos, como posso te chamar?", placeholder="Ex: João da Silva")
    if nome_usuario.strip():
        if st.button(f"Prazer, {nome_usuario.strip().split(' ')[0]}! Continuar 👋", type="primary"):
            st.session_state.user_name = nome_usuario.strip()
            st.session_state.step = "explanation"
            st.rerun()

def tela_explicacao():
    primeiro_nome = st.session_state.get('user_name', 'Usuário').split(' ')[0]
    st.title(f"Perfeito, {primeiro_nome}! 👋")
    st.markdown("### Como eu vou te ajudar:...")
    col1, col2 = st.columns(2)
    if col1.button("⬅️ Voltar"):
        st.session_state.step = "welcome"; st.rerun()
    if col2.button("Vamos começar! 🚀", type="primary"):
        st.session_state.step = "registration"; st.rerun()

def tela_cadastro():
    st.title("Crie sua Conta Gratuita")
    st.markdown("Só mais um passo! Complete seu cadastro para desbloquear sua assessoria.")
    with st.form("cadastro_form"):
        nome = st.text_input("📝 Seu nome completo", value=st.session_state.get('user_name', ''))
        email = st.text_input("📧 Seu melhor e-mail", placeholder="seuemail@exemplo.com")
        aceito_termos = st.checkbox("Li e aceito que este é um aplicativo educacional.")
        submitted = st.form_submit_button("✅ Criar minha conta", type="primary")
        if submitted:
            if not nome.strip() or not email.strip() or not aceito_termos or not validar_email(email):
                st.error("⚠️ Por favor, preencha todos os campos e aceite os termos.")
            else:
                if salvar_usuario(nome, email):
                    st.session_state.step = "main_app"; st.success("🎉 Conta criada!"); time.sleep(1); st.rerun()
                else: st.error("❌ Erro ao criar conta.")

# ==============================================================================
# TELA PRINCIPAL (Com todas as melhorias)
# ==============================================================================
def tela_principal():
    """Tela principal do aplicativo com as análises."""
    primeiro_nome = st.session_state.get('user_name', 'Investidor').split(' ')[0]
    
    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.title(f"Olá, {primeiro_nome}!")
        st.markdown("**Seu painel de investimentos Rendy AI**")
    with col_btn:
        if st.button("🔄", help="Atualizar dados"): st.cache_data.clear(); st.rerun()
        if st.button("🚪", help="Sair"):
            if os.path.exists('data/usuario.json'): os.remove('data/usuario.json')
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
    st.markdown("---")

    tab1, tab2 = st.tabs(["🏆 Ranking de Oportunidades", "📊 Análise de Ações"])

    oportunidades = rodar_analise_de_mercado()
    if not oportunidades:
        st.error("❌ Não foi possível carregar as oportunidades. Tente atualizar os dados.")
        st.stop()

    with tab1:
        st.info("Aqui estão as melhores oportunidades do Ibovespa, classificadas por um score de custo/benefício focado em dividendos e valor.")
        
        melhor_oportunidade = oportunidades[0]
        with st.container(border=True):
            st.subheader(f"🥇 Oportunidade em Destaque: {melhor_oportunidade['ticker']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Empresa", melhor_oportunidade['nome_empresa'].split(' ')[0])
            c2.metric("Score Rendy AI", f"{melhor_oportunidade['score']:.1f}/10")
            c3.metric("Div. Yield", f"{melhor_oportunidade['dividend_yield']*100:.2f}%")
            
        st.write("### Ranking Completo")
        df = pd.DataFrame(oportunidades)
        df_display = df[['ticker', 'nome_empresa', 'score', 'dividend_yield', 'p_l', 'roe']].copy()
        df_display.columns = ['Ticker', 'Empresa', 'Score', 'Div. Yield', 'P/L', 'ROE']
        df_display['Div. Yield'] = df['dividend_yield'].apply(lambda x: f"{x*100:.2f}%" if x > 0 else "N/A")
        df_display['P/L'] = df['p_l'].apply(lambda x: f"{x:.2f}" if x > 0 else "N/A")
        df_display['ROE'] = df['roe'].apply(lambda x: f"{x*100:.2f}%" if x > 0 else "N/A")
        
        st.dataframe(
            df_display.head(10 if not st.session_state.ver_todos else None),
            hide_index=True, use_container_width=True,
            column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=10, format="%.1f")}
        )
        if not st.session_state.ver_todos and len(oportunidades) > 10:
            if st.button("📈 Ver Ranking Completo"):
                st.session_state.ver_todos = True; st.rerun()

    with tab2:
        st.info("Escolha uma ação do ranking e informe quanto você quer investir para receber uma análise e projeção personalizadas.")
        
        col1, col2 = st.columns(2)
        with col1:
            ticker_selecionado = st.selectbox("📈 Escolha uma ação:", options=[o['ticker'] for o in oportunidades])
        with col2:
            st.session_state.valor_investir = st.number_input("💰 Quanto quer investir (R$):", min_value=100.0, value=st.session_state.valor_investir, step=100.0)

        if st.button("🚀 Gerar Minha Análise", type="primary", use_container_width=True):
            if not ticker_selecionado:
                st.warning("⚠️ Por favor, selecione uma ação.")
            else:
                invest_agent = RendyInvestAgent()
                finance_agent = RendyFinanceAgent()
                xai_agent = RendyXaiAgent()

                with st.spinner(f"Executando análise completa para {ticker_selecionado}..."):
                    perfil = invest_agent.obter_perfil_usuario()
                    analise = finance_agent.analisar_ativo(ticker_selecionado)
                    xai_agent.apresentar_relatorio_visual(analise, perfil)

# ==============================================================================
# CONTROLE PRINCIPAL DA APLICAÇÃO (Sem alterações)
# ==============================================================================
def main():
    try:
        inicializar_sessao()
        current_step = st.session_state.get('step', 'welcome')
        
        if current_step == "welcome": tela_boas_vindas()
        elif current_step == "explanation": tela_explicacao()
        elif current_step == "registration": tela_cadastro()
        elif current_step == "main_app": tela_principal()
        else: st.session_state.step = "welcome"; st.rerun()
    except Exception as e:
        logger.error(f"Erro crítico na aplicação: {e}")
        st.error("❌ Erro crítico. Por favor, recarregue a página.")
        if st.button("🔄 Resetar Aplicação"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()

