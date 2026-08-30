# Sistema Inteligente de Processamento e Consulta de Atendimentos

Processa documentos de atendimento em PDF — digitais e digitalizados —, extrai e
padroniza os dados, persiste o histórico, produz indicadores e responde a
perguntas em linguagem natural sobre os atendimentos.

**Desafio 2 — Introdução a Python para IA · FIC_DEV, Programador de Sistemas com IA**  
**Módulo:** COD 001 - Introdução a Python para IA  
**Modalidade:** Equipe de 03 discentes  

### Equipe / Discentes
- Gabriel André de Siqueira Nonato
- João Flávio Pompeo
- Kristiann Marcellus Rocha Júnior

Esta é uma solução recebida pronta e submetida a auditoria. A documentação completa do projeto compreende:

- **Diagnóstico Inicial:** [`docs/RELATORIO_DIAGNOSTICO_INICIAL.md`](docs/RELATORIO_DIAGNOSTICO_INICIAL.md)
- **Catálogo de 34 Defeitos Corrigidos:** [`docs/CATALOGO_DE_DEFEITOS.md`](docs/CATALOGO_DE_DEFEITOS.md)
- **Documentação Técnica e Diagramas:** [`docs/ARQUITETURA_E_DIAGRAMAS.md`](docs/ARQUITETURA_E_DIAGRAMAS.md)
- **Crítica e Plano de Melhorias (P0 a P3):** [`docs/CRITICA_E_PLANO_DE_MELHORIAS.md`](docs/CRITICA_E_PLANO_DE_MELHORIAS.md)
- **Apoio Visual e Roteiro do Pitch (5 min):** [`docs/PITCH_E_SLIDES.md`](docs/PITCH_E_SLIDES.md)

---

## Resultado do processamento

Os quatro documentos oficiais somam **100 registros em 27 páginas**:

| Classificação | Registros | % |
|---|---:|---:|
| Válidos | 50 | 50,0 |
| Incompletos | 27 | 27,0 |
| Inválidos | 13 | 13,0 |
| Duplicados | 10 | 10,0 |

Páginas lidas por OCR: **25,93%** (7 de 27). Municípios identificados em 94 dos
100 registros; UF em todos.

---

## Arquitetura

```
PDFs ──► pdf_processor ──┬──► texto selecionável ──► validation ──┐
                         │                                         │
                         └──► ocr_processor ──► ocr_table ─────────┤
                              (imagem embutida)  (célula a célula)  │
                                                                    ▼
                                          pipeline ──► SQLite (models/database)
                                             │            │
                                             │            └──► text_processor (chunks)
                                             │                      │
                                             ├──► cep_client        ▼
                                             │    (município/UF)  embeddings ──► ChromaDB
                                             │                                  (vector_store)
                                             └──► analytics                        │
                                                  (CSV, JSON, gráficos)            ▼
                                                                       indexer ──► rag
                                                                                    │
                                                                    api (FastAPI) ──┤
                                                                                    ▼
                                                                          app_streamlit
```

| Módulo | Responsabilidade |
|---|---|
| `config` | Carrega `config.json` e `.env`; resolve caminhos e a URL do banco |
| `pdf_processor` | Extração direta e decisão de encaminhar ao OCR |
| `ocr_processor` | Obtém a imagem da página e executa o Tesseract |
| `ocr_table` | Lê o formulário digitalizado célula a célula |
| `validation` | Regex, normalização, validação e classificação |
| `text_processor` | Limpeza linguística e divisão em chunks |
| `models` / `database` | Modelos SQLAlchemy, sessão e operações |
| `cep_client` | Consulta de CEP tolerante a falhas |
| `pipeline` | Orquestra o processamento ponta a ponta |
| `analytics` | Indicadores, exportações e gráficos |
| `embeddings` / `vector_store` / `indexer` | Busca semântica e ChromaDB |
| `rag` | Resposta local ou com modelo, sempre com fontes |
| `api` / `app_streamlit` | Serviço HTTP e interface de consulta |

---

## Pré-requisitos

- **Python 3.11 ou superior** (validado em 3.13.5)
- **Tesseract OCR** com o idioma português, para os documentos digitalizados

O **Poppler não é necessário**. A imagem de cada página digitalizada é lida
direto do PDF com `pypdf`. Instale-o apenas se for processar PDFs cuja página
não seja uma imagem única — nesse caso `pdf2image` assume.

### Instalando o Tesseract

```powershell
# Windows
winget install -e --id UB-Mannheim.TesseractOCR
tesseract --version
tesseract --list-langs        # precisa listar "por"
```

```bash
# Ubuntu / Debian
sudo apt install -y tesseract-ocr tesseract-ocr-por

# macOS
brew install tesseract tesseract-lang
```

> **No Windows o instalador não acrescenta o Tesseract ao `PATH`.** O sistema
> procura nos locais de instalação padrão; se o seu for outro, informe-o em
> `config.json` → `ocr.tesseract_cmd`.

---

## Instalação

```powershell
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Se o PowerShell bloquear a ativação:
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

A instalação baixa cerca de 2,5 GB, quase tudo `torch`, exigido por
`sentence-transformers`. Reserve de 10 a 20 minutos na primeira vez.

### Variáveis de ambiente

| Variável | Para que serve |
|---|---|
| `OPENAI_API_KEY` | Opcional. Sem ela o sistema opera em modo local |
| `OPENAI_MODEL` | Modelo usado quando há chave (padrão `gpt-4.1-mini`) |
| `API_BASE_URL` | Endereço da API para o Streamlit (padrão `http://127.0.0.1:8000`) |
| `APP_ENV` | Rótulo do ambiente |

`.env` está no `.gitignore` e o `.env.example` traz apenas nomes. **Nenhuma
chave é lida do código, do `config.json` ou do repositório.**

---

## Execução

```bash
python -m src.main                 # processa os PDFs e gera as saídas
python -m src.main --indexar       # processa e indexa no ChromaDB
python -m src.main --recriar       # descarta banco e coleção antes de processar
python -m src.main --verbose       # rastreamento completo das exceções no log
python -m src.main --pergunta "Quais problemas mencionam instalacao do Python?"
```

`--pergunta` consulta a base já processada, sem reprocessar os PDFs. Para fazer
os dois, acrescente `--processar`.

O comando encerra com **código de saída 1** quando algum documento não produz
nenhum registro — a perda deixa de ser silenciosa.

### Serviço e interface

```bash
uvicorn src.api:app --reload --port 8000
streamlit run src/app_streamlit.py --server.address 127.0.0.1
```

- Documentação interativa: <http://127.0.0.1:8000/docs>
- `GET /health` — estado e modo de resposta
- `POST /ask` — pergunta, fontes e pontuações

O Streamlit escuta em todas as interfaces por padrão; `--server.address
127.0.0.1` mantém a interface restrita à máquina local.

### Testes e verificação de estilo

```bash
pytest              # 172 testes
ruff check .
```

### Saídas geradas

| Arquivo | Conteúdo |
|---|---|
| `database/atendimentos.db` | Documentos, atendimentos, chunks e erros |
| `database/chroma/` | Coleção vetorial persistente |
| `output/atendimentos_processados.csv` | Dados tratados, UTF-8 |
| `output/indicadores.json` | Os 15 indicadores |
| `output/processamento.log` | Log da execução |
| `output/graficos/*.png` | Atendimentos por categoria, tempo médio por categoria, atendimentos por município |

---

## Decisões de projeto

### Validação e classificação

Cada campo produz no máximo um motivo: `*_ausente` quando não há valor,
`*_invalido` quando o valor existe mas está malformado, e `*_ilegivel` quando a
digitalização não permitiu recuperá-lo.

A precedência é **inválido acima de incompleto**: um registro com um campo
errado é inválido mesmo que outro campo esteja faltando. Um registro sem
nenhuma pendência é válido.

Os documentos marcam campo ausente com o literal `[vazio]`. Esse e outros
marcadores (`N/A`, `-`, `?`) são normalizados para ausência antes da validação.

### Leitura dos documentos digitalizados

O PDF escaneado usa um layout diferente: tabela de duas colunas, e não a lista
vertical dos documentos digitais. Sobre o texto corrido do OCR os próprios
rótulos saem corrompidos (`Protocob`, `Probkm a`, `Solicao`), e nenhum padrão de
regex casa. A leitura é feita **célula a célula**: a grade é detectada por
projeção de pixels e cada célula recebe OCR com a lista de caracteres do seu
tipo de campo.

O **protocolo exige unanimidade entre quatro passadas** de OCR com escalas e
reamostragens diferentes. Um protocolo errado vira a identidade do registro, e a
confiança do Tesseract não distingue acerto de erro nestes documentos. Sem
unanimidade, o registro recebe uma chave sintética `SEM-PROTOCOLO-…` e o valor
lido é preservado em `protocolo_bruto`.

Categoria, status e município degradados são aproximados do vocabulário
conhecido com corte conservador de similaridade. Abaixo do corte, o campo é
declarado ilegível — **nada é reconstruído por inferência**.

### Deduplicação

Registros repetidos pelo protocolo são classificados como duplicados e não são
reinseridos. A ocorrência fica em `erros_processamento`, etapa `deduplicacao`,
e os duplicados aparecem no CSV e nas contagens de qualidade — mas ficam fora
das médias e das contagens por categoria.

### Chunking

Chunks de 500 caracteres com 80 de sobreposição, configuráveis. Os registros
deste conjunto têm 382 caracteres em média e **produzem um chunk cada**: a
sobreposição não chega a ser exercida. Os metadados de cada chunk guardam
protocolo, documento, página, categoria, classificação e método de leitura, o
que preserva o vínculo entre trecho e fonte.

A sobreposição é limitada a metade do tamanho: acima disso o avanço degenera.

### Indicadores

As estatísticas usam a **base útil** — válidos e incompletos. Duplicados e
inválidos entram apenas nas contagens de qualidade. O percentual de OCR é
medido sobre páginas, não sobre registros. O desvio-padrão é amostral.

### Município e UF

Vêm do campo `CEP / cidade` do próprio documento; o ViaCEP complementa e tem
precedência onde o CEP resolve. As grafias são canonizadas para que `Cáceres` e
`Caceres` não contem como cidades diferentes. Sem rede, o pipeline conclui
normalmente com os dados do documento.

---

## Modo sem chave da OpenAI

Os embeddings são locais e a busca semântica funciona sem nenhuma chave. Sem
`OPENAI_API_KEY`, o sistema compõe uma **resposta extrativa** a partir dos
trechos recuperados, citando protocolo, documento e página, e **declara
explicitamente quando os documentos não sustentam uma resposta**.

Com a chave configurada, LangChain e o modelo definido em `OPENAI_MODEL`
produzem uma síntese fundamentada no mesmo contexto. Falha de rede ou de cota
faz o sistema cair para o modo local, com aviso.

Por padrão, apenas atendimentos válidos ou incompletos embasam respostas.
Registros inválidos e duplicados só entram com `incluir_rejeitados`.

---

## Limitações conhecidas

- **O e-mail e o nome do solicitante dos 25 registros digitalizados são
  irrecuperáveis.** A digitalização tem cerca de 150 DPI e o `@`, os pontos e os
  espaços entre vocábulos não estão na imagem. Foram testadas as configurações
  que fazem diferença — PSM 3/4/6/7, `por`/`eng`/`por+eng`, motor legado e LSTM,
  escalas de 2× a 6×, escala de cinza e binarização em quatro limiares. Por isso
  esses 25 registros ficam permanentemente como **incompletos**. Uma
  digitalização em resolução maior resolveria.
- **12 dos 25 protocolos digitalizados** passam no critério de unanimidade; os
  demais recebem chave sintética.
- O enriquecimento por CEP depende de rede. O ViaCEP resolve 2 dos 9 CEPs do
  conjunto — os demais são fictícios.
- A API não tem limite de requisições nem política de CORS. É adequada a um MVP
  local, não a exposição pública.
- Com `OPENAI_API_KEY` configurada, o conteúdo dos atendimentos — inclusive
  nomes e e-mails — é enviado à OpenAI no contexto do RAG. Os dados deste
  desafio são fictícios; antes de usar dados reais, essa decisão precisa ser
  revista.
- `app_streamlit` e `vector_store` não têm teste automatizado direto.

---

## Uso de ferramentas de IA

A solução original foi produzida por uma ferramenta de IA e entregue como se
estivesse pronta. O trabalho registrado neste repositório é a **auditoria**
dessa entrega: diagnóstico com evidências de execução, catálogo de 34 defeitos,
correção em quatro ondas e documentação.

O assistente Claude foi usado na auditoria, na correção e na redação da
documentação. Cada correção tem commit próprio, com a medição de antes e depois,
e o teste que a sustenta. As decisões de projeto que mudavam o significado dos
dados — em especial tratar campo ilegível por OCR como ausência, e não como
invalidez — foram submetidas à equipe antes de serem implementadas.
