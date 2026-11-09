"""Testes unitários automatizados para o pipeline ETL e Pydantic"""

import pytest
import pandas as pd
from pathlib import Path
from pydantic import ValidationError

from src.etl.schemas import PaperInput, PaperScreeningOutput
from src.etl.loader import PaperLoader


def test_paper_input_schema_validation():
    """Valida se aceita dados corretos e limpa espaços extras"""
    valid_data = {
        "paper_id": "TEST-001",
        "title": "  Hybrid RAG Architectures for Customer Support  ",
        "abstract": "This study analyzes how vector retrieval improves latency and accuracy in customer support queries.",
        "authors": "Silva, M.",
        "year": 2025
    }
    paper = PaperInput(**valid_data)
    assert paper.paper_id == "TEST-001"
    assert paper.title == "Hybrid RAG Architectures for Customer Support"
    assert paper.year == 2025


def test_paper_input_schema_rejects_empty_abstract():
    """Garante que resumos muito curtos ou vazios sejam rejeitados"""
    with pytest.raises(ValidationError):
        PaperInput(
            paper_id="TEST-FAIL",
            title="Short Abstract Paper",
            abstract="Too short"
        )


def test_paper_screening_output_schema():
    """Valida se a resposta esperada da LLM cumpre as restrições"""
    output_data = {
        "paper_id": "TEST-001",
        "decision": "SIM",
        "relevance_score": 9,
        "justification": "Foco direto em suporte ao cliente e RAG.",
        "key_points": ["Redução de 34% em chamados", "Alucinação abaixo de 1.2%"],
        "methodology": "Hybrid RAG com FAISS e BM25"
    }
    result = PaperScreeningOutput(**output_data)
    assert result.decision == "SIM"
    assert 1 <= result.relevance_score <= 10


def test_loader_idempotency_and_filtering(tmp_path: Path):
    """Testa se o loader filtra apenas artigos 'SIM' e grava os arquivos corretamente"""
    cache_file = tmp_path / "cache.csv"
    approved_csv = tmp_path / "approved.csv"
    approved_excel = tmp_path / "approved.xlsx"

    loader = PaperLoader(
        cache_path=cache_file,
        approved_csv_path=approved_csv,
        approved_excel_path=approved_excel
    )

    inputs = [
        PaperInput(paper_id="P1", title="Paper One on NLP", abstract="Detailed abstract about NLP and conversational agents in production.", year=2025),
        PaperInput(paper_id="P2", title="Paper Two on History", abstract="Detailed abstract about medieval agricultural practices and feudal history.", year=2020)
    ]

    outputs = [
        PaperScreeningOutput(paper_id="P1", decision="SIM", relevance_score=9, justification="Relevante", key_points=["Ponto 1"], methodology="RAG"),
        PaperScreeningOutput(paper_id="P2", decision="NAO", relevance_score=1, justification="Fora de escopo", key_points=["Ponto 2"], methodology="Histórica")
    ]

    df_approved = loader.transform_and_load(inputs, outputs)

    assert len(df_approved) == 1
    assert df_approved.iloc[0]["paper_id"] == "P1"
    assert approved_csv.exists()
    assert approved_excel.exists()

    cache_df = pd.read_csv(cache_file)
    assert len(cache_df) == 2