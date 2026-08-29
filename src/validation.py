"""Extração por regex, normalização e validação dos registros."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PROTO_RE = re.compile(r"^AT-\d{3}$")
CEP_RE = re.compile(r"^\d{5}-?\d{3}$")

FIELD_PATTERNS = {
    "protocolo": r"Protocolo\s+(AT-\d{3}|PROTOCOLO\?)",
    "data": r"Data\s+(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})",
    "solicitante": r"Solicitante\s+(.+?)\s+E-mail",
    "email": r"E-mail\s+(\S+)",
    "categoria": r"Categoria\s+(.+?)\s+Status",
    "status": r"Status\s+(Concluido|Pendente|Em atendimento)",
    "cep": r"CEP\s*/?\s*cidade\s+(\S+)",
    "municipio_uf": r"CEP\s*/?\s*cidade\s+\S+\s*-\s*(.+?)\s+Tempo",
    "tempo_minutos": r"Tempo\s+(-?\d+)?\s*min",
    "descricao": r"Problema\s+(.+?)\s+Solucao",
    "solucao": r"Solucao\s+(.+?)\s+Observacoes",
    "observacoes": r"Observacoes\s+(.+)$",
}

#: Marcadores que os documentos usam no lugar de um valor ausente. Sem esta
#: normalização, ``Solicitante [vazio]`` passava como campo preenchido e o
#: registro era classificado como válido (BUG-004).
SENTINELAS_AUSENCIA = frozenset({
    "", "[vazio]", "[ vazio ]", "vazio", "n/a", "na", "nao informado",
    "sem informacao", "-", "--", "---", "?", "null", "none", "nulo",
})

#: Campos obrigatórios cuja ausência, isoladamente, torna o registro incompleto.
CAMPOS_OBRIGATORIOS = ("solicitante", "descricao")


def clean_text(text: str) -> str:
    """Colapsa espaços e remove caracteres nulos, preservando o conteúdo."""
    text = text.replace("\x00", " ")
    return re.sub(r"\s+", " ", text).strip()


def extract_fields(text: str) -> dict:
    """Localiza os campos do formulário no texto de um registro.

    Returns:
        Um dicionário com uma chave por campo de :data:`FIELD_PATTERNS`;
        campos não encontrados vêm como string vazia.
    """
    clean = clean_text(text)
    result = {}
    for key, pattern in FIELD_PATTERNS.items():
        match = re.search(pattern, clean, re.I | re.S)
        result[key] = match.group(1).strip() if match else ""
    return result


def parse_date(value: str):
    """Converte uma data em ``dd/mm/aaaa`` ou ``aaaa-mm-dd``; ``None`` se inválida."""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except (ValueError, TypeError):
            pass
    return None


def normalize_key(value: str) -> str:
    """Reduz um texto a uma chave comparável: sem acento, minúscula, sem espaço extra."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"\s+", " ", value)


def is_missing(value) -> bool:
    """Diz se um valor deve ser tratado como ausente.

    Cobre tanto o campo vazio quanto os marcadores textuais usados nos
    documentos, como ``[vazio]`` (BUG-004).
    """
    if value is None:
        return True
    return normalize_key(str(value)) in SENTINELAS_AUSENCIA


def normalize_category(value: str, categories: dict) -> str | None:
    """Converte uma variação de escrita na categoria oficial correspondente."""
    target = normalize_key(value)
    for item in categories.get("categorias_oficiais", []):
        if target in {normalize_key(item["nome"]), *(normalize_key(v) for v in item["variacoes"])}:
            return item["nome"]
    return None


def validate_record(
    record: dict,
    categories: dict,
    campos_ilegiveis: frozenset[str] | set[str] = frozenset(),
) -> tuple[str, list[str], dict]:
    """Valida, normaliza e classifica um registro.

    Cada campo produz, no máximo, um motivo: ``*_ausente`` quando não há valor e
    ``*_invalido`` quando há valor malformado. A classificação segue a
    precedência **inválido acima de incompleto** — um registro com um campo
    errado é inválido mesmo que outro campo esteja faltando (BUG-005).

    Campos que o OCR não conseguiu ler recebem o motivo ``*_ilegivel`` e contam
    como ausência, não como invalidez: dizer que o dado está errado quando o
    problema foi a leitura falsearia o indicador de qualidade.

    Args:
        record: campos brutos, como devolvidos por :func:`extract_fields`.
        categories: conteúdo de ``categorias.json``.
        campos_ilegiveis: campos que a digitalização não permitiu recuperar.

    Returns:
        A classificação (``valido``, ``incompleto`` ou ``invalido``), a lista de
        motivos e o registro com os valores normalizados.
    """
    r = dict(record)
    ausentes: list[str] = []
    invalidos: list[str] = []
    ilegiveis = set(campos_ilegiveis)

    def registrar_ausencia(campo: str, sufixo: str) -> None:
        ausentes.append(f"{campo}_ilegivel" if campo in ilegiveis else f"{campo}_{sufixo}")

    protocolo = (r.get("protocolo") or "").strip().upper()
    r["protocolo"] = protocolo
    if is_missing(protocolo):
        registrar_ausencia("protocolo", "ausente")
    elif not PROTO_RE.fullmatch(protocolo):
        invalidos.append("protocolo_invalido")

    data_bruta = r.get("data", "")
    if is_missing(data_bruta):
        r["data_obj"] = None
        registrar_ausencia("data", "ausente")
    else:
        r["data_obj"] = parse_date(data_bruta.strip())
        if not r["data_obj"]:
            invalidos.append("data_invalida")

    email = (r.get("email") or "").strip()
    if is_missing(email):
        registrar_ausencia("email", "ausente")
    elif not EMAIL_RE.fullmatch(email):
        invalidos.append("email_invalido")

    cep = (r.get("cep") or "").strip()
    r["cep"] = cep
    if is_missing(cep):
        registrar_ausencia("cep", "ausente")
    elif not CEP_RE.fullmatch(cep):
        invalidos.append("cep_invalido")

    categoria = r.get("categoria", "")
    if is_missing(categoria):
        r["categoria_normalizada"] = None
        registrar_ausencia("categoria", "ausente")
    else:
        r["categoria_normalizada"] = normalize_category(categoria, categories)
        if not r["categoria_normalizada"]:
            invalidos.append("categoria_invalida")

    tempo = r.get("tempo_minutos", "")
    if is_missing(tempo):
        r["tempo_obj"] = None
        registrar_ausencia("tempo", "ausente")
    else:
        try:
            valor = float(str(tempo).strip())
            if valor < 0:
                raise ValueError("tempo negativo")
            r["tempo_obj"] = valor
        except (ValueError, TypeError):
            r["tempo_obj"] = None
            invalidos.append("tempo_invalido")

    for campo in CAMPOS_OBRIGATORIOS:
        if is_missing(r.get(campo)):
            registrar_ausencia(campo, "ausente")

    reasons = invalidos + ausentes
    if invalidos:
        classification = "invalido"
    elif ausentes:
        classification = "incompleto"
    else:
        classification = "valido"
    return classification, reasons, r
