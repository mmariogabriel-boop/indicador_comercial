from __future__ import annotations

from io import BytesIO
from pathlib import Path
import unicodedata

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "logo_mediatorie.png"

st.set_page_config(
    page_title="Dashboard Comercial | Mediatorie",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 3.8rem !important;
            padding-bottom: 2rem;
            max-width: 1500px;
        }

        [data-testid="stSidebar"] {
            background-color: #F5F7F2;
        }

        [data-testid="stMetric"] {
            background: white;
            border: 1px solid #E4E9DF;
            border-left: 5px solid #86BC25;
            border-radius: 10px;
            padding: 12px 15px;
        }

        .titulo-mediatorie {
            font-size: 2rem;
            font-weight: 750;
            color: #343A36;
            margin-bottom: 2px;
        }

        .subtitulo-mediatorie {
            color: #6B736D;
            font-size: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# REGRAS FIXAS DO PROCESSO
# =========================================================
STATUS_BENEFICIARIO = "Ativado"
STATUS_CONTRATO = "Aprovado"
STATUS_VIDA = [
    "Ag.Ativação",
    "Aposentado / Demitido",
    "Ativo",
    "Em Análise",
]

DATA_CORTE = pd.Timestamp("2025-12-01")


# =========================================================
# COLUNAS OBRIGATÓRIAS
# =========================================================
COLUNAS_BASE_TOTAL = [
    "Id Corretora",
    "Tipo Movimentação",
    "Data Início Beneficiário",
    "Data Inclusão Vida",
    "Descrição Status Atual Beneficiário",
    "Descrição Status Atual Contrato",
    "Descrição Status Vida",
    "Id Acomodação",
    "Descrição Beneficiário",
    "Descrição Material",
    "Descrição Corretora",
    "Descrição Vendedor",
]

COLUNAS_CARTEIRA = [
    "ID Parceiro",
    "NOME",
]


# =========================================================
# LEITURA
# =========================================================
@st.cache_data(show_spinner=False, max_entries=4)
def ler_excel_upload(nome: str, conteudo: bytes) -> pd.DataFrame:
    """
    Lê o arquivo uma única vez e mantém em cache entre os reruns
    do Streamlit. Isso é importante principalmente para a base total.
    """
    return pd.read_excel(BytesIO(conteudo))


def validar_colunas(
    df: pd.DataFrame,
    colunas_obrigatorias: list[str],
    nome_base: str,
) -> None:
    faltantes = [
        coluna
        for coluna in colunas_obrigatorias
        if coluna not in df.columns
    ]

    if faltantes:
        raise KeyError(
            f"{nome_base}: faltam as colunas: "
            + ", ".join(faltantes)
        )


def normalizar_cabecalho(texto: str) -> str:
    texto = str(texto).strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )
    return " ".join(texto.upper().split())


def localizar_coluna(
    df: pd.DataFrame,
    candidatos: list[str],
) -> str | None:
    mapa = {
        normalizar_cabecalho(coluna): coluna
        for coluna in df.columns
    }

    for candidato in candidatos:
        chave = normalizar_cabecalho(candidato)
        if chave in mapa:
            return mapa[chave]

    return None


def padronizar_colunas_comerciais(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Mantém nomes canônicos no restante do código, aceitando pequenas
    diferenças de cabeçalho encontradas nas planilhas.
    """
    df = df.copy()

    aliases = {
        "Descrição Material": [
            "Descrição Material",
            "Descricao Material",
        ],
        "Descrição Corretora": [
            "Descrição Corretora",
            "Descrição de Corretora",
            "Descricao Corretora",
            "Descricao de Corretora",
        ],
        "Descrição Vendedor": [
            "Descrição Vendedor",
            "Descrição Vendendor",
            "Descricao Vendedor",
            "Descricao Vendendor",
        ],
    }

    renomear = {}

    for nome_padrao, candidatos in aliases.items():
        if nome_padrao in df.columns:
            continue

        encontrada = localizar_coluna(
            df,
            candidatos,
        )

        if encontrada is not None:
            renomear[encontrada] = nome_padrao

    if renomear:
        df = df.rename(columns=renomear)

    return df


# =========================================================
# PROCESSAMENTO
# =========================================================
@st.cache_data(show_spinner=False, max_entries=2)
def processar_bases(
    nome_base: str,
    bytes_base: bytes,
    nome_carteira: str,
    bytes_carteira: bytes,
):
    """
    REPRODUÇÃO DIRETA DO PROCESSO HOMOLOGADO NO NOTEBOOK.

    Não usa nunique.
    Não altera a chave do merge.
    Não altera os filtros.
    Não altera os groupbys.
    """

    # -----------------------------------------------------
    # 1. LEITURA
    # -----------------------------------------------------
    df = ler_excel_upload(nome_base, bytes_base).copy()
    carteira_exec = ler_excel_upload(
        nome_carteira,
        bytes_carteira,
    ).copy()

    df.columns = df.columns.astype(str).str.strip()
    carteira_exec.columns = (
        carteira_exec.columns.astype(str).str.strip()
    )

    df = padronizar_colunas_comerciais(df)

    validar_colunas(
        df,
        COLUNAS_BASE_TOTAL,
        "Base Total",
    )
    validar_colunas(
        carteira_exec,
        COLUNAS_CARTEIRA,
        "Carteira de Executivos",
    )

    # -----------------------------------------------------
    # 2. MERGE - EXATAMENTE COMO NO CÓDIGO ORIGINAL
    # -----------------------------------------------------
    df = pd.merge(
        df,
        carteira_exec,
        how="left",
        right_on="ID Parceiro",
        left_on="Id Corretora",
    )

    # -----------------------------------------------------
    # 3. SOMENTE VIDA NOVA
    # -----------------------------------------------------
    df = df[
        df["Tipo Movimentação"] == "VIDA NOVA"
    ].copy()

    # -----------------------------------------------------
    # 4. DATAS E DIFERENÇA
    # -----------------------------------------------------
    df["Data Início Beneficiário"] = pd.to_datetime(
        df["Data Início Beneficiário"],
        errors="coerce",
        dayfirst=True,
    )

    df["Data Inclusão Vida"] = pd.to_datetime(
        df["Data Inclusão Vida"],
        errors="coerce",
        dayfirst=True,
    )

    df["Diferenca"] = (
        df["Data Inclusão Vida"]
        - df["Data Início Beneficiário"]
    ).dt.days

    # -----------------------------------------------------
    # 5. STATUS - MESMA REGRA DO NOTEBOOK
    # -----------------------------------------------------
    df = df[
        (
            df["Descrição Status Atual Beneficiário"]
            == STATUS_BENEFICIARIO
        )
        & (
            df["Descrição Status Atual Contrato"]
            == STATUS_CONTRATO
        )
        & (
            df["Descrição Status Vida"].isin(
                STATUS_VIDA
            )
        )
    ].copy()

    # -----------------------------------------------------
    # 6. REGISTROS NÃO CORRETOS
    # -----------------------------------------------------
    df_nao_corretos = df[
        df["Diferenca"] > 0
    ].copy()

    df_nao_corretos = df_nao_corretos[
        df_nao_corretos[
            "Descrição Status Atual Beneficiário"
        ] == "Ativado"
    ].copy()

    colunas_nao_corretos = [
        "Descrição Beneficiário",
        "Data Início Beneficiário",
        "Data Inclusão Vida",
        "Diferenca",
    ]

    df_nao_corretoss = df_nao_corretos[
        colunas_nao_corretos
    ].copy()

    # -----------------------------------------------------
    # 7. REGISTROS CORRETOS
    # -----------------------------------------------------
    df_certo = df[
        df["Diferenca"] <= 0
    ].copy()

    df_certo["Data Inclusão Vida"] = pd.to_datetime(
        df_certo["Data Inclusão Vida"],
        dayfirst=True,
        errors="coerce",
    )

    df_certo["Competencia"] = (
        df_certo["Data Inclusão Vida"]
        .dt.strftime("%m/%Y")
    )

    # -----------------------------------------------------
    # 8. SAÚDE
    # Exclui ODO e SEM
    # -----------------------------------------------------
    ACOM_SAUDE = ["ODO", "SEM"]

    df_saude = df_certo[
        ~df_certo["Id Acomodação"].isin(
            ACOM_SAUDE
        )
    ].copy()

    # -----------------------------------------------------
    # 9. ODONTO
    # Somente ODO
    # -----------------------------------------------------
    ACOM_ODONTO = ["ODO"]

    df_odonto = df_certo[
        df_certo["Id Acomodação"].isin(
            ACOM_ODONTO
        )
    ].copy()

    # -----------------------------------------------------
    # 10. SAÚDE - COMPETÊNCIA + EXECUTIVO
    # -----------------------------------------------------
    df_saude_agru_comp_analista = (
        df_saude
        .groupby(
            ["Competencia", "NOME"]
        )
        .agg(
            {
                "Id Corretora": "count",
            }
        )
        .reset_index()
    )

    df_saude_agru_comp_analista[
        "Competencia"
    ] = pd.to_datetime(
        df_saude_agru_comp_analista[
            "Competencia"
        ],
        format="%m/%Y",
        errors="coerce",
    )

    df_saude_agru_comp_analista = (
        df_saude_agru_comp_analista[
            df_saude_agru_comp_analista[
                "Competencia"
            ] > DATA_CORTE
        ]
        .sort_values(
            ["Competencia", "NOME"]
        )
        .reset_index(drop=True)
    )

    # -----------------------------------------------------
    # 11. ODONTO - COMPETÊNCIA + EXECUTIVO
    # -----------------------------------------------------
    df_odonto_agru_comp_analista = (
        df_odonto
        .groupby(
            ["Competencia", "NOME"]
        )
        .agg(
            {
                "Id Corretora": "count",
            }
        )
        .reset_index()
    )

    df_odonto_agru_comp_analista[
        "Competencia"
    ] = pd.to_datetime(
        df_odonto_agru_comp_analista[
            "Competencia"
        ],
        format="%m/%Y",
        errors="coerce",
    )

    df_odonto_agru_comp_analista = (
        df_odonto_agru_comp_analista[
            df_odonto_agru_comp_analista[
                "Competencia"
            ] > DATA_CORTE
        ]
        .sort_values(
            ["Competencia", "NOME"]
        )
        .reset_index(drop=True)
    )

    # -----------------------------------------------------
    # 12. SAÚDE - TOTAL POR COMPETÊNCIA
    # -----------------------------------------------------
    df_saude_group = (
        df_saude
        .groupby("Competencia")
        .agg(
            {
                "Descrição Beneficiário": "count",
            }
        )
        .reset_index()
    )

    df_saude_group["Competencia"] = (
        pd.to_datetime(
            df_saude_group["Competencia"],
            format="%m/%Y",
            errors="coerce",
        )
    )

    df_saude_group = (
        df_saude_group[
            df_saude_group[
                "Competencia"
            ] > DATA_CORTE
        ]
        .sort_values("Competencia")
        .reset_index(drop=True)
    )

    # -----------------------------------------------------
    # 13. ODONTO - TOTAL POR COMPETÊNCIA
    # -----------------------------------------------------
    df_odonto_group = (
        df_odonto
        .groupby("Competencia")
        .agg(
            {
                "Descrição Beneficiário": "count",
            }
        )
        .reset_index()
    )

    df_odonto_group["Competencia"] = (
        pd.to_datetime(
            df_odonto_group["Competencia"],
            format="%m/%Y",
            errors="coerce",
        )
    )

    df_odonto_group = (
        df_odonto_group[
            df_odonto_group[
                "Competencia"
            ] > DATA_CORTE
        ]
        .sort_values("Competencia")
        .reset_index(drop=True)
    )

    # -----------------------------------------------------
    # 14. BASE COMERCIAL VÁLIDA PARA OS NOVOS RANKINGS
    # Mesmas regras já aplicadas acima + competência 01/2026+
    # -----------------------------------------------------
    df_comercial = df_certo.copy()

    df_comercial["Competencia_Data"] = pd.to_datetime(
        df_comercial["Competencia"],
        format="%m/%Y",
        errors="coerce",
    )

    df_comercial = (
        df_comercial[
            df_comercial["Competencia_Data"] > DATA_CORTE
        ]
        .copy()
    )

    # -----------------------------------------------------
    # 15. CLASSIFICAÇÃO DO TIPO DE PRODUTO
    # -----------------------------------------------------
    acomodacao = (
        df_comercial["Id Acomodação"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    mapa_tipo_produto = {
        "AMB": "Ambulatorial",
        "ENF": "Completo",
        "QUA": "Completo",
        "ODO": "Odonto",
    }

    df_comercial["Tipo Produto"] = (
        acomodacao
        .map(mapa_tipo_produto)
        .fillna("Não classificado")
    )

    # -----------------------------------------------------
    # 16. PRODUTOS MAIS VENDIDOS
    # Regra: Descrição Material -> count(Descrição Beneficiário)
    # -----------------------------------------------------
    df_produtos_ranking = (
        df_comercial
        .assign(
            **{
                "Descrição Material": (
                    df_comercial["Descrição Material"]
                    .astype("string")
                    .fillna("Não informado")
                    .str.strip()
                    .replace("", "Não informado")
                )
            }
        )
        .groupby(
            "Descrição Material",
            dropna=False,
        )
        .agg(
            {
                "Descrição Beneficiário": "count",
            }
        )
        .reset_index()
        .rename(
            columns={
                "Descrição Beneficiário": "Quantidade",
            }
        )
        .sort_values(
            "Quantidade",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    # -----------------------------------------------------
    # 17. MAIORES CORRETORAS
    # Regra: Descrição Corretora -> count(Descrição Beneficiário)
    # -----------------------------------------------------
    df_corretoras_ranking = (
        df_comercial
        .assign(
            **{
                "Descrição Corretora": (
                    df_comercial["Descrição Corretora"]
                    .astype("string")
                    .fillna("Não informado")
                    .str.strip()
                    .replace("", "Não informado")
                )
            }
        )
        .groupby(
            "Descrição Corretora",
            dropna=False,
        )
        .agg(
            {
                "Descrição Beneficiário": "count",
            }
        )
        .reset_index()
        .rename(
            columns={
                "Descrição Beneficiário": "Quantidade",
            }
        )
        .sort_values(
            "Quantidade",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    # -----------------------------------------------------
    # 18. MAIORES VENDEDORES
    # Regra: Descrição Vendedor -> count(Descrição Beneficiário)
    # -----------------------------------------------------
    df_vendedores_ranking = (
        df_comercial
        .assign(
            **{
                "Descrição Vendedor": (
                    df_comercial["Descrição Vendedor"]
                    .astype("string")
                    .fillna("Não informado")
                    .str.strip()
                    .replace("", "Não informado")
                )
            }
        )
        .groupby(
            "Descrição Vendedor",
            dropna=False,
        )
        .agg(
            {
                "Descrição Beneficiário": "count",
            }
        )
        .reset_index()
        .rename(
            columns={
                "Descrição Beneficiário": "Quantidade",
            }
        )
        .sort_values(
            "Quantidade",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    # -----------------------------------------------------
    # 19. DISTRIBUIÇÃO POR TIPO DE PRODUTO
    # -----------------------------------------------------
    df_tipo_produto = (
        df_comercial
        .groupby(
            "Tipo Produto",
            dropna=False,
        )
        .agg(
            {
                "Descrição Beneficiário": "count",
            }
        )
        .reset_index()
        .rename(
            columns={
                "Descrição Beneficiário": "Quantidade",
            }
        )
        .sort_values(
            "Quantidade",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    # Formatação da data apenas na base detalhada.
    df_certo["Data Inclusão Vida"] = (
        df_certo["Data Inclusão Vida"]
        .dt.strftime("%d/%m/%Y")
    )

    return (
        df,
        df_certo,
        df_nao_corretoss,
        df_saude,
        df_odonto,
        df_saude_agru_comp_analista,
        df_odonto_agru_comp_analista,
        df_saude_group,
        df_odonto_group,
        df_comercial,
        df_produtos_ranking,
        df_corretoras_ranking,
        df_vendedores_ranking,
        df_tipo_produto,
    )


# =========================================================
# GRÁFICOS
# =========================================================
def grafico_total_competencia(
    dados: pd.DataFrame,
    titulo: str,
) -> go.Figure:
    fig = go.Figure()

    fig.add_bar(
        x=dados["Competencia"],
        y=dados["Descrição Beneficiário"],
        text=dados["Descrição Beneficiário"],
        textposition="outside",
        marker_color="#86BC25",
        hovertemplate=(
            "<b>%{x|%m/%Y}</b><br>"
            "Quantidade: %{y}<extra></extra>"
        ),
    )

    fig.update_layout(
        title=titulo,
        height=430,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(
            l=35,
            r=25,
            t=70,
            b=50,
        ),
        showlegend=False,
        font=dict(
            family="Arial",
            color="#404640",
        ),
    )

    fig.update_xaxes(
        title="Competência",
        tickformat="%m/%Y",
        showgrid=False,
    )

    fig.update_yaxes(
        title="Quantidade de beneficiários",
        gridcolor="#E8EDE4",
        zeroline=False,
    )

    return fig


def grafico_por_executivo(
    dados: pd.DataFrame,
    titulo: str,
) -> go.Figure:
    plot = dados.copy()
    plot["Competencia_Label"] = (
        plot["Competencia"].dt.strftime("%m/%Y")
    )

    fig = px.bar(
        plot,
        x="Competencia_Label",
        y="Id Corretora",
        color="NOME",
        barmode="group",
        text="Id Corretora",
    )

    fig.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "Competência: %{x}<br>"
            "Quantidade: %{y}<extra></extra>"
        ),
    )

    fig.update_layout(
        title=titulo,
        height=520,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(
            l=35,
            r=25,
            t=75,
            b=55,
        ),
        legend_title="Executivo",
        font=dict(
            family="Arial",
            color="#404640",
        ),
    )

    fig.update_xaxes(
        title="Competência",
        showgrid=False,
    )

    fig.update_yaxes(
        title="Contagem de Id Corretora",
        gridcolor="#E8EDE4",
        zeroline=False,
    )

    return fig




def recalcular_rankings_comerciais(
    df_comercial_filtrado: pd.DataFrame,
):
    """
    Recalcula todos os rankings comerciais depois do filtro de competência.
    Mantém as mesmas regras já homologadas.
    """

    df_produtos_ranking = (
        df_comercial_filtrado
        .assign(
            **{
                "Descrição Material": (
                    df_comercial_filtrado["Descrição Material"]
                    .astype("string")
                    .fillna("Não informado")
                    .str.strip()
                    .replace("", "Não informado")
                )
            }
        )
        .groupby(
            "Descrição Material",
            dropna=False,
        )
        .agg(
            {
                "Descrição Beneficiário": "count",
            }
        )
        .reset_index()
        .rename(
            columns={
                "Descrição Beneficiário": "Quantidade",
            }
        )
        .sort_values(
            "Quantidade",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    df_corretoras_ranking = (
        df_comercial_filtrado
        .assign(
            **{
                "Descrição Corretora": (
                    df_comercial_filtrado["Descrição Corretora"]
                    .astype("string")
                    .fillna("Não informado")
                    .str.strip()
                    .replace("", "Não informado")
                )
            }
        )
        .groupby(
            "Descrição Corretora",
            dropna=False,
        )
        .agg(
            {
                "Descrição Beneficiário": "count",
            }
        )
        .reset_index()
        .rename(
            columns={
                "Descrição Beneficiário": "Quantidade",
            }
        )
        .sort_values(
            "Quantidade",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    df_vendedores_ranking = (
        df_comercial_filtrado
        .assign(
            **{
                "Descrição Vendedor": (
                    df_comercial_filtrado["Descrição Vendedor"]
                    .astype("string")
                    .fillna("Não informado")
                    .str.strip()
                    .replace("", "Não informado")
                )
            }
        )
        .groupby(
            "Descrição Vendedor",
            dropna=False,
        )
        .agg(
            {
                "Descrição Beneficiário": "count",
            }
        )
        .reset_index()
        .rename(
            columns={
                "Descrição Beneficiário": "Quantidade",
            }
        )
        .sort_values(
            "Quantidade",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    df_tipo_produto = (
        df_comercial_filtrado
        .groupby(
            "Tipo Produto",
            dropna=False,
        )
        .agg(
            {
                "Descrição Beneficiário": "count",
            }
        )
        .reset_index()
        .rename(
            columns={
                "Descrição Beneficiário": "Quantidade",
            }
        )
        .sort_values(
            "Quantidade",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    return (
        df_produtos_ranking,
        df_corretoras_ranking,
        df_vendedores_ranking,
        df_tipo_produto,
    )



def grafico_ranking_comercial(
    dados: pd.DataFrame,
    coluna_nome: str,
    titulo: str,
    top_n: int = 10,
) -> go.Figure:
    ranking = (
        dados.head(top_n)
        .sort_values("Quantidade", ascending=True)
        .copy()
    )

    fig = go.Figure(
        go.Bar(
            x=ranking["Quantidade"],
            y=ranking[coluna_nome],
            orientation="h",
            text=ranking["Quantidade"],
            textposition="outside",
            marker_color="#86BC25",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Quantidade: %{x}<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=titulo,
        height=max(410, 42 * len(ranking) + 120),
        paper_bgcolor="white",
        plot_bgcolor="white",
        showlegend=False,
        margin=dict(
            l=20,
            r=65,
            t=70,
            b=45,
        ),
        font=dict(
            family="Arial",
            color="#404640",
        ),
    )

    fig.update_xaxes(
        title="Quantidade de beneficiários",
        gridcolor="#E8EDE4",
        zeroline=False,
    )

    fig.update_yaxes(
        title=None,
    )

    return fig


def grafico_tipo_produto(
    dados: pd.DataFrame,
) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=dados["Tipo Produto"],
            y=dados["Quantidade"],
            text=dados["Quantidade"],
            textposition="outside",
            marker_color="#86BC25",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Quantidade: %{y}<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=(
            "Produção por tipo de produto"
            "<br><sup>AMB = Ambulatorial | ENF/QUA = Completo | ODO = Odonto</sup>"
        ),
        height=430,
        paper_bgcolor="white",
        plot_bgcolor="white",
        showlegend=False,
        margin=dict(
            l=35,
            r=25,
            t=85,
            b=50,
        ),
        font=dict(
            family="Arial",
            color="#404640",
        ),
    )

    fig.update_xaxes(
        title="Tipo de produto",
        showgrid=False,
    )

    fig.update_yaxes(
        title="Quantidade de beneficiários",
        gridcolor="#E8EDE4",
        zeroline=False,
    )

    return fig



def tabela_formatada_competencia(
    df: pd.DataFrame,
) -> pd.DataFrame:
    resultado = df.copy()

    if "Competencia" in resultado.columns:
        resultado["Competencia"] = (
            resultado["Competencia"]
            .dt.strftime("%m/%Y")
        )

    return resultado


# =========================================================
# CABEÇALHO
# =========================================================
col_logo, col_titulo = st.columns(
    [0.9, 4.1],
    vertical_alignment="center",
)

with col_logo:
    if LOGO_PATH.exists():
        st.image(
            str(LOGO_PATH),
            width=190,
        )

with col_titulo:
    st.markdown(
        """
        <div class="titulo-mediatorie">
            Dashboard Comercial
        </div>
        <div class="subtitulo-mediatorie">
            Mediatorie Administradora de Benefícios
        </div>
        """,
        unsafe_allow_html=True,
    )

st.caption(
    "O painel reproduz as regras e os agrupamentos do processo já validado em Pandas."
)


# =========================================================
# UPLOAD
# =========================================================
with st.sidebar:
    st.header("Bases")

    arquivo_base = st.file_uploader(
        "1. Base Total",
        type=["xlsx", "xls"],
        key="upload_base_total",
        help="Ex.: Itens - 2026-09-17T133257.920.xlsx",
    )

    arquivo_carteira = st.file_uploader(
        "2. Carteira de Executivos",
        type=["xlsx", "xls"],
        key="upload_carteira",
        help="Ex.: 2026.09 - atualizado em 15.09.xlsx",
    )

    st.divider()

    st.markdown("#### Regras fixas")
    st.caption("Movimentação: VIDA NOVA")
    st.caption("Beneficiário: Ativado")
    st.caption("Contrato: Aprovado")
    st.caption(
        "Vida: Ag.Ativação, Aposentado / Demitido, Ativo ou Em Análise"
    )
    st.caption("Registros válidos: Diferença ≤ 0")
    st.caption("Competências disponíveis: 01/2026 em diante")


if arquivo_base is None or arquivo_carteira is None:
    st.info(
        "Envie as duas planilhas no menu lateral para gerar o dashboard."
    )
    st.stop()


# =========================================================
# EXECUÇÃO DO PROCESSO
# =========================================================
try:
    with st.spinner(
        "Processando Base Total e Carteira de Executivos..."
    ):
        (
            df_merge_filtrado,
            df_certo,
            df_nao_corretos,
            df_saude,
            df_odonto,
            df_saude_exec,
            df_odonto_exec,
            df_saude_comp,
            df_odonto_comp,
            df_comercial,
            df_produtos_ranking,
            df_corretoras_ranking,
            df_vendedores_ranking,
            df_tipo_produto,
        ) = processar_bases(
            arquivo_base.name,
            arquivo_base.getvalue(),
            arquivo_carteira.name,
            arquivo_carteira.getvalue(),
        )

except Exception as erro:
    st.error(
        f"Não foi possível processar as bases: {erro}"
    )
    st.stop()


# =========================================================
# FILTRO DE COMPETÊNCIA
# =========================================================
competencias_disponiveis = (
    df_comercial[
        ["Competencia_Data", "Competencia"]
    ]
    .dropna(subset=["Competencia_Data"])
    .drop_duplicates()
    .sort_values("Competencia_Data")
    ["Competencia"]
    .tolist()
)

with st.sidebar:
    st.divider()
    st.markdown("### Filtro de competência")

    competencias_selecionadas = st.multiselect(
        "Competência",
        options=competencias_disponiveis,
        default=competencias_disponiveis,
        help=(
            "O filtro afeta Saúde, Odonto, executivos, produtos, "
            "corretoras, vendedores, tipo de produto e os KPIs."
        ),
    )

if not competencias_selecionadas:
    st.warning(
        "Selecione pelo menos uma competência para exibir o dashboard."
    )
    st.stop()

competencias_datas = pd.to_datetime(
    competencias_selecionadas,
    format="%m/%Y",
    errors="coerce",
)

# ---------------------------------------------------------
# Filtra os agrupamentos homologados de Saúde/Odonto
# ---------------------------------------------------------
df_saude_exec = df_saude_exec[
    df_saude_exec["Competencia"].isin(
        competencias_datas
    )
].copy()

df_odonto_exec = df_odonto_exec[
    df_odonto_exec["Competencia"].isin(
        competencias_datas
    )
].copy()

df_saude_comp = df_saude_comp[
    df_saude_comp["Competencia"].isin(
        competencias_datas
    )
].copy()

df_odonto_comp = df_odonto_comp[
    df_odonto_comp["Competencia"].isin(
        competencias_datas
    )
].copy()

# ---------------------------------------------------------
# Filtra a base comercial usada pelos novos rankings
# ---------------------------------------------------------
df_comercial = df_comercial[
    df_comercial["Competencia"].isin(
        competencias_selecionadas
    )
].copy()

# ---------------------------------------------------------
# Recalcula os rankings após o filtro
# ---------------------------------------------------------
(
    df_produtos_ranking,
    df_corretoras_ranking,
    df_vendedores_ranking,
    df_tipo_produto,
) = recalcular_rankings_comerciais(
    df_comercial
)


# =========================================================
# DIAGNÓSTICO DO MERGE
# =========================================================
sem_executivo = int(
    df_merge_filtrado["NOME"].isna().sum()
)

if sem_executivo:
    st.warning(
        f"{sem_executivo:,}".replace(",", ".")
        + " registro(s) ficaram sem NOME após o merge "
        "entre Id Corretora e ID Parceiro."
    )


st.caption(
    "**Competência selecionada:** "
    + ", ".join(competencias_selecionadas)
)

# =========================================================
# KPIs
# Os totais abaixo são obtidos dos mesmos agrupamentos
# que alimentam os gráficos.
# =========================================================
total_saude = int(
    df_saude_comp["Descrição Beneficiário"].sum()
) if not df_saude_comp.empty else 0

total_odonto = int(
    df_odonto_comp["Descrição Beneficiário"].sum()
) if not df_odonto_comp.empty else 0

total_validos = total_saude + total_odonto
total_nao_corretos = len(df_nao_corretos)

k1, k2, k3, k4 = st.columns(4)

k1.metric(
    "Saúde | 01/2026+",
    f"{total_saude:,}".replace(",", "."),
)

k2.metric(
    "Odonto | 01/2026+",
    f"{total_odonto:,}".replace(",", "."),
)

k3.metric(
    "Saúde + Odonto",
    f"{total_validos:,}".replace(",", "."),
)

k4.metric(
    "Diferença > 0",
    f"{total_nao_corretos:,}".replace(",", "."),
)


# =========================================================
# DASHBOARD
# =========================================================
(
    aba_geral,
    aba_saude,
    aba_odonto,
    aba_rankings,
    aba_conferencia,
) = st.tabs(
    [
        "Visão Geral",
        "Saúde",
        "Odonto",
        "Rankings Comerciais",
        "Conferência",
    ]
)


# ---------------------------------------------------------
# VISÃO GERAL
# ---------------------------------------------------------
with aba_geral:
    c1, c2 = st.columns(2)

    with c1:
        if df_saude_comp.empty:
            st.info(
                "Sem dados de Saúde para as competências válidas."
            )
        else:
            st.plotly_chart(
                grafico_total_competencia(
                    df_saude_comp,
                    "Saúde por competência",
                ),
                use_container_width=True,
                config={
                    "displaylogo": False,
                },
            )

    with c2:
        if df_odonto_comp.empty:
            st.info(
                "Sem dados de Odonto para as competências válidas."
            )
        else:
            st.plotly_chart(
                grafico_total_competencia(
                    df_odonto_comp,
                    "Odonto por competência",
                ),
                use_container_width=True,
                config={
                    "displaylogo": False,
                },
            )


# ---------------------------------------------------------
# SAÚDE
# ---------------------------------------------------------
with aba_saude:
    st.subheader("Saúde")

    st.caption(
        "Regra: Id Acomodação diferente de ODO e SEM."
    )

    if df_saude_exec.empty:
        st.info(
            "Não existem registros de Saúde para o período."
        )
    else:
        st.plotly_chart(
            grafico_por_executivo(
                df_saude_exec,
                "Saúde por competência e executivo",
            ),
            use_container_width=True,
            config={
                "displaylogo": False,
            },
        )

    with st.expander(
        "Ver agrupamento Saúde por executivo"
    ):
        st.dataframe(
            tabela_formatada_competencia(
                df_saude_exec
            ),
            use_container_width=True,
            hide_index=True,
        )

    with st.expander(
        "Ver agrupamento Saúde por competência"
    ):
        st.dataframe(
            tabela_formatada_competencia(
                df_saude_comp
            ),
            use_container_width=True,
            hide_index=True,
        )


# ---------------------------------------------------------
# ODONTO
# ---------------------------------------------------------
with aba_odonto:
    st.subheader("Odonto")

    st.caption(
        "Regra: Id Acomodação igual a ODO."
    )

    if df_odonto_exec.empty:
        st.info(
            "Não existem registros de Odonto para o período."
        )
    else:
        st.plotly_chart(
            grafico_por_executivo(
                df_odonto_exec,
                "Odonto por competência e executivo",
            ),
            use_container_width=True,
            config={
                "displaylogo": False,
            },
        )

    with st.expander(
        "Ver agrupamento Odonto por executivo"
    ):
        st.dataframe(
            tabela_formatada_competencia(
                df_odonto_exec
            ),
            use_container_width=True,
            hide_index=True,
        )

    with st.expander(
        "Ver agrupamento Odonto por competência"
    ):
        st.dataframe(
            tabela_formatada_competencia(
                df_odonto_comp
            ),
            use_container_width=True,
            hide_index=True,
        )


# ---------------------------------------------------------
# RANKINGS COMERCIAIS
# ---------------------------------------------------------
with aba_rankings:
    st.subheader("Rankings Comerciais")

    st.caption(
        "Todos os rankings abaixo utilizam a mesma base válida do processo: "
        "VIDA NOVA, status homologados, Diferença ≤ 0 e as competências selecionadas no filtro lateral."
    )

    c1, c2 = st.columns(2)

    with c1:
        st.plotly_chart(
            grafico_ranking_comercial(
                df_produtos_ranking,
                "Descrição Material",
                "Produtos mais vendidos",
                top_n=10,
            ),
            use_container_width=True,
            config={
                "displaylogo": False,
            },
        )

    with c2:
        st.plotly_chart(
            grafico_ranking_comercial(
                df_corretoras_ranking,
                "Descrição Corretora",
                "Maiores corretoras",
                top_n=10,
            ),
            use_container_width=True,
            config={
                "displaylogo": False,
            },
        )

    c3, c4 = st.columns(2)

    with c3:
        st.plotly_chart(
            grafico_ranking_comercial(
                df_vendedores_ranking,
                "Descrição Vendedor",
                "Maiores vendedores",
                top_n=10,
            ),
            use_container_width=True,
            config={
                "displaylogo": False,
            },
        )

    with c4:
        st.plotly_chart(
            grafico_tipo_produto(
                df_tipo_produto,
            ),
            use_container_width=True,
            config={
                "displaylogo": False,
            },
        )

    tabela_produto, tabela_corretora, tabela_vendedor, tabela_tipo = st.tabs(
        [
            "Produtos",
            "Corretoras",
            "Vendedores",
            "Tipo de produto",
        ]
    )

    with tabela_produto:
        st.dataframe(
            df_produtos_ranking,
            use_container_width=True,
            hide_index=True,
        )

    with tabela_corretora:
        st.dataframe(
            df_corretoras_ranking,
            use_container_width=True,
            hide_index=True,
        )

    with tabela_vendedor:
        st.dataframe(
            df_vendedores_ranking,
            use_container_width=True,
            hide_index=True,
        )

    with tabela_tipo:
        st.dataframe(
            df_tipo_produto,
            use_container_width=True,
            hide_index=True,
        )

    nao_classificados = int(
        df_comercial.loc[
            df_comercial["Tipo Produto"].eq("Não classificado"),
            "Descrição Beneficiário",
        ].count()
    )

    if nao_classificados:
        st.info(
            f"{nao_classificados:,}".replace(",", ".")
            + " registro(s) possuem Id Acomodação diferente de "
            "AMB, ENF, QUA ou ODO e foram exibidos como 'Não classificado'."
        )


# ---------------------------------------------------------
# CONFERÊNCIA
# ---------------------------------------------------------
with aba_conferencia:
    st.subheader("Conferência do processamento")

    st.markdown(
        """
        Esta aba existe para facilitar a comparação do Streamlit
        com os DataFrames do notebook original.
        """
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Após merge + filtros de status",
        f"{len(df_merge_filtrado):,}".replace(",", "."),
    )

    c2.metric(
        "Diferença ≤ 0",
        f"{len(df_certo):,}".replace(",", "."),
    )

    c3.metric(
        "Diferença > 0",
        f"{len(df_nao_corretos):,}".replace(",", "."),
    )

    with st.expander(
        "Registros com Diferença > 0"
    ):
        st.dataframe(
            df_nao_corretos,
            use_container_width=True,
            hide_index=True,
        )

    with st.expander(
        "Base válida após Diferença ≤ 0"
    ):
        st.dataframe(
            df_certo,
            use_container_width=True,
            hide_index=True,
        )
