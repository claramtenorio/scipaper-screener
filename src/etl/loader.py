import logging
from pathlib import Path
from typing import List
import pandas as pd
from src.config import CACHE_FILE_PATH, APPROVED_CSV_PATH, APPROVED_EXCEL_PATH
from src.etl.schemas import PaperInput, PaperScreeningOutput

logger = logging.getLogger(__name__)


class PaperLoader:
    """Responsável por cruzar resultados da IA com os dados originais e exportar tabelas limpas"""

    def __init__(
        self,
        cache_path: Path = CACHE_FILE_PATH,
        approved_csv_path: Path = APPROVED_CSV_PATH,
        approved_excel_path: Path = APPROVED_EXCEL_PATH
    ):
        self.cache_path = Path(cache_path)
        self.approved_csv_path = Path(approved_csv_path)
        self.approved_excel_path = Path(approved_excel_path)
        self.cache_path.parent.makedirs(parents=True, exist_ok=True)

    def transform_and_load(
        self,
        inputs: List[PaperInput],
        outputs: List[PaperScreeningOutput]
    ) -> pd.DataFrame:
        """Une entradas e saídas, salva cache completo e exporta apenas artigos aprovados"""
        if inputs and outputs:
            input_map = {p.paper_id: p for p in inputs}
            new_records = []

            for out in outputs:
                orig = input_map.get(out.paper_id)
                if not orig:
                    continue
                new_records.append({
                    "paper_id": out.paper_id,
                    "title": orig.title,
                    "authors": orig.authors,
                    "year": orig.year,
                    "decision": out.decision,
                    "relevance_score": out.relevance_score,
                    "methodology": out.methodology,
                    "justification": out.justification,
                    "key_points": " • ".join(out.key_points),
                    "abstract": orig.abstract
                })

            new_df = pd.DataFrame(new_records)

            # Atualiza histórico completo (idempotência)
            if self.cache_path.exists():
                existing_df = pd.read_csv(self.cache_path)
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=["paper_id"], keep="last")
            else:
                combined_df = new_df

            combined_df.to_csv(self.cache_path, index=False)
            logger.info(f"Histórico completo atualizado em: {self.cache_path} ({len(combined_df)} artigos)")
        elif self.cache_path.exists():
            combined_df = pd.read_csv(self.cache_path)
        else:
            return pd.DataFrame()

        # Filtra apenas os artigos úteis e ordena por relevância
        approved_df = combined_df[combined_df["decision"] == "SIM"].sort_values(
            by="relevance_score", ascending=False
        ).reset_index(drop=True)

        # Exporta em CSV e Excel
        approved_df.to_csv(self.approved_csv_path, index=False)
        approved_df.to_excel(self.approved_excel_path, index=False)
        logger.info(
            f"Tabelas finais exportadas com sucesso! {len(approved_df)} artigos aprovados salvos em "
            f"{self.approved_csv_path} e {self.approved_excel_path}"
        )
        return approved_df