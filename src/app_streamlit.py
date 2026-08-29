"""Interface mínima de consulta aos atendimentos."""
from __future__ import annotations

import os

import requests
import streamlit as st

#: Endereço da API. Estava fixo no código: mudar porta ou host exigia editar o
#: fonte (BUG-027).
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

ROTULO_CLASSIFICACAO = {
    "valido": "válido",
    "incompleto": "incompleto",
    "invalido": "inválido",
    "duplicado": "duplicado",
}

st.set_page_config(page_title="Consulta de atendimentos", page_icon="🔎")
st.title("Consulta inteligente de atendimentos")
st.caption(f"API: {API_BASE_URL}")

pergunta = st.text_area(
    "Pergunta",
    placeholder="Quais problemas de instalação do Python aparecem com maior frequência?",
)
top_k = st.slider("Quantidade de fontes", 1, 10, 5)
incluir_rejeitados = st.checkbox(
    "Incluir registros inválidos e duplicados",
    value=False,
    help="Por padrão, só atendimentos válidos ou incompletos embasam a resposta.",
)

if st.button("Consultar", type="primary", disabled=not pergunta.strip()):
    try:
        resposta = requests.post(
            f"{API_BASE_URL}/ask",
            json={
                "pergunta": pergunta,
                "top_k": top_k,
                "incluir_rejeitados": incluir_rejeitados,
            },
            timeout=60,
        )
        if resposta.status_code == 409:
            st.warning(resposta.json().get("detail", "A base ainda não foi indexada."))
            st.stop()
        resposta.raise_for_status()
        dados = resposta.json()

        st.subheader("Resposta")
        st.write(dados["resposta"])
        rodape = f"Modo: {dados.get('modo')}"
        if dados.get("sustentada") is False:
            rodape += " · sem fundamento suficiente nos documentos"
        st.caption(rodape)
        if dados.get("aviso"):
            st.info(dados["aviso"])

        st.subheader("Fontes")
        if not dados.get("fontes"):
            st.write("Nenhum trecho recuperado.")
        for fonte in dados.get("fontes", []):
            classificacao = ROTULO_CLASSIFICACAO.get(
                fonte.get("classificacao"), "sem classificação"
            )
            st.markdown(
                f"**{fonte.get('protocolo')}** — {fonte.get('documento')}, "
                f"página {fonte.get('pagina')} · similaridade {fonte.get('similaridade')} "
                f"· registro {classificacao}"
            )
    except requests.HTTPError as exc:
        detalhe = ""
        try:
            detalhe = exc.response.json().get("detail", "")
        except ValueError:
            detalhe = exc.response.text[:200]
        st.error(f"A API respondeu {exc.response.status_code}. {detalhe}")
    except requests.RequestException as exc:
        st.error(
            f"Não foi possível falar com a API em {API_BASE_URL}. "
            f"Verifique se o serviço está no ar. Detalhe: {exc}"
        )
