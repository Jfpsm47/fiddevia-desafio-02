"""Extração estruturada dos formulários digitalizados.

O PDF escaneado usa um layout diferente dos demais: uma tabela de duas colunas
de rótulo e valor, e não a lista vertical dos documentos digitais. Sobre o texto
corrido do OCR os próprios rótulos saem corrompidos — ``Protocob``, ``Probkm a``,
``Solicao`` — e nenhum padrão do :mod:`src.validation` casa (BUG-032).

A estratégia aqui é ler **célula a célula**: a grade da tabela é detectada por
projeção de pixels, e cada célula recebe OCR com a lista de caracteres do seu
tipo de campo. Isso recupera protocolo, CEP e tempo integralmente, e boa parte
de data, categoria e status.

O que a imagem não contém, ninguém recupera: a 150 DPI o ``@`` e os pontos dos
e-mails simplesmente não estão lá. Esses campos são marcados como **ilegíveis**,
nunca inventados nem confundidos com dado inválido.
"""
from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from typing import Any

#: Passadas de OCR usadas no campo de identidade. Um protocolo errado é pior
#: que um protocolo ausente — ele vira a chave do registro. Só é aceito o valor
#: em que todas as passadas concordam.
PASSADAS_PROTOCOLO = (
    {"escala": 3},
    {"escala": 4},
    {"escala": 5},
    {"escala": 4, "resample": "BICUBIC"},
)

#: Só ASCII, de propósito: incluir letras acentuadas na lista de caracteres do
#: Tesseract degrada o reconhecimento dos dígitos vizinhos — o CEP 78205-160
#: chegava a sair como 7825-169.
LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz "

#: Lista de caracteres por campo: restringir o alfabeto reduz muito o erro.
WHITELIST = {
    "protocolo": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-?",
    "data": "0123456789/-",
    "solicitante": LETRAS,
    "email": "abcdefghijklmnopqrstuvwxyz0123456789.@-_",
    "categoria": LETRAS,
    "status": LETRAS,
    # A célula "CEP / cidade" é lida sem restrição: qualquer lista de
    # caracteres elimina os espaços que separam o município da UF.
    "cep": None,
    "tempo_minutos": "0123456789- minvazio[]",
}

#: Posição de cada campo na grade: (linha, coluna de valor).
POSICOES = {
    "protocolo": (0, 1), "data": (0, 3),
    "solicitante": (1, 1), "email": (1, 3),
    "categoria": (2, 1), "status": (2, 3),
    "cep": (3, 1), "tempo_minutos": (3, 3),
    "descricao": (4, 1), "solucao": (5, 1), "observacoes": (6, 1),
}

#: O formulário digitalizado tem quatro colunas, portanto cinco divisórias.
BORDAS_ESPERADAS = 5

#: Abaixo desta semelhança, um valor lido não é atribuído a um valor oficial.
CORTE_SEMELHANCA = 0.75

#: Um nome plausível tem ao menos dois vocábulos separados. A digitalização
#: costuma perder os espaços ("HenrgueOlveiraLuz"), e um nome assim é ruído com
#: aparência de dado — não serve para identificar ninguém.
MINIMO_VOCABULOS_NOME = 2


def _grupos(indices, folga: int = 2) -> list[list[int]]:
    grupos: list[list[int]] = []
    for i in indices:
        if grupos and i - grupos[-1][-1] <= folga:
            grupos[-1].append(i)
        else:
            grupos.append([i])
    return grupos


def detectar_grade(imagem) -> tuple[list[list[int]], list[int]]:
    """Localiza as bordas da tabela por projeção de pixels escuros.

    Args:
        imagem: página digitalizada, em ``PIL.Image``.

    Returns:
        Um par ``(registros, colunas)``. Cada registro é a lista das 8 linhas
        horizontais que delimitam suas 7 faixas; ``colunas`` são as verticais.
    """
    import numpy as np
    from PIL import ImageOps

    matriz = np.asarray(ImageOps.grayscale(imagem), dtype=float)
    escuro = matriz < 200
    altura, largura = matriz.shape

    horizontais = [
        int(np.mean(g))
        for g in _grupos(np.where(escuro.sum(axis=1) > largura * 0.5)[0])
    ]
    horizontais = [y for y in horizontais if y > altura * 0.08]

    registros: list[list[int]] = []
    atual = horizontais[:1]
    for anterior, seguinte in zip(horizontais, horizontais[1:]):
        if seguinte - anterior > 25:
            atual.append(seguinte)
        else:
            if len(atual) == 8:
                registros.append(atual)
            atual = [seguinte]
    if len(atual) == 8:
        registros.append(atual)

    # As divisórias internas só existem nas quatro primeiras faixas de cada
    # registro — as três últimas ocupam a largura toda. O limiar acompanha essa
    # altura útil: fixo, ele descartaria as colunas de uma página com poucos
    # registros ou exigiria demais de uma página cheia.
    if registros:
        util = sum(linhas[4] - linhas[0] for linhas in registros)
    else:
        util = altura * 0.3
    minimo = max(util * 0.5, 40)
    perfil = escuro.sum(axis=0)
    candidatos = [
        (int(np.mean(g)), float(perfil[g].sum()))
        for g in _grupos(np.where(perfil > minimo)[0])
    ]

    # Agrupa divisórias vizinhas, mantendo a mais forte de cada aglomerado.
    agrupados: list[tuple[int, float]] = []
    for x, forca in candidatos:
        if agrupados and x - agrupados[-1][0] <= 60:
            if forca > agrupados[-1][1]:
                agrupados[-1] = (x, forca)
        else:
            agrupados.append((x, forca))

    # O formulário tem quatro colunas, logo cinco divisórias. Uma página esparsa
    # pode produzir picos extras onde o texto se alinha: ficam as mais fortes.
    if len(agrupados) > BORDAS_ESPERADAS:
        agrupados = sorted(
            sorted(agrupados, key=lambda par: par[1], reverse=True)[:BORDAS_ESPERADAS]
        )
    return registros, [x for x, _ in agrupados]


def ler_celula(imagem, caixa, whitelist: str | None, escala: int = 4, resample: str = "LANCZOS") -> str:
    """Executa OCR em uma célula, com o alfabeto restrito ao tipo do campo."""
    import pytesseract
    from PIL import Image

    x0, y0, x1, y1 = caixa
    if x1 - x0 < 6 or y1 - y0 < 6:
        return ""
    recorte = imagem.crop((x0 + 3, y0 + 3, x1 - 3, y1 - 3))
    filtro = getattr(Image, resample, Image.LANCZOS)
    recorte = recorte.resize((recorte.width * escala, recorte.height * escala), filtro)
    config = "--psm 7"
    if whitelist:
        config += f" -c tessedit_char_whitelist={whitelist}"
    texto = pytesseract.image_to_string(recorte, lang="por", config=config)
    return re.sub(r"\s+", " ", texto).strip()


def _ler_protocolo(imagem, caixa) -> tuple[str, bool]:
    """Lê o protocolo exigindo unanimidade entre passadas independentes.

    Returns:
        O valor lido e se ele é confiável. Sem unanimidade o protocolo é
        considerado ilegível: aceitar um ``AT-951`` no lugar de ``AT-051``
        criaria um registro com identidade errada.
    """
    leituras = [
        re.sub(r"\s+", "", ler_celula(imagem, caixa, WHITELIST["protocolo"], **passada))
        for passada in PASSADAS_PROTOCOLO
    ]
    unico = set(leituras)
    if len(unico) == 1 and leituras[0]:
        return leituras[0], True
    return max(leituras, key=len, default=""), False


def semelhante(valor: str, candidatos, corte: float = CORTE_SEMELHANCA) -> str | None:
    """Aproxima um valor degradado do vocabulário oficial mais próximo.

    Usado só em texto vindo de OCR, e com corte conservador: abaixo dele o
    valor é declarado ilegível em vez de ser atribuído a um palpite.
    """
    from .validation import normalize_key

    alvo = normalize_key(valor)
    if not alvo:
        return None
    melhor, melhor_nota = None, 0.0
    for candidato in candidatos:
        nota = SequenceMatcher(None, alvo, normalize_key(candidato)).ratio()
        if nota > melhor_nota:
            melhor, melhor_nota = candidato, nota
    return melhor if melhor_nota >= corte else None


def nome_plausivel(valor: str) -> bool:
    """Diz se o nome lido tem estrutura suficiente para ser aproveitado."""
    vocabulos = [parte for parte in re.split(r"\s+", valor.strip()) if len(parte) > 1]
    return len(vocabulos) >= MINIMO_VOCABULOS_NOME


def normalizar_data(valor: str) -> str:
    """Recompõe separadores perdidos em datas lidas por OCR (``0107/2026``)."""
    digitos = re.sub(r"\D", "", valor)
    if len(digitos) != 8:
        return valor.strip()
    if digitos.startswith(("19", "20")):
        return f"{digitos[:4]}-{digitos[4:6]}-{digitos[6:]}"
    return f"{digitos[:2]}/{digitos[2:4]}/{digitos[4:]}"


def normalizar_cep(valor: str) -> str:
    """Extrai o CEP da célula ``CEP / cidade``."""
    achado = re.search(r"(\d{5})\s*-?\s*(\d{3})", valor)
    return f"{achado.group(1)}-{achado.group(2)}" if achado else valor.strip()


def separar_municipio_uf(valor: str) -> tuple[str, str]:
    """Separa município e UF de um texto como ``Sinop/MT`` ou ``CaceresM T``.

    A UF é recuperável mesmo em leitura degradada — são as duas últimas letras.
    O município só é aproveitado quando sobrevive à digitalização com estrutura
    reconhecível; caso contrário volta vazio, para ser marcado como ilegível.

    Returns:
        O par ``(municipio, uf)``, com strings vazias no que não foi recuperado.
    """
    texto = valor.strip().strip("-").strip()
    if not texto:
        return "", ""
    if "/" in texto:
        municipio, _, uf = texto.rpartition("/")
        return municipio.strip(), re.sub(r"[^A-Za-z]", "", uf).upper()[:2]

    letras = re.sub(r"[^A-Za-z]", "", texto)
    uf = letras[-2:].upper() if len(letras) >= 2 else ""
    # remove as duas últimas letras de trás para frente, preservando o resto
    restante, removidas = [], 0
    for caractere in reversed(texto):
        if caractere.isalpha() and removidas < 2:
            removidas += 1
            continue
        restante.append(caractere)
    municipio = re.sub(r"\s+", " ", "".join(reversed(restante))).strip()
    return municipio, uf


def municipio_plausivel(valor: str) -> bool:
    """Diz se o município lido sobreviveu à digitalização com estrutura sadia.

    Rejeita as duas marcas típicas da degradação: vocábulos de uma letra, que
    denunciam um espaço inserido no meio da palavra ("Varzea G rande"), e
    maiúscula no miolo de um vocábulo ("CuiBba"). Um município assim é ruído
    com aparência de dado.
    """
    limpo = re.sub(r"[^A-Za-z ]", "", valor).strip()
    if len(limpo.replace(" ", "")) < 4:
        return False
    for vocabulo in limpo.split():
        if len(vocabulo) < 2:
            return False
        if any(letra.isupper() for letra in vocabulo[1:]):
            return False
    return True


def normalizar_tempo(valor: str) -> str:
    """Extrai os minutos de células como ``53mh`` ou ``60mn``."""
    achado = re.search(r"(-?\d+)", valor)
    return achado.group(1) if achado else ""


def extrair_registros(imagem, categorias: dict) -> list[dict[str, Any]]:
    """Lê todos os formulários de uma página digitalizada.

    Args:
        imagem: a página, em ``PIL.Image``.
        categorias: conteúdo de ``categorias.json``, usado para aproximar
            categoria e status do vocabulário oficial.

    Returns:
        Uma lista de dicionários com ``campos`` (mesmas chaves de
        :func:`src.validation.extract_fields`), ``ilegiveis`` (conjunto de
        campos que o OCR não recuperou) e ``texto`` (o que foi efetivamente
        lido, preservado para rastreabilidade).
    """
    registros, colunas = detectar_grade(imagem)
    if len(colunas) < 4 or not registros:
        logging.warning("Grade da tabela não reconhecida nesta página; nenhum registro extraído.")
        return []

    limites = colunas + [imagem.width]
    faixas = [(limites[i], limites[i + 1]) for i in range(len(limites) - 1)]
    status_validos = categorias.get("status_validos", [])
    nomes_categoria = [
        variacao
        for item in categorias.get("categorias_oficiais", [])
        for variacao in [item["nome"], *item["variacoes"]]
    ]

    saida = []
    for linhas in registros:
        campos: dict[str, str] = {}
        ilegiveis: set[str] = set()

        for campo, (linha, coluna) in POSICOES.items():
            if coluna >= len(faixas):
                continue
            # As três últimas faixas ocupam a largura toda da tabela.
            direita = faixas[-1][1] if linha >= 4 else faixas[coluna][1]
            caixa = (faixas[coluna][0], linhas[linha], direita, linhas[linha + 1])

            if campo == "protocolo":
                valor, confiavel = _ler_protocolo(imagem, caixa)
                campos[campo] = valor if confiavel else ""
                if not confiavel:
                    ilegiveis.add(campo)
                continue

            bruto = ler_celula(imagem, caixa, WHITELIST.get(campo, LETRAS))
            campos[campo] = bruto

        campos["data"] = normalizar_data(campos.get("data", ""))
        celula_cep = campos.get("cep", "")
        campos["cep"] = normalizar_cep(celula_cep)
        resto = celula_cep.replace(campos["cep"], "", 1) if campos["cep"] in celula_cep else celula_cep
        municipio, uf = separar_municipio_uf(resto)
        campos["uf"] = uf
        if municipio and municipio_plausivel(municipio):
            campos["municipio"] = municipio
        else:
            campos["municipio"] = ""
            if resto.strip(" -"):
                ilegiveis.add("municipio")
        campos["tempo_minutos"] = normalizar_tempo(campos.get("tempo_minutos", ""))

        categoria = semelhante(campos.get("categoria", ""), nomes_categoria)
        if categoria:
            campos["categoria"] = categoria
        elif campos.get("categoria"):
            ilegiveis.add("categoria")
            campos["categoria"] = ""

        status = semelhante(campos.get("status", ""), status_validos)
        if status:
            campos["status"] = status
        elif campos.get("status"):
            ilegiveis.add("status")
            campos["status"] = ""

        # O e-mail e o nome do solicitante dependem de detalhes que a
        # digitalização não preservou. Validamos o que foi lido; o que não
        # resiste à validação é declarado ilegível, jamais reconstruído.
        from .validation import EMAIL_RE

        email = campos.get("email", "").replace(" ", "")
        if EMAIL_RE.fullmatch(email):
            campos["email"] = email
        elif campos.get("email"):
            ilegiveis.add("email")
            campos["email"] = ""

        from .validation import parse_date

        if campos["data"] and not parse_date(campos["data"]):
            ilegiveis.add("data")
            campos["data"] = ""

        if campos.get("solicitante") and not nome_plausivel(campos["solicitante"]):
            ilegiveis.add("solicitante")
            campos["solicitante"] = ""

        texto = " ".join(
            f"{campo.replace('_minutos', '')}: {valor}"
            for campo, valor in campos.items()
            if valor
        )
        saida.append({"campos": campos, "ilegiveis": ilegiveis, "texto": texto})
    return saida
