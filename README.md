# Rendy AI - Assistente de Investimentos 🤖

Uma aplicação Streamlit para análise de investimentos em ações brasileiras com foco em dividendos e renda passiva.

## 📋 Funcionalidades

- **Análise de Ações**: Avaliação completa de ativos com score proprietário e explicação automática do motivo do score (XAI)
- **Simulação de Investimentos**: Calcule o potencial de retorno dos seus investimentos com explicação didática dos resultados
- **Montagem de Carteira**: Monte e gerencie sua carteira de investimentos
- **Comparação de Ativos**: Compare diferentes ações lado a lado
- **Alocação de Recursos**: Defina como distribuir seu capital
- **Histórico de Preços**: Visualize o desempenho das ações no último ano
- **Privacidade Total**: Dados permanecem apenas no seu dispositivo
- **Logout/Limpar dados**: Apague seus dados a qualquer momento

## 🚀 Como Executar Localmente

### Pré-requisitos
- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### Instalação

1. Clone o repositório:
    ```bash
    git clone https://github.com/MarckDigital/RendyAi-App.git
    cd RendyAi-App
    ```

2. Crie um ambiente virtual (recomendado):
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    # ou
    venv\Scripts\activate  # Windows
    ```

3. Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```

4. Execute a aplicação:
    ```bash
    streamlit run app.py
    ```

5. Acesse a aplicação em: `http://localhost:8501`

## 📊 Como Usar

1. **Login/Cadastro**: Insira seu nome e email para acessar o dashboard
2. **Simulação**: Selecione uma ação e valor para simular o investimento
3. **Adicionar à Carteira**: Adicione ações interessantes à sua carteira
4. **Definir Alocação**: Distribua seu capital entre as ações escolhidas
5. **Salvar Plano**: Confirme e salve seu plano de investimentos

## 🌐 Publicação no Streamlit Cloud

Siga as etapas detalhadas no modelo anterior. Use `app.py` como arquivo principal.

## 📁 Estrutura do Projeto

```
RendyAi-App/
├── app.py                 # Aplicação principal
├── requirements.txt       # Dependências Python
├── README.md              # Documentação
├── data/                  # Dados do usuário (criado automaticamente)
│   └── usuario.json       # Perfil e carteira do usuário
└── .streamlit/            # Configurações do Streamlit (opcional)
    └── config.toml
```

## 🔒 Política de Privacidade

- Nenhum dado pessoal é enviado a servidores externos ou terceiros.
- Todos os dados são armazenados apenas localmente no seu dispositivo.
- Você pode apagar todos os dados salvos a qualquer momento pelo menu.
- Dúvidas? Abra uma issue no repositório.

## 🛣️ Roadmap (Próximas Entregas)

- [ ] Perfis de usuário (iniciante, avançado, etc.) para personalizar recomendações
- [ ] Simulações contrafactuais ("E se o DY cair 10%?")
- [ ] Modularização para agentes especializados (perfil, fundamentalista, XAI, etc)
- [ ] Feedback contínuo do usuário para ajuste de recomendações
- [ ] Onboarding dinâmico por perfil
- [ ] Explicação visual avançada das decisões (XAI visual)
- [ ] Exportação/backup de dados

## 📈 Métricas Utilizadas

- **Score Rendy AI**: Pontuação proprietária (0-10) baseada em DY, ROE, P/L e P/VP
- **Dividend Yield (DY)**: Percentual de dividendos anualizado
- **P/L**: Preço/lucro
- **P/VP**: Preço/valor patrimonial
- **ROE**: Retorno sobre patrimônio líquido

## 👩‍💻 Contribua

Sinta-se livre para abrir issues, sugerir melhorias ou enviar pull requests!


