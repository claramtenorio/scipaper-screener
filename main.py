import logging
import sys
from pathlib import Path
import pandas as pd

# Garante que a pasta raiz do projeto esteja no sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import (
    RAW_DATA_PATH,
    CACHE_FILE_PATH,
    APPROVED_CSV_PATH,
    APPROVED_EXCEL_PATH,
)
from src.etl.extractor import extract_papers_to_screen
from src.etl.loader import save_screening_results
from src.agents.screener_agent import PaperScreenerAgent
from src.analytics.insights import calculate_kpis, generate_executive_summary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def run_pipeline() -> None:
    logger.info("=== Iniciando o Triador de Artigos Científicos ===")

    # 1. Extração com verificação de cache
    logger.info("[1/4] Extraindo e validando artigos...")
    papers_to_screen = extract_papers_to_screen(
        raw_data_path=RAW_DATA_PATH,
        cache_path=CACHE_FILE_PATH,
    )

    # 2. Triagem pelo Agente Gemini
    if papers_to_screen:
        logger.info(f"[2/4] Acionando Agente Gemini para {len(papers_to_screen)} artigos...")
        agent = PaperScreenerAgent()
        screening_results = agent.screen_batch(papers_to_screen)
        if not screening_results:
            logger.error("Nenhum artigo avaliado com sucesso. Verifique a GEMINI_API_KEY.")
            return

        # 3. Carga e persistência dos dados
        logger.info("[3/4] Exportando tabelas e atualizando cache...")
        save_screening_results(
            new_results=screening_results,
            raw_data_path=RAW_DATA_PATH,
            cache_path=CACHE_FILE_PATH,
            approved_csv_path=APPROVED_CSV_PATH,
            approved_excel_path=APPROVED_EXCEL_PATH,
        )
    else:
        logger.info("[2/4] Nenhum artigo pendente de triagem (todos em cache).")
        logger.info("[3/4] Mantendo tabelas consolidadas existentes.")

    # 4. Analytics e Resumo Executivo
    logger.info("[4/4] Atualizando métricas e Resumo Executivo...")
    if CACHE_FILE_PATH.exists():
        df_all = pd.read_csv(CACHE_FILE_PATH)
        kpis = calculate_kpis(df_all)
        generate_executive_summary(df_all)
        logger.info(
            f"KPIs Consolidados: {kpis['total_approved']}/{kpis['total_evaluated']} aprovados | "
            f"Economia: ~{kpis['time_saved_minutes']} min"
        )

    logger.info("=== Pipeline concluído com sucesso! ===")


if __name__ == "__main__":
    run_pipeline()