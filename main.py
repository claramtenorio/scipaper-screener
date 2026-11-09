import logging
import pandas as pd
from src.config import CACHE_FILE_PATH
from src.etl.extractor import PaperExtractor
from src.agents.screener_agent import PaperScreenerAgent
from src.etl.loader import PaperLoader
from src.analytics.insights import calculate_kpis, generate_executive_summary

# Visual dos logs no terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== Iniciando o Triador de Artigos Científicos ===")

    # 1. Extração e Validação (ETL - Extract)
    logger.info("[1/4] Iniciando Extração de Dados...")
    extractor = PaperExtractor()
    papers = extractor.extract_unprocessed_papers()

    if papers:
        # 2. Triagem com o Gemini Agent
        logger.info(f"[2/4] Acionando o Agente Gemini para avaliar {len(papers)} artigos...")
        try:
            agent = PaperScreenerAgent()
            outputs = agent.screen_batch(papers, sleep_between_calls=2.0)
        except Exception as e:
            logger.error(f"Erro ao conectar com a API do Gemini: {e}")
            return

        if not outputs:
            logger.error("Nenhum artigo foi avaliado com sucesso. Verifique sua chave GEMINI_API_KEY no arquivo .env.")
            return

        # 3. Transformação, Filtro e Exportação (ETL - Load)
        logger.info("[3/4] Exportando resultados aprovados...")
        loader = PaperLoader()
        df_approved = loader.transform_and_load(papers, outputs)

        if not df_approved.empty:
            logger.info(f"Total de artigos aprovados nesta rodada: {len(df_approved)}")
            logger.info(f"Top 1 Artigo Recomendado: {df_approved.iloc[0]['title']} (Nota: {df_approved.iloc[0]['relevance_score']}/10)")
    else:
        logger.info("[2/4] Nenhum artigo novo para processar no momento (todos já estão no cache).")
        logger.info("[3/4] Mantendo planilhas consolidadas em 'data/processed/'.")

    # 4. Analytics e Resumo Executivo (AI Insights)
    logger.info("[4/4] Atualizando KPIs e Resumo Executivo...")
    if CACHE_FILE_PATH.exists():
        df_all = pd.read_csv(CACHE_FILE_PATH)
        kpis = calculate_kpis(df_all)
        generate_executive_summary(df_all)
        logger.info(
            f"KPIs Consolidados: {kpis['total_approved']}/{kpis['total_evaluated']} aprovados "
            f"({kpis['approval_rate']}%) | Economia: ~{kpis['time_saved_minutes']} min"
        )

    logger.info("=== Pipeline concluído com sucesso! ===")


if __name__ == "__main__":
    main()