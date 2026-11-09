from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class PaperInput(BaseModel):
    """Schema de validação para cada artigo bruto carregado no Extract"""
    paper_id: str =Field(..., description="Identificador único do artigo (ID)")
    title: str = Field(..., min_length=5, description="Título do artigo")
    abstract: str = Field(..., min_length=30, description="Resumo/abstract completo do artigo")
    authors: Optional[str] = Field(default="Desconhecido", description="Autores do artigo")
    year: Optional[int] = Field(default=None, description="Ano de publicação")

    @field_validator("title", "abstract")
    @classmethod
    def clean_whitespace(cls, v: str) -> str:
        # Para remover as quebras de linha duplicadas e espaços nas pontas
        return " ".join(v.split())


class PaperScreeningOutput(BaseModel):
    """Schema estrito que a API do Gemini deve retornar (Structured Output)."""
    paper_id: str = Field(..., description="ID correspondente ao artigo avaliado")
    decision: Literal["SIM", "NAO"] = Field(
        ..., description="Decisão estrita: 'SIM' se atende aos critérios de inclusão, 'NAO' caso contrário"
    )
    relevance_score: int = Field(
        ..., ge=1, le=10, description="Nota de 1 a 10 indicando a aderência aos critérios da pesquisa"
    )
    justification: str = Field(
        ..., description="Justificativa curta (1 a 2 frases) explicando o motivo da decisão"
    )
    key_points: List[str] = Field(
        ..., description="Lista com 2 a 4 pontos-chave ou resultados quantitativos extraídos do resumo"
    )
    methodology: str = Field(
        ..., description="Técnica, algoritmo ou arquitetura principal utilizada (ex: DQN, GNN, Transformer)"
    )