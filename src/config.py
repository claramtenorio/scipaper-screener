import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Caminhos base de todo o projeto
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = BASE_DIR / "data" / "raw" / "sample_papers.csv"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CACHE_FILE_PATH = PROCESSED_DIR / "all_evaluated_papers.csv"
APPROVED_CSV_PATH = PROCESSED_DIR / "approved_papers.csv"
APPROVED_EXCEL_PATH = PROCESSED_DIR / "approved_papers.xlsx"

# Configurações da API do Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

# Critérios padrão de inclusão e exclusão para a pesquisa, podem ser customizados
DEFAULT_RESEARCH_CRITERIA = """
CRITÉRIOS DE INCLUSÃO:
1. Artigos que aplicam Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), Agentes Autônomos (Tool Calling / Multi-Agent) ou NLP para automação de atendimento ao cliente, triagem de tickets, análise de sentimento ou resolução de disputas.
2. Estudos que apresentem métricas quantitativas de performance técnica ou de negócio (ex: taxa de retenção/deflexão de chamados, redução de latência, precisão na classificação de intenção, mitigação de alucinações).

CRITÉRIOS DE EXCLUSÃO:
1. Artigos puramente teóricos sobre linguística histórica, psicologia comportamental sem uso de IA ou tradução literária.
2. Artigos focados em hardware de telecomunicações, redes 5G físicas ou robótica industrial sem aplicação em processamento de linguagem natural ou atendimento digital.
"""