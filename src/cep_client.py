"""Cliente tolerante a falhas para consulta de CEP."""
from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)


def lookup_cep(cep: str, base_url: str, timeout: int = 8) -> dict | None:
    """Consulta município, UF e logradouro de um CEP.

    Args:
        cep: CEP com ou sem separadores.
        base_url: raiz do serviço, sem a barra final.
        timeout: tempo máximo de espera, em segundos.

    Returns:
        Os dados da localidade, ou ``None`` quando o CEP é malformado, não
        existe ou o serviço está indisponível. Nunca levanta exceção: o
        enriquecimento é complementar e não pode interromper o pipeline (RF07).
    """
    digits = "".join(ch for ch in cep if ch.isdigit())
    if len(digits) != 8:
        return None
    try:
        response = requests.get(
            f"{base_url.rstrip('/')}/{digits}/json/",
            timeout=timeout,
            headers={"User-Agent": "fic-dev-desafio/1.0"},
        )
        response.raise_for_status()
        data = response.json()
        if data.get("erro"):
            return None
        return {
            "municipio": data.get("localidade"),
            "uf": data.get("uf"),
            "logradouro": data.get("logradouro"),
        }
    except (requests.RequestException, ValueError) as exc:
        # Sem detalhes da resposta no log: ela pode conter dados de endereço.
        logger.warning("Consulta de CEP indisponível (%s).", type(exc).__name__)
        return None
