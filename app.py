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
    A ferramenta cruza as audiências agendadas no TRT
    com a carteira de processos e com a pauta interna.

    O resultado separa processos efetivamente ausentes
    de possíveis divergências de data ou horário.
    """
)

st.divider()


coluna_1, coluna_2, coluna_3 = st.columns(3)


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
            "Comparando as bases..."
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

        indicador_1, indicador_2 = st.columns(2)

        indicador_1.metric(
            "Audiências agendadas no TRT",
            resultado[
                "total_audiencias_trt"
            ],
        )

        indicador_2.metric(
            "Audiências dos seus processos",
            resultado[
                "total_audiencias_carteira"
            ],
        )

        indicador_3, indicador_4, indicador_5 = (
            st.columns(3)
        )

        indicador_3.metric(
            "Ausentes da pauta interna",
            resultado[
                "total_ausentes"
            ],
        )

        indicador_4.metric(
            "Data ou horário divergente",
            resultado[
                "total_divergencias"
            ],
        )

        indicador_5.metric(
            "Conferidas",
            resultado[
                "total_conferidas"
            ],
        )

        st.divider()

        aba_ausentes, aba_divergencias, aba_conferidas = (
            st.tabs(
                [
                    "Ausentes da pauta",
                    "Divergências",
                    "Conferidas",
                ]
            )
        )

        with aba_ausentes:
            st.header(
                "Processos sem qualquer registro "
                "na pauta interna"
            )

            ausentes = resultado[
                "ausentes"
            ]

            if ausentes.empty:
                st.success(
                    "Nenhum processo está totalmente "
                    "ausente da pauta interna."
                )

            else:
                st.error(
                    f"Foram identificadas "
                    f"{len(ausentes)} audiências "
                    "cujos processos não aparecem "
                    "na pauta interna."
                )

                st.dataframe(
                    ausentes,
                    use_container_width=True,
                    hide_index=True,
                )

        with aba_divergencias:
            st.header(
                "Processos encontrados com data "
                "ou horário diferente"
            )

            divergencias = resultado[
                "divergencias"
            ]

            if divergencias.empty:
                st.success(
                    "Nenhuma divergência de data "
                    "ou horário foi encontrada."
                )

            else:
                st.warning(
                    f"Foram identificadas "
                    f"{len(divergencias)} audiências "
                    "com possível divergência."
                )

                st.write(
                    """
                    Esses processos existem na pauta interna,
                    mas não foi encontrada correspondência exata
                    com a data e o horário informados pelo TRT.
                    """
                )

                st.dataframe(
                    divergencias,
                    use_container_width=True,
                    hide_index=True,
                )

        with aba_conferidas:
            st.header(
                "Audiências com processo, data e horário "
                "correspondentes"
            )

            st.dataframe(
                resultado[
                    "conferidas"
                ],
                use_container_width=True,
                hide_index=True,
            )

        arquivo_excel = gerar_excel_resultado(
            ausentes=resultado[
                "ausentes"
            ],
            divergencias=resultado[
                "divergencias"
            ],
            conferidas=resultado[
                "conferidas"
            ],
        )

        st.divider()

        st.download_button(
            label="Baixar resultado em Excel",
            data=arquivo_excel,
            file_name=(
                "resultado_conferencia_audiencias.xlsx"
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