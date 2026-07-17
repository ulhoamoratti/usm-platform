import pandas as pd
import streamlit as st

from services.comparacao import (
    gerar_excel_resultado,
    realizar_conferencia,
)


st.set_page_config(
    page_title="USM Platform",
    layout="wide",
)


st.title("USM Platform")

st.subheader(
    "Conferência de Audiências"
)

st.write(
    """
    A ferramenta identifica as audiências agendadas no TRT
    relativas aos processos da carteira e compara cada evento
    com a pauta interna.

    O resultado distingue processos ausentes, divergências
    de data, divergências de horário e audiências conferidas.
    """
)

st.divider()


coluna_1, coluna_2, coluna_3 = st.columns(
    3
)


with coluna_1:
    arquivo_carteira = st.file_uploader(
        "1. Carteira de processos",
        type=["xlsx"],
        key="arquivo_carteira",
    )


with coluna_2:
    arquivo_trt = st.file_uploader(
        "2. Base do TRT",
        type=["xlsx"],
        key="arquivo_trt",
    )


with coluna_3:
    arquivo_pauta = st.file_uploader(
        "3. Pauta interna",
        type=["xlsx"],
        key="arquivo_pauta",
    )


arquivos_enviados = (
    arquivo_carteira is not None
    and arquivo_trt is not None
    and arquivo_pauta is not None
)


if not arquivos_enviados:
    st.info(
        "Envie os três arquivos para habilitar "
        "o processamento."
    )


botao_processar = st.button(
    "Processar conferência",
    type="primary",
    disabled=not arquivos_enviados,
)


if botao_processar:
    try:
        with st.spinner(
            "Lendo e comparando as bases..."
        ):
            carteira = pd.read_excel(
                arquivo_carteira
            )

            trt = pd.read_excel(
                arquivo_trt
            )

            pauta_interna = pd.read_excel(
                arquivo_pauta
            )

            resultado = realizar_conferencia(
                carteira=carteira,
                trt=trt,
                pauta_interna=pauta_interna,
            )

        st.success(
            "Conferência concluída com sucesso."
        )

        st.divider()

        linha_1_coluna_1, linha_1_coluna_2 = (
            st.columns(2)
        )

        linha_1_coluna_1.metric(
            "Audiências agendadas no TRT",
            resultado[
                "total_audiencias_trt"
            ],
        )

        linha_1_coluna_2.metric(
            "Audiências dos seus processos",
            resultado[
                "total_audiencias_carteira"
            ],
        )

        (
            linha_2_coluna_1,
            linha_2_coluna_2,
            linha_2_coluna_3,
            linha_2_coluna_4,
        ) = st.columns(4)

        linha_2_coluna_1.metric(
            "Processos ausentes",
            resultado[
                "total_ausentes"
            ],
        )

        linha_2_coluna_2.metric(
            "Data divergente",
            resultado[
                "total_divergencias_data"
            ],
        )

        linha_2_coluna_3.metric(
            "Horário divergente",
            resultado[
                "total_divergencias_horario"
            ],
        )

        linha_2_coluna_4.metric(
            "Conferidas",
            resultado[
                "total_conferidas"
            ],
        )

        st.divider()

        st.header(
            "Inconsistências identificadas"
        )

        inconsistencias = resultado[
            "inconsistencias"
        ]

        if inconsistencias.empty:
            st.success(
                "Todas as audiências foram encontradas "
                "na pauta interna com a mesma data e horário."
            )

        else:
            st.error(
                f"Foram identificadas "
                f"{resultado['total_inconsistencias']} "
                "audiências que exigem conferência."
            )

            st.dataframe(
                inconsistencias,
                use_container_width=True,
                hide_index=True,
            )

        (
            aba_ausentes,
            aba_data,
            aba_horario,
            aba_conferidas,
        ) = st.tabs(
            [
                "Processos ausentes",
                "Divergências de data",
                "Divergências de horário",
                "Conferidas",
            ]
        )

        with aba_ausentes:
            ausentes = resultado[
                "ausentes"
            ]

            if ausentes.empty:
                st.success(
                    "Nenhum processo está ausente "
                    "da pauta interna."
                )
            else:
                st.dataframe(
                    ausentes,
                    use_container_width=True,
                    hide_index=True,
                )

        with aba_data:
            divergencias_data = resultado[
                "divergencias_data"
            ]

            if divergencias_data.empty:
                st.success(
                    "Nenhuma divergência de data "
                    "foi identificada."
                )
            else:
                st.dataframe(
                    divergencias_data,
                    use_container_width=True,
                    hide_index=True,
                )

        with aba_horario:
            divergencias_horario = resultado[
                "divergencias_horario"
            ]

            if divergencias_horario.empty:
                st.success(
                    "Nenhuma divergência de horário "
                    "foi identificada."
                )
            else:
                st.dataframe(
                    divergencias_horario,
                    use_container_width=True,
                    hide_index=True,
                )

        with aba_conferidas:
            st.dataframe(
                resultado[
                    "conferidas"
                ],
                use_container_width=True,
                hide_index=True,
            )

        arquivo_excel = gerar_excel_resultado(
            resultado
        )

        st.divider()

        st.download_button(
            label="Baixar resultado detalhado em Excel",
            data=arquivo_excel,
            file_name=(
                "resultado_detalhado_conferencia_audiencias.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
        )

    except ValueError as erro:
        st.error(
            str(erro)
        )

    except Exception as erro:
        st.error(
            "Ocorreu um erro inesperado durante "
            "a conferência."
        )

        st.exception(
            erro
        )