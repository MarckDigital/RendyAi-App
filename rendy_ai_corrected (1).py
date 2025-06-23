

def get_poupanca_anual_return(year):
    # Dados históricos aproximados da poupança (exemplo, idealmente de uma API ou fonte confiável)
    # Fonte: https://brasilindicadores.com.br/poupanca/
    # Considera a regra nova (0.5% a.m. + TR) ou 70% da Selic + TR
    # Para simplificar, usaremos valores médios anualizados aproximados
    data = {
        2024: 7.09, # Estimativa
        2023: 8.03,
        2022: 7.90,
        2021: 2.94,
        2020: 2.11,
        2019: 4.26,
        2018: 4.62,
        2017: 6.17,
        2016: 8.30,
        2015: 8.15,
        2014: 7.14,
        2013: 6.20,
        2012: 7.00, # Mudança de regra em 2012
        2011: 6.70,
        2010: 6.70
    }
    return data.get(year, 0.0)





def get_tesouro_ipca_anual_return(year):
    # Dados históricos aproximados do Tesouro IPCA+ (exemplo, idealmente de uma API ou fonte confiável)
    # A rentabilidade do Tesouro IPCA+ é IPCA + uma taxa. Para simplificar, usaremos uma estimativa anualizada.
    # Fonte: Tesouro Direto e notícias de mercado
    data = {
        2024: 6.5, # Estimativa IPCA + taxa real
        2023: 8.0,
        2022: 7.5,
        2021: 5.0,
        2020: 3.5,
        2019: 5.0,
        2018: 6.0,
        2017: 7.0,
        2016: 8.0,
        2015: 9.0,
        2014: 7.0,
        2013: 6.0,
        2012: 5.5,
        2011: 6.0,
        2010: 5.0
    }
    return data.get(year, 0.0)





def get_cdi_anual_return(year):
    # Dados históricos aproximados do CDI (exemplo, idealmente de uma API ou fonte confiável)
    # Fonte: https://investidor10.com.br/indices/cdi/
    data = {
        2024: 11.80, # Estimativa
        2023: 13.24,
        2022: 12.38,
        2021: 4.42,
        2020: 2.76,
        2019: 5.96,
        2018: 6.42,
        2017: 9.93,
        2016: 14.19,
        2015: 13.19,
        2014: 10.81,
        2013: 8.07,
        2012: 8.30,
        2011: 11.80,
        2010: 10.70
    }
    return data.get(year, 0.0)





def get_fiis_anual_return(year):
    # Dados históricos aproximados do IFIX (exemplo, idealmente de uma API ou fonte confiável)
    # Fonte: B3 e notícias de mercado
    data = {
        2024: 10.36, # Estimativa até maio/2025 (Exame)
        2023: 12.00,
        2022: -2.30,
        2021: -2.28,
        2020: -10.00,
        2019: 35.98,
        2018: 10.00,
        2017: 20.00,
        2016: 15.00,
        2015: 5.00,
        2014: 8.00,
        2013: 12.00,
        2012: 10.00,
        2011: 8.00,
        2010: 7.00
    }
    return data.get(year, 0.0)





def get_dolar_anual_return(year):
    # Dados históricos aproximados do Dólar (USD/BRL) (exemplo, idealmente de uma API ou fonte confiável)
    # Fonte: yfinance e notícias de mercado
    data = {
        2024: 0.99, # Estimativa (Mais Retorno)
        2023: 7.90,
        2022: -5.38,
        2021: 4.93,
        2020: 29.38,
        2019: 3.50,
        2018: 17.00,
        2017: -1.50,
        2016: -17.00,
        2015: 48.00,
        2014: 13.00,
        2013: 15.00,
        2012: 8.00,
        2011: -11.00,
        2010: -4.00
    }
    return data.get(year, 0.0)





def get_ouro_anual_return(year):
    # Dados históricos aproximados do Ouro (exemplo, idealmente de uma API ou fonte confiável)
    # Fonte: Bullion Rates, Exame
    data = {
        2024: 46.12, # Estimativa GOLD11 (Investidor10)
        2023: 15.00,
        2022: 54.00,
        2021: -7.00,
        2020: 55.00,
        2019: 54.00,
        2018: 10.00,
        2017: 1.00,
        2016: 18.00,
        2015: 10.00,
        2014: 15.00,
        2013: -10.00,
        2012: 10.00,
        2011: 20.00,
        2010: 30.00
    }
    return data.get(year, 0.0)





def get_ibovespa_anual_return(year):
    # Dados históricos aproximados do Ibovespa (exemplo, idealmente de uma API ou fonte confiável)
    # Fonte: yfinance e notícias de mercado
    data = {
        2024: 15.00, # Estimativa
        2023: 22.29,
        2022: -4.64,
        2021: -11.93,
        2020: 2.92,
        2019: 31.58,
        2018: 15.03,
        2017: 26.86,
        2016: 38.94,
        2015: -13.31,
        2014: -2.91,
        2013: -15.50,
        2012: 7.40,
        2011: -18.11,
        2010: 1.00
    }
    return data.get(year, 0.0)





def get_inflation_data(series_id, start_date, end_date):
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series_id}/dados?formato=json&dataInicial={start_date}&dataFinal={end_date}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        df = pd.DataFrame(data)
        df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
        df = df.set_index("data")
        return df
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao buscar dados da série {series_id} do BCB: {e}")
        return pd.DataFrame()

def calculate_annual_inflation(df):
    if df.empty:
        return 0.0
    # Calcula a inflação anualizada a partir dos dados mensais
    # Assumindo que o último valor é o mais recente e queremos a variação anual
    # Isso pode ser mais complexo para um cálculo preciso de 12 meses, mas para MVP, usaremos uma simplificação
    # Para um cálculo mais preciso, seria necessário somar os valores mensais e converter para anual
    # Ou usar a função de retorno anualizado de uma série de tempo
    
    # Simplificação: pega o último valor disponível e assume como a taxa anual
    # Isso NÃO é um cálculo de inflação anual acumulada, mas sim o último valor mensal
    # Para inflação anual acumulada, seria necessário somar os 12 últimos meses
    
    # Exemplo de cálculo de inflação acumulada em 12 meses:
    # df_anual = df.resample('Y').sum()
    # return df_anual['valor'].iloc[-1] if not df_anual.empty else 0.0
    
    # Para o MVP, vamos simular um valor anualizado baseado no último mês ou em um valor fixo
    # A série 433 (IPCA) e 189 (IGP-M) e 188 (INPC) são mensais
    # Para obter o valor anual, precisamos acumular 12 meses ou usar a variação anual
    
    # Para simplificar, vamos pegar o último valor e multiplicar por 12 para uma estimativa anual
    # OU, se a série já for anual, apenas o último valor
    
    # Vamos buscar a série 433 (IPCA), 189 (IGP-M) e 188 (INPC)
    # A API do BCB retorna valores mensais. Para anualizar, precisamos acumular 12 meses.
    
    # Exemplo de cálculo de inflação acumulada em 12 meses:
    # Se o DataFrame tiver dados suficientes, calcula a variação percentual dos últimos 12 meses
    if len(df) >= 12:
        # Pega os últimos 12 meses
        df_12_meses = df.iloc[-12:]
        # Calcula o produto acumulado (1 + taxa_mensal)
        accumulated_return = (1 + df_12_meses['valor'] / 100).prod() - 1
        return accumulated_return * 100 # Retorna em percentual
    elif not df.empty:
        # Se não tiver 12 meses, retorna o último valor mensal
        return df['valor'].iloc[-1]
    return 0.0


def get_ipca_anual_return(year):
    end_date = datetime.now().strftime("%d/%m/%Y")
    start_date = (datetime.now() - timedelta(days=365*2)).strftime("%d/%m/%Y") # Últimos 2 anos
    df_ipca = get_inflation_data(433, start_date, end_date) # Série IPCA
    return calculate_annual_inflation(df_ipca)

def get_igpm_anual_return(year):
    end_date = datetime.now().strftime("%d/%m/%Y")
    start_date = (datetime.now() - timedelta(days=365*2)).strftime("%d/%m/%Y") # Últimos 2 anos
    df_igpm = get_inflation_data(189, start_date, end_date) # Série IGP-M
    return calculate_annual_inflation(df_igpm)

def get_inpc_anual_return(year):
    end_date = datetime.now().strftime("%d/%m/%Y")
    start_date = (datetime.now() - timedelta(days=365*2)).strftime("%d/%m/%Y") # Últimos 2 anos
    df_inpc = get_inflation_data(188, start_date, end_date) # Série INPC
    return calculate_annual_inflation(df_inpc)





def get_market_overview_data():
    current_year = datetime.now().year
    last_year = current_year - 1

    # Coleta de dados históricos e do último ano
    data_last_year = {
        "Poupança": get_poupanca_anual_return(last_year),
        "Tesouro IPCA+": get_tesouro_ipca_anual_return(last_year),
        "CDI/CDB": get_cdi_anual_return(last_year),
        "FIIs (IFIX)": get_fiis_anual_return(last_year),
        "Dólar (USD/BRL)": get_dolar_anual_return(last_year),
        "Ouro": get_ouro_anual_return(last_year),
        "Ibovespa": get_ibovespa_anual_return(last_year),
    }

    # Coleta de dados de inflação
    ipca_last_year = get_ipca_anual_return(last_year)
    igpm_last_year = get_igpm_anual_return(last_year)
    inpc_last_year = get_inpc_anual_return(last_year)

    # Previsões para o ano atual (mockadas para MVP)
    # Em um ambiente real, estas previsões viriam de APIs de mercado ou modelos preditivos
    data_current_year_forecast = {
        "Poupança": 7.00, # Exemplo de previsão
        "Tesouro IPCA+": 6.80,
        "CDI/CDB": 10.50,
        "FIIs (IFIX)": 11.00,
        "Dólar (USD/BRL)": 5.00,
        "Ouro": 10.00,
        "Ibovespa": 18.00,
    }
    ipca_current_year_forecast = 4.00 # Exemplo de previsão
    igpm_current_year_forecast = 3.50 # Exemplo de previsão
    inpc_current_year_forecast = 3.80 # Exemplo de previsão

    # Estruturando os dados para exibição e ranking
    overview_data = []
    for invest_type, return_last_year in data_last_year.items():
        overview_data.append({
            "Investimento": invest_type,
            f"Rentabilidade {last_year} (%)": return_last_year,
            f"Previsão {current_year} (%)": data_current_year_forecast.get(invest_type, 0.0)
        })

    # Adicionando inflação
    overview_data.append({
        "Investimento": "IPCA",
        f"Rentabilidade {last_year} (%)": ipca_last_year,
        f"Previsão {current_year} (%)": ipca_current_year_forecast
    })
    overview_data.append({
        "Investimento": "IGP-M",
        f"Rentabilidade {last_year} (%)": igpm_last_year,
        f"Previsão {current_year} (%)": igpm_current_year_forecast
    })
    overview_data.append({
        "Investimento": "INPC",
        f"Rentabilidade {last_year} (%)": inpc_last_year,
        f"Previsão {current_year} (%)": inpc_current_year_forecast
    })

    df_overview = pd.DataFrame(overview_data)
    df_overview = df_overview.sort_values(by=f"Rentabilidade {last_year} (%)", ascending=False).reset_index(drop=True)

    return df_overview, current_year, last_year


class RendyOrchestrator:
    """Orquestrador principal que gerencia os agentes e a interface do usuário"""
    def __init__(self):
        self.perfil_usuario = carregar_perfil_usuario()
        self.finance_agent = RendyFinanceAgent()
        self.invest_agent = RendyInvestAgent()
        self.xai_agent = RendyXAI()
        self.TODAY_NEWS_DATA = self._fetch_today_news_data()
        self.historico_interacoes = self._carregar_historico_interacoes()

    def _fetch_today_news_data(self):
        df_overview, current_year, last_year = get_market_overview_data()
        
        # Formata os dados para o formato esperado pelo TODAY_NEWS_DATA
        # Isso é uma adaptação temporária, a estrutura final será mais flexível
        manchetes = [
          # Extrai os valores do DataFrame para evitar problemas de aspas aninhadas em f-strings
        rentabilidade_col = f"Rentabilidade {last_year} (%)"
        ibovespa_rent_last_year = df_overview.loc[df_overview["Investimento"] == "Ibovespa", rentabilidade_col].iloc[0]
        dolar_rent_last_year = df_overview.loc[df_overview["Investimento"] == "Dólar (USD/BRL)", rentabilidade_col].iloc[0]
        ipca_rent_last_year = df_overview.loc[df_overview["Investimento"] == "IPCA", rentabilidade_col].iloc[0]
        poupanca_rent_last_year = df_overview.loc[df_overview["Investimento"] == "Poupança", rentabilidade_col].iloc[0]
        fiis_rent_last_year = df_overview.loc[df_overview["Investimento"] == "FIIs (IFIX)", rentabilidade_col].iloc[0]
        ouro_rent_last_year = df_overview.loc[df_overview["Investimento"] == "Ouro", rentabilidade_col].iloc[0]
            f"Ibovespa rendeu {ibovespa_rent_last_year:.2f}% em {last_year}.",
            f"Dólar variou {dolar_rent_last_year:.2f}% em {last_year}.",
            f"IPCA acumulado em {ipca_rent_last_year:.2f}% em {last_year}."
        ]
        
        indices = {
            "Ibovespa": f"{ibovespa_rent_last_year:.2f}% ({last_year})",
            "Dólar (USD/BRL)": f"{dolar_rent_last_year:.2f}% ({last_year})",
            "IPCA": f"{ipca_rent_last_year:.2f}% ({last_year})"
        }
        
        destaques_renda_fixa = [
            f"Poupança rendeu {poupanca_rent_last_year:.2f}% em {last_year}.",
            f"CDI/CDB superou a inflação em {last_year}."
        ]
        
        destaques_renda_variavel = [
            f"FIIs (IFIX) com rentabilidade de {fiis_rent_last_year:.2f}% em {last_year}.",
            f"Ouro com forte valorização de {ouro_rent_last_year:.2f}% em {last_year}."
        ]    ]      return {
            "manchetes": manchetes,
            "indices": indices,
            "destaques_renda_fixa": destaques_renda_fixa,
            "destaques_renda_variavel": destaques_renda_variavel,
            "df_overview": df_overview,
            "current_year": current_year,
            "last_year": last_year
        }

    def _carregar_historico_interacoes(self):
        try:
            if os.path.exists(HISTORICO_JSON):
                with open(HISTORICO_JSON, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar histórico de interações: {e}")
        return []

    def _salvar_historico_interacoes(self):
        try:
            inicializar_ambiente()
            with open(HISTORICO_JSON, 'w', encoding='utf-8') as f:
                json.dump(self.historico_interacoes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar histórico de interações: {e}")

    def exibir_tela_cadastro(self):
        st.title("Bem-vindo à Rendy AI!")
        st.subheader("Crie seu perfil para começar a investir de forma inteligente.")

        with st.form("form_cadastro"):
            nome = st.text_input("Nome Completo", value=self.perfil_usuario.nome if self.perfil_usuario else "")
            email = st.text_input("E-mail", value=self.perfil_usuario.email if self.perfil_usuario else "")
            
            col1, col2 = st.columns(2)
            with col1:
                tolerancia_risco = st.selectbox(
                    "Tolerância a Risco",
                    ["conservador", "moderado", "agressivo"],
                    index=["conservador", "moderado", "agressivo"].index(self.perfil_usuario.tolerancia_risco) if self.perfil_usuario else 1
                )
                horizonte_investimento = st.selectbox(
                    "Horizonte de Investimento",
                    ["curto", "medio", "longo"],
                    index=["curto", "medio", "longo"].index(self.perfil_usuario.horizonte_investimento) if self.perfil_usuario else 1
                )
            with col2:
                objetivo_principal = st.selectbox(
                    "Objetivo Principal",
                    ["renda_passiva", "crescimento", "preservacao"],
                    index=["renda_passiva", "crescimento", "preservacao"].index(self.perfil_usuario.objetivo_principal) if self.perfil_usuario else 0
                )
                experiencia = st.selectbox(
                    "Experiência em Investimentos",
                    ["iniciante", "intermediario", "avancado"],
                    index=["iniciante", "intermediario", "avancado"].index(self.perfil_usuario.experiencia) if self.perfil_usuario else 0
                )
            
            valor_disponivel = st.number_input("Valor Disponível para Investimento (R$)", min_value=0.0, value=self.perfil_usuario.valor_disponivel if self.perfil_usuario else 0.0, format="%.2f")
            
            setores_preferidos = st.multiselect(
                "Setores de Ações Preferidos (Opcional)",
                SETORES_DISPONIVEIS,
                default=self.perfil_usuario.setores_preferidos if self.perfil_usuario else []
            )

            submitted = st.form_submit_button("Salvar Perfil")
            if submitted:
                if not validar_email(email):
                    st.error("Por favor, insira um e-mail válido.")
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
                    st.session_state.perfil_carregado = True
                    st.success("Perfil salvo com sucesso!")
                    st.rerun()

    def aba_inicio(self):
        st.header(f"Olá, {self.perfil_usuario.nome}! 👋")
        st.subheader("Visão Geral do Mercado")

        df_overview = self.TODAY_NEWS_DATA["df_overview"]
        current_year = self.TODAY_NEWS_DATA["current_year"]
        last_year = self.TODAY_NEWS_DATA["last_year"]

        st.markdown(f"### Rentabilidade Anualizada e Previsões ({last_year} e {current_year})")
        st.write("Compare a rentabilidade dos principais investimentos e índices de inflação:")

        # Tabela de dados
        st.dataframe(df_overview.set_index("Investimento").style.format("{:.2f}%"), use_container_width=True)

        # Gráfico de barras para rentabilidade do último ano
        fig_last_year = px.bar(df_overview, x="Investimento", y=f"Rentabilidade {last_year} (%)",
                               title=f"Rentabilidade Anualizada em {last_year}",
                               labels={f"Rentabilidade {last_year} (%)": "Rentabilidade Anualizada (%)"},
                               color=f"Rentabilidade {last_year} (%)",
                               color_continuous_scale=px.colors.sequential.Plasma)
        fig_last_year.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_last_year, use_container_width=True)

        # Gráfico de barras para previsões do ano atual
        fig_current_year = px.bar(df_overview, x="Investimento", y=f"Previsão {current_year} (%)",
                                  title=f"Previsão de Rentabilidade Anualizada para {current_year}",
                                  labels={f"Previsão {current_year} (%)": "Previsão de Rentabilidade Anualizada (%)"},
                                  color=f"Previsão {current_year} (%)",
                                  color_continuous_scale=px.colors.sequential.Viridis)
        fig_current_year.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_current_year, use_container_width=True)

        st.markdown("--- ")
        st.markdown("### Destaques do Mercado")
        for manchete in self.TODAY_NEWS_DATA["manchetes"]:
            st.info(manchete)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Ibovespa", self.TODAY_NEWS_DATA["indices"]["Ibovespa"])
        with col2:
            st.metric("Dólar (USD/BRL)", self.TODAY_NEWS_DATA["indices"]["Dólar (USD/BRL)"])
        with col3:
            st.metric("IPCA (últimos 12 meses)", self.TODAY_NEWS_DATA["indices"]["IPCA"])

        st.markdown("#### Renda Fixa")
        for destaque in self.TODAY_NEWS_DATA["destaques_renda_fixa"]:
            st.success(destaque)

        st.markdown("#### Renda Variável")
        for destaque in self.TODAY_NEWS_DATA["destaques_renda_variavel"]:
            st.success(destaque)

    def aba_ranking_inteligente(self):
        st.subheader("Ranking Inteligente de Ações de Dividendos")
        
        if not self.perfil_usuario or self.perfil_usuario.valor_disponivel == 0:
            st.warning("Por favor, complete seu perfil e informe o 'Valor Disponível para Investimento' na aba 'Meu Perfil' para usar o Ranking Inteligente.")
            return

        # Filtrar tickers com base nos setores preferidos do usuário
        tickers_para_analise = LISTA_TICKERS_IBOV
        if self.perfil_usuario.setores_preferidos and 'Todos' not in self.perfil_usuario.setores_preferidos:
            # Esta lógica precisaria de um mapeamento de ticker para setor, que não temos no MVP
            # Por enquanto, vamos manter todos os tickers e adicionar um aviso
            st.info("A filtragem por setores preferidos ainda não está totalmente implementada no MVP. Exibindo todos os tickers do Ibovespa.")

        with st.spinner("Analisando o mercado e gerando recomendações..."):
            recomendacoes = self.invest_agent.recomendar_ativos(tickers_para_analise, limite=20)

        if recomendacoes:
            st.success("Análise concluída! Aqui estão as recomendações personalizadas para você:")
            
            df_recomendacoes = pd.DataFrame([
                {
                    "Ticker": rec.ticker,
                    "Empresa": rec.nome_empresa,
                    "Setor": rec.setor,
                    "Preço Atual": f"R$ {rec.preco_atual:.2f}",
                    "DY (%)": f"{rec.dy:.2%}",
                    "P/L": f"{rec.pl:.2f}",
                    "P/VP": f"{rec.pvp:.2f}",
                    "ROE (%)": f"{rec.roe:.2%}",
                    "Score": f"{rec.score:.2f}",
                    "Risco": rec.risco_nivel.capitalize(),
                    "Super Investimento": "Sim" if rec.super_investimento else "Não"
                }
                for rec in recomendacoes
            ])
            st.dataframe(df_recomendacoes, use_container_width=True)

            # Gráfico de barras para o Score
            fig_score = px.bar(df_recomendacoes.sort_values(by="Score", ascending=False), x="Empresa", y="Score",
                               title="Score dos Ativos Recomendados",
                               labels={"Score": "Score de Recomendação"},
                               color="Score",
                               color_continuous_scale=px.colors.sequential.Plasma)
            fig_score.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_score, use_container_width=True)

            # Gráfico de pizza para distribuição por Risco
            df_risco = df_recomendacoes["Risco"].value_counts().reset_index()
            df_risco.columns = ["Nível de Risco", "Contagem"]
            fig_risco = px.pie(df_risco, values="Contagem", names="Nível de Risco",
                               title="Distribuição dos Ativos por Nível de Risco",
                               color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_risco, use_container_width=True)

            st.markdown("--- ")
            st.subheader("Detalhes e Explicações")
            
            for i, rec in enumerate(recomendacoes):
                with st.expander(f"**{rec.nome_empresa} ({rec.ticker}) - Score: {rec.score:.2f}**"):
                    st.write(f"**Setor:** {rec.setor}")
                    st.write(f"**Preço Atual:** R$ {rec.preco_atual:.2f}")
                    st.write(f"**Dividend Yield (DY):** {rec.dy:.2%}")
                    st.write(f"**P/L:** {rec.pl:.2f}")
                    st.write(f"**P/VP:** {rec.pvp:.2f}")
                    st.write(f"**ROE:** {rec.roe:.2%}")
                    st.write(f"**Risco:** {rec.risco_nivel.capitalize()}")
                    if rec.alerta_dy:
                        st.markdown(rec.alerta_dy, unsafe_allow_html=True)
                    
                    st.markdown(self.xai_agent.explicar_score(rec))
                    
                    # Gráfico de histórico de preços
                    if rec.historico is not None and not rec.historico.empty:
                        fig = px.line(rec.historico, x=rec.historico.index, y=rec.historico.values, title=f"Histórico de Preços de {rec.nome_empresa}")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Histórico de preços não disponível para este ativo.")

        else:
            st.warning("Não foi possível gerar recomendações no momento. Tente novamente mais tarde.")

    def aba_simulador_investimento(self):
        st.subheader("Simulador de Investimentos")

        if not self.perfil_usuario or self.perfil_usuario.valor_disponivel == 0:
            st.warning("Por favor, complete seu perfil e informe o 'Valor Disponível para Investimento' na aba 'Meu Perfil' para usar o Simulador de Investimentos.")
            return

        st.info(f"Seu valor disponível para investimento: R$ {self.perfil_usuario.valor_disponivel:,.2f}")

        num_ativos = st.slider("Quantos ativos você deseja simular?", 1, 5, 1)

        tickers_simulacao = []
        valores_simulacao = []

        for i in range(num_ativos):
            st.markdown(f"#### Ativo {i+1}")
            col1, col2 = st.columns(2)
            with col1:
                ticker = st.text_input(f"Ticker do Ativo {i+1} (ex: BBAS3.SA)", key=f"ticker_{i}").upper()
            with col2:
                valor = st.number_input(f"Valor a Alocar (R$)", min_value=0.0, value=0.0, key=f"valor_{i}", format="%.2f")
            
            if ticker and valor > 0:
                tickers_simulacao.append(ticker)
                valores_simulacao.append(valor)

        if st.button("Simular Carteira"):
            if not tickers_simulacao:
                st.warning("Por favor, adicione pelo menos um ativo para simular.")
                return
            
            with st.spinner("Calculando simulação..."):
                analise_carteira = self.finance_agent.analisar_carteira(tickers_simulacao, valores_simulacao)

            if analise_carteira["analises"]:
                st.success("Simulação concluída!")
                st.markdown(f"### Resumo da Carteira Simulada")
                st.write(f"**Valor Total Alocado:** R$ {analise_carteira["valor_total"]:,.2f}")
                st.write(f"**Renda Anual Estimada (Dividendos):** R$ {analise_carteira["renda_total_anual"]:,.2f}")
                st.write(f"**Dividend Yield da Carteira:** {analise_carteira["yield_carteira"]:.2%}")
                st.write(f"**Diversificação (Setores):** {analise_carteira["diversificacao"]} setores")

                st.markdown("#### Detalhes por Ativo")
                df_simulacao = pd.DataFrame([
                    {
                        "Ticker": item["analise"].ticker,
                        "Empresa": item["analise"].nome_empresa,
                        "Setor": item["analise"].setor,
                        "Valor Alocado": f"R$ {item["valor_alocado"]:,.2f}",
                        "Qtd. Ações": item["qtd_acoes"],
                        "Preço Médio": f"R$ {item["analise"].preco_atual:.2f}",
                        "Renda Anual (DY)": f"R$ {item["renda_anual"]:,.2f}",
                        "Peso na Carteira": f"{item["peso_carteira"]:.2%}"
                    }
                    for item in analise_carteira["analises"]
                ])
                st.dataframe(df_simulacao, use_container_width=True)

                st.markdown("--- ")
                st.subheader("Gráfico de Renda Anual Estimada por Ativo")
                fig_renda_anual = px.bar(df_simulacao, x="Ticker", y="Renda Anual (DY)",
                                        title="Renda Anual Estimada por Ativo",
                                        labels={"Renda Anual (DY)": "Renda Anual (R$)"},
                                        color="Renda Anual (DY)",
                                        color_continuous_scale=px.colors.sequential.Greens)
                fig_renda_anual.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_renda_anual, use_container_width=True)

                st.subheader("Gráfico de Alocação por Ativo")
                fig_alocacao = px.pie(df_simulacao, values="Valor Alocado", names="Ticker", title="Alocação da Carteira por Ativo")
                st.plotly_chart(fig_alocacao, use_container_width=True)

                st.subheader("Gráfico de Alocação por Setor")
                df_setor = df_simulacao.groupby("Setor")["Valor Alocado"].sum().reset_index()
                fig_setor = px.pie(df_setor, values="Valor Alocado", names="Setor", title="Alocação da Carteira por Setor")
                st.plotly_chart(fig_setor, use_container_width=True)

            else:
                st.warning("Não foi possível simular a carteira com os ativos fornecidos. Verifique os tickers e valores.")

    def aba_historico_interacoes(self):
        st.subheader("Histórico de Interações com a Rendy AI")
        if self.historico_interacoes:
            for i, interacao in enumerate(reversed(self.historico_interacoes)):
                st.markdown(f"**Data:** {interacao["data"]}")
                st.markdown(f"**Tipo:** {interacao["tipo"]}")
                st.markdown(f"**Detalhes:** {interacao["detalhes"]}")
                st.markdown("--- ")
        else:
            st.info("Nenhuma interação registrada ainda.")

    def run(self):
        inicializar_ambiente()

        if "perfil_carregado" not in st.session_state:
            st.session_state.perfil_carregado = False

        if not st.session_state.perfil_carregado:
            self.perfil_usuario = carregar_perfil_usuario()
            if self.perfil_usuario:
                st.session_state.perfil_carregado = True
            else:
                self.exibir_tela_cadastro()
                return

        self.invest_agent.definir_perfil(self.perfil_usuario)

        with st.sidebar:
            st.image("https://www.rendy.com.br/logo.png", width=150) # Substituir por logo real
            st.title("Rendy AI")
            st.write(f"Bem-vindo, {self.perfil_usuario.nome}!")
            
            menu_options = ["Início", "Ranking Inteligente", "Simulador de Investimentos", "Histórico de Interações", "Meu Perfil"]
            choice = st.radio("Navegação", menu_options)

            st.markdown("--- ")
            if st.button("Atualizar Perfil"):
                st.session_state.perfil_carregado = False
                st.rerun()
            if st.button("Sair / Trocar Usuário"):
                if os.path.exists(USUARIO_JSON):
                    os.remove(USUARIO_JSON)
                st.session_state.perfil_carregado = False
                st.rerun()

        if choice == "Início":
            self.aba_inicio()
        elif choice == "Ranking Inteligente":
            self.aba_ranking_inteligente()
        elif choice == "Simulador de Investimentos":
            self.aba_simulador_investimento()
        elif choice == "Histórico de Interações":
            self.aba_historico_interacoes()
        elif choice == "Meu Perfil":
            self.exibir_tela_cadastro()


if __name__ == "__main__":
    orchestrator = RendyOrchestrator()
    orchestrator.run()


