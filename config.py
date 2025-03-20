"""
Arquivo de configuração para o Dashboard Gerencial de Vendas
"""

import os

# Configurações gerais
CONFIG = {
    # Nome do aplicativo
    "app_name": "Dashboard Gerencial de Vendas",
    
    # Ícone do aplicativo
    "app_icon": "📊",
    
    # Porta para servir o aplicativo (padrão do Streamlit é 8501)
    "port": 8501,
    
    # Layout do aplicativo - 'wide' ou 'centered'
    "layout": "wide",
    
    # Estado inicial da barra lateral - 'expanded' ou 'collapsed'
    "sidebar_state": "expanded",
    
    # Tema de cores - pode ser 'light' ou 'dark'
    "theme": "light",
    
    # Pasta onde os arquivos de dados serão buscados automaticamente
    "data_folder": "dados",
    
    # Nome padrão do arquivo (se nenhum for especificado)
    "default_filename": "Relatorio.xlsx",
    
    # Extensões de arquivo permitidas
    "allowed_extensions": [".xlsx", ".xls"],
    
    # Opções de cache - pode ser 'memory' ou 'disk'
    "cache_type": "memory",
    
    # Tempo de expiração do cache em segundos (3600 = 1 hora)
    "cache_ttl": 3600,
}

# Verificar e criar pasta de dados se não existir
if not os.path.exists(CONFIG["data_folder"]):
    os.makedirs(CONFIG["data_folder"])

# Caminho completo para o arquivo padrão
DEFAULT_FILE_PATH = os.path.join(CONFIG["data_folder"], CONFIG["default_filename"])