# Dashboard Gerencial de Vendas

Este é um dashboard interativo para análise de dados de vendas, desenvolvido com Streamlit, Pandas e Plotly.

## Funcionalidades

- Análise de dados de vendas com métricas-chave (total de vendas, ticket médio, etc.)
- Visualização da evolução mensal de vendas
- Análise por dia da semana e hora do dia
- Análise de desempenho por vendedor
- Calendário de vendas mensal com visualização detalhada
- Simulação de modelos de comissionamento
- Detecção automática de arquivos Excel na pasta do projeto

## Requisitos

- Python 3.7+
- Streamlit
- Pandas
- Numpy
- Plotly
- Outros pacotes especificados em requirements.txt

## Instalação

1. Clone este repositório ou baixe os arquivos para sua máquina local.

2. Instale as dependências necessárias:

```bash
pip install -r requirements.txt
```

## Execução Simplificada

### Windows
1. Clique duas vezes no arquivo `dashboard.bat`
   
   OU
   
2. Execute via linha de comando:
```bash
python run_dashboard.py
```

### Linux/Mac
1. Torne o script executável:
```bash
chmod +x dashboard.sh
```

2. Execute o script:
```bash
./dashboard.sh
```

   OU
   
3. Execute diretamente com Python:
```bash
python3 run_dashboard.py
```

### Execução Manual via Streamlit
Você também pode executar o dashboard diretamente com o Streamlit:

```bash
streamlit run insight.py
```

## Estrutura de Arquivos

- `insight.py`: Código principal do dashboard
- `run_dashboard.py`: Script Python para execução simplificada
- `dashboard.bat`: Script batch para Windows
- `dashboard.sh`: Script shell para Linux/Mac
- `config.py`: Arquivo de configuração do dashboard
- `requirements.txt`: Lista de dependências
- `dados/`: Pasta para armazenar os arquivos de dados (Excel)

## Uso

1. Ao iniciar o dashboard, ele automaticamente procurará por arquivos Excel (.xlsx, .xls) na pasta do projeto.
2. Selecione um arquivo local ou faça upload de um novo arquivo.
3. Os dados serão carregados e você poderá explorar as diferentes análises nas abas disponíveis.
4. Use os filtros na barra lateral para personalizar a análise conforme necessário.

## Configuração

Você pode personalizar configurações no arquivo `config.py`, incluindo:

- Porta do servidor
- Tema (claro/escuro)
- Pastas de busca de arquivos
- Outras opções de layout e comportamento