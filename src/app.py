import sys
from pathlib import Path
import streamlit as st
import pandas as pd

# Adiciona a pasta raiz do projeto (scipaper-screener) ao sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import (
    CACHE_FILE_PATH,
    APPROVED_CSV_PATH,
    APPROVED_EXCEL_PATH,
)
from src.analytics.insights import (
    calculate_kpis,
    generate_executive_summary,
    EXECUTIVE_SUMMARY_MD,
)

st.set_page_config(
    page_title="SciPaper Screener | AI Builder",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📑 SciPaper Screener: Triagem Inteligente de Artigos")
st.caption("Pipeline autônomo de ETL, Agentes Gemini 3 Flash e Resumos Executivos orientados a produto.")


@st.cache_data(ttl=60)
def load_data():
    if not CACHE_FILE_PATH.exists():
        return pd.DataFrame(), pd.DataFrame()
    df_all = pd.read_csv(CACHE_FILE_PATH)
    df_approved = (
        pd.read_csv(APPROVED_CSV_PATH)
        if APPROVED_CSV_PATH.exists()
        else df_all[df_all["decision"] == "SIM"]
    )
    return df_all, df_approved


df_all, df_approved = load_data()

if df_all.empty:
    st.warning("Nenhum dado encontrado. Execute `python3 main.py` no terminal para processar os artigos.")
    st.stop()

# KPIs no topo
kpis = calculate_kpis(df_all)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Analisado", f"{kpis['total_evaluated']} artigos")
col2.metric("Aprovados (Relevantes)", f"{kpis['total_approved']} ({kpis['approval_rate']}%)")
col3.metric("Score Médio (Aprovados)", f"{kpis['avg_approved_score']}/10")
col4.metric("Tempo Economizado", f"~{kpis['time_saved_minutes']} min")

st.divider()

# Barra lateral
with st.sidebar:
    st.header("⚙️ Controles & Exportação")
    st.write("Baixe a base curada pronta para o time técnico:")

    if APPROVED_CSV_PATH.exists():
        with open(APPROVED_CSV_PATH, "rb") as f:
            st.download_button(
                label="📥 Baixar Aprovados (.CSV)",
                data=f,
                file_name="approved_papers.csv",
                mime="text/csv",
            )

    if APPROVED_EXCEL_PATH.exists():
        with open(APPROVED_EXCEL_PATH, "rb") as f:
            st.download_button(
                label="📊 Baixar Aprovados (.XLSX)",
                data=f,
                file_name="approved_papers.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    st.markdown("---")
    if st.button("🔄 Regenerar Resumo Executivo com IA"):
        with st.spinner("Consultando Gemini 3 Flash para nova síntese..."):
            generate_executive_summary(df_all)
            st.success("Resumo atualizado!")
            st.rerun()

# Abas principais
tab_summary, tab_explorer = st.tabs(["📊 Resumo Executivo (AI Insights)", "🔍 Explorador de Artigos"])

with tab_summary:
    if EXECUTIVE_SUMMARY_MD.exists():
        summary_text = EXECUTIVE_SUMMARY_MD.read_text(encoding="utf-8")
        st.markdown(summary_text)
    else:
        st.info("Resumo ainda não gerado. Clique em 'Regenerar Resumo Executivo' na barra lateral.")

with tab_explorer:
    st.subheader("Base Geral de Artigos Avaliados")

    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        decision_filter = st.multiselect(
            "Filtrar por Decisão:",
            options=["SIM", "NAO"],
            default=["SIM", "NAO"],
        )
    with col_f2:
        score_filter = st.slider("Score Mínimo de Relevância:", min_value=1, max_value=10, value=1)

    filtered_df = df_all[
        (df_all["decision"].isin(decision_filter))
        & (df_all["relevance_score"] >= score_filter)
    ]

    st.dataframe(
        filtered_df[
            ["paper_id", "decision", "relevance_score", "title", "methodology", "justification"]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Detalhes por Artigo")
    selected_id = st.selectbox(
        "Selecione um artigo para auditar a avaliação completa:",
        df_all["paper_id"],
    )
    paper_row = df_all[df_all["paper_id"] == selected_id].iloc[0]

    with st.expander(f"Visualizar Ficha Técnica: {paper_row['title']}", expanded=True):
        st.write(f"**Decisão:** `{paper_row['decision']}` | **Score:** `{paper_row['relevance_score']}/10`")
        st.write(f"**Metodologia:** {paper_row['methodology']}")
        st.write(f"**Pontos-Chave:** {paper_row['key_points']}")
        st.write(f"**Justificativa do Agente:** {paper_row['justification']}")
        st.caption(f"Abstract original: {paper_row['abstract']}")