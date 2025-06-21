V3

# Rendy AI - Assistente de Investimentos 🤖

Uma aplicação Streamlit para análise de investimentos em ações brasileiras com foco em dividendos e renda passiva.

## 📋 Funcionalidades

- **Análise de Ações**: Avaliação completa de ativos com score proprietário
- **Simulação de Investimentos**: Calcule o potencial de retorno dos seus investimentos
- **Montagem de Carteira**: Monte e gerencie sua carteira de investimentos
- **Comparação de Ativos**: Compare diferentes ações lado a lado
- **Alocação de Recursos**: Defina como distribuir seu capital
- **Histórico de Preços**: Visualize o desempenho das ações no último ano

## 🚀 Como Executar Localmente

### Pré-requisitos
- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/rendy-ai.git
cd rendy-ai
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

### Passo 1: Preparar o Repositório GitHub

1. Crie um novo repositório no GitHub
2. Faça upload dos seguintes arquivos:
   - `app.py` (código principal)
   - `requirements.txt` (dependências)
   - `README.md` (este arquivo)

### Passo 2: Deploy no Streamlit Cloud

1. Acesse [share.streamlit.io](https://share.streamlit.io)
2. Faça login com sua conta GitHub
3. Clique em "New app"
4. Selecione seu repositório GitHub
5. Configure:
   - **Branch**: `main` (ou `master`)
   - **Main file path**: `app.py`
   - **App URL**: escolha uma URL personalizada
6. Clique em "Deploy!"

### Passo 3: Configurações Avançadas (Opcional)

Se necessário, você pode criar um arquivo `.streamlit/config.toml` para configurações específicas:

```toml
[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"

[server]
maxUploadSize = 1028
```

## 📁 Estrutura do Projeto

```
rendy-ai/
├── app.py                 # Aplicação principal
├── requirements.txt       # Dependências Python
├── README.md             # Documentação
├── data/                 # Dados do usuário (criado automaticamente)
│   └── usuario.json      # Perfil e carteira do usuário
└── .streamlit/           # Configurações do Streamlit (opcional)
    └── config.toml
```

## 🔧 Principais Correções Realizadas

### Problemas Corrigidos:
1. **Formatação de Código**: Corrigida indentação e estrutura
2. **Tratamento de Erros**: Adicionado try/catch adequado
3. **Validação de Dados**: Validação de email e dados de entrada
4. **Cache do Streamlit**: Corrigido uso do `@st.cache_data`
5. **Inicialização de Sessão**: Melhorada a inicialização das variáveis
6. **Preços de Ações**: Tratamento quando preço não está disponível na API
7. **Divisão por Zero**: Prevenção de erros matemáticos
8. **Gerenciamento de Estado**: Melhor controle do estado da aplicação

### Melhorias Implementadas:
1. **Documentação**: Comentários e docstrings adicionados
2. **Validação de Email**: Regex para validar formato de email
3. **Tratamento de Exceções**: Logs detalhados para debugging
4. **Responsividade**: Layout otimizado para diferentes telas
5. **Performance**: Cache implementado para análises financeiras

## 📈 Métricas Utilizadas

- **Score Rendy AI**: Pontuação proprietária (0-10) baseada em DY, ROE, P/L e P/VP
- **Dividend Yield (DY