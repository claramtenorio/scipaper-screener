import logging
import re
import time
from typing import List, Optional
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config import GEMINI_API_KEY, GEMINI_MODEL, DEFAULT_RESEARCH_CRITERIA
from src.etl.schemas import PaperInput, PaperScreeningOutput
from src.agents.prompts import SCREENER_SYSTEM_INSTRUCTION, build_paper_user_prompt

logger = logging.getLogger(__name__)


class PaperScreenerAgent:
    """Agente de IA responsável pela triagem de artigos acadêmicos via API do Gemini."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = GEMINI_MODEL,
        criteria: str = DEFAULT_RESEARCH_CRITERIA
    ):
        self.api_key = (api_key or GEMINI_API_KEY).strip()
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY não foi encontrada! Configure-a no arquivo .env antes de executar."
            )

        # Inicializa o cliente oficial sem travas de gateway timeout
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name.strip()
        self.criteria = criteria

    @staticmethod
    def _clean_json_text(raw_text: str) -> str:
        """Extrai e limpa apenas o bloco JSON da resposta do modelo."""
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def evaluate_single_paper(self, paper: PaperInput) -> PaperScreeningOutput:
        """Avalia um único artigo e valida estritamente o retorno com Pydantic."""
        logger.info(f"Avaliando artigo {paper.paper_id}: '{paper.title[:50]}...'")

        schema_instruction = """
Responda APENAS com um objeto JSON válido (sem comentários e sem texto fora do JSON) contendo exatamente estas chaves:
{
  "paper_id": "string",
  "decision": "SIM" ou "NAO",
  "relevance_score": número inteiro de 1 a 10,
  "justification": "string (1 a 2 frases em português)",
  "key_points": ["ponto 1", "ponto 2"],
  "methodology": "string"
}
"""
        user_prompt = (
            build_paper_user_prompt(
                title=paper.title,
                abstract=paper.abstract,
                criteria=self.criteria
            )
            + "\n\n"
            + schema_instruction
        )

        config = types.GenerateContentConfig(
            system_instruction=SCREENER_SYSTEM_INSTRUCTION,
            temperature=0.1,
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=config
        )

        cleaned_json = self._clean_json_text(response.text)
        result = PaperScreeningOutput.model_validate_json(cleaned_json)
        result.paper_id = paper.paper_id

        logger.info(
            f"Artigo {paper.paper_id} avaliado -> Decisão: {result.decision} (Nota: {result.relevance_score}/10)"
        )
        return result

    def screen_batch(self, papers: List[PaperInput], sleep_between_calls: float = 1.5) -> List[PaperScreeningOutput]:
        """Processa um lote de artigos sequencialmente respeitando boas práticas de rate-limit."""
        results: List[PaperScreeningOutput] = []
        total = len(papers)

        logger.info(f"Iniciando triagem em lote para {total} artigos com o modelo {self.model_name}...")

        for idx, paper in enumerate(papers, start=1):
            try:
                evaluated = self.evaluate_single_paper(paper)
                results.append(evaluated)
            except Exception as e:
                logger.error(f"Falha ao avaliar artigo {paper.paper_id} após retentativas: {e}")

            if idx < total and sleep_between_calls > 0:
                time.sleep(sleep_between_calls)

        logger.info(f"Triagem concluída: {len(results)}/{total} artigos processados com sucesso.")
        return results