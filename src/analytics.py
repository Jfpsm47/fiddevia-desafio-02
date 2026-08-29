"""Indicadores, exportações e gráficos."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

#: Classificações que representam atendimentos reais e distintos. Duplicados e
#: inválidos são contados à parte: incluí-los nas médias e nas contagens por
#: categoria inflava os indicadores com registros que o próprio sistema
#: rejeitou (BUG-016).
CLASSIFICACOES_UTEIS = ("valido", "incompleto")

ROTULO_SEM_CATEGORIA = "Não classificada"


def base_util(df: pd.DataFrame) -> pd.DataFrame:
    """Recorta os registros que devem sustentar os indicadores analíticos."""
    if "classificacao" not in df:
        return df
    return df[df["classificacao"].isin(CLASSIFICACOES_UTEIS)]


def _contagem(serie: pd.Series) -> dict:
    return {str(k): int(v) for k, v in serie.value_counts(dropna=False).items()}


def _percentuais(serie: pd.Series, total: int) -> dict:
    if not total:
        return {}
    return {str(k): round(100 * int(v) / total, 2) for k, v in serie.value_counts().items()}


def build_indicators(
    df: pd.DataFrame,
    total_documentos: int = 0,
    total_paginas: int = 0,
    paginas_por_metodo: dict | None = None,
    erros: list[dict] | None = None,
) -> dict:
    """Calcula os indicadores exigidos pelo enunciado.

    As estatísticas de tempo e as contagens por categoria, status e município
    usam apenas a base útil; duplicados e inválidos aparecem nas contagens de
    qualidade. O percentual de OCR é medido sobre **páginas**, como o enunciado
    pede, e não sobre registros (BUG-009).

    Args:
        df: um registro por atendimento encontrado.
        total_documentos: documentos processados.
        total_paginas: páginas lidas em todos os documentos.
        paginas_por_metodo: quantas páginas por método de leitura.
        erros: ocorrências registradas, com as chaves ``etapa`` e ``tipo``.

    Returns:
        O dicionário de indicadores, pronto para serialização.
    """
    paginas_por_metodo = paginas_por_metodo or {}
    erros = erros or []
    util = base_util(df)
    total = int(len(df))

    coluna_tempo = util.get("tempo_minutos", pd.Series(dtype=float))
    tempos = pd.to_numeric(coluna_tempo, errors="coerce").dropna().to_numpy(dtype=float)
    categorias = util.get("categoria", pd.Series(dtype=str)).fillna(ROTULO_SEM_CATEGORIA)

    por_categoria = _contagem(categorias)
    tempo_por_categoria = (
        util.assign(_t=pd.to_numeric(coluna_tempo, errors="coerce"))
        .groupby(categorias)["_t"]
        .mean()
        .dropna()
        if len(util)
        else pd.Series(dtype=float)
    )

    paginas_ocr = int(paginas_por_metodo.get("ocr", 0))
    erros_por_etapa: dict[str, int] = {}
    erros_por_tipo: dict[str, int] = {}
    for erro in erros:
        erros_por_etapa[erro["etapa"]] = erros_por_etapa.get(erro["etapa"], 0) + 1
        erros_por_tipo[erro["tipo"]] = erros_por_tipo.get(erro["tipo"], 0) + 1

    return {
        "total_documentos": int(total_documentos),
        "total_paginas": int(total_paginas),
        "total_registros": total,
        "base_util": int(len(util)),
        "por_classificacao": _contagem(df.get("classificacao", pd.Series(dtype=str))),
        "percentual_por_classificacao": _percentuais(
            df.get("classificacao", pd.Series(dtype=str)), total
        ),
        "por_categoria": por_categoria,
        "por_status": _contagem(util.get("status", pd.Series(dtype=str))),
        "por_municipio": _contagem(util.get("municipio", pd.Series(dtype=str)).dropna()),
        "por_uf": _contagem(util.get("uf", pd.Series(dtype=str)).dropna()),
        "por_metodo_extracao": _contagem(df.get("metodo", pd.Series(dtype=str))),
        "categoria_maior_volume": (
            max(por_categoria, key=por_categoria.get) if por_categoria else None
        ),
        "categoria_maior_tempo_medio": (
            str(tempo_por_categoria.idxmax()) if len(tempo_por_categoria) else None
        ),
        "tempo_medio": float(np.mean(tempos)) if tempos.size else None,
        "tempo_mediano": float(np.median(tempos)) if tempos.size else None,
        # Desvio amostral: os atendimentos são uma amostra, não a população.
        "tempo_desvio_padrao": float(np.std(tempos, ddof=1)) if tempos.size > 1 else None,
        "paginas_por_metodo": {str(k): int(v) for k, v in paginas_por_metodo.items()},
        "percentual_paginas_ocr": (
            round(100 * paginas_ocr / total_paginas, 2) if total_paginas else 0.0
        ),
        "total_erros": len(erros),
        "erros_por_etapa": erros_por_etapa,
        "erros_por_tipo": erros_por_tipo,
    }


def export_results(
    df: pd.DataFrame,
    output_dir: str | Path,
    csv_name: str,
    json_name: str,
    **contexto,
) -> dict:
    """Exporta o CSV tratado e o JSON de indicadores, ambos em UTF-8."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    indicators = build_indicators(df, **contexto)
    df.to_csv(out / csv_name, index=False, encoding="utf-8")
    (out / json_name).write_text(
        json.dumps(indicators, ensure_ascii=False, indent=2, default=float), encoding="utf-8"
    )
    return indicators


def _barras(serie: pd.Series, titulo: str, eixo_x: str, cor: str, destino: Path) -> None:
    if serie.empty:
        return
    eixo = serie.sort_values().plot.barh(color=cor, figsize=(9, 5))
    eixo.set_title(titulo)
    eixo.set_xlabel(eixo_x)
    eixo.set_ylabel("")
    plt.tight_layout()
    plt.savefig(destino, dpi=160)
    plt.close()


def generate_charts(df: pd.DataFrame, directory: str | Path) -> list[Path]:
    """Gera os gráficos obrigatórios, todos sobre a base útil.

    Returns:
        Os arquivos escritos.
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    util = base_util(df)
    if util.empty:
        return []

    categorias = util.get("categoria", pd.Series(dtype=str)).fillna(ROTULO_SEM_CATEGORIA)
    gerados = []

    destino = path / "atendimentos_categoria.png"
    _barras(
        categorias.value_counts(), "Atendimentos por categoria", "Quantidade", "#1F4E78", destino
    )
    gerados.append(destino)

    coluna = util.get("tempo_minutos", pd.Series(dtype=float))
    tempos = util.assign(_t=pd.to_numeric(coluna, errors="coerce"))
    media = tempos.groupby(categorias)["_t"].mean().dropna()
    destino = path / "tempo_medio_categoria.png"
    _barras(media, "Tempo médio por categoria", "Minutos", "#D6A84B", destino)
    gerados.append(destino)

    municipios = util.get("municipio", pd.Series(dtype=str)).dropna()
    destino = path / "atendimentos_municipio.png"
    if not municipios.empty:
        _barras(
            municipios.value_counts(), "Atendimentos por município",
            "Quantidade", "#2E7D5B", destino,
        )
        gerados.append(destino)
    else:
        # Sem município resolvido, o terceiro gráfico obrigatório recai sobre
        # status, alternativa admitida pelo enunciado.
        destino = path / "atendimentos_status.png"
        _barras(
            util.get("status", pd.Series(dtype=str)).fillna("Sem informação").value_counts(),
            "Atendimentos por status", "Quantidade", "#2E7D5B", destino,
        )
        gerados.append(destino)

    return gerados
