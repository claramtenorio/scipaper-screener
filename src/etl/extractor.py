import logging
from pathlib import Path
from typing import List, Set
import pandas as pd
from src.config import RAW_DATA_PATH, CACHE_FILE_PATH
from src.etl.schemas import PaperInput

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class PaperExtractor:
    """Responsável pela extração, criação de dados de amostra, validação e controle de idempotência."""

    def __init__(self, raw_path: Path = RAW_DATA_PATH, cache_path: Path = CACHE_FILE_PATH):
        self.raw_path = Path(raw_path)
        self.cache_path = Path(cache_path)

    def create_sample_dataset_if_not_exists(self) -> None:
        """Cria um dataset de 6 artigos (4 relevantes e 2 fora de escopo)."""
        if self.raw_path.exists():
            return

        self.raw_path.parent.makedirs(parents=True, exist_ok=True)
        sample_data = [
            {
                "paper_id": "ARXIV-2502.101",
                "title": "Hybrid RAG Architectures for Automated Customer Support Ticket Resolution",
                "abstract": "High-volume digital platforms deal with thousands of daily customer inquiries. We propose a Hybrid Retrieval-Augmented Generation (RAG) pipeline combining dense vector search (FAISS) with BM25 keyword matching and a cross-encoder reranker. Deployed in a live production environment, the system increased automated ticket deflection by 34% while reducing hallucination rates to under 1.2%.",
                "authors": "Almeida, L.; Chen, W.",
                "year": 2025
            },
            {
                "paper_id": "ARXIV-2502.102",
                "title": "Phonetic Evolution of Romance Languages in 14th Century Iberian Manuscripts",
                "abstract": "This philological study examines vowel shifts and consonant palatalization across medieval legal parchments in the Iberian Peninsula, proposing a revised chronology for archaic morphological structures.",
                "authors": "Gomez, E.",
                "year": 2020
            },
            {
                "paper_id": "ARXIV-2502.103",
                "title": "Multi-Agent LLM Workflows for Automated Refund and Dispute Triage in E-Commerce",
                "abstract": "Handling refund requests requires verifying user history, payment logs, and policy rules. We design a deterministic-guarded Multi-Agent framework using tool-calling LLMs to classify dispute intent and execute automated resolution actions. Experiments on 50,000 support logs demonstrate a 68% reduction in average handling time (AHT) and 94.5% policy compliance accuracy.",
                "authors": "Ribeiro, F.; Patel, S.",
                "year": 2026
            },
            {
                "paper_id": "ARXIV-2502.104",
                "title": "Antenna Beamforming Optimization for Millimeter-Wave 6G Satellite Relays",
                "abstract": "We investigate phase-array antenna calibration under atmospheric turbulence for low-earth orbit satellite links, focusing on signal-to-noise ratio maximization in physical layer telecommunications.",
                "authors": "Takahashi, K.",
                "year": 2024
            },
            {
                "paper_id": "ARXIV-2502.105",
                "title": "Real-Time Escalation Prediction in Customer Service Chats Using Fine-Tuned Small Language Models",
                "abstract": "Detecting frustrated users before they churn is critical for digital marketplaces. By fine-tuning a 7B parameter Small Language Model (SLM) with LoRA on multi-turn chat transcripts, we achieve 91.2% F1-score in early sentiment escalation detection with an inference latency of just 45ms per message.",
                "authors": "Martins, V.; Rossi, B.",
                "year": 2025
            },
            {
                "paper_id": "ARXIV-2502.106",
                "title": "LLM-as-a-Judge for Continuous Hallucination Monitoring in Conversational Support Agents",
                "abstract": "Evaluating autonomous support agents at scale without human annotation bottlenecks remains challenging. We introduce an automated evaluation pipeline using calibrated LLM judges with structured rubrics to audit faithfulness, tone, and policy adherence in production chat logs, achieving 0.89 Cohen's kappa agreement with human experts.",
                "authors": "Nogueira, P. et al.",
                "year": 2026
            }
        ]
        pd.DataFrame(sample_data).to_csv(self.raw_path, index=False)
        logger.info(f"Dataset de exemplo criado com 6 artigos em: {self.raw_path}")

    def get_already_processed_ids(self) -> Set[str]:
        """Retorna os IDs dos artigos que já foram avaliados anteriormente (idempotência)."""
        if not self.cache_path.exists():
            return set()
        try:
            cache_df = pd.read_csv(self.cache_path)
            return set(cache_df["paper_id"].astype(str).tolist())
        except Exception as e:
            logger.warning(f"Não foi possível ler o cache existente: {e}")
            return set()

    def extract_unprocessed_papers(self, force_reprocess: bool = False) -> List[PaperInput]:
        """Carrega o CSV bruto, valida via Pydantic e retorna apenas os artigos ainda não processados."""
        self.create_sample_dataset_if_not_exists()
        df = pd.read_csv(self.raw_path)

        processed_ids = set() if force_reprocess else self.get_already_processed_ids()
        valid_papers: List[PaperInput] = []

        for idx, row in df.iterrows():
            paper_id = str(row.get("paper_id", "")).strip()
            if paper_id in processed_ids:
                logger.info(f"Artigo {paper_id} já avaliado no cache. Pulando...")
                continue

            try:
                paper = PaperInput(
                    paper_id=paper_id,
                    title=str(row["title"]),
                    abstract=str(row["abstract"]),
                    authors=str(row.get("authors", "Desconhecido")) if pd.notna(row.get("authors")) else "Desconhecido",
                    year=int(row["year"]) if pd.notna(row.get("year")) else None
                )
                valid_papers.append(paper)
            except Exception as e:
                logger.error(f"Linha {idx} (ID: {paper_id}) reprovada na validação de contrato: {e}")

        logger.info(f"Extração concluída: {len(valid_papers)} artigos novos prontos para triagem.")
        return valid_papers