from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st

from services.subsidios import (
    gerar_excel_subsidios,
    realizar_conferencia_subsidios,
)


def _ler_excel_ou_html(arquivo) -> pd.DataFrame:
    nome = arquivo.name.lower()
    conteudo = arquivo.getvalue()

    if nome.endswith(".xlsx"):
        return pd.read_excel(BytesIO(conteudo))

    if nome.endswith(".xls"):
        # Primeiro tenta como Excel tradicional.
        try:
            return pd.read_excel(BytesIO(conteudo))
        except Exception:
            pass

        # Algumas exportações .xls do sistema são, na verdade,
        # arquivos HTML com uma tabela dentro.
        try:
            tabelas = pd.read_html(
                BytesIO(conteudo),
                encoding="latin1",
            )
        except Exception as erro:
            raise ValueError(
                f"Não foi possível ler o arquivo '{arquivo.name}'."
            ) from erro

        if not tabelas:
            raise ValueError(
                f"Nenhuma tabela foi encontrada em '{arquivo.name}'."
            )

        df = tabelas[0]

        # Nos relatórios HTML, a primeira linha traz os cabeçalhos reais.
        if all(
            isinstance(coluna, int)
            for coluna in df.columns
        ):
            df.columns = (
                df.iloc[0]
                .astype(str)
                .str.strip()
            )

            df = (
                df.iloc[1:]
                .reset_index(drop=True)
            )

        return df

    raise ValueError(
        f"Formato não suportado: {arquivo.name}"
    )


def renderizar() -> None:
    st.header("Conferência de Subsídios")

    st.write(
        "Verifica se existem documentos ou subsídios pendentes "
        "para as contestações em elaboração."
    )

    st.divider()

    modalidade = st.radio(
        "Quais contestações deseja conferir?",
        [
            "Todos",
            "Próprios",
            "Terceiros",
        ],
        horizontal=True,
    )

    arquivo_contestacoes = st.file_uploader(
        "1. Contestações pendentes",
        type=["xlsx"],
        key="subsidios_contestacoes",
    )

    arquivo_rh = None
    arquivo_destra = None
    arquivo_terceiros = None

    if modalidade in ["Todos", "Próprios"]:
        arquivo_rh = st.file_uploader(
            "2. Documentos RH",
            type=["xls", "xlsx"],
            key="subsidios_rh",
        )

    if modalidade in ["Todos", "Terceiros"]:
        colunas = st.columns(2)

        with colunas[0]:
            arquivo_destra = st.file_uploader(
                "3. Documentos DESTRA",
                type=["xls", "xlsx"],
                key="subsidios_destra",
            )

        with colunas[1]:
            arquivo_terceiros = st.file_uploader(
                "4. Documentos de Terceiros",
                type=["xls", "xlsx"],
                key="subsidios_terceiros",
            )

    arquivos_ok = (
        arquivo_contestacoes is not None
    )

    if modalidade == "Próprios":
        arquivos_ok = (
            arquivos_ok
            and arquivo_rh is not None
        )

    elif modalidade == "Terceiros":
        arquivos_ok = (
            arquivos_ok
            and arquivo_destra is not None
            and arquivo_terceiros is not None
        )

    elif modalidade == "Todos":
        arquivos_ok = (
            arquivos_ok
            and arquivo_rh is not None
            and arquivo_destra is not None
            and arquivo_terceiros is not None
        )

    if not arquivos_ok:
        if modalidade == "Próprios":
            st.info(
                "Envie Contestações Pendentes e Documentos RH."
            )

        elif modalidade == "Terceiros":
            st.info(
                "Envie Contestações Pendentes, "
                "Documentos DESTRA e Documentos de Terceiros."
            )

        else:
            st.info(
                "Para conferir todos os casos, "
                "envie as quatro planilhas."
            )

    processar = st.button(
        "Processar conferência de subsídios",
        type="primary",
        disabled=not arquivos_ok,
    )

    if not processar:
        return

    try:
        with st.spinner(
            "Lendo planilhas e conferindo subsídios..."
        ):
            contestacoes = _ler_excel_ou_html(
                arquivo_contestacoes
            )

            rh = (
                _ler_excel_ou_html(arquivo_rh)
                if arquivo_rh is not None
                else None
            )

            destra = (
                _ler_excel_ou_html(arquivo_destra)
                if arquivo_destra is not None
                else None
            )

            terceiros = (
                _ler_excel_ou_html(arquivo_terceiros)
                if arquivo_terceiros is not None
                else None
            )

            resultado = realizar_conferencia_subsidios(
                contestacoes=contestacoes,
                modalidade=modalidade,
                rh=rh,
                destra=destra,
                terceiros=terceiros,
            )

        st.success("Conferência concluída.")

        metricas = st.columns(4)

        metricas[0].metric(
            "Contestações conferidas",
            resultado["total_contestacoes"],
        )

        metricas[1].metric(
            "Com pendências",
            resultado["total_pendentes"],
        )

        metricas[2].metric(
            "Sem pendência identificada",
            resultado["total_sem_pendencia"],
        )

        metricas[3].metric(
            "Verificar",
            resultado["total_verificar"],
        )

        st.divider()

        st.subheader(
            "Casos com subsídios pendentes"
        )

        if resultado["pendentes"].empty:
            st.success(
                "Nenhuma pendência de subsídios "
                "foi identificada."
            )
        else:
            st.dataframe(
                resultado["pendentes"],
                use_container_width=True,
                hide_index=True,
            )

        abas = st.tabs(
            [
                "Todos os casos",
                "Sem pendência",
                "Verificar",
            ]
        )

        with abas[0]:
            st.dataframe(
                resultado["resultado"],
                use_container_width=True,
                hide_index=True,
            )

        with abas[1]:
            st.dataframe(
                resultado["sem_pendencia"],
                use_container_width=True,
                hide_index=True,
            )

        with abas[2]:
            st.dataframe(
                resultado["verificar"],
                use_container_width=True,
                hide_index=True,
            )

        st.download_button(
            "Baixar resultado em Excel",
            data=gerar_excel_subsidios(
                resultado
            ),
            file_name=(
                "resultado_conferencia_subsidios.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
        )

    except Exception as erro:
        st.error(
            "Não foi possível concluir a conferência."
        )
        st.exception(erro)