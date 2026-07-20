from __future__ import annotations

from io import BytesIO
import re
import unicodedata
from typing import Any

import pandas as pd


_COL_PROCESSO_BASE = "Processo"
_COL_PASTA_BASE = "Pasta"
_COL_TIPO_BASE = "Próprio/Terceiro"


def _texto(valor: Any) -> str:
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def _sem_acentos(valor: Any) -> str:
    texto = _texto(valor)
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )


def _normalizar_cabecalhos(df: pd.DataFrame) -> pd.DataFrame:
    copia = df.copy()
    copia.columns = [_texto(coluna) for coluna in copia.columns]
    return copia


def _normalizar_processo(valor: Any) -> str:
    digitos = re.sub(r"\D", "", _texto(valor))
    return digitos if len(digitos) == 20 else ""


def _normalizar_pasta(valor: Any) -> str:
    texto = _texto(valor)
    if not texto:
        return ""
    try:
        numero = float(texto.replace(",", "."))
        if numero.is_integer():
            return str(int(numero))
    except ValueError:
        pass
    return re.sub(r"\s+", "", texto).upper()


def _normalizar_tipo(valor: Any) -> str:
    texto = _sem_acentos(valor).upper()
    if "TERCEIR" in texto:
        return "TERCEIRO"
    if "PROPRI" in texto:
        return "PRÓPRIO"
    return "NÃO IDENTIFICADO"


def _valor_coluna(linha: pd.Series, nomes: list[str]) -> str:
    for nome in nomes:
        if nome in linha.index:
            valor = _texto(linha[nome])
            if valor:
                return valor
    return ""


def _validar_colunas(df: pd.DataFrame, obrigatorias: list[str], nome_base: str) -> None:
    ausentes = [coluna for coluna in obrigatorias if coluna not in df.columns]
    if ausentes:
        raise ValueError(
            f"A planilha '{nome_base}' não possui as colunas obrigatórias: "
            + ", ".join(ausentes)
        )


def _preparar_chaves(df: pd.DataFrame, coluna_processo: str, coluna_pasta: str) -> pd.DataFrame:
    copia = df.copy()
    copia["__processo"] = copia[coluna_processo].map(_normalizar_processo)
    copia["__pasta"] = copia[coluna_pasta].map(_normalizar_pasta)
    return copia


def _localizar_registros(
    df: pd.DataFrame,
    processo: str,
    pasta: str,
) -> tuple[pd.DataFrame, str]:
    if processo:
        por_processo = df[df["__processo"] == processo]
        if not por_processo.empty:
            return por_processo, "Processo CNJ"

    if pasta:
        por_pasta = df[df["__pasta"] == pasta]
        if not por_pasta.empty:
            return por_pasta, "Pasta"

    return df.iloc[0:0].copy(), "Não localizado"


def _status_pendente(valor: Any) -> bool:
    texto = _sem_acentos(valor).upper()
    return "PENDENTE" in texto or texto in {"ABERTO", "NAO CONCLUIDO"}


def _resumir_rh(registros: pd.DataFrame) -> dict[str, str]:
    if registros.empty:
        return {
            "status": "SEM PENDÊNCIA IDENTIFICADA",
            "faltantes": "",
            "detalhe": "Nenhuma pendência de RH localizada.",
        }

    pendentes = registros[registros["STATUS"].map(_status_pendente)]
    if pendentes.empty:
        return {
            "status": "OK",
            "faltantes": "",
            "detalhe": "Registros de RH localizados sem status pendente.",
        }

    documentos = []
    for _, linha in pendentes.iterrows():
        documento = _valor_coluna(linha, ["DOCUMENTO"])
        observacao = _valor_coluna(linha, ["OBSERVAÇÕES", "OBSERVACOES"])
        item = documento or "Documento de RH não especificado"
        if observacao:
            item = f"{item} ({observacao})"
        documentos.append(item)

    documentos = list(dict.fromkeys(documentos))
    return {
        "status": "PENDENTE",
        "faltantes": " | ".join(documentos),
        "detalhe": f"{len(pendentes)} pendência(s) de RH localizada(s).",
    }


def _resumir_destra(registros: pd.DataFrame) -> dict[str, str]:
    if registros.empty:
        return {
            "status": "SEM PENDÊNCIA IDENTIFICADA",
            "faltantes": "",
            "detalhe": "Nenhuma solicitação DESTRA localizada.",
        }

    pendentes = registros[registros["STATUS"].map(_status_pendente)]
    if pendentes.empty:
        return {
            "status": "OK",
            "faltantes": "",
            "detalhe": "Solicitação DESTRA localizada sem status pendente.",
        }

    itens = []
    for _, linha in pendentes.iterrows():
        andamento = _valor_coluna(linha, ["Andamento", "ANDAMENTO"])
        prazo = _valor_coluna(linha, ["PRAZO FATAL"])
        item = andamento or "Documentação DESTRA"
        if prazo:
            item = f"{item} - prazo: {prazo}"
        itens.append(item)

    itens = list(dict.fromkeys(itens))
    return {
        "status": "PENDENTE",
        "faltantes": " | ".join(itens),
        "detalhe": f"{len(pendentes)} solicitação(ões) DESTRA pendente(s).",
    }


def _resumir_terceiros(registros: pd.DataFrame) -> dict[str, str]:
    if registros.empty:
        return {
            "status": "SEM PENDÊNCIA IDENTIFICADA",
            "faltantes": "",
            "detalhe": "Nenhuma solicitação pendente de Terceiros localizada.",
        }

    solicitacoes = []
    for _, linha in registros.iterrows():
        solicitacao = _valor_coluna(linha, ["SOLICITAÇÃO", "SOLICITACAO"])
        prazo = _valor_coluna(linha, ["DATA PRAZO"])
        item = solicitacao or "Documentação de Terceiros"
        if prazo:
            item = f"{item} - prazo: {prazo}"
        solicitacoes.append(item)

    solicitacoes = list(dict.fromkeys(solicitacoes))
    return {
        "status": "PENDENTE",
        "faltantes": " | ".join(solicitacoes),
        "detalhe": f"{len(registros)} solicitação(ões) de Terceiros pendente(s).",
    }


def realizar_conferencia_subsidios(
    contestacoes: pd.DataFrame,
    destra: pd.DataFrame,
    terceiros: pd.DataFrame,
    rh: pd.DataFrame,
) -> dict[str, Any]:
    contestacoes = _normalizar_cabecalhos(contestacoes)
    destra = _normalizar_cabecalhos(destra)
    terceiros = _normalizar_cabecalhos(terceiros)
    rh = _normalizar_cabecalhos(rh)

    _validar_colunas(
        contestacoes,
        [_COL_PROCESSO_BASE, _COL_PASTA_BASE, _COL_TIPO_BASE],
        "Contestações pendentes",
    )
    _validar_colunas(destra, ["NÚMERO DO PROCESSO", "Nº PASTA", "STATUS"], "Documentos DESTRA")
    _validar_colunas(terceiros, ["NÚMERO DO PROCESSO", "PASTA", "SOLICITAÇÃO"], "Documentos de Terceiros")
    _validar_colunas(rh, ["NÚMERO DO PROCESSO", "PASTA", "DOCUMENTO", "STATUS"], "Documentos RH")

    destra = _preparar_chaves(destra, "NÚMERO DO PROCESSO", "Nº PASTA")
    terceiros = _preparar_chaves(terceiros, "NÚMERO DO PROCESSO", "PASTA")
    rh = _preparar_chaves(rh, "NÚMERO DO PROCESSO", "PASTA")

    linhas_resultado: list[dict[str, Any]] = []

    for _, linha in contestacoes.iterrows():
        processo_original = _texto(linha[_COL_PROCESSO_BASE])
        pasta_original = _texto(linha[_COL_PASTA_BASE])
        processo = _normalizar_processo(processo_original)
        pasta = _normalizar_pasta(pasta_original)
        tipo = _normalizar_tipo(linha[_COL_TIPO_BASE])

        resultado_linha: dict[str, Any] = {
            "Pasta": pasta_original,
            "Processo": processo_original,
            "Adverso": _valor_coluna(linha, ["Adverso do processo", "Pessoa"]),
            "Prazo fatal": _valor_coluna(linha, ["Data do prazo fatal"]),
            "Próprio/Terceiro": tipo,
            "Status geral": "",
            "Fonte pendente": "",
            "O que está faltando": "",
            "Critério de correspondência": "",
            "Status RH": "N/A",
            "Status DESTRA": "N/A",
            "Status Terceiros": "N/A",
        }

        if tipo == "PRÓPRIO":
            registros_rh, criterio = _localizar_registros(rh, processo, pasta)
            resumo_rh = _resumir_rh(registros_rh)
            resultado_linha["Status RH"] = resumo_rh["status"]
            resultado_linha["Critério de correspondência"] = criterio

            if resumo_rh["status"] == "PENDENTE":
                resultado_linha["Status geral"] = "SUBSÍDIOS PENDENTES"
                resultado_linha["Fonte pendente"] = "RH"
                resultado_linha["O que está faltando"] = resumo_rh["faltantes"]
            else:
                resultado_linha["Status geral"] = "SEM PENDÊNCIA IDENTIFICADA"

        elif tipo == "TERCEIRO":
            registros_destra, criterio_destra = _localizar_registros(destra, processo, pasta)
            registros_terceiros, criterio_terceiros = _localizar_registros(terceiros, processo, pasta)

            resumo_destra = _resumir_destra(registros_destra)
            resumo_terceiros = _resumir_terceiros(registros_terceiros)

            resultado_linha["Status DESTRA"] = resumo_destra["status"]
            resultado_linha["Status Terceiros"] = resumo_terceiros["status"]

            criterios = [
                criterio
                for criterio in [criterio_destra, criterio_terceiros]
                if criterio != "Não localizado"
            ]
            resultado_linha["Critério de correspondência"] = " / ".join(dict.fromkeys(criterios)) or "Não localizado"

            fontes = []
            faltantes = []
            if resumo_destra["status"] == "PENDENTE":
                fontes.append("DESTRA")
                faltantes.append(f"DESTRA: {resumo_destra['faltantes']}")
            if resumo_terceiros["status"] == "PENDENTE":
                fontes.append("TERCEIROS")
                faltantes.append(f"TERCEIROS: {resumo_terceiros['faltantes']}")

            if fontes:
                resultado_linha["Status geral"] = "SUBSÍDIOS PENDENTES"
                resultado_linha["Fonte pendente"] = " + ".join(fontes)
                resultado_linha["O que está faltando"] = " || ".join(faltantes)
            else:
                resultado_linha["Status geral"] = "SEM PENDÊNCIA IDENTIFICADA"

        else:
            resultado_linha["Status geral"] = "VERIFICAR CLASSIFICAÇÃO"
            resultado_linha["O que está faltando"] = "Valor de Próprio/Terceiro não reconhecido."
            resultado_linha["Critério de correspondência"] = "Não aplicável"

        linhas_resultado.append(resultado_linha)

    resultado_df = pd.DataFrame(linhas_resultado)
    pendentes = resultado_df[resultado_df["Status geral"] == "SUBSÍDIOS PENDENTES"].copy()
    sem_pendencia = resultado_df[resultado_df["Status geral"] == "SEM PENDÊNCIA IDENTIFICADA"].copy()
    verificar = resultado_df[resultado_df["Status geral"] == "VERIFICAR CLASSIFICAÇÃO"].copy()

    return {
        "resultado": resultado_df,
        "pendentes": pendentes,
        "sem_pendencia": sem_pendencia,
        "verificar": verificar,
        "total_contestacoes": len(resultado_df),
        "total_pendentes": len(pendentes),
        "total_sem_pendencia": len(sem_pendencia),
        "total_verificar": len(verificar),
    }


def gerar_excel_subsidios(resultado: dict[str, Any]) -> bytes:
    saida = BytesIO()
    with pd.ExcelWriter(saida, engine="openpyxl") as writer:
        resultado["resultado"].to_excel(writer, sheet_name="Resultado geral", index=False)
        resultado["pendentes"].to_excel(writer, sheet_name="Subsídios pendentes", index=False)
        resultado["sem_pendencia"].to_excel(writer, sheet_name="Sem pendência", index=False)
        resultado["verificar"].to_excel(writer, sheet_name="Verificar", index=False)
    saida.seek(0)
    return saida.getvalue()

