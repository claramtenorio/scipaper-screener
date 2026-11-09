import logging
from src.etl.extractor import PaperExtractor
from src.agents.screener_agent import PaperScreenerAgent
from src.etl.loader import PaperLoader

# Vizual dos logs no terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== Iniciando o Triador de Artigos Científicos ===")

    # Extração e Validação (ETL - Extract)
    logger.info("[1/3] Iniciando Extração de Dados...")
    extractor = PaperExtractor()
    papers = extractor.extract_unprocessed_papers()

    if not papers:
        logger.info("Nenhum artigo novo para processar no momento (todos já estão no cache).")
        return

    # Triagem com o Gemini Agent
    logger.info(f"[2/3] Acionando o Agente Gemini para avaliar {len(papers)} artigos...")
    try:
        agent = PaperScreenerAgent()
        outputs = agent.screen_batch(papers, sleep_between_calls=2.0)
    except Exception as e:
        logger.error(f"Erro ao conectar com a API do Gemini: {e}")
        return

    if not outputs:
        logger.error("Nenhum artigo foi avaliado com sucesso. Verifique sua chave GEMINI_API_KEY no arquivo .env.")
        return

    # Transformação, Filtro e Exportação (ETL - Load)
    logger.info("[3/3] Exportando resultados aprovados...")
    loader = PaperLoader()
    df_approved = loader.transform_and_load(papers, outputs)

    logger.info("=== Pipeline concluído com sucesso! ===")
    if not df_approved.empty:
        logger.info(f"Total de artigos aprovados: {len(df_approved)}")
        logger.info(f"Top 1 Artigo Recomendado: {df_approved.iloc[0]['title']} (Nota: {df_approved.iloc[0]['relevance_score']}/10)")
        logger.info("Planilhas geradas na pasta 'data/processed/'!")


if __name__ == "__main__":
    main()