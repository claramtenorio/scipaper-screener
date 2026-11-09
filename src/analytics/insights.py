import logging
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
from google import genai
from google.genai import types

from src.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    CACHE_FILE_PATH,
    PROCESSED_DIR,
)

logger = logging.getLogger(__name__)

EXECUTIVE_SUMMARY_MD = PROCESSED_DIR / "executive_summary.md"
MINUTES_SAVED_PER_PAPER = 15  # Benchmark médio de triagem e fichamento manual por paper


def calculate_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """Calcula métricas técnicas e KPIs de impacto de negócio sobre a triagem."""
    if df.empty:
        return {
            "total_evaluated": 0,
            "total_approved": 0,
            "total_rejected": 0,
            "approval_rate": 0.0,
            "avg_approved_score": 0.0,
            "time_saved_minutes": 0,
        }

    total_evaluated = len(df)
    approved_df = df[df["decision"] == "SIM"]
    total_approved = len(approved_df)
    total_rejected = total_evaluated - total_approved

    approval_rate = round((total_approved / total_evaluated) * 100, 1)
    avg_approved_score = (
        round(float(approved_df["relevance_score"].mean()), 1)
        if not approved_df.empty
        else 0.0
    )
    time_saved_minutes = total_evaluated * MINUTES_SAVED_PER_PAPER

    return {
        "total_evaluated": total_evaluated,
        "total_approved": total_approved,
        "total_rejected": total_rejected,
        "approval_rate": approval_rate,
        "avg_approved_score": avg_approved_score,
        "time_saved_minutes": time_saved_minutes,
    }


def generate_executive_summary(
    df: pd.DataFrame,
    api_key: Optional[str] = None,
    model_name: str = GEMINI_MODEL,
) -> str:
    """Gera um Resumo Executivo com IA estruturado em O que aconteceu, Por que e O que fazer agora."""
    approved_df = df[df["decision"] == "SIM"].sort_values(
        by="relevance_score", ascending=False
    )

    if approved_df.empty:
        return "Nenhum artigo aprovado disponível para geração de síntese executiva."

    kpis = calculate_kpis(df)

    # Monta o contexto apenas com os artigos aprovados
    papers_context = []
    for _, row in approved_df.iterrows():
        papers_context.append(
            f"- ID: {row['paper_id']} | Título: {row['title']} (Nota: {row['relevance_score']}/10)\n"
            f"  Metodologia: {row['methodology']}\n"
            f"  Pontos-Chave: {row['key_points']}\n"
            f"  Justificativa: {row['justification']}"
        )
    context_text = "\n\n".join(papers_context)

    prompt = f"""
Você é um Staff AI Engineer apresentando os resultados de uma triagem científica automatizada para a liderança de Produto e Engenharia.

MÉTRICAS DO PIPELINE:
- Total de artigos analisados: {kpis['total_evaluated']}
- Artigos aprovados (alta relevância): {kpis['total_approved']} ({kpis['approval_rate']}%)
- Nota média de relevância dos aprovados: {kpis['avg_approved_score']}/10
- Tempo operacional economizado na triagem: ~{kpis['time_saved_minutes']} minutos

ARTIGOS APROVADOS PELO AGENTE:
{context_text}

Escreva um Resumo Executivo em Markdown (em português, direto ao ponto, sem introduções genéricas) dividido EXATAMENTE nestas 3 seções:

### 1. O que aconteceu? (Tendências e Padrões Identificados)
Sintetize os principais avanços e arquiteturas encontrados nos {kpis['total_approved']} artigos aprovados.

### 2. Por que importa? (Impacto em Produto e Operação)
Explique como essas descobertas (ex: RAG híbrido, fluxos multi-agentes, predição de escalonamento e monitoramento de alucinações) atacam gargalos reais de operações de atendimento em larga escala.

### 3. O que fazer agora? (Plano de Ação Recomendado)
Liste 3 recomendações práticas e acionáveis para o time de engenharia testar ou implementar no roadmap técnico, citando os IDs dos artigos correspondentes.
"""

    key = (api_key or GEMINI_API_KEY).strip()
    client = genai.Client(api_key=key)

    logger.info("Gerando Resumo Executivo com IA a partir dos artigos aprovados...")
    response = client.models.generate_content(
        model=model_name.strip(),
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2),
    )

    summary_md = response.text.strip()
    EXECUTIVE_SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)
    EXECUTIVE_SUMMARY_MD.write_text(summary_md, encoding="utf-8")
    logger.info(f"Resumo Executivo salvo com sucesso em: {EXECUTIVE_SUMMARY_MD}")

    return summary_md


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    if not CACHE_FILE_PATH.exists():
        logger.error(f"Arquivo {CACHE_FILE_PATH} não encontrado. Rode 'python3 main.py' primeiro.")
    else:
        df_evaluated = pd.read_csv(CACHE_FILE_PATH)
        kpis_result = calculate_kpis(df_evaluated)
        logger.info(f"KPIs Calculados: {kpis_result}")
        summary = generate_executive_summary(df_evaluated)
        print("\n" + "=" * 60)
        print("RESUMO EXECUTIVO GERADO PELA IA:")
        print("=" * 60 + "\n")
        print(summary)