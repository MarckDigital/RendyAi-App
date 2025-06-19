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

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================================================
# SISTEMA DE PERSISTÊNCIA DE DADOS
# ==============================================================================

def salvar_usuario(nome: str, email: str) -> bool:
    """Salva dados do usuário em arquivo JSON local"""
    try:
        # Validação de entrada
        if not nome or not email:
            logger.error("Nome ou email vazios")
            return False
            
        # Cria diretório se não existir
        if not os.path.exists('data'):
            os.makedirs('data')
        
        # Dados do usuário
        usuario_data = {
            'nome': nome.strip(),
            'email': email.strip().lower(),
            'data_cadastro': datetime.now().isoformat(),
            'perfil_risco': 'Moderado',
            'objetivo_principal': 'Aumentar Renda Passiva'
        }
        
        # Salva em arquivo
        with open('data/usuario.json', 'w', encoding='utf-8') as f:
            json.dump(usuario_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Usuário {nome} salvo com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao salvar dados do usuário: {e}")
        st.error(f"Erro ao salvar dados do usuário: {e}")
        return False

def carregar_usuario() -> Optional[Dict]:
    """Carrega dados do usuário do arquivo JSON"""
    try:
        if os.path.exists('data/usuario.json'):
            with open('data/usuario.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info("Dados do usuário carregados com sucesso")
                return data
        return None
    except Exception as e:
        logger.error(f"Erro ao carregar dados do usuário: {e}")
        return None

def validar_email(email: str) -> bool:
    """Valida formato básico do email"""
    if not email or '@' not in email or '.' not in email:
        return False
    
    # Validação mais robusta
    parts = email.split('@')
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return False
    
    domain_parts = parts[1].split('.')
    if len(domain_parts) < 2 or not all(part for part in domain_parts):
        return False
        
    return True

# ==============================================================================
# SISTEMA DE NAVEGAÇÃO
# ==============================================================================

def inicializar_sessao():
    """Inicializa variáveis de sessão"""
    if 'step' not in st.session_state:
        # Verifica se já existe usuário cadastrado
        usuario_existente = carregar_usuario()
        if usuario_existente:
            st.session_state.step = "main_app"
            st.session_state.user_name = usuario_existente['nome']
            st.session_state.user_email = usuario_existente['email']
        else:
            st.session_state.step = "welcome"
    
    # Inicializar outras variáveis de sessão com valores padrão
    default_values = {
        'ver_todos': False,
        'valor_investir': 5000.0,
        'user_name': '',
        'user_email': ''
    }
    
    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ==============================================================================
# AGENTES DE IA (CLASSES DE ANÁLISE)
# ==============================================================================

class RendyInvestAgent:
    """Agente responsável por gerenciar perfis de usuário"""
    
    def obter_perfil_usuario(self) -> Dict:
        """Obtém o perfil do usuário com validação a partir dos dados da sessão e do arquivo"""
        try:
            # Carrega dados do usuário cadastrado
            usuario_data = carregar_usuario()
            
            perfil = {
                'user_id': st.session_state.get('user_email', 'user_123'),
                'nome': st.session_state.get('user_name', 'Usuário'),
                'perfil_risco': usuario_data.get('perfil_risco', 'Moderado') if usuario_data else 'Moderado',
                'objetivo_principal': usuario_data.get('objetivo_principal', 'Aumentar Renda Passiva') if usuario_data else 'Aumentar Renda Passiva',
                'valor_disponivel': st.session_state.get('valor_investir', 5000.00)
            }
            
            # Validação do valor
            if not isinstance(perfil['valor_disponivel'], (int, float)) or perfil['valor_disponivel'] <= 0:
                perfil['valor_disponivel'] = 5000.00
                
            return perfil
            
        except Exception as e:
            logger.error(f"Erro ao obter perfil do usuário: {e}")
            st.error(f"Erro ao obter perfil do usuário: {e}")
            return {
                'user_id': 'user_default',
                'nome': 'Usuário',
                'perfil_risco': 'Moderado',
                'objetivo_principal': 'Aumentar Renda Passiva',
                'valor_disponivel': 5000.00
            }

class RendyFinanceAgent:
    """Agente responsável por análises financeiras"""
    
    def _calcular_score_custo_beneficio(self, dados: Dict) -> float:
        """Calcula score de custo/benefício com tratamento de erros"""
        try:
            score = 0
            
            # Dividend Yield (peso 15)
            dy = dados.get('dividend_yield', 0)
            if isinstance(dy, (int, float)) and dy > 0: 
                score += dy * 15
            
            # ROE (peso 10)
            roe = dados.get('roe', 0)
            if isinstance(roe, (int, float)) and roe > 0: 
                score += roe * 10
            
            # P/L inverso (peso 5) - quanto menor o P/L, melhor
            pl = dados.get('p_l', 0)
            if isinstance(pl, (int, float)) and pl > 0: 
                score += (1 / pl) * 5
            
            # P/VP inverso (peso 5) - quanto menor o P/VP, melhor
            pvp = dados.get('p_vp', 0)
            if isinstance(pvp, (int, float)) and pvp > 0: 
                score += (1 / pvp) * 5
            
            return round(max(score, 0), 2)
            
        except Exception as e:
            logger.error(f"Erro ao calcular score: {e}")
            return 0.0

    def analisar_ativo(self, ticker: str) -> Dict:
        """Analisa um ativo específico com tratamento robusto de erros"""
        if not ticker or not isinstance(ticker, str):
            return {'erro': 'Ticker inválido ou não fornecido'}
        
        try:
            ticker = ticker.strip().upper()
            acao = yf.Ticker(ticker)
            info = acao.info
            
            # Verificações mais rigorosas
            if not info or not isinstance(info, dict):
                return {'erro': f"Nenhum dado retornado para '{ticker}'"}
                
            if 'longName' not in info or not info.get('longName'):
                return {'erro': f"Dados insuficientes para '{ticker}'. Ativo pode não existir."}

            # Função auxiliar para obter valores numéricos seguros
            def get_numeric_value(key: str, default: float = 0.0) -> float:
                value = info.get(key, default)
                if value is None:
                    return default
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return default

            dados = {
                'ticker': ticker,
                'nome_empresa': info.get('longName', 'Nome não disponível'),
                'preco_atual': get_numeric_value('currentPrice') or get_numeric_value('regularMarketPrice'),
                'dividend_yield': get_numeric_value('dividendYield'),
                'p_l': get_numeric_value('trailingPE') or get_numeric_value('forwardPE'),
                'p_vp': get_numeric_value('priceToBook'),
                'roe': get_numeric_value('returnOnEquity'),
            }
            
            # Normalizar dividend yield e ROE se necessário
            if dados['dividend_yield'] > 1: 
                dados['dividend_yield'] /= 100
            if dados['roe'] > 1: 
                dados['roe'] /= 100
            
            dados['score'] = self._calcular_score_custo_beneficio(dados)
            
            logger.info(f"Análise concluída para {ticker}")
            return dados
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados para {ticker}: {str(e)}")
            return {'erro': f"Erro ao buscar dados para {ticker}: {str(e)}"}

    def descobrir_oportunidades(self) -> List[Dict]:
        """Descobre oportunidades no mercado com melhor controle de progresso"""
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
        total_tickers = len(tickers_ibov)
        
        # Usar containers do Streamlit para melhor controle
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        try:
            for i, ticker in enumerate(tickers_ibov):
                status_text.text(f"🔍 Analisando {ticker}... ({i+1}/{total_tickers})")
                resultado = self.analisar_ativo(ticker)
                
                # Validações mais rigorosas para incluir resultado
                if ('erro' not in resultado and 
                    isinstance(resultado.get('preco_atual'), (int, float)) and 
                    resultado.get('preco_atual', 0) > 0):
                    resultados.append(resultado)
                
                progress_bar.progress((i + 1) / total_tickers)
                time.sleep(0.05)  # Reduzir delay para melhor UX
                
        except Exception as e:
            logger.error(f"Erro durante análise de mercado: {e}")
            st.error(f"Erro durante análise de mercado: {e}")
        finally:
            progress_bar.empty()
            status_text.empty()
        
        # Ordenar por score de forma segura
        try:
            resultados_ordenados = sorted(
                resultados, 
                key=lambda x: x.get('score', 0) if isinstance(x.get('score'), (int, float)) else 0, 
                reverse=True
            )
            logger.info(f"Análise de mercado concluída: {len(resultados_ordenados)} ativos válidos")
            return resultados_ordenados
        except Exception as e:
            logger.error(f"Erro ao ordenar resultados: {e}")
            return resultados

class RendyXaiAgent:
    """Agente responsável por explicações, projeções e recomendações"""
    
    def _gerar_recomendacao(self, score: float) -> str:
        """Gera recomendação baseada no score"""
        if not isinstance(score, (int, float)):
            score = 0
            
        if score >= 7:
            return "🟢 **OPORTUNIDADE EXCELENTE** - Esta ação apresenta indicadores muito favoráveis para dividendos e valorização."
        elif score >= 5:
            return "🟡 **BOA OPORTUNIDADE** - Esta ação tem potencial interessante, mas analise outros fatores antes de investir."
        elif score >= 3:
            return "🟠 **OPORTUNIDADE MODERADA** - Esta ação pode ser considerada, mas há opções potencialmente melhores no mercado."
        else:
            return "🔴 **CAUTELA RECOMENDADA** - Esta ação apresenta indicadores menos favoráveis. Considere outras alternativas."

    def gerar_explicacao_e_projecao(self, analise_ativo: Dict, perfil_usuario: Dict) -> str:
        """Gera explicação detalhada e projeção personalizada com validações"""
        if 'erro' in analise_ativo:
            return f"❌ **Não foi possível gerar um relatório:** {analise_ativo['erro']}"

        # Validações de entrada
        try:
            nome_usuario = perfil_usuario.get('nome', 'Investidor').split(' ')[0]
            valor_investir = float(perfil_usuario.get('valor_disponivel', 0))
            preco_acao = float(analise_ativo.get('preco_atual', 0))
            dy = float(analise_ativo.get('dividend_yield', 0))
            roe = float(analise_ativo.get('roe', 0))
            pl = float(analise_ativo.get('p_l', 0))
            pvp = float(analise_ativo.get('p_vp', 0))
        except (ValueError, TypeError) as e:
            logger.error(f"Erro na conversão de dados numéricos: {e}")
            return "❌ **Erro:** Dados numéricos inválidos para gerar projeção."
        
        if valor_investir <= 0 or preco_acao <= 0:
            return "❌ **Erro:** Dados insuficientes para gerar projeção (valor de investimento ou preço da ação inválidos)."

        try:
            qtd_acoes = int(valor_investir / preco_acao)
            valor_investido_real = qtd_acoes * preco_acao
            renda_passiva_anual = valor_investido_real * dy if dy > 0 else 0
            valorizacao_estimada_anual = valor_investido_real * roe if roe > 0 else 0
            total_estimado_1_ano = valor_investido_real + renda_passiva_anual + valorizacao_estimada_anual
            
            relatorio = [
                f"# 📊 Relatório Personalizado para {nome_usuario}",
                f"## {analise_ativo.get('nome_empresa', 'N/A')} ({analise_ativo.get('ticker', 'N/A')})",
                "",
                f"### 🎯 Resumo do Seu Investimento",
                f"- **Seu objetivo:** {perfil_usuario.get('objetivo_principal', 'N/A')}",
                f"- **Valor disponível:** R$ {valor_investir:,.2f}",
                f"- **Preço por ação:** R$ {preco_acao:,.2f}",
                f"- **Quantidade de ações:** {qtd_acoes:,} ações",
                f"- **Valor efetivamente investido:** R$ {valor_investido_real:,.2f}",
                "",
                f"### 📈 Suas Projeções para 12 meses",
                f"- **💰 Renda Passiva (Dividendos):** R$ {renda_passiva_anual:,.2f} ({dy*100:.2f}% a.a.)" if dy > 0 else "- **💰 Renda Passiva:** Não disponível",
                f"- **🚀 Valorização Estimada:** R$ {valorizacao_estimada_anual:,.2f} (baseada no ROE de {roe*100:.2f}%)" if roe > 0 else "- **🚀 Valorização Estimada:** Dados insuficientes",
                f"- **💎 Valor Total Estimado:** R$ {total_estimado_1_ano:,.2f}",
                "",
                f"### 🔍 Análise Técnica (Score: {analise_ativo.get('score', 0):.1f}/10)",
            ]
            
            # Análise detalhada dos indicadores com validações
            if dy > 0: 
                status_dy = 'Excelente' if dy >= 0.06 else 'Bom' if dy >= 0.04 else 'Regular'
                relatorio.append(f"- **✅ Dividend Yield {dy*100:.2f}%:** {status_dy} potencial de renda.")
            else: 
                relatorio.append("- **⚠️ Dividend Yield:** Empresa não paga dividendos regulares.")
            
            if pl > 0: 
                icon = '✅' if pl <= 15 else '⚠️' if pl <= 25 else '❌'
                status_pl = 'Ação subvalorizada' if pl <= 15 else 'Preço justo' if pl <= 25 else 'Ação pode estar cara'
                relatorio.append(f"- **{icon} P/L {pl:.2f}:** {status_pl}.")
            else: 
                relatorio.append("- **⚠️ P/L:** Dado não disponível.")

            if roe > 0: 
                icon = '✅' if roe >= 0.15 else '⚠️' if roe >= 0.10 else '❌'
                status_roe = 'Excelente' if roe >= 0.15 else 'Boa' if roe >= 0.10 else 'Fraca'
                relatorio.append(f"- **{icon} ROE {roe*100:.2f}%:** {status_roe} capacidade de gerar lucro.")
            else: 
                relatorio.append("- **⚠️ ROE:** Dado não disponível.")

            if pvp > 0: 
                icon = '✅' if pvp <= 1.5 else '⚠️' if pvp <= 3 else '❌'
                status_pvp = 'Boa oportunidade' if pvp <= 1.5 else 'Preço razoável' if pvp <= 3 else 'Preço elevado'
                relatorio.append(f"- **{icon} P/VP {pvp:.2f}:** {status_pvp}.")
            else: 
                relatorio.append("- **⚠️ P/VP:** Dado não disponível.")
            
            relatorio.extend([
                "",
                f"### 💡 Recomendação para {nome_usuario}",
                self._gerar_recomendacao(analise_ativo.get('score', 0)),
                "",
                "### ⚠️ Avisos Importantes",
                "- Esta análise é baseada em dados históricos e não garante resultados futuros.",
                "- Investimentos em ações envolvem riscos de perda do capital.",
                "- Consulte sempre um assessor de investimentos qualificado e diversifique seus investimentos.",
                "",
                f"**Relatório gerado em:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
            ])
            
            logger.info(f"Relatório gerado com sucesso para {nome_usuario}")
            return "\n".join(relatorio)
            
        except Exception as e:
            logger.error(f"Erro ao gerar projeção: {str(e)}")
            return f"❌ **Erro ao gerar projeção:** {str(e)}"

# ==============================================================================
# FUNÇÃO DE ORQUESTRAÇÃO E CACHE
# ==============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def rodar_analise_de_mercado():
    """Executa análise de mercado com cache otimizado"""
    try:
        finance_agent = RendyFinanceAgent()
        resultados = finance_agent.descobrir_oportunidades()
        logger.info(f"Cache atualizado com {len(resultados)} oportunidades")
        return resultados
    except Exception as e:
        logger.error(f"Erro na análise de mercado: {e}")
        st.error(f"Erro na análise de mercado: {e}")
        return []

# ==============================================================================
# TELAS DO APLICATIVO (NAVEGAÇÃO)
# ==============================================================================

def tela_boas_vindas():
    """Tela 1: Apresentação e coleta do nome."""
    # Usar URL de imagem mais confiável
    st.markdown("🤖", unsafe_allow_html=True)
    st.title("Olá! Eu sou o Rendy.AI 🤖")
    st.markdown(
        """
        ### Seu assistente de investimentos pessoal
        Minha missão é te ajudar a investir com mais confiança, analisando as
        melhores oportunidades do mercado de dividendos.
        
        **Para começarmos, como posso te chamar?**
        """
    )

    nome_usuario = st.text_input("Digite seu nome abaixo:", placeholder="Ex: João da Silva", key="nome_input")

    if nome_usuario and nome_usuario.strip():
        primeiro_nome = nome_usuario.strip().split(' ')[0]
        if st.button(f"Prazer em te conhecer, {primeiro_nome}! Vamos continuar? 👋", type="primary"):
            st.session_state.user_name = nome_usuario.strip()
            st.session_state.step = "explanation"
            st.rerun()

def tela_explicacao():
    """Tela 2: Explica o funcionamento do App."""
    primeiro_nome = st.session_state.get('user_name', '').split(' ')[0] if st.session_state.get('user_name') else 'Usuário'
    st.title(f"Perfeito, {primeiro_nome}! 👋")
    st.markdown(
        """
        ### Como eu vou te ajudar:
        - 🔍 **Análise Inteligente:** Analiso as principais ações do Ibovespa e calculo scores de custo/benefício.
        - 📊 **Relatórios Personalizados:** Crio projeções baseadas no valor que você quer investir.
        - 🎯 **Recomendações Claras:** Sugiro investimentos alinhados com seu objetivo de renda passiva.
        
        **Pronto para descobrir suas melhores oportunidades?**
        """
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Voltar"):
            st.session_state.step = "welcome"
            st.rerun()
    with col2:
        if st.button("Vamos começar! 🚀", type="primary"):
            st.session_state.step = "registration"
            st.rerun()

def tela_cadastro():
    """Tela 3: Formulário de cadastro."""
    primeiro_nome = st.session_state.get('user_name', '').split(' ')[0] if st.session_state.get('user_name') else 'Usuário'
    st.title("Crie sua Conta Gratuita")
    st.markdown(f"Só mais um passo, {primeiro_nome}! Complete seu cadastro para desbloquear sua assessoria.")

    with st.form("cadastro_form"):
        nome = st.text_input("📝 Seu nome completo", value=st.session_state.get('user_name', ''))
        email = st.text_input("📧 Seu melhor e-mail", placeholder="seuemail@exemplo.com")
        aceito_termos = st.checkbox("Li e aceito que este é um aplicativo educacional.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("⬅️ Voltar"):
                st.session_state.step = "explanation"
                st.rerun()
        with col2:
            if st.form_submit_button("✅ Criar minha conta", type="primary"):
                if not nome or not nome.strip():
                    st.error("⚠️ Por favor, preencha o nome.")
                elif not email or not email.strip():
                    st.error("⚠️ Por favor, preencha o e-mail.")
                elif not validar_email(email.strip()):
                    st.error("⚠️ Por favor, digite um e-mail válido.")
                elif not aceito_termos:
                    st.error("⚠️ Por favor, aceite os termos para continuar.")
                else:
                    if salvar_usuario(nome.strip(), email.strip()):
                        st.session_state.user_name = nome.strip()
                        st.session_state.user_email = email.strip()
                        st.session_state.step = "main_app"
                        st.success(f"🎉 Tudo certo, {nome.strip().split(' ')[0]}! Conta criada.")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("❌ Erro ao criar conta. Tente novamente.")

def tela_principal():
    """Tela principal do aplicativo com as análises."""
    primeiro_nome = st.session_state.get('user_name', 'Investidor').split(' ')[0] if st.session_state.get('user_name') else 'Investidor'
    
    # Cabeçalho e botões de ação
    st.title(f"🤖 Rendy AI - Olá, {primeiro_nome}!")
    st.markdown("**Suas oportunidades de investimento personalizadas**")
    
    col1, _, col2, col3 = st.columns([5, 1, 1, 1])
    with col2:
        if st.button("🔄", help="Atualizar dados do mercado"):
            st.cache_data.clear()
            st.rerun()
    with col3:
        if st.button("🚪", help="Sair da conta"):
            try:
                if os.path.exists('data/usuario.json'): 
                    os.remove('data/usuario.json')
                # Limpar session state de forma mais segura
                keys_to_remove = list(st.session_state.keys())
                for key in keys_to_remove: 
                    del st.session_state[key]
                st.rerun()
            except Exception as e:
                logger.error(f"Erro ao fazer logout: {e}")
                st.error("Erro ao sair. Recarregue a página.")
    
    st.markdown("---")

    # Seção 1: Descoberta de Oportunidades
    st.header("🔍 Suas Melhores Oportunidades no Ibovespa")
    
    try:
        with st.spinner("Analisando mercado para você..."):
            oportunidades = rodar_analise_de_mercado()

        if not oportunidades:
            st.error("❌ Não foi possível carregar as oportunidades. Tente atualizar os dados.")
            st.stop()

        # Criar DataFrame com tratamento de erros
        try:
            df = pd.DataFrame(oportunidades)
            df_display = df[['ticker', 'nome_empresa', 'score', 'dividend_yield', 'p_l', 'roe']].copy()
            df_display.columns = ['Ticker', 'Empresa', 'Score', 'Div. Yield', 'P/L', 'ROE']
            
            # Formatação segura do DataFrame
            df_display['Div. Yield'] = df['dividend_yield'].apply(
                lambda x: f"{x*100:.2f}%" if isinstance(x, (int, float)) and x > 0 else "N/A"
            )
            df_display['P/L'] = df['p_l'].apply(
                lambda x: f"{x:.2f}" if isinstance(x, (int, float)) and x > 0 else "N/A"
            )
            df_display['ROE'] = df['roe'].apply(
                lambda x: f"{x*100:.2f}%" if isinstance(x, (int, float)) and x > 0 else "N/A"
            )

            num_items = len(df_display) if st.session_state.ver_todos else 10
            st.dataframe(
                df_display.head(num_items),
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "Score": st.column_config.ProgressColumn(
                        "Score", 
                        min_value=0, 
                        max_value=10,
                        format="%.1f"
                    )
                }
            )

            if not st.session_state.ver_todos and len(oportunidades) > 10:
                if st.button("📈 Ver Ranking Completo"):
                    st.session_state.ver_todos = True
                    st.rerun()
                    
        except Exception as e:
            logger.error(f"Erro ao criar DataFrame: {e}")
            st.error("Erro ao exibir dados do mercado. Tente atualizar.")
            
    except Exception as e:
        logger.error(f"Erro na seção de oportunidades: {e}")
        st.error("Erro ao carregar oportunidades. Tente novamente.")
        return
    
    st.markdown("---")

    # Seção 2: Análise Detalhada
    st.header(f"📊 Sua Análise Personalizada, {primeiro_nome}")
    
    if not oportunidades:
        st.warning("⚠️ Nenhuma oportunidade disponível para análise.")
        return
        
    try:
        col1, col2 = st.columns(2)
        with col1:
            ticker_options = [o['ticker'] for o in oportunidades if 'ticker' in o]
            if not ticker_options:
                st.error("❌ Nenhum ticker válido encontrado.")
                return
            ticker = st.selectbox("📈 Escolha uma ação:", options=ticker_options)
        with col2:
            valor_investir = st.number_input(
                "💰 Quanto quer investir (R$):", 
                min_value=100.0, 
                max_value=1000000.0,
                value=float(st.session_state.get('valor_investir', 5000.0)), 
                step=100.0, 
                key='valor_investir'
            )

        if st.button("🚀 Gerar Minha Análise", type="primary"):
            if not ticker:
                st.warning("⚠️ Por favor, selecione uma ação.")
                return
            
            # Validar valor de investimento
            if valor_investir <= 0:
                st.error("⚠️ Valor de investimento deve ser maior que zero.")
                return
            
            invest_agent = RendyInvestAgent()
            finance_agent = RendyFinanceAgent()
            xai_agent = RendyXaiAgent()

            with st.spinner(f"Executando análise completa para {ticker}..."):
                try:
                    perfil = invest_agent.obter_perfil_usuario()
                    analise = finance_agent.analisar_ativo(ticker)
                    relatorio = xai_agent.gerar_explicacao_e_projecao(analise, perfil)
                    
                    if relatorio:
                        st.markdown(relatorio)
                        
                        # Botão de download com nome de arquivo mais específico
                        nome_arquivo = f"relatorio_rendy_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
                        st.download_button(
                            label="📄 Baixar Relatório", 
                            data=relatorio,
                            file_name=nome_arquivo, 
                            mime="text/markdown"
                        )
                    else:
                        st.error("❌ Não foi possível gerar o relatório.")
                        
                except Exception as e:
                    logger.error(f"Erro ao gerar análise: {e}")
                    st.error(f"❌ Erro ao gerar análise: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Erro na seção de análise: {e}")
        st.error("Erro na seção de análise. Tente novamente.")

# ==============================================================================
# CONTROLE PRINCIPAL DA APLICAÇÃO
# ==============================================================================

def main():
    """Função principal que gerencia a navegação entre as telas."""
    try:
        inicializar_sessao()

        # Navegação com tratamento de erros
        current_step = st.session_state.get('step', 'welcome')
        
        if current_step == "welcome":
            tela_boas_vindas()
        elif current_step == "explanation":
            tela_explicacao()
        elif current_step == "registration":
            tela_cadastro()
        elif current_step == "main_app":
            tela_principal()
        else:
            logger.warning(f"Step inválido: {current_step}. Redirecionando para welcome.")
            st.session_state.step = "welcome"
            st.rerun()
            
    except Exception as e:
        logger.error(f"Erro crítico na aplicação: {e}")
        st.error("❌ Erro crítico na aplicação. Por favor, recarregue a página.")
        
        # Botão de emergência para resetar a aplicação
        if st.button("🔄 Resetar Aplicação"):
            # Limpar tudo e recomeçar
            try:
                if os.path.exists('data/usuario.json'): 
                    os.remove('data/usuario.json')
                keys_to_remove = list(st.session_state.keys())
                for key in keys_to_remove: 
                    del st.session_state[key]
                st.cache_data.clear()
                st.rerun()
            except Exception as reset_error:
                logger.error(f"Erro ao resetar aplicação: {reset_error}")
                st.error("Erro ao resetar. Por favor, recarregue a página manualmente.")

if __name__ == "__main__":
    main()