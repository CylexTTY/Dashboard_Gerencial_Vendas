import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import calendar
from datetime import datetime, timedelta, time
import os
import locale
import re
from pathlib import Path
import warnings
import io
import base64

# Tentar importar o arquivo de configuração
try:
    from config import CONFIG, DEFAULT_FILE_PATH
except ImportError:
    # Configurações padrão caso o arquivo config.py não exista
    CONFIG = {
        "app_name": "Dashboard Gerencial de Vendas",
        "app_icon": "📊",
        "layout": "wide",
        "sidebar_state": "expanded",
        "data_folder": "dados",
        "default_filename": "Relatorio.xlsx",
        "allowed_extensions": [".xlsx", ".xls"]
    }
    
    # Criar pasta de dados se não existir
    if not os.path.exists(CONFIG["data_folder"]):
        os.makedirs(CONFIG["data_folder"])
    
    DEFAULT_FILE_PATH = os.path.join(CONFIG["data_folder"], CONFIG["default_filename"])

# Configuração da página - IMPORTANTE: deve ser a primeira chamada Streamlit no script
st.set_page_config(
    page_title=CONFIG["app_name"],
    page_icon=CONFIG["app_icon"],
    layout=CONFIG["layout"],
    initial_sidebar_state=CONFIG["sidebar_state"]
)

# Ignorar avisos
warnings.filterwarnings('ignore')

# Configurar o locale para formatação de números em português
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        pass  # Se falhar, usaremos formatação manual

# Adicionar CSS personalizado para garantir responsividade
st.markdown("""
    <style>
    /* Ajuste responsivo para telas menores */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
            padding-top: 1rem;
        }
        
        div[data-testid="stMetric"] {
            padding: 5px !important;
        }
        
        div[data-testid="stMetricValue"] {
            font-size: 1rem !important;
        }
        
        div[data-testid="stMetricLabel"] {
            font-size: 0.8rem !important;
        }
    }
    
        /* Estilo para o calendário sem barra de rolagem */
    .calendario-container {
        overflow: visible !important;
        width: 100%;
        padding: 0 !important;
        margin-top: 10px;
        margin-bottom: 20px;
    }

    .calendario {
        width: 100%;
        table-layout: fixed;
        border-collapse: collapse;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        background-color: white;
    }

    .calendario th {
        background-color: #4CAF50;
        color: white;
        text-align: center;
        font-size: 0.9rem;
        padding: 8px 4px;
        font-weight: bold;
    }

    .calendario td {
        border: 1px solid #e0e0e0;
        padding: 8px 4px;
        text-align: center;
        position: relative;
        height: 70px;
        vertical-align: top;
        transition: all 0.2s ease;
        background-color: white;
    }

    .calendario td:hover {
        box-shadow: inset 0 0 0 2px #4CAF50;
    }

    .calendario td.vazio {
        background-color: #f5f5f5;
        color: #ccc;
    }

    .dia-num {
        font-weight: bold;
        font-size: 0.9rem;
        display: block;
        margin-bottom: 4px;
        color: #333;
    }

    .valor {
        font-weight: bold;
        color: #0366d6;
        font-size: 0.85rem;
        display: block;
        margin-bottom: 4px;
    }

    .qtd {
        font-size: 0.75rem;
        color: #666;
        display: block;
    }

    /* Fundo colorido para destacar fins de semana */
    .calendario td.sabado {
        background-color: #f0f8ff;
    }

    .calendario td.domingo {
        background-color: #fff0f0;
    }

    /* Melhorias para hoje */
    .calendario td.hoje {
        border: 2px solid #4CAF50;
    }

    .hoje .dia-num {
        color: #4CAF50;
    }

    /* Ajustes responsivos */
    @media (max-width: 768px) {
        .calendario td {
            height: 60px;
            padding: 4px 2px;
        }
        
        .dia-num {
            font-size: 0.8rem;
            margin-bottom: 2px;
        }
        
        .valor {
            font-size: 0.7rem;
            margin-bottom: 2px;
        }
        
        .qtd {
            font-size: 0.6rem;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Função para formatar valores em reais
def formatar_real(valor):
    if pd.isna(valor):
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Função para formatar percentuais
def formatar_percentual(valor):
    if pd.isna(valor):
        return "0,00%"
    return f"{valor:.2f}%".replace(".", ",")

# Função para converter valores no formato brasileiro para float
def converter_valor_br_para_float(valor_str):
    """
    Converte um valor no formato brasileiro (1.234,56) para float (1234.56).
    Função robusta que lida com diferentes formatos de entrada.
    """
    # Retorna NaN para valores nulos
    if valor_str is None or pd.isna(valor_str):
        return np.nan
    
    # Se já for um número, retorna como está
    if isinstance(valor_str, (int, float)):
        return float(valor_str)
    
    # Garantir que seja uma string e remover espaços
    valor_str = str(valor_str).strip()
    
    # Remover símbolos de moeda e espaços
    valor_str = re.sub(r'[R$€£$]', '', valor_str).strip()
    
    # Se estiver vazio, retorna NaN
    if not valor_str:
        return np.nan
    
    try:
        if '.' in valor_str and ',' in valor_str:
            # Verificar qual vem primeiro
            primeiro_ponto = valor_str.find('.')
            primeira_virgula = valor_str.find(',')
            
            if primeiro_ponto < primeira_virgula:
                # Formato brasileiro: 1.234,56
                valor_str = valor_str.replace('.', '').replace(',', '.')
            else:
                # Formato americano: 1,234.56
                valor_str = valor_str.replace(',', '')
        elif ',' in valor_str:
            # Verificar se a vírgula está sendo usada como decimal
            posicao_virgula = valor_str.find(',')
            
            # Se a vírgula estiver a menos de 3 caracteres do final, é provavelmente decimal
            if len(valor_str) - posicao_virgula <= 3:
                valor_str = valor_str.replace(',', '.')
            else:
                # Vírgula como separador de milhares
                valor_str = valor_str.replace(',', '')
    
        return float(valor_str)
    except ValueError:
        # Se falhar na conversão, tentar remover caracteres não numéricos
        valor_limpo = re.sub(r'[^\d.,]', '', valor_str)
        
        try:
            # Se ainda tiver vírgula, assumir que é decimal
            if ',' in valor_limpo:
                valor_limpo = valor_limpo.replace(',', '.')
            
            # Remover todos os pontos exceto o último (assumindo que é decimal)
            if valor_limpo.count('.') > 1:
                ultimo_ponto = valor_limpo.rfind('.')
                valor_limpo = valor_limpo.replace('.', '')
                valor_limpo = valor_limpo[:ultimo_ponto] + '.' + valor_limpo[ultimo_ponto:]
            
            return float(valor_limpo)
        except ValueError:
            return np.nan

# Função para limpar nomes de colunas
def limpar_nome_coluna(nome):
    return re.sub(r'\s+', '_', nome).lower().strip()

# Função segura para converter para inteiro
def safe_int(x, default=0):
    """Converte para inteiro de forma segura, lidando com NaN e inf"""
    if pd.isna(x) or np.isinf(x):
        return default
    try:
        return int(x)
    except:
        return default

# Função para preparar o tema de cores para os gráficos
def obter_paleta_cores(n_cores=10):
    """
    Retorna uma paleta de cores harmoniosa para os gráficos.
    Baseada nas recomendações do livro 'Storytelling com Dados'.
    """
    # Cores base (azuis, verdes, laranjas - evitando vermelhos excessivos)
    cores_base = [
        '#4e79a7', '#59a14f', '#f28e2c', '#76b7b2', '#edc949',
        '#af7aa1', '#ff9da7', '#9c755f', '#bab0ab', '#3c6e8c'
    ]
    
    # Se precisar de mais cores, gerar cores semelhantes
    if n_cores <= len(cores_base):
        return cores_base[:n_cores]
    else:
        return cores_base + px.colors.qualitative.Pastel[:n_cores-len(cores_base)]

# Função para carregar e processar os dados
@st.cache_data
def carregar_dados(file):
    try:
        # Verificar se o arquivo é uma string (caminho do arquivo) ou objeto UploadedFile
        if isinstance(file, str):
            # É um caminho de arquivo
            df = pd.read_excel(file)
        else:
            # É um objeto de arquivo carregado
            df = pd.read_excel(file)
        
        # Processando nomes das colunas
        df.columns = [limpar_nome_coluna(col) for col in df.columns]
        
        # Identificar colunas relevantes
        colunas_data = [col for col in df.columns if "dt" in col.lower() or "data" in col.lower()]
        colunas_valor = [col for col in df.columns if "vl" in col.lower() or "valor" in col.lower() or "total" in col.lower()]
        colunas_vendedor = [col for col in df.columns if "vendedor" in col.lower() or "atendente" in col.lower() or "balconista" in col.lower()]
        
        # Verificar se encontramos as colunas necessárias
        if not colunas_data:
            st.error("Não foi possível identificar a coluna de data no arquivo")
            return None
        
        if not colunas_valor:
            st.error("Não foi possível identificar a coluna de valor no arquivo")
            return None
        
        # Selecionar as primeiras colunas identificadas
        coluna_data = colunas_data[0]
        coluna_valor = colunas_valor[0]
        coluna_vendedor = colunas_vendedor[0] if colunas_vendedor else None
        
        # Converter coluna de data para datetime
        df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
        
        # Remover linhas com datas inválidas
        df_valido = df.dropna(subset=[coluna_data]).copy()
        
        # Converter coluna de valor para numérico
        df_valido[coluna_valor] = df_valido[coluna_valor].apply(converter_valor_br_para_float)
        
        # Adicionar colunas úteis para análise de forma segura
        df_valido['data'] = df_valido[coluna_data].dt.date
        
        # Usar método seguro para extrair componentes de data
        df_valido['mes'] = df_valido[coluna_data].dt.month.apply(safe_int, default=1)
        df_valido['ano'] = df_valido[coluna_data].dt.year.apply(safe_int, default=2000)
        df_valido['dia_mes'] = df_valido[coluna_data].dt.day.apply(safe_int, default=1)
        df_valido['hora'] = df_valido[coluna_data].dt.hour.apply(safe_int, default=0)
        df_valido['dia_semana_num'] = df_valido[coluna_data].dt.weekday.apply(safe_int, default=0)  # 0 = segunda, 6 = domingo
        
        # Calcular semana do mês de forma segura
        df_valido['semana_mes'] = df_valido['dia_mes'].apply(lambda x: ((x - 1) // 7 + 1) if x > 0 else 1)
        
        # Formatar strings de data de forma segura
        df_valido['mes_ano'] = df_valido.apply(
            lambda row: f"{row['mes']:02d}/{row['ano']}" if pd.notna(row['mes']) and pd.notna(row['ano']) else "00/0000",
            axis=1
        )
        df_valido['mes_ano_ordem'] = df_valido.apply(
            lambda row: f"{row['ano']}-{row['mes']:02d}" if pd.notna(row['mes']) and pd.notna(row['ano']) else "0000-00",
            axis=1
        )
        
        # Extrair dia da semana de forma segura
        df_valido['dia_semana'] = df_valido[coluna_data].dt.day_name()
        
        # Traduzir nomes dos dias da semana
        dias_traduzidos = {
            'Monday': 'Segunda-feira',
            'Tuesday': 'Terça-feira',
            'Wednesday': 'Quarta-feira',
            'Thursday': 'Quinta-feira',
            'Friday': 'Sexta-feira',
            'Saturday': 'Sábado',
            'Sunday': 'Domingo'
        }
        df_valido['dia_semana_pt'] = df_valido['dia_semana'].map(dias_traduzidos)
        
        # Traduzir nomes dos meses
        meses_traduzidos = {
            1: 'Janeiro',
            2: 'Fevereiro',
            3: 'Março',
            4: 'Abril',
            5: 'Maio',
            6: 'Junho',
            7: 'Julho',
            8: 'Agosto',
            9: 'Setembro',
            10: 'Outubro',
            11: 'Novembro',
            12: 'Dezembro'
        }
        df_valido['mes_pt'] = df_valido['mes'].map(meses_traduzidos)
        
        # Adicionar flag para horário comercial 
        # Segunda a sexta: 8h às 19h, Sábado: 8h às 17h
        def esta_em_horario_comercial(row):
            # Se for domingo (6), não é horário comercial
            if row['dia_semana_num'] == 6:
                return False
            
            hora = row['hora']
            # Se for sábado (5)
            if row['dia_semana_num'] == 5:
                return 8 <= hora < 17
            else:
                # Segunda a sexta
                return 8 <= hora < 19
        
        df_valido['horario_comercial'] = df_valido.apply(esta_em_horario_comercial, axis=1)
        
        # Determinar total geral para referência
        total_geral = df_valido[coluna_valor].sum()
        
        # Verificar se o total está correto (debugando)
        st.info(f"Arquivo carregado com sucesso. De {len(df)} registros, {len(df_valido)} têm datas válidas, totalizando {formatar_real(total_geral)}.")
        
        return {
            'df': df_valido,
            'coluna_data': coluna_data,
            'coluna_valor': coluna_valor,
            'coluna_vendedor': coluna_vendedor,
            'total_geral': total_geral
        }
    
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# Função para aplicar filtros
def aplicar_filtros(df, periodo, vendedores_selecionados, coluna_vendedor, apenas_horario_comercial=True):
    df_filtrado = df.copy()
    
    # Filtrar por período
    data_inicio, data_fim = periodo
    df_filtrado = df_filtrado[(df_filtrado['data'] >= data_inicio) & (df_filtrado['data'] <= data_fim)]
    
    # Filtrar por vendedor (se especificado)
    if coluna_vendedor and vendedores_selecionados and "Todos" not in vendedores_selecionados:
        df_filtrado = df_filtrado[df_filtrado[coluna_vendedor].isin(vendedores_selecionados)]
    
    # Filtrar apenas por horário comercial, se solicitado
    if apenas_horario_comercial:
        df_filtrado = df_filtrado[df_filtrado['horario_comercial'] == True]
    
    return df_filtrado

# Função para gerar métricas e indicadores
def gerar_metricas(df, coluna_valor, periodo_anterior=None):
    total_vendas = df[coluna_valor].sum()
    qtd_vendas = len(df)
    ticket_medio = total_vendas / qtd_vendas if qtd_vendas > 0 else 0
    
    # Calcular venda média por dia
    dias_unicos = df['data'].nunique()
    venda_media_diaria = total_vendas / dias_unicos if dias_unicos > 0 else 0
    
    # Calcular venda média por dia útil (excluindo domingos)
    dias_uteis = df[df['dia_semana_num'] != 6]['data'].nunique()
    venda_media_dia_util = total_vendas / dias_uteis if dias_uteis > 0 else 0
    
    # Calcular variação em relação ao período anterior (se fornecido)
    variacao_total = None
    variacao_ticket = None
    variacao_qtd = None
    
    if periodo_anterior is not None:
        total_anterior = periodo_anterior[coluna_valor].sum()
        if total_anterior > 0:
            variacao_total = ((total_vendas / total_anterior) - 1) * 100
        
        qtd_anterior = len(periodo_anterior)
        if qtd_anterior > 0:
            variacao_qtd = ((qtd_vendas / qtd_anterior) - 1) * 100
            
            ticket_anterior = total_anterior / qtd_anterior
            if ticket_anterior > 0:
                variacao_ticket = ((ticket_medio / ticket_anterior) - 1) * 100
    
    return {
        'total_vendas': total_vendas,
        'qtd_vendas': qtd_vendas,
        'ticket_medio': ticket_medio,
        'venda_media_diaria': venda_media_diaria,
        'venda_media_dia_util': venda_media_dia_util,
        'dias_unicos': dias_unicos,
        'dias_uteis': dias_uteis,
        'variacao_total': variacao_total,
        'variacao_ticket': variacao_ticket,
        'variacao_qtd': variacao_qtd
    }

# Função para calcular métricas mensais
def calcular_metricas_mensais(df, coluna_valor):
    # Agrupar vendas por mês
    vendas_mensais = df.groupby(['mes_ano_ordem', 'mes_ano']).agg({
        coluna_valor: ['sum', 'count', 'mean'],
        'mes': 'first',
        'ano': 'first',
        'data': 'nunique'
    }).reset_index()
    
    # Renomear colunas
    vendas_mensais.columns = ['mes_ano_ordem', 'mes_ano', 'total_vendas', 'qtd_vendas', 
                              'ticket_medio', 'mes', 'ano', 'dias_vendas']
    
    # Adicionar mês por extenso
    meses_traduzidos = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    vendas_mensais['mes_nome'] = vendas_mensais['mes'].map(meses_traduzidos)
    
    # Ordenar por mês
    vendas_mensais = vendas_mensais.sort_values('mes_ano_ordem')
    
    # Calcular média diária
    vendas_mensais['media_diaria'] = vendas_mensais['total_vendas'] / vendas_mensais['dias_vendas']
    
    # Calcular crescimento mês a mês
    vendas_mensais['crescimento_pct'] = vendas_mensais['total_vendas'].pct_change() * 100
    
    # Calcular crescimento de ticket médio
    vendas_mensais['crescimento_ticket_pct'] = vendas_mensais['ticket_medio'].pct_change() * 100
    
    # Calcular média móvel de 3 meses
    if len(vendas_mensais) >= 3:
        vendas_mensais['media_movel_3m'] = vendas_mensais['total_vendas'].rolling(window=3, min_periods=1).mean()
    
    # Preencher NaNs com 0 para o primeiro mês
    vendas_mensais['crescimento_pct'] = vendas_mensais['crescimento_pct'].fillna(0)
    vendas_mensais['crescimento_ticket_pct'] = vendas_mensais['crescimento_ticket_pct'].fillna(0)
    
    # Calcular participação percentual de cada mês
    total_geral = vendas_mensais['total_vendas'].sum()
    if total_geral > 0:
        vendas_mensais['participacao_pct'] = (vendas_mensais['total_vendas'] / total_geral) * 100
    else:
        vendas_mensais['participacao_pct'] = 0
    
    return vendas_mensais

# Função para calcular métricas por vendedor
def calcular_metricas_por_vendedor(df, coluna_valor, coluna_vendedor):
    if not coluna_vendedor or coluna_vendedor not in df.columns:
        return pd.DataFrame()
    
    # Agrupar vendas por vendedor
    vendas_por_vendedor = df.groupby(coluna_vendedor).agg({
        coluna_valor: ['sum', 'count', 'mean', 'max', 'min'],
        'data': 'nunique'
    }).reset_index()
    
    # Renomear colunas
    vendas_por_vendedor.columns = [coluna_vendedor, 'total_vendas', 'qtd_vendas', 
                                   'ticket_medio', 'maior_venda', 'menor_venda', 'dias_trabalhados']
    
    # Calcular média diária por vendedor
    vendas_por_vendedor['media_diaria'] = vendas_por_vendedor['total_vendas'] / vendas_por_vendedor['dias_trabalhados']
    
    # Calcular percentual de participação
    total_geral = vendas_por_vendedor['total_vendas'].sum()
    vendas_por_vendedor['participacao_pct'] = (vendas_por_vendedor['total_vendas'] / total_geral) * 100 if total_geral > 0 else 0
    
    # Ordenar por total de vendas (decrescente)
    vendas_por_vendedor = vendas_por_vendedor.sort_values('total_vendas', ascending=False)
    
    # Calcular métricas para análise de desempenho
    media_vendas = vendas_por_vendedor['total_vendas'].mean()
    vendas_por_vendedor['vs_media_pct'] = ((vendas_por_vendedor['total_vendas'] / media_vendas) - 1) * 100
    
    return vendas_por_vendedor

# Função para analisar desempenho por dias da semana
def analisar_dias_semana(df, coluna_valor):
    # Dias da semana em ordem
    ordem_dias = [
        'Segunda-feira', 'Terça-feira', 'Quarta-feira', 
        'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'
    ]
    
    # Agrupar por dia da semana
    df_dias = df.groupby('dia_semana_pt').agg({
        coluna_valor: ['sum', 'count', 'mean'],
        'data': 'nunique'
    }).reset_index()
    
    # Renomear colunas
    df_dias.columns = ['dia_semana', 'total_vendas', 'qtd_vendas', 'ticket_medio', 'dias_ocorrencia']
    
    # Ordenar dias da semana
    df_dias['ordem'] = df_dias['dia_semana'].map({dia: i for i, dia in enumerate(ordem_dias)})
    df_dias = df_dias.sort_values('ordem')
    
    # Calcular média por dia
    df_dias['media_por_dia'] = df_dias['total_vendas'] / df_dias['dias_ocorrencia']
    
    # Calcular percentual em relação ao total
    total_geral = df_dias['total_vendas'].sum()
    df_dias['percentual_total'] = (df_dias['total_vendas'] / total_geral) * 100 if total_geral > 0 else 0
    
    # Identificar melhor e pior dia
    melhor_dia = df_dias.loc[df_dias['media_por_dia'].idxmax()]
    pior_dia = df_dias.loc[df_dias['media_por_dia'].idxmin()]
    
    return {
        'df_dias': df_dias,
        'melhor_dia': melhor_dia,
        'pior_dia': pior_dia
    }

# Função para analisar desempenho por hora
def analisar_horas(df, coluna_valor):
    # Agrupar por hora
    df_horas = df.groupby('hora').agg({
        coluna_valor: ['sum', 'count', 'mean'],
        'data': 'nunique'
    }).reset_index()
    
    # Renomear colunas
    df_horas.columns = ['hora', 'total_vendas', 'qtd_vendas', 'ticket_medio', 'dias_ocorrencia']
    
    # Calcular média por hora por dia
    df_horas['media_por_dia'] = df_horas['total_vendas'] / df_horas['dias_ocorrencia']
    
    # Calcular percentual em relação ao total
    total_geral = df_horas['total_vendas'].sum()
    df_horas['percentual_total'] = (df_horas['total_vendas'] / total_geral) * 100 if total_geral > 0 else 0
    
    # Ordenar por hora
    df_horas = df_horas.sort_values('hora')
    
    # Identificar melhor e pior hora
    melhor_hora = df_horas.loc[df_horas['media_por_dia'].idxmax()]
    pior_hora = df_horas.loc[df_horas['media_por_dia'].idxmin()]
    
    # Calcular picos de horas (top 3)
    picos = df_horas.nlargest(3, 'media_por_dia')
    
    return {
        'df_horas': df_horas,
        'melhor_hora': melhor_hora,
        'pior_hora': pior_hora,
        'picos': picos
    }

# Função para criar um calendário de vendas
def calendario_vendas(df, coluna_valor, mes_selecionado=None, ano_selecionado=None):
    if not mes_selecionado or not ano_selecionado:
        # Usar o último mês disponível
        data_max = df['data'].max()
        if pd.notna(data_max):
            if isinstance(data_max, datetime):
                mes_selecionado = data_max.month
                ano_selecionado = data_max.year
            else:
                try:
                    data_obj = pd.to_datetime(data_max)
                    mes_selecionado = data_obj.month
                    ano_selecionado = data_obj.year
                except:
                    hoje = datetime.now()
                    mes_selecionado = hoje.month
                    ano_selecionado = hoje.year
        else:
            # Se não houver dados, usar o mês atual
            hoje = datetime.now()
            mes_selecionado = hoje.month
            ano_selecionado = hoje.year
    
    # Filtrar dados do mês selecionado
    df_mes = df[(df['mes'] == mes_selecionado) & (df['ano'] == ano_selecionado)]
    
    # Agrupar por dia do mês
    vendas_por_dia = df_mes.groupby('dia_mes').agg({
        coluna_valor: ['sum', 'count']
    }).reset_index()
    
    # Renomear colunas
    vendas_por_dia.columns = ['dia', 'total', 'qtd']
    
    # Criar dicionário para lookup rápido
    dict_vendas = {row['dia']: (row['total'], row['qtd']) for _, row in vendas_por_dia.iterrows()}
    
    # Obter número de dias no mês
    num_dias = calendar.monthrange(ano_selecionado, mes_selecionado)[1]
    
    # Obter o dia da semana do primeiro dia do mês (0 = segunda, 6 = domingo)
    primeiro_dia_semana = datetime(ano_selecionado, mes_selecionado, 1).weekday()
    
    # Criar matriz do calendário (6 semanas x 7 dias)
    calendario = []
    dia_atual = 1
    
    for semana in range(6):  # Máximo de 6 semanas em um mês
        linha = []
        for dia_semana in range(7):  # 7 dias na semana
            if (semana == 0 and dia_semana < primeiro_dia_semana) or (dia_atual > num_dias):
                # Célula vazia
                linha.append({"dia": "", "total": 0, "qtd": 0, "vazio": True})
            else:
                # Obter dados de vendas para este dia
                total, qtd = dict_vendas.get(dia_atual, (0, 0))
                linha.append({"dia": dia_atual, "total": total, "qtd": qtd, "vazio": False})
                dia_atual += 1
        calendario.append(linha)
    
    # Remover semanas vazias
    calendario = [semana for semana in calendario if any(not dia['vazio'] for dia in semana)]
    
    # Calcular o maior valor para normalização de cores
    max_valor = max([dia['total'] for semana in calendario for dia in semana if not dia['vazio'] and dia['total'] > 0], default=1)
    
    # Calcular o total mensal
    total_mes = sum([dia['total'] for semana in calendario for dia in semana if not dia['vazio']])
    qtd_mes = sum([dia['qtd'] for semana in calendario for dia in semana if not dia['vazio']])
    
    # Obter nome do mês
    nome_mes = calendar.month_name[mes_selecionado]
    
    return {
        'calendario': calendario,
        'max_valor': max_valor,
        'mes': nome_mes,
        'ano': ano_selecionado,
        'total_mes': total_mes,
        'qtd_mes': qtd_mes
    }

# Simulador de cenários de comissão
def simular_comissao(df_vendedores, modelo, parametros, df_mensal=None):
    """
    Simula diferentes modelos de comissionamento para os vendedores.
    
    Args:
        df_vendedores: DataFrame com métricas por vendedor
        modelo: Tipo de modelo de comissão ('fixo', 'progressivo', 'meta')
        parametros: Dicionário com parâmetros do modelo
        df_mensal: DataFrame com vendas mensais (para simulação mensal)
        
    Returns:
        DataFrame com simulação de comissões
    """
    # Copiar o dataframe para não modificar o original
    df_sim = df_vendedores.copy()
    coluna_vendedor = df_sim.columns[0]  # A primeira coluna deve ser o nome do vendedor
    
    # Parâmetros do modelo
    salario_base = parametros.get('salario_base', 3000)
    
    # Alocar salário base
    df_sim['salario_base'] = salario_base
    
    # Aplicar o modelo de comissão
    if modelo == "fixo":
        # Modelo de comissão fixa (percentual fixo sobre vendas)
        comissao_pct = parametros.get('comissao_pct', 1.0)
        df_sim['comissao_pct'] = comissao_pct
        df_sim['comissao_valor'] = df_sim['total_vendas'] * (comissao_pct / 100)
        df_sim['meta_atingida'] = None  # Não há meta neste modelo
        
    elif modelo == "meta":
        # Modelo com meta (comissão se atingir meta)
        comissao_pct = parametros.get('comissao_pct', 1.0)
        meta_tipo = parametros.get('meta_tipo', 'valor')  # 'valor' ou 'media'
        
        if meta_tipo == 'valor':
            meta_valor = parametros.get('meta_valor', 50000)
            df_sim['meta_atingida'] = df_sim['total_vendas'] >= meta_valor
            df_sim['meta_valor'] = meta_valor
        else:  # meta_tipo == 'media'
            meta_percentual = parametros.get('meta_percentual', 5.0)
            media_vendas = df_sim['total_vendas'].mean()
            meta_valor = media_vendas * (1 + meta_percentual / 100)
            df_sim['meta_atingida'] = df_sim['total_vendas'] >= meta_valor
            df_sim['meta_valor'] = meta_valor
        
        # Comissão apenas se atingir meta ou comissão base + bônus
        if parametros.get('apenas_com_meta', False):
            df_sim['comissao_pct'] = np.where(df_sim['meta_atingida'], comissao_pct, 0)
        else:
            # Comissão base + bônus se atingir meta
            bonus_pct = parametros.get('bonus_pct', 0.5)
            df_sim['comissao_pct'] = np.where(df_sim['meta_atingida'], comissao_pct + bonus_pct, comissao_pct)
        
        df_sim['comissao_valor'] = df_sim['total_vendas'] * (df_sim['comissao_pct'] / 100)
        
    elif modelo == "progressivo":
        # Modelo progressivo (faixas de comissão)
        faixas = parametros.get('faixas', [
            {'valor_min': 0, 'valor_max': 50000, 'comissao_pct': 0.5},
            {'valor_min': 50000, 'valor_max': 100000, 'comissao_pct': 1.0},
            {'valor_min': 100000, 'valor_max': float('inf'), 'comissao_pct': 1.5}
        ])
        
        # Determinar faixa para cada vendedor
        def calcular_comissao_progressiva(total_vendas):
            for faixa in faixas:
                if faixa['valor_min'] <= total_vendas < faixa['valor_max']:
                    return faixa['comissao_pct'], total_vendas * (faixa['comissao_pct'] / 100)
            return 0, 0
        
        resultados = df_sim['total_vendas'].apply(calcular_comissao_progressiva)
        df_sim['comissao_pct'] = [r[0] for r in resultados]
        df_sim['comissao_valor'] = [r[1] for r in resultados]
        df_sim['meta_atingida'] = None  # Não há meta neste modelo
    
    # Calcular salário total
    df_sim['salario_total'] = df_sim['salario_base'] + df_sim['comissao_valor']
    
    # Calcular impacto financeiro
    df_sim['impacto_percentual'] = (df_sim['comissao_valor'] / df_sim['total_vendas']) * 100
    
    # Se temos dados mensais, simular mês a mês
    df_mensal_sim = None
    if df_mensal is not None and not df_mensal.empty:
        # Simular para cada mês, usando o mesmo modelo
        resultados_mensais = []
        
        for mes in df_mensal['mes_ano'].unique():
            # Filtrar dados do mês
            df_mes = df_mensal[df_mensal['mes_ano'] == mes].copy()
            
            # Aplicar o mesmo modelo de comissão
            if modelo == 'fixo':
                df_mes['comissao_pct'] = comissao_pct
                df_mes['comissao_valor'] = df_mes['total_vendas'] * (comissao_pct / 100)
                df_mes['meta_atingida'] = None
            elif modelo == 'meta':
                # Implementar lógica de metas mensais aqui, se necessário
                pass
            elif modelo == 'progressivo':
                # Implementar lógica de faixas progressivas mensais aqui, se necessário
                pass
            
            # Adicionar mês e outras informações
            df_mes['salario_base'] = salario_base / len(df_mensal['mes_ano'].unique())  # Dividir pelo número de meses
            df_mes['modelo'] = modelo
            
            resultados_mensais.append(df_mes)
        
        if resultados_mensais:
            df_mensal_sim = pd.concat(resultados_mensais)
    
    return df_sim, df_mensal_sim

# Criar dashboards otimizados para cada seção
def dashboard_metricas_principais(metricas):
    """Exibe as métricas principais de forma responsiva"""
    # Usar duas linhas em dispositivos pequenos, uma linha em dispositivos grandes
    use_container_width = True
    
    # Primeira linha com total de vendas e quantidade
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Total de Vendas",
            formatar_real(metricas['total_vendas']),
            f"{metricas['variacao_total']:.1f}%" if metricas['variacao_total'] is not None else None,
            help="Valor total das vendas no período"
        )
    
    with col2:
        st.metric(
            "Quantidade de Vendas",
            f"{metricas['qtd_vendas']} pedidos",
            f"{metricas['variacao_qtd']:.1f}%" if metricas['variacao_qtd'] is not None else None,
            help="Número total de pedidos no período"
        )
    
    # Segunda linha com ticket médio e média diária
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Ticket Médio",
            formatar_real(metricas['ticket_medio']),
            f"{metricas['variacao_ticket']:.1f}%" if metricas['variacao_ticket'] is not None else None,
            help="Valor médio por pedido no período"
        )
    
    with col2:
        st.metric(
            "Média por Dia Útil",
            formatar_real(metricas['venda_media_dia_util']),
            help=f"Valor médio vendido por dia útil ({metricas['dias_uteis']} dias)"
        )

def dashboard_evolucao_mensal(vendas_mensais):
    """Exibe a evolução mensal das vendas"""
    if vendas_mensais.empty:
        st.warning("Não há dados mensais disponíveis para o período selecionado.")
        return
    
    # Criar gráfico de evolução mensal
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Definir cores
    cores = obter_paleta_cores(3)
    
    # Adicionar barras de total de vendas
    fig.add_trace(
        go.Bar(
            x=vendas_mensais['mes_ano'],
            y=vendas_mensais['total_vendas'],
            name="Total de Vendas",
            marker_color=cores[0],
            text=[formatar_real(val) for val in vendas_mensais['total_vendas']],
            textposition='auto',
            hoverinfo='text+name',
            hovertext=[f"{mes} {ano}<br>Total: {formatar_real(valor)}<br>Quantidade: {int(qtd)} vendas" 
                      for mes, ano, valor, qtd in zip(
                          vendas_mensais['mes_nome'], 
                          vendas_mensais['ano'],
                          vendas_mensais['total_vendas'], 
                          vendas_mensais['qtd_vendas'])]
        ),
        secondary_y=False
    )
    
    # Adicionar linha de crescimento percentual
    if len(vendas_mensais) > 1:
        fig.add_trace(
            go.Scatter(
                x=vendas_mensais['mes_ano'],
                y=vendas_mensais['crescimento_pct'],
                name="Variação %",
                marker_color=cores[1],
                mode='lines+markers',
                line=dict(width=3),
                hoverinfo='text+name',
                hovertext=[f"{mes} {ano}<br>Crescimento: {val:.1f}%" 
                          for mes, ano, val in zip(
                              vendas_mensais['mes_nome'], 
                              vendas_mensais['ano'],
                              vendas_mensais['crescimento_pct'])]
            ),
            secondary_y=True
        )
        
        # Adicionar linha média móvel de 3 meses se disponível
        if 'media_movel_3m' in vendas_mensais.columns:
            fig.add_trace(
                go.Scatter(
                    x=vendas_mensais['mes_ano'],
                    y=vendas_mensais['media_movel_3m'],
                    name="Média Móvel (3 meses)",
                    marker_color=cores[2],
                    mode='lines',
                    line=dict(width=3, dash='dot'),
                    hoverinfo='text+name',
                    hovertext=[f"{mes} {ano}<br>Média Móvel: {formatar_real(val)}" 
                              for mes, ano, val in zip(
                                  vendas_mensais['mes_nome'], 
                                  vendas_mensais['ano'],
                                  vendas_mensais['media_movel_3m'])]
                ),
                secondary_y=False
            )
    
    # Configurações dos eixos
    fig.update_layout(
        title="Evolução Mensal de Vendas",
        xaxis_title="Mês",
        yaxis_title="Total de Vendas (R$)",
        yaxis2_title="Variação (%)",
        height=400,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(t=50, l=50, r=50, b=80)
    )
    
    # Otimizações de aparência
    fig.update_yaxes(title_text="Total de Vendas (R$)", secondary_y=False)
    fig.update_yaxes(title_text="Variação (%)", secondary_y=True)
    fig.update_xaxes(tickangle=45)
    
    # Exibir gráfico
    st.plotly_chart(fig, use_container_width=True)
    
    # Exibir tabela com detalhes mensais
    with st.expander("Detalhamento de Vendas Mensais"):
        # Formatar valores para exibição
        tabela_vendas = vendas_mensais.copy()
        tabela_vendas['total_vendas_fmt'] = tabela_vendas['total_vendas'].apply(lambda x: formatar_real(x))
        tabela_vendas['ticket_medio_fmt'] = tabela_vendas['ticket_medio'].apply(lambda x: formatar_real(x))
        tabela_vendas['media_diaria_fmt'] = tabela_vendas['media_diaria'].apply(lambda x: formatar_real(x))
        tabela_vendas['crescimento_pct_fmt'] = tabela_vendas['crescimento_pct'].apply(lambda x: f"{x:.2f}%")
        
        # Selecionar colunas relevantes
        tabela_exibir = tabela_vendas[['mes_nome', 'ano', 'total_vendas_fmt', 'qtd_vendas', 
                                       'ticket_medio_fmt', 'media_diaria_fmt', 'crescimento_pct_fmt']]
        tabela_exibir.columns = ['Mês', 'Ano', 'Total de Vendas', 'Quantidade', 
                                'Ticket Médio', 'Média Diária', 'Crescimento']
        
        st.table(tabela_exibir)

def dashboard_dias_semana(analise_dias):
    """Exibe análise por dia da semana"""
    if analise_dias is None:
        st.warning("Não há dados suficientes para análise por dia da semana.")
        return
    
    df_dias = analise_dias['df_dias']
    melhor_dia = analise_dias['melhor_dia']
    pior_dia = analise_dias['pior_dia']
    
    # Criar gráfico de barras para vendas por dia da semana
    cores = obter_paleta_cores(7)
    
    # Gráfico de barras com média diária por dia da semana
    fig = go.Figure()
    
    # Adicionar barras de média por dia
    fig.add_trace(go.Bar(
        x=df_dias['dia_semana'],
        y=df_dias['media_por_dia'],
        marker_color=cores,
        text=[formatar_real(val) for val in df_dias['media_por_dia']],
        textposition='auto',
        hoverinfo='text',
        hovertext=[f"{dia}<br>Média: {formatar_real(media)}<br>Total: {formatar_real(total)}<br>Dias: {dias}" 
                  for dia, media, total, dias in zip(
                      df_dias['dia_semana'], 
                      df_dias['media_por_dia'],
                      df_dias['total_vendas'],
                      df_dias['dias_ocorrencia'])]
    ))
    
    # Adicionar linha para média geral
    media_geral = df_dias['media_por_dia'].mean()
    fig.add_hline(
        y=media_geral, 
        line_width=1, 
        line_dash="dash", 
        line_color="red",
        annotation_text=f"Média: {formatar_real(media_geral)}",
        annotation_position="top right"
    )
    
    # Configurações de layout
    fig.update_layout(
        title="Média de Vendas por Dia da Semana",
        xaxis_title="Dia da Semana",
        yaxis_title="Média de Vendas (R$)",
        height=400,
        xaxis=dict(
            tickangle=0  # Evitar ângulo nos rótulos para melhor leitura
        ),
        margin=dict(t=50, l=50, r=50, b=50)
    )
    
    # Exibir gráfico
    st.plotly_chart(fig, use_container_width=True)
    
    # Exibir insights sobre dias da semana
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"""
        **Melhor dia de vendas: {melhor_dia['dia_semana']}**
        - Média por dia: {formatar_real(melhor_dia['media_por_dia'])}
        - Total no período: {formatar_real(melhor_dia['total_vendas'])}
        - Quantidade de dias: {int(melhor_dia['dias_ocorrencia'])}
        """)
    
    with col2:
        st.warning(f"""
        **Dia com menor venda: {pior_dia['dia_semana']}**
        - Média por dia: {formatar_real(pior_dia['media_por_dia'])}
        - Total no período: {formatar_real(pior_dia['total_vendas'])}
        - Quantidade de dias: {int(pior_dia['dias_ocorrencia'])}
        """)

def dashboard_horas(analise_horas):
    """Exibe análise por hora do dia"""
    if analise_horas is None:
        st.warning("Não há dados suficientes para análise por hora.")
        return
    
    df_horas = analise_horas['df_horas']
    picos = analise_horas['picos']
    
    # Somente mostrar horas comerciais
    df_horas = df_horas[(df_horas['hora'] >= 8) & (df_horas['hora'] < 19)]
    
    # Criar gráfico de barras para vendas por hora
    fig = go.Figure()
    
    # Cores alternadas para horas
    cores = obter_paleta_cores(2)
    cores_alternadas = [cores[0] if h < 12 else cores[1] for h in df_horas['hora']]
    
    # Adicionar barras de média por hora
    fig.add_trace(go.Bar(
        x=df_horas['hora'].apply(lambda x: f"{x:02d}h"),
        y=df_horas['media_por_dia'],
        marker_color=cores_alternadas,
        text=[formatar_real(val) for val in df_horas['media_por_dia']],
        textposition='auto',
        hoverinfo='text',
        hovertext=[f"{h:02d}h<br>Média: {formatar_real(media)}<br>Total: {formatar_real(total)}<br>Qtd: {int(qtd)}" 
                  for h, media, total, qtd in zip(
                      df_horas['hora'], 
                      df_horas['media_por_dia'],
                      df_horas['total_vendas'],
                      df_horas['qtd_vendas'])]
    ))
    
    # Adicionar linha para média geral
    media_geral = df_horas['media_por_dia'].mean()
    fig.add_hline(
        y=media_geral, 
        line_width=1, 
        line_dash="dash", 
        line_color="red",
        annotation_text=f"Média: {formatar_real(media_geral)}",
        annotation_position="top right"
    )
    
    # Configurações de layout
    fig.update_layout(
        title="Média de Vendas por Hora do Dia (Horário Comercial)",
        xaxis_title="Hora",
        yaxis_title="Média de Vendas (R$)",
        height=400,
        margin=dict(t=50, l=50, r=50, b=50)
    )
    
    # Exibir gráfico
    st.plotly_chart(fig, use_container_width=True)
    
    # Exibir insights sobre picos de horas
    st.info("#### Picos de Venda por Hora")
    
    # Mostrar os horários de pico em colunas
    colunas = st.columns(3)
    
    for i, (_, pico) in enumerate(picos.iterrows()):
        with colunas[i]:
            st.metric(
                f"{int(pico['hora']):02d}h - {int(pico['hora'])+1:02d}h",
                formatar_real(pico['media_por_dia']),
                f"{(pico['media_por_dia']/media_geral - 1) * 100:.1f}% acima da média"
            )

def dashboard_distribuicao_vendas(df, coluna_valor):
    """Exibe análise da distribuição de vendas por dia da semana e período do mês"""
    # Em vez do heatmap, vamos criar uma visualização mais direta
    # Vamos dividir o mês em semanas e mostrar a performance de cada semana
    
    # Agrupar por semana do mês
    vendas_por_semana = df.groupby('semana_mes').agg({
        coluna_valor: ['sum', 'count', 'mean'],
        'data': 'nunique'
    }).reset_index()
    
    # Renomear colunas
    vendas_por_semana.columns = ['semana', 'total_vendas', 'qtd_vendas', 'ticket_medio', 'dias_ocorrencia']
    
    # Calcular média por dia
    vendas_por_semana['media_por_dia'] = vendas_por_semana['total_vendas'] / vendas_por_semana['dias_ocorrencia']
    
    # Calcular percentual do total
    total_geral = vendas_por_semana['total_vendas'].sum()
    vendas_por_semana['percentual'] = (vendas_por_semana['total_vendas'] / total_geral) * 100
    
    # Ordenar por semana
    vendas_por_semana = vendas_por_semana.sort_values('semana')
    
    # Criar gráfico de barras
    fig = go.Figure()
    
    # Adicionar barras de percentual por semana
    fig.add_trace(go.Bar(
        x=["Semana " + str(i) for i in vendas_por_semana['semana']],
        y=vendas_por_semana['percentual'],
        marker_color=obter_paleta_cores(len(vendas_por_semana)),
        text=[f"{p:.1f}%" for p in vendas_por_semana['percentual']],
        textposition='auto',
        hoverinfo='text',
        hovertext=[f"Semana {s} do mês<br>Participação: {p:.1f}%<br>Total: {formatar_real(t)}<br>Média diária: {formatar_real(m)}" 
                  for s, p, t, m in zip(
                      vendas_por_semana['semana'], 
                      vendas_por_semana['percentual'],
                      vendas_por_semana['total_vendas'],
                      vendas_por_semana['media_por_dia'])]
    ))
    
    # Configurações de layout
    fig.update_layout(
        title="Distribuição de Vendas por Semana do Mês",
        xaxis_title="Semana do Mês",
        yaxis_title="Participação no Total (%)",
        height=400,
        margin=dict(t=50, l=50, r=50, b=50)
    )
    
    # Exibir gráfico
    st.plotly_chart(fig, use_container_width=True)
    
    # Agora, vamos criar um segundo gráfico mostrando a distribuição por dia da semana e período do dia
    
    # Criar período do dia (manhã, tarde, noite)
    def obter_periodo(hora):
        if 8 <= hora < 12:
            return 'Manhã (8h-12h)'
        elif 12 <= hora < 18:
            return 'Tarde (12h-18h)'
        elif hora >= 18:
            return 'Noite (18h+)'
        else:
            return 'Madrugada (0h-8h)'
    
    # Adicionar coluna de período
    df_temp = df.copy()
    df_temp['periodo_dia'] = df_temp['hora'].apply(obter_periodo)
    
    # Agrupar por dia da semana e período do dia
    dist_dia_periodo = df_temp.groupby(['dia_semana_pt', 'periodo_dia']).agg({
        coluna_valor: ['sum', 'count']
    }).reset_index()
    
    # Renomear colunas
    dist_dia_periodo.columns = ['dia_semana', 'periodo_dia', 'total_vendas', 'qtd_vendas']
    
    # Ordenar dias da semana
    ordem_dias = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    ordem_periodos = ['Manhã (8h-12h)', 'Tarde (12h-18h)', 'Noite (18h+)']
    
    # Filtrar apenas os períodos e dias relevantes
    dist_dia_periodo = dist_dia_periodo[
        (dist_dia_periodo['dia_semana'].isin(ordem_dias[:6])) &  # Seg a Sáb
        (dist_dia_periodo['periodo_dia'].isin(ordem_periodos))   # Períodos comerciais
    ]
    
    # Criar ordem personalizada
    dist_dia_periodo['ordem_dia'] = dist_dia_periodo['dia_semana'].map({dia: i for i, dia in enumerate(ordem_dias)})
    dist_dia_periodo['ordem_periodo'] = dist_dia_periodo['periodo_dia'].map({periodo: i for i, periodo in enumerate(ordem_periodos)})
    
    # Ordenar
    dist_dia_periodo = dist_dia_periodo.sort_values(['ordem_dia', 'ordem_periodo'])
    
    # Calcular percentual do total
    total_geral = dist_dia_periodo['total_vendas'].sum()
    dist_dia_periodo['percentual'] = (dist_dia_periodo['total_vendas'] / total_geral) * 100
    
    # Criar um gráfico de barras agrupadas
    fig = px.bar(
        dist_dia_periodo, 
        x='dia_semana', 
        y='percentual', 
        color='periodo_dia',
        barmode='group',
        text=dist_dia_periodo['percentual'].apply(lambda x: f"{x:.1f}%"),
        color_discrete_sequence=obter_paleta_cores(3),
        labels={
            'dia_semana': 'Dia da Semana',
            'percentual': 'Participação no Total (%)',
            'periodo_dia': 'Período do Dia'
        },
        title="Distribuição de Vendas por Dia da Semana e Período do Dia",
        height=450
    )
    
    # Ajustes de layout
    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(t=70, l=50, r=50, b=50)
    )
    
    # Exibir gráfico
    st.plotly_chart(fig, use_container_width=True)
    
    # Exibir insights
    st.markdown("#### Principais Insights da Distribuição de Vendas")
    
    # Encontrar a melhor combinação dia-período
    melhor_combinacao = dist_dia_periodo.loc[dist_dia_periodo['percentual'].idxmax()]
    
    # Encontrar melhor semana
    melhor_semana = vendas_por_semana.loc[vendas_por_semana['percentual'].idxmax()]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"""
        **Melhor combinação: {melhor_combinacao['dia_semana']} no período da {melhor_combinacao['periodo_dia']}**
        - Participação: {melhor_combinacao['percentual']:.1f}% do total
        - Valor: {formatar_real(melhor_combinacao['total_vendas'])}
        """)
    
    with col2:
        st.info(f"""
        **Semana mais forte: Semana {melhor_semana['semana']} do mês**
        - Participação: {melhor_semana['percentual']:.1f}% do total
        - Valor médio diário: {formatar_real(melhor_semana['media_por_dia'])}
        """)

def dashboard_calendario(df, coluna_valor):
    """Exibe o calendário mensal de vendas com estilização aprimorada"""
    if df.empty:
        st.warning("Não há dados para exibir no calendário.")
        return
    
    # Usar session_state para persistir seleções entre recarregamentos
    if 'calendario_ano' not in st.session_state:
        # Dados para primeiro carregamento
        meses_com_dados = df.groupby(['ano', 'mes']).size().reset_index()
        meses_com_dados.columns = ['ano', 'mes', 'contagem']
        anos_disponiveis = sorted(meses_com_dados['ano'].unique())
        
        # Inicializar session_state com valores padrão
        st.session_state.calendario_ano = anos_disponiveis[-1] if anos_disponiveis else None
        st.session_state.calendario_meses_com_dados = meses_com_dados
    
    # Mostrar mensagem informativa sobre possível recarregamento na primeira mudança
    st.info("ℹ️ Dica: Se ao mudar o ano a página recarregar, basta acessar o calendário novamente.")
    
    # Seção de seletores com design aprimorado
    st.markdown("""
    <style>
    .calendar-selectors {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .calendar-title {
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 15px;
        color: #1E3A8A;
        padding-bottom: 10px;
        border-bottom: 2px solid #4CAF50;
    }
    .calendar-subtitle {
        font-size: 20px;
        font-weight: bold;
        margin-top: 15px;
        margin-bottom: 10px;
        color: #1E3A8A;
    }
    .calendar-metrics {
        display: flex;
        gap: 20px;
        margin: 15px 0;
    }
    .calendar-metric {
        background-color: white;
        padding: 10px 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        flex: 1;
        text-align: center;
    }
    .metric-value {
        font-size: 20px;
        font-weight: bold;
        color: #2196F3;
    }
    .metric-label {
        font-size: 14px;
        color: #666;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Seletores de ano e mês
    col1, col2 = st.columns(2)
    
    with col1:
        # Recuperar anos disponíveis
        anos_disponiveis = sorted(st.session_state.calendario_meses_com_dados['ano'].unique())
        
        # Selecionar ano
        ano_selecionado = st.selectbox(
            "Selecione o Ano",
            options=anos_disponiveis,
            index=anos_disponiveis.index(st.session_state.calendario_ano) if st.session_state.calendario_ano in anos_disponiveis else 0,
            key="ano_selector"
        )
        
        # Atualizar session_state com o ano selecionado
        st.session_state.calendario_ano = ano_selecionado
    
    # Filtrar meses disponíveis para o ano selecionado
    meses_no_ano = st.session_state.calendario_meses_com_dados[st.session_state.calendario_meses_com_dados['ano'] == ano_selecionado]
    meses_disponiveis = sorted(meses_no_ano['mes'].unique())
    
    # Mapear números dos meses para nomes capitalizados
    meses_traduzidos = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    
    with col2:
        if not meses_disponiveis:
            st.warning(f"Não há dados disponíveis para o ano {ano_selecionado}.")
            return
        
        # Selecionar mês
        mes_selecionado = st.selectbox(
            "Selecione o Mês",
            options=meses_disponiveis,
            format_func=lambda x: meses_traduzidos.get(x, f"Mês {x}"),
            index=len(meses_disponiveis)-1,  # Último mês como padrão
            key="mes_selector"
        )
    
    # Gerar e exibir calendário
    if mes_selecionado and ano_selecionado:
        cal_data = calendario_vendas(df, coluna_valor, mes_selecionado, ano_selecionado)
        
        # Título do calendário com nome do mês capitalizado
        mes_nome = meses_traduzidos.get(mes_selecionado, "")
        
        # Criar cabeçalho estilizado com métricas
        st.markdown(f"""
        <div class="calendar-title">
            {mes_nome} {ano_selecionado}
        </div>
        <div class="calendar-metrics">
            <div class="calendar-metric">
                <div class="metric-value">{formatar_real(cal_data['total_mes'])}</div>
                <div class="metric-label">Total de Vendas</div>
            </div>
            <div class="calendar-metric">
                <div class="metric-value">{cal_data['qtd_mes']}</div>
                <div class="metric-label">Quantidade de Vendas</div>
            </div>
            <div class="calendar-metric">
                <div class="metric-value">{formatar_real(cal_data['total_mes'] / cal_data['qtd_mes']) if cal_data['qtd_mes'] > 0 else "R$ 0,00"}</div>
                <div class="metric-label">Ticket Médio</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Criar CSS embutido diretamente na página
        css = """
        <style>
            .cal-container {
                font-family: Arial, sans-serif;
                max-width: 100%;
                margin: 0 auto 20px auto;
                padding: 20px;
                background-color: #f1f1f1;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            
            .cal-table {
                width: 100%;
                border-collapse: separate;
                border-spacing: 5px;
                margin-top: 10px;
            }
            
            .cal-th {
                background-color: #4CAF50;
                color: white;
                text-align: center;
                padding: 15px 5px;
                font-weight: bold;
                border-radius: 5px;
                text-transform: uppercase;
                font-size: 14px;
            }
            
            .cal-th-weekend {
                background-color: #f57c00;
            }
            
            .cal-td {
                background-color: white;
                border: 1px solid #ddd;
                padding: 0;
                text-align: center;
                border-radius: 5px;
                height: 90px;
                position: relative;
                vertical-align: top;
                overflow: hidden;
                box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                transition: transform 0.2s, box-shadow 0.2s;
            }
            
            .cal-td:hover {
                transform: scale(1.03);
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                z-index: 10;
            }
            
            .cal-td-content {
                position: relative;
                padding: 10px;
                height: 100%;
                box-sizing: border-box;
            }
            
            .cal-day-num {
                position: absolute;
                top: 5px;
                left: 5px;
                font-size: 16px;
                font-weight: bold;
                color: #333;
                background-color: rgba(255,255,255,0.7);
                width: 25px;
                height: 25px;
                line-height: 25px;
                text-align: center;
                border-radius: 50%;
            }
            
            .cal-empty {
                background-color: #f5f5f5;
                border: 1px solid #eee;
            }
            
            .cal-saturday {
                background-color: #E3F2FD;
            }
            
            .cal-sunday {
                background-color: #FFEBEE;
            }
            
            .cal-hoje {
                border: 3px solid #4CAF50;
            }
            
            .cal-valor {
                margin-top: 30px;
                font-weight: bold;
                color: #2196F3;
                font-size: 16px;
            }
            
            .cal-qtd {
                margin-top: 5px;
                font-size: 12px;
                color: #757575;
            }
            
            /* Níveis de vendas */
            .cal-nivel-0 { background-color: #f5f5f5; }  /* Sem vendas */
            .cal-nivel-1 { background-color: #E3F2FD; }  /* Vendas baixas */
            .cal-nivel-2 { background-color: #BBDEFB; }  /* Vendas médias */
            .cal-nivel-3 { background-color: #90CAF9; }  /* Vendas altas */
            .cal-nivel-4 { background-color: #42A5F5; }  /* Vendas muito altas */
            .cal-nivel-4 .cal-valor, .cal-nivel-4 .cal-qtd { color: white; }
            
            .legenda {
                display: flex;
                flex-wrap: wrap;
                margin: 15px 0;
                gap: 10px;
            }
            
            .legenda-item {
                display: flex;
                align-items: center;
                margin-right: 15px;
                font-size: 14px;
            }
            
            .legenda-cor {
                width: 20px;
                height: 20px;
                margin-right: 5px;
                border: 1px solid #ddd;
                border-radius: 3px;
            }
            
            .calendar-subtitle {
                font-size: 18px;
                font-weight: bold;
                margin: 20px 0 10px 0;
                color: #333;
                border-bottom: 1px solid #ddd;
                padding-bottom: 5px;
            }
        </style>
        """
        
        # Criar calendário com HTML otimizado para responsividade
        dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
        
        # Data atual para destacar o dia de hoje
        hoje = datetime.now().date()
        
        # Função para determinar o nível de vendas para estilização
        def get_nivel_vendas(valor, max_valor):
            if valor == 0:
                return 0  # Sem vendas
            
            ratio = valor / max_valor
            if ratio < 0.25:
                return 1  # Vendas baixas
            elif ratio < 0.5:
                return 2  # Vendas médias
            elif ratio < 0.75:
                return 3  # Vendas altas
            else:
                return 4  # Vendas muito altas
        
        # Construir o calendário
        html = css + '<div class="cal-container">'
        html += '<table class="cal-table"><tr>'
        
        # Cabeçalhos - dias da semana
        for i, dia in enumerate(dias_semana):
            if i > 4:  # Sábado e Domingo
                html += f'<th class="cal-th cal-th-weekend">{dia}</th>'
            else:
                html += f'<th class="cal-th">{dia}</th>'
        
        html += '</tr>'
        
        # Adicionar as semanas
        for semana in cal_data['calendario']:
            html += '<tr>'
            for i, dia in enumerate(semana):
                if dia['vazio']:
                    html += '<td class="cal-td cal-empty"></td>'
                else:
                    # Determinar classes para estilos
                    classes = ["cal-td"]
                    
                    # Adicionar classe para fins de semana
                    if i == 5:  # Sábado
                        classes.append("cal-saturday")
                    elif i == 6:  # Domingo
                        classes.append("cal-sunday")
                    
                    # Adicionar classe para hoje
                    data_dia = datetime(ano_selecionado, mes_selecionado, dia['dia']).date()
                    if data_dia == hoje:
                        classes.append("cal-hoje")
                    
                    # Adicionar classe para nível de vendas
                    nivel = get_nivel_vendas(dia['total'], cal_data['max_valor'])
                    classes.append(f"cal-nivel-{nivel}")
                    
                    # Montar a célula com o conteúdo
                    class_str = ' '.join(classes)
                    
                    html += f"""
                    <td class="{class_str}">
                        <div class="cal-td-content">
                            <div class="cal-day-num">{dia['dia']}</div>
                            <div class="cal-valor">{formatar_real(dia['total'])}</div>
                            <div class="cal-qtd">{dia['qtd']} {dia['qtd'] == 1 and 'venda' or 'vendas'}</div>
                        </div>
                    </td>
                    """
            html += '</tr>'
        
        html += '</table>'
        
        # Adicionar legenda
        html += """
        <div class="calendar-subtitle">Legenda</div>
        <div class="legenda">
            <div class="legenda-item"><div class="legenda-cor" style="background-color: #f5f5f5;"></div> Sem vendas</div>
            <div class="legenda-item"><div class="legenda-cor" style="background-color: #E3F2FD;"></div> Vendas baixas</div>
            <div class="legenda-item"><div class="legenda-cor" style="background-color: #BBDEFB;"></div> Vendas médias</div>
            <div class="legenda-item"><div class="legenda-cor" style="background-color: #90CAF9;"></div> Vendas altas</div>
            <div class="legenda-item"><div class="legenda-cor" style="background-color: #42A5F5;"></div> Vendas muito altas</div>
        </div>
        <div class="legenda">
            <div class="legenda-item"><div class="legenda-cor" style="background-color: #E3F2FD;"></div> Sábado</div>
            <div class="legenda-item"><div class="legenda-cor" style="background-color: #FFEBEE;"></div> Domingo</div>
            <div class="legenda-item"><div class="legenda-cor" style="border: 3px solid #4CAF50; background-color: white;"></div> Hoje</div>
        </div>
        """
        
        html += '</div>'
        
        # Exibir o calendário
        st.components.v1.html(html, height=800)
        
        # Adicionar análise dos melhores e piores dias
        st.markdown('<div class="calendar-subtitle">Análise de Desempenho do Mês</div>', unsafe_allow_html=True)
        
        # Encontrar o melhor e o pior dia
        dias_com_vendas = []
        for semana in cal_data['calendario']:
            for dia in semana:
                if not dia['vazio'] and dia['total'] > 0:
                    dias_com_vendas.append(dia)
        
        if dias_com_vendas:
            # Melhor dia
            melhor_dia = max(dias_com_vendas, key=lambda x: x['total'])
            pior_dia = min(dias_com_vendas, key=lambda x: x['total'])
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"""
                **Melhor dia do mês: {melhor_dia['dia']} de {cal_data['mes']}**
                - Total de vendas: {formatar_real(melhor_dia['total'])}
                - Quantidade: {melhor_dia['qtd']} vendas
                """)
            
            with col2:
                st.info(f"""
                **Dia com menor venda: {pior_dia['dia']} de {cal_data['mes']}**
                - Total de vendas: {formatar_real(pior_dia['total'])}
                - Quantidade: {pior_dia['qtd']} vendas
                """)
        else:
            st.warning("Não há dados de vendas neste mês para análise.")

def dashboard_vendedores(metricas_vendedores, coluna_vendedor):
    """Exibe análise de desempenho dos vendedores"""
    if metricas_vendedores.empty:
        st.warning("Não há dados de vendedores disponíveis para o período selecionado.")
        return
    
    # Criar gráfico de barras para total de vendas
    fig = go.Figure()
    
    # Ordenar por total de vendas (decrescente)
    df_ord = metricas_vendedores.sort_values('total_vendas', ascending=False)
    
    # Cores para os vendedores
    cores = obter_paleta_cores(len(df_ord))
    
    # Adicionar barras de total de vendas
    fig.add_trace(go.Bar(
        x=df_ord[coluna_vendedor],
        y=df_ord['total_vendas'],
        marker_color=cores,
        text=[formatar_real(val) for val in df_ord['total_vendas']],
        textposition='auto',
        hoverinfo='text',
        hovertext=[f"{vendedor}<br>Total: {formatar_real(valor)}<br>Qtd: {int(qtd)} pedidos<br>Ticket Médio: {formatar_real(ticket)}" 
                  for vendedor, valor, qtd, ticket in zip(
                      df_ord[coluna_vendedor], 
                      df_ord['total_vendas'],
                      df_ord['qtd_vendas'],
                      df_ord['ticket_medio'])]
    ))
    
    # Adicionar linha para média
    media_vendas = df_ord['total_vendas'].mean()
    fig.add_hline(
        y=media_vendas, 
        line_width=1, 
        line_dash="dash", 
        line_color="red",
        annotation_text=f"Média: {formatar_real(media_vendas)}",
        annotation_position="top right"
    )
    
    # Configurações de layout
    fig.update_layout(
        title="Desempenho dos Vendedores - Total de Vendas",
        xaxis_title="Vendedor",
        yaxis_title="Total de Vendas (R$)",
        height=450,
        margin=dict(t=50, l=50, r=50, b=100)
    )
    
    # Ajustar eixo x para melhor legibilidade
    fig.update_xaxes(tickangle=45)
    
    # Exibir gráfico
    st.plotly_chart(fig, use_container_width=True)
    
    # Segundo gráfico: Comparativo multidimensional
    fig2 = go.Figure()
    
    # Adicionar barras para diferentes métricas
    # 1. Participação percentual
    fig2.add_trace(go.Bar(
        x=df_ord[coluna_vendedor],
        y=df_ord['participacao_pct'],
        name="Participação %",
        marker_color=cores[0],
        text=[f"{val:.1f}%" for val in df_ord['participacao_pct']],
        textposition='auto'
    ))
    
    # 2. Desempenho vs média
    fig2.add_trace(go.Bar(
        x=df_ord[coluna_vendedor],
        y=df_ord['vs_media_pct'],
        name="Vs. Média %",
        marker_color=cores[1],
        text=[f"{val:.1f}%" for val in df_ord['vs_media_pct']],
        textposition='auto'
    ))
    
    # Configurações de layout
    fig2.update_layout(
        title="Análise Comparativa dos Vendedores",
        xaxis_title="Vendedor",
        yaxis_title="Percentual (%)",
        height=450,
        barmode='group',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(t=70, l=50, r=50, b=100)
    )
    
    # Ajustar eixo x para melhor legibilidade
    fig2.update_xaxes(tickangle=45)
    
    # Exibir gráfico
    st.plotly_chart(fig2, use_container_width=True)
    
    # Tabela de desempenho
    with st.expander("Detalhamento de Desempenho por Vendedor"):
        # Formatar valores para exibição
        tabela_vendedores = df_ord.copy()
        tabela_vendedores['total_vendas_fmt'] = tabela_vendedores['total_vendas'].apply(lambda x: formatar_real(x))
        tabela_vendedores['ticket_medio_fmt'] = tabela_vendedores['ticket_medio'].apply(lambda x: formatar_real(x))
        tabela_vendedores['media_diaria_fmt'] = tabela_vendedores['media_diaria'].apply(lambda x: formatar_real(x))
        tabela_vendedores['participacao_pct_fmt'] = tabela_vendedores['participacao_pct'].apply(lambda x: f"{x:.2f}%")
        tabela_vendedores['vs_media_pct_fmt'] = tabela_vendedores['vs_media_pct'].apply(lambda x: f"{x:.2f}%")
        
        # Selecionar colunas relevantes
        tabela_exibir = tabela_vendedores[[
            coluna_vendedor, 'total_vendas_fmt', 'qtd_vendas', 'ticket_medio_fmt', 
            'dias_trabalhados', 'media_diaria_fmt', 'participacao_pct_fmt', 'vs_media_pct_fmt'
        ]]
        
        tabela_exibir.columns = [
            'Vendedor', 'Total de Vendas', 'Quantidade', 'Ticket Médio', 
            'Dias Trabalhados', 'Média Diária', 'Participação', 'Vs. Média'
        ]
        
        st.table(tabela_exibir)

def dashboard_simulacao_comissoes(metricas_vendedores, vendas_mensais, coluna_vendedor):
    """Dashboard interativo para simulação de comissões"""
    if metricas_vendedores.empty:
        st.warning("Não há dados de vendedores para simular comissões.")
        return
    
    # Introdução clara ao proprietário
    st.markdown("""
    ### Simulação de Modelos de Comissionamento
    
    Esta ferramenta permite verificar diferentes estratégias de remuneração para sua equipe de vendas,
    comparando diferentes cenários e calculando o impacto financeiro para sua empresa.
    
    Você pode simular comissões baseadas nas vendas mensais de cada balconista e avaliar os custos
    para decidir qual modelo é mais vantajoso para o seu negócio.
    """)
    
    # Determinar o período analisado e número de meses
    # Usar vendas_mensais para determinar o número de meses no período
    num_meses = len(vendas_mensais['mes_ano'].unique()) if not vendas_mensais.empty else 1
    
    # Informar ao usuário sobre o período da simulação
    st.info(f"**Período analisado**: {num_meses} {'mês' if num_meses == 1 else 'meses'}. A simulação considerará salários e comissões para o período total.")
    
    # Passo 1: Permitir selecionar quais vendedores incluir na simulação
    st.subheader("Passo 1: Selecione os vendedores para simular")
    
    # Obter lista de vendedores
    vendedores_lista = metricas_vendedores[coluna_vendedor].tolist()
    
    # Criar opção para excluir o próprio dono da análise
    col1, col2 = st.columns([2, 1])
    
    with col1:
        vendedores_para_simular = st.multiselect(
            "Incluir na simulação de comissão:",
            options=vendedores_lista,
            default=vendedores_lista,  # Todos por padrão
            help="Selecione apenas os funcionários que receberão comissão. Você pode excluir o dono ou gerentes que tenham salário fixo."
        )
    
    with col2:
        # Botão para selecionar/desselecionar todos
        if st.button("Selecionar Todos"):
            # Este botão só muda o valor ao ser clicado, para atualizar o multiselect é necessário refresh
            vendedores_para_simular = vendedores_lista
            st.success("Todos vendedores selecionados! Clique em Atualizar Simulação para aplicar.")
        
        if st.button("Limpar Seleção"):
            # Este botão só muda o valor ao ser clicado
            vendedores_para_simular = []
            st.info("Seleção limpa! Clique em Atualizar Simulação para aplicar.")
    
    # Filtrar apenas os vendedores selecionados
    if not vendedores_para_simular:
        st.warning("Selecione pelo menos um vendedor para continuar a simulação.")
        return
    
    metricas_vendedores_filtrados = metricas_vendedores[metricas_vendedores[coluna_vendedor].isin(vendedores_para_simular)].copy()
    
    # Passo 2: Selecionar o modelo de comissão
    st.markdown("---")
    st.subheader("Passo 2: Escolha o modelo de comissionamento")
    
    modelo_comissao = st.radio(
        "Selecione o modelo de comissionamento:",
        options=["Comissão fixa", "Comissão com meta", "Comissão progressiva"],
        horizontal=True,
        index=0
    )
    
    # Converter para formato interno
    modelo_map = {
        "Comissão fixa": "fixo",
        "Comissão com meta": "meta",
        "Comissão progressiva": "progressivo"
    }
    modelo = modelo_map[modelo_comissao]
    
    # Configurar parâmetros específicos para cada modelo
    st.markdown("### Configuração dos Parâmetros")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Parâmetros comuns
        salario_base_mensal = st.number_input(
            "Salário base mensal por pessoa (R$)",
            min_value=0,
            max_value=10000,
            value=1500,
            step=100,
            help="Salário base fixo mensal sem comissão"
        )
        # Calcular salário base para o período total
        salario_base_periodo = salario_base_mensal * num_meses
    
    # Parâmetros específicos para cada modelo
    parametros = {'salario_base': salario_base_periodo}  # Ajustado para o período total
    
    if modelo == "fixo":
        with col2:
            comissao_pct = st.number_input(
                "Percentual de comissão sobre vendas (%)",
                min_value=0.0,
                max_value=10.0,
                value=1.0,
                step=0.1,
                format="%.1f",
                help="Percentual sobre o total de vendas"
            )
        
        parametros['comissao_pct'] = comissao_pct
        
        # Explicação do modelo
        with st.expander("Entenda o modelo de comissão fixa"):
            st.markdown(f"""
            **Como funciona a comissão fixa:**
            
            Neste modelo, cada vendedor recebe um salário base fixo de **{formatar_real(salario_base_mensal)} por mês** (total de **{formatar_real(salario_base_periodo)} no período de {num_meses} {'mês' if num_meses == 1 else 'meses'}**) mais uma 
            comissão de **{comissao_pct}%** sobre o total de suas vendas no período.
            
            **Exemplo:**
            - Se um vendedor vender R$ 100.000,00 em um mês, receberá:
                - Salário base mensal: {formatar_real(salario_base_mensal)}
                - Comissão: {formatar_real(100000 * comissao_pct / 100)} ({comissao_pct}% de R$ 100.000,00)
                - Total mensal: {formatar_real(salario_base_mensal + 100000 * comissao_pct / 100)}
            
            **Vantagens:**
            - Simplicidade e transparência para os funcionários
            - Fácil de calcular e controlar
            - Todos recebem proporcionalmente ao seu desempenho
            
            **Desvantagens:**
            - Não incentiva especificamente o atingimento de metas
            - Pode gerar custos maiores em meses de alto volume de vendas
            """)
    
    elif modelo == "meta":
        with col2:
            comissao_pct = st.number_input(
                "Percentual de comissão base (%)",
                min_value=0.0,
                max_value=5.0,
                value=0.5,
                step=0.1,
                format="%.1f",
                help="Percentual base sobre o total de vendas"
            )
            
            meta_tipo = st.radio(
                "Tipo de meta:",
                options=["Valor fixo", "Acima da média"],
                horizontal=True,
                index=0
            )
        
        parametros['comissao_pct'] = comissao_pct
        
        # Configurações adicionais com base no tipo de meta
        bonus_style = st.radio(
            "Estilo de bonificação:",
            options=["Comissão base + bônus ao atingir meta", "Comissão apenas se atingir meta"],
            horizontal=True,
            index=0
        )
        
        parametros['apenas_com_meta'] = bonus_style == "Comissão apenas se atingir meta"
        
        col1, col2 = st.columns(2)
        
        with col1:
            if meta_tipo == "Valor fixo":
                # Calcular uma meta razoável baseada na média de vendas mensais
                vendas_media = metricas_vendedores_filtrados['total_vendas'].mean() / num_meses  # Média mensal
                vendas_meta_periodo = vendas_media * num_meses  # Meta para o período total
                
                meta_valor = st.number_input(
                    f"Meta de vendas para o período de {num_meses} {'mês' if num_meses == 1 else 'meses'} (R$)",
                    min_value=1000,
                    max_value=int(vendas_meta_periodo * 3),
                    value=int(vendas_meta_periodo),
                    step=1000,
                    help=f"Valor de vendas a ser atingido no período de {num_meses} {'mês' if num_meses == 1 else 'meses'} para ganhar a comissão extra"
                )
                parametros['meta_tipo'] = 'valor'
                parametros['meta_valor'] = meta_valor
            else:  # "Acima da média"
                meta_percentual = st.slider(
                    "Meta: % acima da média da equipe",
                    min_value=0,
                    max_value=30,
                    value=10,
                    step=5,
                    help="Vendedor deve vender X% acima da média para ganhar bônus"
                )
                parametros['meta_tipo'] = 'media'
                parametros['meta_percentual'] = meta_percentual
        
        with col2:
            if not parametros['apenas_com_meta']:
                bonus_pct = st.number_input(
                    "Bônus adicional (%)",
                    min_value=0.1,
                    max_value=5.0,
                    value=0.5,
                    step=0.1,
                    format="%.1f",
                    help="Percentual extra ao atingir a meta"
                )
                parametros['bonus_pct'] = bonus_pct
        
        # Explicação do modelo
        with st.expander("Entenda o modelo de comissão com meta"):
            st.markdown(f"""
            **Como funciona a comissão com meta:**
            
            Neste modelo, cada vendedor recebe um salário base fixo de **{formatar_real(salario_base_mensal)} por mês** (total de **{formatar_real(salario_base_periodo)} no período de {num_meses} {'mês' if num_meses == 1 else 'meses'}**). 
            
            {"Além disso, recebe uma comissão base de **" + str(comissao_pct) + "%** sobre suas vendas, e se atingir a meta, ganha um bônus adicional de **" + str(parametros.get('bonus_pct', 0)) + "%**." if not parametros['apenas_com_meta'] else "A comissão de **" + str(comissao_pct) + "%** só é paga se o vendedor atingir a meta estabelecida."}
            
            **Meta definida:**
            {f"- Valor fixo para o período: {formatar_real(meta_valor)}" if meta_tipo == "Valor fixo" else f"- Vender {meta_percentual}% acima da média da equipe"}
            
            **Vantagens:**
            - Incentivo claro para o atingimento de objetivos específicos
            - Maior controle sobre o desempenho esperado da equipe
            - Recompensa os vendedores mais produtivos
            
            **Desvantagens:**
            - Pode criar competição interna
            - Funcionários podem se desmotivar se perceberem a meta como inalcançável
            - Exige monitoramento constante para ajustar metas realistas
            """)
    
    elif modelo == "progressivo":
        # Em um modelo progressivo, configuramos faixas de comissão
        st.markdown("#### Configure as faixas de comissão")
        
        # Explicação adicional para metas do período
        st.info(f"Os valores das faixas se referem ao volume total de vendas no período de {num_meses} {'mês' if num_meses == 1 else 'meses'}.")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            valor_min_1 = 0  # Sempre começa em 0
            valor_max_1 = st.number_input(
                "Faixa 1: até (R$)",
                min_value=5000,
                max_value=100000 * num_meses,  # Ajustado para o período
                value=30000 * num_meses if num_meses > 1 else 30000,  # Valor padrão ajustado ao período
                step=5000,
                help=f"Valor máximo da primeira faixa para o período de {num_meses} {'mês' if num_meses == 1 else 'meses'}"
            )
            comissao_1 = st.number_input(
                "Comissão Faixa 1 (%)",
                min_value=0.0,
                max_value=5.0,
                value=0.5,
                step=0.1,
                format="%.1f"
            )
            
        with col2:
            valor_min_2 = valor_max_1  # Começa onde termina a faixa 1
            valor_max_2 = st.number_input(
                "Faixa 2: até (R$)",
                min_value=valor_min_2 + 5000,
                max_value=200000 * num_meses,  # Ajustado para o período
                value=60000 * num_meses if num_meses > 1 else 60000,  # Valor padrão ajustado ao período
                step=5000,
                help=f"Valor máximo da segunda faixa para o período de {num_meses} {'mês' if num_meses == 1 else 'meses'}"
            )
            comissao_2 = st.number_input(
                "Comissão Faixa 2 (%)",
                min_value=0.0,
                max_value=5.0,
                value=1.0,
                step=0.1,
                format="%.1f"
            )
            
        with col3:
            valor_min_3 = valor_max_2  # Começa onde termina a faixa 2
            valor_max_3 = float('inf')  # Não tem limite superior
            comissao_3 = st.number_input(
                f"Comissão Faixa 3 (acima de {formatar_real(valor_min_3)}) (%)",
                min_value=0.0,
                max_value=7.0,
                value=1.5,
                step=0.1,
                format="%.1f",
                help=f"Comissão para vendas acima de {formatar_real(valor_min_3)} no período de {num_meses} {'mês' if num_meses == 1 else 'meses'}"
            )
        
        # Configurar faixas
        faixas = [
            {'valor_min': valor_min_1, 'valor_max': valor_max_1, 'comissao_pct': comissao_1},
            {'valor_min': valor_min_2, 'valor_max': valor_max_2, 'comissao_pct': comissao_2},
            {'valor_min': valor_min_3, 'valor_max': valor_max_3, 'comissao_pct': comissao_3}
        ]
        
        parametros['faixas'] = faixas
        
        # Explicação do modelo
        with st.expander("Entenda o modelo de comissão progressiva"):
            # Valores mensais aproximados para exemplos
            faixa1_mensal = round(valor_max_1 / num_meses)
            faixa2_mensal = round(valor_max_2 / num_meses)
            valor_min_3_mensal = round(valor_min_3 / num_meses)
            
            st.markdown(f"""
            **Como funciona a comissão progressiva:**
            
            Neste modelo, cada vendedor recebe um salário base fixo de **{formatar_real(salario_base_mensal)} por mês** (total de **{formatar_real(salario_base_periodo)} no período de {num_meses} {'mês' if num_meses == 1 else 'meses'}**) mais uma 
            comissão que aumenta conforme o volume de vendas:
            
            Para o período total de {num_meses} {'mês' if num_meses == 1 else 'meses'}:
            - **Faixa 1:** {comissao_1}% para vendas até {formatar_real(valor_max_1)}
            - **Faixa 2:** {comissao_2}% para vendas entre {formatar_real(valor_min_2)} e {formatar_real(valor_max_2)}
            - **Faixa 3:** {comissao_3}% para vendas acima de {formatar_real(valor_min_3)}
            
            Equivalente mensal aproximado:
            - **Faixa 1:** {comissao_1}% para vendas até {formatar_real(faixa1_mensal)} por mês
            - **Faixa 2:** {comissao_2}% para vendas entre {formatar_real(faixa1_mensal)} e {formatar_real(faixa2_mensal)} por mês
            - **Faixa 3:** {comissao_3}% para vendas acima de {formatar_real(valor_min_3_mensal)} por mês
            
            **Vantagens:**
            - Incentiva fortemente os vendedores a venderem cada vez mais
            - Recompensa desempenho excepcional de forma progressiva
            - Aumenta a motivação para superar recordes pessoais
            
            **Desvantagens:**
            - Pode ser mais complexo para os funcionários entenderem
            - Requer mais controle e cálculos na folha de pagamento
            - Custos podem aumentar significativamente se vários vendedores atingirem faixas altas
            """)
    
    # Botão para executar simulação
    st.markdown("---")
    if st.button("Executar Simulação", type="primary"):
        # Executar simulação
        st.markdown("## Resultados da Simulação")
        
        # Executar simulação com base no modelo selecionado
        df_simulacao, _ = simular_comissao(metricas_vendedores_filtrados, modelo, parametros, None)
        
        # Exibir resultados
        if df_simulacao is not None:
            # Exibir resultados
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Calcular métricas gerais
                total_vendas = df_simulacao['total_vendas'].sum()
                total_comissao = df_simulacao['comissao_valor'].sum()
                total_salario = df_simulacao['salario_total'].sum()
                percentual_folha = (total_salario / total_vendas) * 100 if total_vendas > 0 else 0
                percentual_comissao = (total_comissao / total_vendas) * 100 if total_vendas > 0 else 0
                
                # Informar sobre o período total vs. mensal
                periodo_texto = f"para o período total ({num_meses} {'mês' if num_meses == 1 else 'meses'})"
                
                st.markdown(f"""
                ### Impacto Financeiro {periodo_texto.capitalize()}
                
                - **Total de vendas:** {formatar_real(total_vendas)}
                - **Total de comissões:** {formatar_real(total_comissao)} ({percentual_comissao:.2f}% das vendas)
                - **Total da folha salarial:** {formatar_real(total_salario)} ({percentual_folha:.2f}% das vendas)
                - **Custo mensal médio:** {formatar_real(total_salario / num_meses)}
                """)
                
                # Verificar se o percentual está dentro do recomendado
                if percentual_folha < 5:
                    st.success("✅ Custo total da folha abaixo de 5% das vendas - excelente para lucratividade.")
                elif percentual_folha <= 12:
                    st.info("✓ Custo total da folha entre 5% e 12% das vendas - dentro da faixa típica do varejo.")
                else:
                    st.warning("⚠️ Custo total da folha acima de 12% das vendas - considere ajustar os parâmetros.")
            
            with col2:
                # Mostrar distribuição salário base vs comissão
                fig = go.Figure(data=[go.Pie(
                    labels=['Salário Base', 'Comissões'],
                    values=[df_simulacao['salario_base'].sum(), df_simulacao['comissao_valor'].sum()],
                    hole=.4,
                    marker_colors=['#3498db', '#2ecc71']
                )])
                
                fig.update_layout(
                    title="Composição da Folha",
                    height=250,
                    margin=dict(t=30, l=15, r=15, b=15)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Exibir tabela de simulação
            st.markdown(f"### Projeção de Remuneração por Vendedor ({periodo_texto})")
            
            # Formatar valores para exibição
            tabela_simulacao = df_simulacao.copy()
            tabela_simulacao['total_vendas_fmt'] = tabela_simulacao['total_vendas'].apply(lambda x: formatar_real(x))
            tabela_simulacao['comissao_valor_fmt'] = tabela_simulacao['comissao_valor'].apply(lambda x: formatar_real(x))
            tabela_simulacao['salario_total_fmt'] = tabela_simulacao['salario_total'].apply(lambda x: formatar_real(x))
            tabela_simulacao['salario_mensal_fmt'] = (tabela_simulacao['salario_total'] / num_meses).apply(lambda x: formatar_real(x))
            tabela_simulacao['comissao_pct_fmt'] = tabela_simulacao['comissao_pct'].apply(lambda x: f"{x:.2f}%")
            tabela_simulacao['impacto_percentual_fmt'] = tabela_simulacao['impacto_percentual'].apply(
                lambda x: f"{x:.2f}%" if pd.notna(x) and x >= 0 else "N/A"
            )
            
            # Selecionar colunas relevantes
            colunas_exibir = [
                coluna_vendedor, 'total_vendas_fmt', 'comissao_pct_fmt', 
                'comissao_valor_fmt', 'salario_base', 'salario_total_fmt', 
                'salario_mensal_fmt', 'impacto_percentual_fmt'
            ]
            
            if 'meta_atingida' in tabela_simulacao.columns and tabela_simulacao['meta_atingida'].notna().any():
                colunas_exibir.append('meta_atingida')
            
            tabela_exibir = tabela_simulacao[colunas_exibir]
            
            # Renomear colunas
            colunas_rename = {
                coluna_vendedor: 'Vendedor', 
                'total_vendas_fmt': 'Total de Vendas', 
                'comissao_pct_fmt': 'Comissão %', 
                'comissao_valor_fmt': 'Valor Comissão', 
                'salario_base': f'Salário Base ({num_meses} {"mês" if num_meses == 1 else "meses"})', 
                'salario_total_fmt': 'Salário Total', 
                'salario_mensal_fmt': 'Média Mensal',
                'impacto_percentual_fmt': 'Impacto %',
                'meta_atingida': 'Meta Atingida'
            }
            
            tabela_exibir.columns = [colunas_rename.get(col, col) for col in tabela_exibir.columns]
            
            # Exibir tabela com formatação condicional
            if 'Meta Atingida' in tabela_exibir.columns:
                st.dataframe(
                    tabela_exibir.style.apply(
                        lambda x: ['background-color: rgba(76, 175, 80, 0.2)' 
                                  if x.name == 'Meta Atingida' and x 
                                  else 'background-color: rgba(244, 67, 54, 0.2)' 
                                  if x.name == 'Meta Atingida' and pd.notna(x) and not x 
                                  else '' for i in x],
                        axis=1
                    )
                )
            else:
                st.dataframe(tabela_exibir)
            
            # Adicionar análise comparativa
            st.markdown("---")
            st.markdown("### Análise e Recomendações")
            
            # Criar colunas para mostrar recomendações e visualização
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # Recomendações com base no modelo e resultados
                if modelo == "fixo":
                    st.markdown(f"""
                    **Análise do modelo de Comissão Fixa:**
                    
                    Com um salário base de {formatar_real(salario_base_mensal)} por mês e comissão de {comissao_pct}%, 
                    o custo total da folha para {num_meses} {'mês' if num_meses == 1 else 'meses'} representa {percentual_folha:.2f}% das vendas.
                    
                    **Projeção mensal média:**
                    - Salário base total: {formatar_real(salario_base_mensal * len(vendedores_para_simular))}
                    - Comissões (média): {formatar_real(total_comissao / num_meses)}
                    - Custo total mensal: {formatar_real(total_salario / num_meses)}
                    
                    **Pontos de atenção:**
                    - Vendedores com alto volume recebem proporcionalmente mais
                    - Não há incentivo específico para atingir metas
                    - Custo previsível e fácil de calcular
                    
                    **Recomendação:** 
                    Este modelo é indicado se você valoriza simplicidade e transparência.
                    {"Considere reduzir o percentual de comissão para melhorar a lucratividade." if percentual_folha > 12 else ""}
                    {"Você pode aumentar o percentual de comissão para motivar ainda mais a equipe." if percentual_folha < 5 else ""}
                    """)
                elif modelo == "meta":
                    meta_desc = f"valor fixo de {formatar_real(parametros.get('meta_valor', 0))}" if parametros.get('meta_tipo') == 'valor' else f"{parametros.get('meta_percentual', 0)}% acima da média"
                    st.markdown(f"""
                    **Análise do modelo de Comissão com Meta:**
                    
                    Com salário base de {formatar_real(salario_base_mensal)} por mês, comissão base de {comissao_pct}% 
                    e meta de {meta_desc}, o custo total para {num_meses} {'mês' if num_meses == 1 else 'meses'} representa {percentual_folha:.2f}% das vendas.
                    
                    **Projeção mensal média:**
                    - Salário base total: {formatar_real(salario_base_mensal * len(vendedores_para_simular))}
                    - Comissões (média): {formatar_real(total_comissao / num_meses)}
                    - Custo total mensal: {formatar_real(total_salario / num_meses)}
                    
                    **Pontos de atenção:**
                    - {"Apenas " + str(sum(df_simulacao['meta_atingida'] == True)) + " de " + str(len(df_simulacao)) + " vendedores atingiram a meta" if 'meta_atingida' in df_simulacao.columns else "Não há dados suficientes sobre atingimento de metas"}
                    - {"A meta parece muito desafiadora, considere ajustá-la para motivar a equipe." if 'meta_atingida' in df_simulacao.columns and sum(df_simulacao['meta_atingida']) < len(df_simulacao) / 3 else ""}
                    - {"A meta parece muito fácil, considere aumentá-la para otimizar custos." if 'meta_atingida' in df_simulacao.columns and sum(df_simulacao['meta_atingida']) > len(df_simulacao) * 0.8 else ""}
                    
                    **Recomendação:** 
                    Este modelo é ideal para estabelecer objetivos claros e impulsionar resultados.
                    {"Uma meta ideal deve ser desafiadora mas atingível. Cerca de 30-50% dos vendedores devem conseguir atingi-la." if 'meta_atingida' in df_simulacao.columns else ""}
                    """)
                elif modelo == "progressivo":
                    st.markdown(f"""
                    **Análise do modelo de Comissão Progressiva:**
                    
                    Com salário base de {formatar_real(salario_base_mensal)} por mês e faixas progressivas de comissão, 
                    o custo total para {num_meses} {'mês' if num_meses == 1 else 'meses'} representa {percentual_folha:.2f}% das vendas.
                    
                    **Projeção mensal média:**
                    - Salário base total: {formatar_real(salario_base_mensal * len(vendedores_para_simular))}
                    - Comissões (média): {formatar_real(total_comissao / num_meses)}
                    - Custo total mensal: {formatar_real(total_salario / num_meses)}
                    
                    **Pontos de atenção:**
                    - As faixas de valor devem estar alinhadas com o volume de vendas da sua equipe
                    - {"A maioria dos vendedores está na faixa 1, considere ajustar os valores para melhor distribuição." if (df_simulacao['comissao_pct'] == comissao_1).sum() > len(df_simulacao) * 0.7 else ""}
                    - {"Nenhum vendedor atingiu a faixa 3, considere reduzir o valor mínimo da faixa 3." if (df_simulacao['comissao_pct'] == comissao_3).sum() == 0 else ""}
                    
                    **Recomendação:** 
                    Este modelo é excelente para motivar os vendedores a buscarem volumes cada vez maiores.
                    Uma distribuição ideal teria cerca de 60% na faixa 1, 30% na faixa 2 e 10% na faixa 3.
                    """)
            
            with col2:
                # Gráfico de barras com salário total vs vendas
                fig = go.Figure()
                
                # Ordenar por valor de vendas
                df_ord = df_simulacao.sort_values('total_vendas', ascending=False)
                
                # Barras para total de vendas
                fig.add_trace(go.Bar(
                    x=df_ord[coluna_vendedor],
                    y=df_ord['total_vendas'],
                    name="Total de Vendas",
                    marker_color='rgba(55, 128, 191, 0.7)',
                    hoverinfo='text',
                    hovertext=[f"{vendedor}<br>Vendas: {formatar_real(val)}" 
                              for vendedor, val in zip(df_ord[coluna_vendedor], df_ord['total_vendas'])]
                ))
                
                # Barras para salário total (em um eixo secundário)
                fig.add_trace(go.Bar(
                    x=df_ord[coluna_vendedor],
                    y=df_ord['salario_total'],
                    name="Salário Total",
                    marker_color='rgba(46, 204, 113, 0.8)',
                    hoverinfo='text',
                    hovertext=[f"{vendedor}<br>Salário: {formatar_real(val)}" 
                              for vendedor, val in zip(df_ord[coluna_vendedor], df_ord['salario_total'])]
                ))
                
                # Layout
                fig.update_layout(
                    title=f"Comparativo: Vendas vs. Salário ({num_meses} {'mês' if num_meses == 1 else 'meses'})",
                    barmode='group',
                    yaxis=dict(
                        title="Valores (R$)",
                        showgrid=True,
                        gridcolor='rgba(0,0,0,0.1)'
                    ),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    height=400,
                    margin=dict(t=50, l=50, r=50, b=100)
                )
                
                # Ajustar eixo x
                fig.update_xaxes(tickangle=45)
                
                # Exibir
                st.plotly_chart(fig, use_container_width=True)
                
                # Adicionar métricas de resumo
                custo_por_real_vendido = (total_salario / total_vendas) * 100 if total_vendas > 0 else 0
                st.metric(
                    "Custo por real vendido",
                    f"{custo_por_real_vendido:.2f} centavos",
                    help="Quanto custa em folha de pagamento cada R$ 1,00 vendido"
                )
                
                # Comparar com referências do mercado
                if custo_por_real_vendido < 5:
                    st.success("Custo muito abaixo da média de mercado (5-10 centavos por real)")
                elif custo_por_real_vendido < 10:
                    st.info("Custo dentro da média de mercado (5-10 centavos por real)")
                else:
                    st.warning("Custo acima da média de mercado (5-10 centavos por real)")
                    
            # Mostrar projeção mensal
            st.markdown("### Projeção de Custo Mensal")
            
            # Criar tabela de projeção mensal
            projecao_mensal = pd.DataFrame({
                'Item': ['Salário Base', 'Comissões', 'Total da Folha'],
                'Valor Mensal': [
                    formatar_real(df_simulacao['salario_base'].sum() / num_meses),
                    formatar_real(df_simulacao['comissao_valor'].sum() / num_meses),
                    formatar_real(df_simulacao['salario_total'].sum() / num_meses)
                ],
                'Percentual das Vendas': [
                    f"{(df_simulacao['salario_base'].sum() / total_vendas) * 100:.2f}%",
                    f"{(df_simulacao['comissao_valor'].sum() / total_vendas) * 100:.2f}%",
                    f"{percentual_folha:.2f}%"
                ]
            })
            
            st.table(projecao_mensal)

# Função auxiliar para simulação de comissões mensais
def simular_comissao_mensal(vendas_por_mes, modelo, parametros, coluna_vendedor):
    """
    Simula diferentes modelos de comissionamento para os vendedores com base em dados mensais.
    
    Args:
        vendas_por_mes: DataFrame com vendas por vendedor por mês
        modelo: Tipo de modelo de comissão ('fixo', 'progressivo', 'meta')
        parametros: Dicionário com parâmetros do modelo
        coluna_vendedor: Nome da coluna que contém os nomes dos vendedores
        
    Returns:
        DataFrame com simulação de comissões
    """
    # Verificar se temos dados
    if vendas_por_mes.empty:
        return None, None
    
    # Agrupar por vendedor para obter métricas agregadas
    metricas_por_vendedor = vendas_por_mes.groupby(coluna_vendedor).agg({
        'total_vendas': 'mean',  # Média mensal de vendas
        'qtd_vendas': 'mean'     # Média mensal de quantidade
    }).reset_index()
    
    # Calcular ticket médio
    metricas_por_vendedor['ticket_medio'] = (
        metricas_por_vendedor['total_vendas'] / metricas_por_vendedor['qtd_vendas']
    ).fillna(0)
    
    # Agora podemos chamar a função original com os dados mensais
    return simular_comissao(metricas_por_vendedor, modelo, parametros, None)

# Função para análise avançada de comissões
def analise_avancada_comissoes(metricas_vendedores, vendas_mensais, coluna_vendedor, coluna_valor):
    """Implementa uma análise avançada e detalhada de modelos de comissionamento"""
    
    st.markdown("""
    ## Análise Avançada de Comissionamento
    
    Esta seção permite uma análise completa dos diferentes modelos de comissionamento e seus impactos financeiros na empresa.
    Você pode ajustar todos os parâmetros e comparar diferentes cenários lado a lado.
    """)
    
    # Definir modelos de comissionamento
    modelos_comissao = [
        "Sem comissão (apenas salário fixo)",
        "Comissão simples (percentual fixo)",
        "Comissão atingindo meta (tudo ou nada)",
        "Comissão base + bônus por meta",
        "Comissão progressiva (faixas)",
        "Comissão progressiva por metas"
    ]
    
    # Interface para seleção e comparação de modelos
    st.markdown("### Selecione os modelos para comparação")
    
    col1, col2 = st.columns(2)
    
    with col1:
        modelo_1 = st.selectbox(
            "Modelo 1", 
            options=modelos_comissao,
            index=1,
            help="Primeiro modelo para comparação"
        )
    
    with col2:
        modelo_2 = st.selectbox(
            "Modelo 2", 
            options=modelos_comissao,
            index=4,
            help="Segundo modelo para comparação"
        )
    
    # Configuração dos parâmetros para cada modelo
    st.markdown("---")
    st.markdown("### Configuração dos Modelos")
    
    col1, col2 = st.columns(2)
    
    # Converter para formatos internos
    def to_internal_model(modelo_selecionado):
        if "Sem comissão" in modelo_selecionado:
            return "fixo_zerado"
        elif "Comissão simples" in modelo_selecionado:
            return "fixo"
        elif "tudo ou nada" in modelo_selecionado:
            return "meta_binaria"
        elif "base + bônus" in modelo_selecionado:
            return "meta_bonus"
        elif "faixas" in modelo_selecionado:
            return "progressivo"
        elif "progressiva por metas" in modelo_selecionado:
            return "progressivo_metas"
    
    modelo_1_interno = to_internal_model(modelo_1)
    modelo_2_interno = to_internal_model(modelo_2)
    
    # Parâmetros para modelo 1
    with col1:
        st.subheader(f"Parâmetros: {modelo_1}")
        
        salario_base_1 = st.number_input(
            "Salário base mensal (R$)", 
            min_value=500, 
            max_value=10000, 
            value=3000, 
            step=100,
            key="salario_base_1"
        )
        
        params_1 = {'salario_base': salario_base_1}
        
        if modelo_1_interno == "fixo":
            comissao_pct_1 = st.number_input(
                "Percentual de comissão (%)", 
                min_value=0.0, 
                max_value=10.0, 
                value=1.0, 
                step=0.1,
                format="%.2f",
                key="comissao_pct_1",
                help="Percentual sobre o valor total de vendas"
            )
            params_1['comissao_pct'] = comissao_pct_1
            
        elif modelo_1_interno == "fixo_zerado":
            st.info("Este modelo usa apenas o salário fixo, sem comissionamento.")
            params_1['comissao_pct'] = 0.0
            
        elif modelo_1_interno in ["meta_binaria", "meta_bonus"]:
            comissao_pct_1 = st.number_input(
                "Percentual de comissão base (%)" if modelo_1_interno == "meta_bonus" else "Percentual de comissão (%)", 
                min_value=0.0, 
                max_value=10.0, 
                value=1.0, 
                step=0.1,
                format="%.2f",
                key="comissao_pct_1"
            )
            params_1['comissao_pct'] = comissao_pct_1
            
            if modelo_1_interno == "meta_bonus":
                bonus_pct_1 = st.number_input(
                    "Bônus adicional ao atingir meta (%)", 
                    min_value=0.1, 
                    max_value=5.0, 
                    value=0.5, 
                    step=0.1,
                    format="%.2f",
                    key="bonus_pct_1"
                )
                params_1['bonus_pct'] = bonus_pct_1
            
            meta_tipo_1 = st.radio(
                "Tipo de meta",
                options=["Valor fixo", "Percentual acima da média"],
                key="meta_tipo_1"
            )
            
            if meta_tipo_1 == "Valor fixo":
                media_vendas = metricas_vendedores['total_vendas'].mean()
                meta_valor_1 = st.number_input(
                    "Valor da meta mensal (R$)", 
                    min_value=1000, 
                    max_value=int(media_vendas * 3), 
                    value=int(media_vendas),
                    step=1000,
                    key="meta_valor_1"
                )
                params_1['meta_tipo'] = 'valor'
                params_1['meta_valor'] = meta_valor_1
            else:
                meta_percentual_1 = st.number_input(
                    "Meta: percentual acima da média (%)", 
                    min_value=0, 
                    max_value=50, 
                    value=5,
                    step=1,
                    key="meta_percentual_1"
                )
                params_1['meta_tipo'] = 'media'
                params_1['meta_percentual'] = meta_percentual_1
            
            params_1['apenas_com_meta'] = modelo_1_interno == "meta_binaria"
            
        elif modelo_1_interno == "progressivo":
            st.markdown("#### Configure as faixas de comissão")
            
            faixa1_max_1 = st.number_input(
                "Faixa 1: até (R$)", 
                min_value=5000, 
                max_value=200000, 
                value=30000, 
                step=5000,
                key="faixa1_max_1"
            )
            
            faixa1_pct_1 = st.number_input(
                "Comissão Faixa 1 (%)", 
                min_value=0.0, 
                max_value=5.0, 
                value=0.3, 
                step=0.1,
                format="%.2f",
                key="faixa1_pct_1"
            )
            
            faixa2_max_1 = st.number_input(
                "Faixa 2: até (R$)", 
                min_value=faixa1_max_1 + 5000, 
                max_value=500000, 
                value=80000, 
                step=10000,
                key="faixa2_max_1"
            )
            
            faixa2_pct_1 = st.number_input(
                "Comissão Faixa 2 (%)", 
                min_value=0.0, 
                max_value=5.0, 
                value=0.8, 
                step=0.1,
                format="%.2f",
                key="faixa2_pct_1"
            )
            
            faixa3_pct_1 = st.number_input(
                f"Comissão Faixa 3 (acima de {formatar_real(faixa2_max_1)}) (%)", 
                min_value=0.0, 
                max_value=10.0, 
                value=1.5, 
                step=0.1,
                format="%.2f",
                key="faixa3_pct_1"
            )
            
            # Configurar faixas
            faixas_1 = [
                {'valor_min': 0, 'valor_max': faixa1_max_1, 'comissao_pct': faixa1_pct_1},
                {'valor_min': faixa1_max_1, 'valor_max': faixa2_max_1, 'comissao_pct': faixa2_pct_1},
                {'valor_min': faixa2_max_1, 'valor_max': float('inf'), 'comissao_pct': faixa3_pct_1}
            ]
            
            params_1['faixas'] = faixas_1
    
    # Parâmetros para modelo 2
    with col2:
        st.subheader(f"Parâmetros: {modelo_2}")
        
        salario_base_2 = st.number_input(
            "Salário base mensal (R$)", 
            min_value=500, 
            max_value=10000, 
            value=2500, 
            step=100,
            key="salario_base_2"
        )
        
        params_2 = {'salario_base': salario_base_2}
        
        if modelo_2_interno == "fixo":
            comissao_pct_2 = st.number_input(
                "Percentual de comissão (%)", 
                min_value=0.0, 
                max_value=10.0, 
                value=1.5, 
                step=0.1,
                format="%.2f",
                key="comissao_pct_2",
                help="Percentual sobre o valor total de vendas"
            )
            params_2['comissao_pct'] = comissao_pct_2
            
        elif modelo_2_interno == "fixo_zerado":
            st.info("Este modelo usa apenas o salário fixo, sem comissionamento.")
            params_2['comissao_pct'] = 0.0
            
        elif modelo_2_interno in ["meta_binaria", "meta_bonus"]:
            comissao_pct_2 = st.number_input(
                "Percentual de comissão base (%)" if modelo_2_interno == "meta_bonus" else "Percentual de comissão (%)", 
                min_value=0.0, 
                max_value=10.0, 
                value=0.5, 
                step=0.1,
                format="%.2f",
                key="comissao_pct_2"
            )
            params_2['comissao_pct'] = comissao_pct_2
            
            if modelo_2_interno == "meta_bonus":
                bonus_pct_2 = st.number_input(
                    "Bônus adicional ao atingir meta (%)", 
                    min_value=0.1, 
                    max_value=5.0, 
                    value=1.0, 
                    step=0.1,
                    format="%.2f",
                    key="bonus_pct_2"
                )
                params_2['bonus_pct'] = bonus_pct_2
            
            meta_tipo_2 = st.radio(
                "Tipo de meta",
                options=["Valor fixo", "Percentual acima da média"],
                key="meta_tipo_2"
            )
            
            if meta_tipo_2 == "Valor fixo":
                media_vendas = metricas_vendedores['total_vendas'].mean()
                meta_valor_2 = st.number_input(
                    "Valor da meta mensal (R$)", 
                    min_value=1000, 
                    max_value=int(media_vendas * 3), 
                    value=int(media_vendas * 1.1),
                    step=1000,
                    key="meta_valor_2"
                )
                params_2['meta_tipo'] = 'valor'
                params_2['meta_valor'] = meta_valor_2
            else:
                meta_percentual_2 = st.number_input(
                    "Meta: percentual acima da média (%)", 
                    min_value=0, 
                    max_value=50, 
                    value=10,
                    step=1,
                    key="meta_percentual_2"
                )
                params_2['meta_tipo'] = 'media'
                params_2['meta_percentual'] = meta_percentual_2
            
            params_2['apenas_com_meta'] = modelo_2_interno == "meta_binaria"
            
        elif modelo_2_interno == "progressivo":
            st.markdown("#### Configure as faixas de comissão")
            
            faixa1_max_2 = st.number_input(
                "Faixa 1: até (R$)", 
                min_value=5000, 
                max_value=200000, 
                value=40000, 
                step=5000,
                key="faixa1_max_2"
            )
            
            faixa1_pct_2 = st.number_input(
                "Comissão Faixa 1 (%)", 
                min_value=0.0, 
                max_value=5.0, 
                value=0.5, 
                step=0.1,
                format="%.2f",
                key="faixa1_pct_2"
            )
            
            faixa2_max_2 = st.number_input(
                "Faixa 2: até (R$)", 
                min_value=faixa1_max_2 + 5000, 
                max_value=500000, 
                value=100000, 
                step=10000,
                key="faixa2_max_2"
            )
            
            faixa2_pct_2 = st.number_input(
                "Comissão Faixa 2 (%)", 
                min_value=0.0, 
                max_value=5.0, 
                value=1.0, 
                step=0.1,
                format="%.2f",
                key="faixa2_pct_2"
            )
            
            faixa3_pct_2 = st.number_input(
                f"Comissão Faixa 3 (acima de {formatar_real(faixa2_max_2)}) (%)", 
                min_value=0.0, 
                max_value=10.0, 
                value=2.0, 
                step=0.1,
                format="%.2f",
                key="faixa3_pct_2"
            )
            
            # Configurar faixas
            faixas_2 = [
                {'valor_min': 0, 'valor_max': faixa1_max_2, 'comissao_pct': faixa1_pct_2},
                {'valor_min': faixa1_max_2, 'valor_max': faixa2_max_2, 'comissao_pct': faixa2_pct_2},
                {'valor_min': faixa2_max_2, 'valor_max': float('inf'), 'comissao_pct': faixa3_pct_2}
            ]
            
            params_2['faixas'] = faixas_2
    
    # Executar as simulações
    st.markdown("---")
    st.markdown("## Resultados Comparativos")
    
    # Simulação adaptada para diferentes modelos
    def simular_modelo_avancado(df_vendedores, modelo, parametros, df_mensal):
        df_sim = df_vendedores.copy()
        
        # Inicializar valores
        df_sim['salario_base'] = parametros.get('salario_base', 0)
        df_sim['comissao_pct'] = 0
        df_sim['comissao_valor'] = 0
        df_sim['meta_atingida'] = None
        
        if modelo == "fixo_zerado":
            # Sem comissão, apenas salário fixo
            pass
            
        elif modelo == "fixo":
            # Modelo de comissão fixa
            comissao_pct = parametros.get('comissao_pct', 0)
            df_sim['comissao_pct'] = comissao_pct
            df_sim['comissao_valor'] = df_sim['total_vendas'] * (comissao_pct / 100)
            
        elif modelo in ["meta_binaria", "meta_bonus"]:
            comissao_pct = parametros.get('comissao_pct', 0)
            meta_tipo = parametros.get('meta_tipo', 'valor')
            apenas_com_meta = parametros.get('apenas_com_meta', False)
            
            # Definir a meta
            if meta_tipo == 'valor':
                meta_valor = parametros.get('meta_valor', 50000)
                df_sim['meta_atingida'] = df_sim['total_vendas'] >= meta_valor
                df_sim['meta_valor'] = meta_valor
            else:  # meta_tipo == 'media'
                meta_percentual = parametros.get('meta_percentual', 10)
                media_vendas = df_sim['total_vendas'].mean()
                meta_valor = media_vendas * (1 + meta_percentual / 100)
                df_sim['meta_atingida'] = df_sim['total_vendas'] >= meta_valor
                df_sim['meta_valor'] = meta_valor
            
            # Aplicar comissão baseada na meta
            if apenas_com_meta:
                # Comissão apenas se atingir meta
                df_sim['comissao_pct'] = np.where(df_sim['meta_atingida'], comissao_pct, 0)
            else:
                # Comissão base + bônus
                bonus_pct = parametros.get('bonus_pct', 0.5)
                df_sim['comissao_pct'] = np.where(df_sim['meta_atingida'], 
                                               comissao_pct + bonus_pct, 
                                               comissao_pct)
            
            df_sim['comissao_valor'] = df_sim['total_vendas'] * (df_sim['comissao_pct'] / 100)
            
        elif modelo == "progressivo":
            # Modelo com faixas progressivas
            faixas = parametros.get('faixas', [])
            
            if faixas:
                # Função para calcular comissão progressiva
                def calcular_comissao_progressiva(total_vendas):
                    for faixa in faixas:
                        if faixa['valor_min'] <= total_vendas < faixa['valor_max']:
                            return faixa['comissao_pct'], total_vendas * (faixa['comissao_pct'] / 100)
                    # Caso não encontre faixa (improvável com a última sendo infinita)
                    return 0, 0
                
                # Aplicar a função a cada vendedor
                resultados = df_sim['total_vendas'].apply(calcular_comissao_progressiva)
                df_sim['comissao_pct'] = [r[0] for r in resultados]
                df_sim['comissao_valor'] = [r[1] for r in resultados]
        
        # Calcular totais
        df_sim['salario_total'] = df_sim['salario_base'] + df_sim['comissao_valor']
        df_sim['impacto_percentual'] = (df_sim['comissao_valor'] / df_sim['total_vendas']) * 100
        
        # Simulação mensal
        df_mensal_sim = None
        if df_mensal is not None and not df_mensal.empty:
            # Aplicar o mesmo modelo mês a mês
            resultados_mensais = []
            
            # Agrupar por mês
            for mes in df_mensal['mes_ano'].unique():
                df_mes = df_mensal[df_mensal['mes_ano'] == mes].copy()
                
                # Aplicar o mesmo modelo
                df_mes_sim = df_mes.copy()
                df_mes_sim['salario_base'] = parametros.get('salario_base', 0) / len(df_mensal['mes_ano'].unique())
                df_mes_sim['comissao_pct'] = 0
                df_mes_sim['comissao_valor'] = 0
                
                if modelo == "fixo":
                    comissao_pct = parametros.get('comissao_pct', 0)
                    df_mes_sim['comissao_pct'] = comissao_pct
                    df_mes_sim['comissao_valor'] = df_mes_sim['total_vendas'] * (comissao_pct / 100)
                
                # Adicionar ao resultado
                df_mes_sim['modelo'] = modelo
                resultados_mensais.append(df_mes_sim)
            
            if resultados_mensais:
                df_mensal_sim = pd.concat(resultados_mensais)
        
        return df_sim, df_mensal_sim
    
    # Executar simulações para ambos os modelos
    df_sim_1, df_mensal_1 = simular_modelo_avancado(metricas_vendedores, modelo_1_interno, params_1, vendas_mensais)
    df_sim_2, df_mensal_2 = simular_modelo_avancado(metricas_vendedores, modelo_2_interno, params_2, vendas_mensais)
    
    # Exibir resumo comparativo
    col1, col2 = st.columns(2)
    
    # Métricas para modelo 1
    with col1:
        total_vendas_1 = df_sim_1['total_vendas'].sum()
        total_comissao_1 = df_sim_1['comissao_valor'].sum()
        total_salario_1 = df_sim_1['salario_total'].sum()
        custo_percentual_1 = (total_salario_1 / total_vendas_1) * 100
        
        st.subheader(f"Modelo 1: {modelo_1}")
        st.metric("Custo total mensal", formatar_real(total_salario_1))
        st.metric("Custo de comissões", formatar_real(total_comissao_1))
        st.metric("Impacto sobre vendas", f"{custo_percentual_1:.2f}% das vendas")
        
        # Avaliar custo-benefício
        if custo_percentual_1 < 4:
            st.success("✅ Custo extremamente eficiente, abaixo de 4% das vendas")
        elif custo_percentual_1 < 8:
            st.success("✅ Custo eficiente, entre 4% e 8% das vendas")
        elif custo_percentual_1 < 12:
            st.info("ℹ️ Custo moderado, entre 8% e 12% das vendas")
        elif custo_percentual_1 < 16:
            st.warning("⚠️ Custo elevado, entre 12% e 16% das vendas")
        else:
            st.error("❌ Custo muito alto, acima de 16% das vendas")
        
        # Salário médio, mínimo e máximo
        st.markdown(f"""
        **Salário médio:** {formatar_real(df_sim_1['salario_total'].mean())}  
        **Menor salário:** {formatar_real(df_sim_1['salario_total'].min())}  
        **Maior salário:** {formatar_real(df_sim_1['salario_total'].max())}
        """)
    
    # Métricas para modelo 2
    with col2:
        total_vendas_2 = df_sim_2['total_vendas'].sum()
        total_comissao_2 = df_sim_2['comissao_valor'].sum()
        total_salario_2 = df_sim_2['salario_total'].sum()
        custo_percentual_2 = (total_salario_2 / total_vendas_2) * 100
        
        st.subheader(f"Modelo 2: {modelo_2}")
        st.metric("Custo total mensal", formatar_real(total_salario_2))
        st.metric("Custo de comissões", formatar_real(total_comissao_2))
        st.metric("Impacto sobre vendas", f"{custo_percentual_2:.2f}% das vendas")
        
        # Avaliar custo-benefício
        if custo_percentual_2 < 4:
            st.success("✅ Custo extremamente eficiente, abaixo de 4% das vendas")
        elif custo_percentual_2 < 8:
            st.success("✅ Custo eficiente, entre 4% e 8% das vendas")
        elif custo_percentual_2 < 12:
            st.info("ℹ️ Custo moderado, entre 8% e 12% das vendas")
        elif custo_percentual_2 < 16:
            st.warning("⚠️ Custo elevado, entre 12% e 16% das vendas")
        else:
            st.error("❌ Custo muito alto, acima de 16% das vendas")
        
        # Salário médio, mínimo e máximo
        st.markdown(f"""
        **Salário médio:** {formatar_real(df_sim_2['salario_total'].mean())}  
        **Menor salário:** {formatar_real(df_sim_2['salario_total'].min())}  
        **Maior salário:** {formatar_real(df_sim_2['salario_total'].max())}
        """)
    
    # Comparação direta
    st.markdown("---")
    st.markdown("### Comparação Direta entre os Modelos")
    
    # Diferença de custos
    diferenca_custo = total_salario_1 - total_salario_2
    diferenca_percentual = diferenca_custo / total_salario_2 * 100
    
    if diferenca_custo > 0:
        st.warning(f"O Modelo 1 é **{formatar_real(diferenca_custo)}** mais caro que o Modelo 2 (diferença de {diferenca_percentual:.1f}%)")
    elif diferenca_custo < 0:
        st.success(f"O Modelo 1 é **{formatar_real(abs(diferenca_custo))}** mais econômico que o Modelo 2 (diferença de {abs(diferenca_percentual):.1f}%)")
    else:
        st.info("Ambos os modelos têm o mesmo custo total para a empresa.")
    
    # Gráfico de barras comparativo por vendedor
    st.markdown("### Salário Total por Vendedor")
    
    # Preparar dados para o gráfico
    df_comparativo = pd.DataFrame({
        'Vendedor': df_sim_1[coluna_vendedor],
        f'Modelo 1: {modelo_1}': df_sim_1['salario_total'],
        f'Modelo 2: {modelo_2}': df_sim_2['salario_total']
    })
    
    # Reorganizar para formato longo
    df_long = df_comparativo.melt(
        id_vars=['Vendedor'],
        value_vars=[f'Modelo 1: {modelo_1}', f'Modelo 2: {modelo_2}'],
        var_name='Modelo',
        value_name='Salário Total'
    )
    
    # Criar gráfico de barras
    fig = px.bar(
        df_long,
        x='Vendedor',
        y='Salário Total',
        color='Modelo',
        barmode='group',
        title="Comparativo de Salário Total por Vendedor",
        color_discrete_sequence=obter_paleta_cores(2)
    )
    
    fig.update_layout(
        xaxis_title="Vendedor",
        yaxis_title="Salário Total (R$)",
        legend_title="Modelo de Comissão",
        height=500,
        margin=dict(t=50, l=50, r=50, b=100)
    )
    
    fig.update_xaxes(tickangle=45)
    
    # Adicionar rótulos de valor
    for trace in fig.data:
        y_data = trace.y
        trace.text = [formatar_real(y) for y in y_data]
        trace.textposition = 'outside'
        trace.textfont.size = 10
    
    # Exibir gráfico
    st.plotly_chart(fig, use_container_width=True)
    
    # Análise detalhada dos resultados
    with st.expander("Detalhamento dos Resultados"):
        # Juntar os resultados lado a lado
        df_detalhado = pd.DataFrame({
            'Vendedor': df_sim_1[coluna_vendedor],
            'Vendas': df_sim_1['total_vendas'].apply(lambda x: formatar_real(x)),
            'Salário 1': df_sim_1['salario_total'].apply(lambda x: formatar_real(x)),
            'Comissão 1': df_sim_1['comissao_valor'].apply(lambda x: formatar_real(x)),
            'Impacto 1 (%)': df_sim_1['impacto_percentual'].apply(lambda x: f"{x:.2f}%"),
            'Salário 2': df_sim_2['salario_total'].apply(lambda x: formatar_real(x)),
            'Comissão 2': df_sim_2['comissao_valor'].apply(lambda x: formatar_real(x)),
            'Impacto 2 (%)': df_sim_2['impacto_percentual'].apply(lambda x: f"{x:.2f}%"),
            'Diferença': (df_sim_1['salario_total'] - df_sim_2['salario_total']).apply(
                lambda x: f"+{formatar_real(x)}" if x > 0 else formatar_real(x)
            )
        })
        
        st.dataframe(df_detalhado)
    
    # Visão mensal (limitada ao modelo fixo por simplicidade)
    if df_mensal_1 is not None and df_mensal_2 is not None:
        st.markdown("### Análise de Impacto Mensal")
        
        # Agrupar por mês
        df_mensal_agrupado_1 = df_mensal_1.groupby('mes_ano').agg({
            'comissao_valor': 'sum',
            'total_vendas': 'sum'
        }).reset_index()
        
        df_mensal_agrupado_2 = df_mensal_2.groupby('mes_ano').agg({
            'comissao_valor': 'sum',
            'total_vendas': 'sum'
        }).reset_index()
        
        # Juntar os dataframes
        df_mensal_comp = pd.merge(
            df_mensal_agrupado_1, 
            df_mensal_agrupado_2,
            on='mes_ano', 
            suffixes=('_1', '_2')
        )
        
        # Calcular percentuais
        df_mensal_comp['pct_1'] = (df_mensal_comp['comissao_valor_1'] / df_mensal_comp['total_vendas_1']) * 100
        df_mensal_comp['pct_2'] = (df_mensal_comp['comissao_valor_2'] / df_mensal_comp['total_vendas_2']) * 100
        
        # Adicionar salário base mensal (dividido pelo número de meses)
        num_meses = len(df_mensal_comp)
        if num_meses > 0:
            df_mensal_comp['salario_base_1'] = salario_base_1
            df_mensal_comp['salario_base_2'] = salario_base_2
            df_mensal_comp['salario_total_1'] = df_mensal_comp['salario_base_1'] + df_mensal_comp['comissao_valor_1']
            df_mensal_comp['salario_total_2'] = df_mensal_comp['salario_base_2'] + df_mensal_comp['comissao_valor_2']
            df_mensal_comp['impacto_total_1'] = (df_mensal_comp['salario_total_1'] / df_mensal_comp['total_vendas_1']) * 100
            df_mensal_comp['impacto_total_2'] = (df_mensal_comp['salario_total_2'] / df_mensal_comp['total_vendas_2']) * 100
        
        # Criar gráfico comparativo mensal
        fig = go.Figure()
        
        # Barras para modelo 1
        fig.add_trace(go.Bar(
            x=df_mensal_comp['mes_ano'],
            y=df_mensal_comp['salario_total_1'],
            name=f"Custo Total - {modelo_1}",
            marker_color=obter_paleta_cores(1)[0],
            text=[formatar_real(val) for val in df_mensal_comp['salario_total_1']],
            textposition='auto'
        ))
        
        # Barras para modelo 2
        fig.add_trace(go.Bar(
            x=df_mensal_comp['mes_ano'],
            y=df_mensal_comp['salario_total_2'],
            name=f"Custo Total - {modelo_2}",
            marker_color=obter_paleta_cores(2)[1],
            text=[formatar_real(val) for val in df_mensal_comp['salario_total_2']],
            textposition='auto'
        ))
        
        # Linhas para percentual sobre vendas
        fig.add_trace(go.Scatter(
            x=df_mensal_comp['mes_ano'],
            y=df_mensal_comp['impacto_total_1'],
            name=f"% sobre Vendas - {modelo_1}",
            mode='lines+markers',
            line=dict(color='rgba(31, 119, 180, 0.8)', width=2, dash='dot'),
            yaxis="y2"
        ))
        
        fig.add_trace(go.Scatter(
            x=df_mensal_comp['mes_ano'],
            y=df_mensal_comp['impacto_total_2'],
            name=f"% sobre Vendas - {modelo_2}",
            mode='lines+markers',
            line=dict(color='rgba(255, 127, 14, 0.8)', width=2, dash='dot'),
            yaxis="y2"
        ))
        
        # Configurações de layout
        fig.update_layout(
            title="Comparativo Mensal de Custos",
            barmode='group',
            xaxis_title="Mês",
            yaxis_title="Custo Total (R$)",
            yaxis2=dict(
                title="% sobre Vendas",
                overlaying="y",
                side="right",
                showgrid=False
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            height=500,
            margin=dict(t=70, l=50, r=50, b=50)
        )
        
        # Exibir gráfico
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela detalhada
        with st.expander("Detalhamento Mensal"):
            df_mensal_tabela = pd.DataFrame({
                'Mês': df_mensal_comp['mes_ano'],
                'Vendas': df_mensal_comp['total_vendas_1'].apply(lambda x: formatar_real(x)),
                f'Custo Total ({modelo_1})': df_mensal_comp['salario_total_1'].apply(lambda x: formatar_real(x)),
                f'Impacto % ({modelo_1})': df_mensal_comp['impacto_total_1'].apply(lambda x: f"{x:.2f}%"),
                f'Custo Total ({modelo_2})': df_mensal_comp['salario_total_2'].apply(lambda x: formatar_real(x)),
                f'Impacto % ({modelo_2})': df_mensal_comp['impacto_total_2'].apply(lambda x: f"{x:.2f}%"),
                'Diferença': (df_mensal_comp['salario_total_1'] - df_mensal_comp['salario_total_2']).apply(
                    lambda x: f"+{formatar_real(x)}" if x > 0 else formatar_real(x)
                )
            })
            
            st.dataframe(df_mensal_tabela)
    
    # Análise de ponto de equilíbrio
    st.markdown("---")
    st.markdown("### Análise de Ponto de Equilíbrio")
    
    st.info("""
    O ponto de equilíbrio representa o volume de vendas em que dois modelos de comissionamento têm o mesmo custo.
    Isto ajuda a decidir qual modelo é mais vantajoso com base no volume de vendas esperado.
    """)
    
    # Tentar calcular o ponto de equilíbrio
    # Para simplificar, vamos considerar apenas modelos fixos ou com meta
    pode_calcular_equilibrio = True
    
    # Para modelos progressivos, simplificar usando a primeira faixa
    if modelo_1_interno == "progressivo" and modelo_2_interno == "progressivo":
        comissao_pct_1 = params_1['faixas'][0]['comissao_pct']
        comissao_pct_2 = params_2['faixas'][0]['comissao_pct']
    elif modelo_1_interno == "progressivo":
        comissao_pct_1 = params_1['faixas'][0]['comissao_pct']
        comissao_pct_2 = params_2.get('comissao_pct', 0)
    elif modelo_2_interno == "progressivo":
        comissao_pct_1 = params_1.get('comissao_pct', 0)
        comissao_pct_2 = params_2['faixas'][0]['comissao_pct']
    else:
        comissao_pct_1 = params_1.get('comissao_pct', 0)
        comissao_pct_2 = params_2.get('comissao_pct', 0)
    
    # Calcular ponto de equilíbrio
    if pode_calcular_equilibrio:
        # Equação: salario_base_1 + (vendas * comissao_pct_1 / 100) = salario_base_2 + (vendas * comissao_pct_2 / 100)
        # Resolvendo para vendas:
        # vendas = (salario_base_2 - salario_base_1) / ((comissao_pct_1 - comissao_pct_2) / 100)
        
        if comissao_pct_1 != comissao_pct_2:
            ponto_equilibrio = (salario_base_2 - salario_base_1) / ((comissao_pct_1 - comissao_pct_2) / 100)
            
            if ponto_equilibrio > 0:
                st.success(f"""
                **Ponto de Equilíbrio:** {formatar_real(ponto_equilibrio)}
                
                - Abaixo deste valor, o modelo "{modelo_1 if comissao_pct_1 < comissao_pct_2 else modelo_2}" é mais econômico.
                - Acima deste valor, o modelo "{modelo_2 if comissao_pct_1 < comissao_pct_2 else modelo_1}" é mais econômico.
                """)
                
                # Visualização do ponto de equilíbrio
                # Criar um range de valores para plotar
                vendas_media = metricas_vendedores['total_vendas'].mean()
                x_min = 0
                x_max = max(ponto_equilibrio * 2, vendas_media * 2)
                x_range = np.linspace(x_min, x_max, 100)
                
                # Calcular custos para cada modelo
                custo_1 = salario_base_1 + (x_range * comissao_pct_1 / 100)
                custo_2 = salario_base_2 + (x_range * comissao_pct_2 / 100)
                
                # Criar dataframe para plotagem
                df_equilibrio = pd.DataFrame({
                    'Vendas': x_range,
                    f'Custo Modelo 1 ({modelo_1})': custo_1,
                    f'Custo Modelo 2 ({modelo_2})': custo_2
                })
                
                # Criar gráfico
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=df_equilibrio['Vendas'],
                    y=df_equilibrio[f'Custo Modelo 1 ({modelo_1})'],
                    name=f'Modelo 1: {modelo_1}',
                    line=dict(color=obter_paleta_cores(2)[0], width=3)
                ))
                
                fig.add_trace(go.Scatter(
                    x=df_equilibrio['Vendas'],
                    y=df_equilibrio[f'Custo Modelo 2 ({modelo_2})'],
                    name=f'Modelo 2: {modelo_2}',
                    line=dict(color=obter_paleta_cores(2)[1], width=3)
                ))
                
                # Adicionar linha vertical no ponto de equilíbrio
                fig.add_vline(
                    x=ponto_equilibrio, 
                    line_width=2, 
                    line_dash="dash", 
                    line_color="green",
                    annotation_text=f"Ponto de Equilíbrio: {formatar_real(ponto_equilibrio)}",
                    annotation_position="top",
                    annotation_font_size=12,
                    annotation_font_color="green"
                )
                
                # Configurar layout
                fig.update_layout(
                    title="Análise de Ponto de Equilíbrio entre os Modelos",
                    xaxis_title="Volume de Vendas (R$)",
                    yaxis_title="Custo Total (R$)",
                    height=500,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    margin=dict(t=70, l=50, r=50, b=50)
                )
                
                # Adicionar área do vendedor médio para referência
                fig.add_vrect(
                    x0=vendas_media * 0.9,
                    x1=vendas_media * 1.1,
                    line_width=0,
                    fillcolor="rgba(255, 235, 59, 0.2)",
                    annotation_text="Faixa de Vendas Médias",
                    annotation_position="top",
                    annotation_font_size=10,
                    annotation_font_color="black"
                )
                
                # Adicionar valores de vendedores para referência
                for i, row in metricas_vendedores.iterrows():
                    fig.add_trace(go.Scatter(
                        x=[row['total_vendas']],
                        y=[salario_base_1 + (row['total_vendas'] * comissao_pct_1 / 100)],
                        name=f"{row[coluna_vendedor]}",
                        mode='markers',
                        marker=dict(
                            size=10,
                            color=obter_paleta_cores(len(metricas_vendedores))[i],
                            symbol='circle',
                            line=dict(width=2, color='DarkSlateGrey')
                        ),
                        showlegend=False,
                        hovertemplate=f"{row[coluna_vendedor]}<br>Vendas: {formatar_real(row['total_vendas'])}"
                    ))
                
                # Exibir gráfico
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"""
                Não foi possível calcular um ponto de equilíbrio positivo entre os modelos.
                Isso indica que um modelo é sempre mais vantajoso que o outro em qualquer volume de vendas.
                
                O modelo "{modelo_1 if salario_base_1 < salario_base_2 and comissao_pct_1 < comissao_pct_2 else modelo_2}" 
                é mais econômico em todos os níveis de venda.
                """)
        else:
            st.warning(f"""
            Os modelos têm a mesma taxa de comissão ({comissao_pct_1}%), então um será sempre mais econômico que o outro.
            
            O modelo com menor salário base ({modelo_1 if salario_base_1 < salario_base_2 else modelo_2}) 
            é mais econômico em todos os níveis de venda.
            """)
    else:
        st.warning("Não foi possível calcular o ponto de equilíbrio para os modelos selecionados devido à complexidade das regras.")
    
    # Conclusão e recomendações
    st.markdown("---")
    st.markdown("## Conclusão e Recomendações")
    
    # Determinar qual modelo é mais econômico
    if custo_percentual_1 < custo_percentual_2:
        modelo_mais_economico = modelo_1
        custo_percentual_economico = custo_percentual_1
        economia = total_salario_2 - total_salario_1
        percentual_economia = abs(diferenca_percentual)
    else:
        modelo_mais_economico = modelo_2
        custo_percentual_economico = custo_percentual_2
        economia = total_salario_1 - total_salario_2
        percentual_economia = abs(diferenca_percentual)
    
    st.success(f"""
    ### Modelo Recomendado: {modelo_mais_economico}
    
    O modelo "{modelo_mais_economico}" é o mais econômico para a empresa, representando um custo de 
    **{custo_percentual_economico:.2f}%** sobre o total de vendas.
    
    Este modelo proporcionaria uma economia de **{formatar_real(economia)}** ({percentual_economia:.1f}%) 
    em relação ao outro modelo analisado.
    """)
    
    # Recomendações específicas
    st.markdown("### Recomendações:")
    
    # Análise do impacto sobre motivação e desempenho
    if "meta" in to_internal_model(modelo_mais_economico) or "progressivo" in to_internal_model(modelo_mais_economico):
        st.markdown(f"""
        - O modelo recomendado pode incentivar os vendedores a buscarem melhores desempenhos para aumentar sua remuneração.
        - Considere comunicar claramente as regras de comissionamento para que todos entendam como podem maximizar seus ganhos.
        - Monitore o desempenho após implementação para verificar se a motivação da equipe aumentou como esperado.
        """)
    else:
        st.markdown(f"""
        - O modelo recomendado é mais simples e previsível para os vendedores, o que pode reduzir competição interna.
        - Para aumentar a motivação, considere complementar este modelo com campanhas pontuais de incentivo.
        - Reavalie periodicamente para garantir que o modelo continua adequado ao crescimento da empresa.
        """)
    
    # Recomendações gerais
    st.markdown(f"""
    - Implemente o modelo por um período de teste de 3 meses antes de definir como permanente.
    - Estabeleça métricas claras para avaliar o sucesso do modelo (custo como % das vendas, satisfação dos vendedores, etc).
    - Considere oferecer treinamentos para os vendedores maximizarem seu desempenho dentro do novo sistema.
    - Revise o modelo a cada 6-12 meses para ajustá-lo à realidade atual da empresa.
    """)

# Função principal para construir o dashboard
def main():
    st.title("Dashboard Gerencial de Vendas")
    
    # Sidebar para upload de arquivo
    with st.sidebar:
        st.header("Configurações")
        
        # Verificar se há arquivos Excel no diretório atual
        import os
        excel_files = [f for f in os.listdir() if f.endswith(('.xlsx', '.xls'))]
        
        if excel_files:
            # Opção para selecionar arquivo local ou fazer upload
            file_option = st.radio(
                "Origem do arquivo:",
                ["Usar arquivo local", "Fazer upload de arquivo"],
                index=0
            )
            
            if file_option == "Usar arquivo local":
                selected_file = st.selectbox(
                    "Selecione o arquivo Excel de vendas", 
                    options=excel_files
                )
                file = selected_file  # Passar o nome do arquivo diretamente
            else:
                file = st.file_uploader("Selecione o arquivo Excel de vendas", type=["xlsx", "xls"])
        else:
            # Nenhum arquivo Excel encontrado, oferecer apenas upload
            file = st.file_uploader("Selecione o arquivo Excel de vendas", type=["xlsx", "xls"])
        
        if not file:
            st.warning("Por favor, faça o upload do arquivo de vendas.")
            # Mostrar exemplo do formato esperado
            st.markdown("""
            **Formato esperado:**
            - Colunas de data (ex: data_venda, dt_pedido)
            - Colunas de valor (ex: valor_total, vl_venda)
            - Opcionalmente, coluna de vendedor
            """)
            return
    
    # Carregar dados
    dados = carregar_dados(file)
    
    if not dados:
        st.error("Não foi possível processar o arquivo. Verifique o formato e tente novamente.")
        return
    
    df = dados['df']
    coluna_data = dados['coluna_data']
    coluna_valor = dados['coluna_valor']
    coluna_vendedor = dados.get('coluna_vendedor')
    
    with st.sidebar:
        # Data mínima e máxima para seleção
        data_min = df['data'].min()
        data_max = df['data'].max()
        
        # Usar o intervalo completo de datas como padrão
        default_start = data_min
        default_end = data_max
        
        # Seletor de período
        st.subheader("Período de Análise")
        periodo = st.date_input(
            "Selecione o período",
            value=(default_start, default_end),
            min_value=data_min,
            max_value=data_max
        )
        
        # Verificar se o período está completo
        if len(periodo) < 2:
            periodo = (periodo[0], periodo[0])  # Usar o mesmo dia para início e fim
        
        # Seletor de vendedores
        st.subheader("Filtros")
        
        if coluna_vendedor:
            vendedores_disponiveis = ["Todos"] + sorted(df[coluna_vendedor].unique().tolist())
            vendedores_selecionados = st.multiselect(
                "Selecione os vendedores",
                options=vendedores_disponiveis,
                default=["Todos"]
            )
        else:
            vendedores_selecionados = None
            st.info("Não foi identificada coluna de vendedores no arquivo.")
        
        # Filtro de horário comercial
        apenas_horario_comercial = st.checkbox(
            "Apenas horário comercial", 
            value=False,
            help="Segunda a sexta: 8h às 19h, Sábado: 8h às 17h"
        )
        
        # Botão para aplicar filtros
        st.markdown("---")
        if st.button("Atualizar Dashboard", type="primary"):
            st.success("Dashboard atualizado!")
    
    # Aplicar filtros
    df_filtrado = aplicar_filtros(
        df, 
        periodo, 
        vendedores_selecionados, 
        coluna_vendedor, 
        apenas_horario_comercial
    )
    
    # Verificar se há dados após filtro
    if df_filtrado.empty:
        st.warning("Não há dados para o período e filtros selecionados.")
        return
    
    # Calcular métricas para o período selecionado
    # Período anterior com a mesma duração para comparação
    dias_periodo = (periodo[1] - periodo[0]).days + 1
    periodo_anterior_fim = periodo[0] - timedelta(days=1)
    periodo_anterior_inicio = periodo_anterior_fim - timedelta(days=dias_periodo - 1)
    
    # Filtrar período anterior
    df_periodo_anterior = aplicar_filtros(
        df, 
        (periodo_anterior_inicio, periodo_anterior_fim), 
        vendedores_selecionados, 
        coluna_vendedor, 
        apenas_horario_comercial
    )
    
    # Calcular métricas
    metricas = gerar_metricas(df_filtrado, coluna_valor, df_periodo_anterior)
    
    # Calcular métricas mensais
    vendas_mensais = calcular_metricas_mensais(df_filtrado, coluna_valor)
    
    # Calcular métricas por vendedor
    if coluna_vendedor:
        metricas_vendedores = calcular_metricas_por_vendedor(df_filtrado, coluna_valor, coluna_vendedor)
    else:
        metricas_vendedores = pd.DataFrame()
    
    # Analisar dias da semana
    analise_dias = analisar_dias_semana(df_filtrado, coluna_valor)
    
    # Analisar horas do dia
    analise_horas = analisar_horas(df_filtrado, coluna_valor)
    
    # Criar abas para organizar o dashboard
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Visão Geral", 
        "Análise Temporal", 
        "Vendedores", 
        "Calendário",
        "Simulação de Comissões"
    ])
    
    # Tab 1: Visão Geral
    with tab1:
        st.header("Visão Geral - Período: " + 
                 f"{periodo[0].strftime('%d/%m/%Y')} a {periodo[1].strftime('%d/%m/%Y')}")
        
        # Métricas principais
        dashboard_metricas_principais(metricas)
        
        # Análise por dia da semana
        st.markdown("---")
        st.subheader("Análise por Dia da Semana")
        dashboard_dias_semana(analise_dias)
        
        # Análise por hora
        st.markdown("---")
        st.subheader("Análise por Hora do Dia")
        dashboard_horas(analise_horas)
    
    # Tab 2: Análise Temporal
    with tab2:
        st.header("Análise Temporal de Vendas")
        
        # Gráfico de evolução mensal
        st.subheader("Evolução Mensal")
        dashboard_evolucao_mensal(vendas_mensais)
        
        # Distribuição de vendas por dia/período
        st.markdown("---")
        st.subheader("Distribuição de Vendas")
        dashboard_distribuicao_vendas(df_filtrado, coluna_valor)
    
    # Tab 3: Vendedores
    with tab3:
        if coluna_vendedor and not metricas_vendedores.empty:
            st.header("Análise por Vendedor")
            dashboard_vendedores(metricas_vendedores, coluna_vendedor)
        else:
            st.info("Não há dados de vendedores para análise.")
    
    # Tab 4: Calendário de Vendas
    with tab4:
        st.header("Calendário de Vendas")
        dashboard_calendario(df_filtrado, coluna_valor)
    
    # Tab 5: Simulação de Comissões
    with tab5:
        if coluna_vendedor and not metricas_vendedores.empty:
            st.header("Simulação de Comissões")
            dashboard_simulacao_comissoes(metricas_vendedores, vendas_mensais, coluna_vendedor)
        else:
            st.info("Não há dados de vendedores para simulação de comissões.")
    
    # Adicionar rodapé
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 10px; font-size: 0.8rem; color: #777;">
        Dashboard Gerencial de Vendas - Desenvolvido com Streamlit - © 2023
    </div>
    """, unsafe_allow_html=True)

# Executar o aplicativo
if __name__ == "__main__":
    main()