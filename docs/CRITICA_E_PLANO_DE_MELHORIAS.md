# Crítica Arquitetural e Plano de Melhorias

**Sistema:** Sistema Inteligente de Processamento e Consulta de Atendimentos de Suporte  
**Desafio:** Desafio 2 — Introdução a Python para IA · FIC_DEV, Programador de Sistemas com IA  
**Entregável Oficial:** Item 6 — Crítica e plano de melhorias com base nos defeitos  

---

## 1. Avaliação Crítica da Solução Gerada por Inteligência Artificial

A solução entregue pela ferramenta de IA apresentava uma estrutura aparente de projeto moderno (FastAPI, Streamlit, ChromaDB, SQLAlchemy, LangChain), mas continha **falhas estruturais graves, comportamentos frágeis e suposições irreais** que a tornavam inviável para operação real em produção.

### 1.1 Principais Fragilidades Identificadas na Auditoria

1. **Perda Silenciosa de Dados e Falta de Resiliência Transacional:**
   - **O que a IA fez:** O pipeline abortava a leitura de arquivos inteiros caso um único registro falhasse, ou descartava silenciosamente os 25 registros do documento digitalizado sem emitir alertas de erro no código de saída (BUG-002 e BUG-003).
   - **Crítica técnica:** Sistemas de processamento em lote (*batch processing*) devem ser tolerantes a falhas parciais. Um erro em uma linha não pode comprometer o processamento das outras 99 linhas.

2. **Suposição Ingênua sobre OCR e Visão Computacional:**
   - **O que a IA fez:** Aplicava OCR em texto corrido e tentava casar expressões regulares simples concebidas para formulários verticais sobre um PDF escaneado em tabela de duas colunas a 150 DPI (BUG-032).
   - **Crítica técnica:** Documentos digitalizados sofrem de distorções geométricas, ruídos e corrupção de caracteres em cabeçalhos (`Protocob`, `Solicao`). Tratar formulários estruturados exige reconhecimento de leiaute (grade celular) e não apenas leitura linear.

3. **Distorção Metodológica nos Indicadores e Estatísticas:**
   - **O que a IA fez:** Calculava médias de tempo e contagens agregadas misturando registros válidos com dados duplicados e registros com tempo negativo ou corrompido (BUG-016). Além disso, calculava a taxa de OCR sobre registros em vez de páginas (BUG-009).
   - **Crítica técnica:** Métricas de negócio não podem ser infladas por registros que o próprio sistema rejeitou na camada de validação.

4. **Ineficiência Crítica na Camada Vetorial e API:**
   - **O que a IA fez:** Recriava a instância do modelo `SentenceTransformer` (centenas de megabytes) e reabria o cliente ChromaDB a cada requisição HTTP recebida no endpoint `/ask`, gerando latência de mais de 5,5 segundos por requisição (BUG-013).
   - **Crítica técnica:** Modelos de Machine Learning e clientes de banco vetorial devem ser instanciados uma única vez no ciclo de vida da aplicação (*Singleton / Lifespan handler*).

5. **Fragilidade no RAG e Alucinação sem Chave:**
   - **O que a IA fez:** Sem a chave da OpenAI, o sistema devolvia uma resposta estática *mockada*, sem analisar os chunks recuperados e sem capacidade de acusar insuficiência de informação (BUG-034).
   - **Crítica técnica:** O RAG deve possuir um modo local extrativo determinístico e um limiar de corte de similaridade que declare explicitamente quando os documentos não sustentam a resposta.

---

## 2. Matriz de Priorização de Melhorias (P0 a P3)

As melhorias foram classificadas de acordo com o padrão oficial do desafio:
- **P0:** Correção imediata — segurança, perda de dados ou indisponibilidade crítica.
- **P1:** Necessária para funcionamento confiável.
- **P2:** Melhoria importante de qualidade, desempenho ou manutenção.
- **P3:** Evolução futura ou conveniência.

---

### Tabela Comparativa de Melhorias

| ID | Melhoria Proposta | Prioridade | Esforço | Risco | Status no Projeto |
|---|---|---|---|---|---|
| **MEL-01** | Extração de formulários digitalizados célula a célula | **P0** | Alto (16h) | Médio | **Implementado** (Onda 2) |
| **MEL-02** | Isolamento transacional com Savepoints e código de saída de erro | **P0** | Médio (8h) | Baixo | **Implementado** (Onda 1) |
| **MEL-03** | Sanitização e Mascaramento de PII antes de chamadas ao LLM | **P0** | Médio (6h) | Médio | Proposta Futura |
| **MEL-04** | Cache Singleton do modelo de embeddings e ChromaDB na API | **P1** | Baixo (4h) | Baixo | **Implementado** (Onda 4) |
| **MEL-05** | Separação da Base Útil nos indicadores estatísticos | **P1** | Médio (6h) | Baixo | **Implementado** (Onda 3) |
| **MEL-06** | Modo RAG Local Extrativo com limiar de suficiência | **P1** | Médio (8h) | Baixo | **Implementado** (Onda 4) |
| **MEL-07** | Fila Assíncrona de Processamento (Celery / Redis / Background Tasks) | **P2** | Alto (20h) | Médio | Proposta Futura |
| **MEL-08** | Autenticação, Autorização (JWT) e Rate Limiting na API FastAPI | **P2** | Médio (10h) | Baixo | Proposta Futura |
| **MEL-09** | Extração direta de imagens do PDF sem dependência externa do Poppler | **P2** | Médio (6h) | Baixo | **Implementado** (Onda 2) |
| **MEL-10** | Ingestão Contínua com File Watcher / Webhooks | **P3** | Médio (12h) | Baixo | Proposta Futura |
| **MEL-11** | Suporte a Múltiplos Modelos de Embeddings Configuráveis via UI | **P3** | Baixo (6h) | Baixo | Proposta Futura |

---

## 3. Detalhamento das Propostas de Melhoria

### MEL-01: Extração Estruturada de Formulários Digitalizados Célula a Célula
- **Prioridade:** `P0`
- **Status:** **Implementado** em [`src/ocr_table.py`](file:///c:/projetos/DesafiosFicDev/fiddevia-desafio-02/src/ocr_table.py).
- **Problema:** A extração por texto corrido sobre PDFs escaneados perdia 100% dos dados estruturados devido a ruídos na imagem e desalinhamento de tabelas.
- **Justificativa:** O documento digitalizado representa 25% dos registros totais da aplicação.
- **Benefício:** Recuperação de 100% dos CEPs, tempos de atendimento e identificação estruturada dos registros.
- **Esforço Estimado:** 16 horas.
- **Risco:** Médio (complexidade na projeção de histogramas de pixels da imagem).
- **Estratégia de Implementação:** Detectar a grade de coordenadas, segmentar cada célula, aplicar listas de caracteres restritas (*whitelists*) no Tesseract e exigir quorum de 4 passadas para o protocolo.

---

### MEL-02: Isolamento Transacional com Savepoints e Detecção de Perda
- **Prioridade:** `P0`
- **Status:** **Implementado** em [`src/pipeline.py`](file:///c:/projetos/DesafiosFicDev/fiddevia-desafio-02/src/pipeline.py).
- **Problema:** Falhas em um único registro abortavam o processamento do documento, e processos com 0 registros extraídos retornavam código de sucesso (0).
- **Justificativa:** Processamento em lote necessita de atomicidade a nível de registro e retorno de status condizente para ferramentas de automação (CI/CD / Airflow).
- **Benefício:** Zero perda de dados em cascata e visibilidade explícita de documentos vazios.
- **Esforço Estimado:** 8 horas.
- **Risco:** Baixo.
- **Estratégia de Implementação:** Utilizar `session.begin_nested()` (SAVEPOINT) do SQLAlchemy por registro, registrando erros na tabela `erros_processamento` e retornando código `1` na CLI caso algum documento não produza dados.

---

### MEL-03: Sanitização e Mascaramento de PII (Privacidade e LGPD)
- **Prioridade:** `P0`
- **Status:** **Proposta de Evolução Futura** (Débito Técnico de Segurança).
- **Problema:** No modo RAG com OpenAI, o conteúdo textual dos atendimentos (incluindo nomes de solicitantes e e-mails reais) é enviado diretamente no prompt para servidores de terceiros.
- **Justificativa:** Violação potencial da LGPD (Lei Geral de Proteção de Dados) ao compartilhar dados pessoais identificáveis (PII) sem consentimento explícito.
- **Benefício:** Conformidade jurídica e proteção de privacidade dos usuários.
- **Esforço Estimado:** 6 horas.
- **Risco:** Médio (necessidade de garantir que o mascaramento não degrade o contexto semântico).
- **Estratégia de Implementação:** Criar um middleware em `src/text_processor.py` que substitua nomes e e-mails por identificadores anônimos (`<SOLICITANTE_1>`, `<EMAIL_1>`) antes da montagem do prompt para a API externa, restaurando-os apenas na interface local.

---

### MEL-04: Cache Singleton do Modelo de Embeddings e Conexão ChromaDB
- **Prioridade:** `P1`
- **Status:** **Implementado** em [`src/api.py`](file:///c:/projetos/DesafiosFicDev/fiddevia-desafio-02/src/api.py) e [`src/indexer.py`](file:///c:/projetos/DesafiosFicDev/fiddevia-desafio-02/src/indexer.py).
- **Problema:** A cada consulta HTTP `POST /ask`, o sistema carregava o modelo neural da memória e reabria o índice ChromaDB, levando ~5,5 segundos por requisição.
- **Justificativa:** Tempo de resposta inaceitável para uma API de consulta em tempo real.
- **Benefício:** Redução da latência de consulta para menos de 80ms após o aquecimento.
- **Esforço Estimado:** 4 horas.
- **Risco:** Baixo.
- **Estratégia de Implementação:** Uso de decorador `@lru_cache` para o modelo e gerenciamento de contexto assíncrono `@asynccontextmanager (lifespan)` na inicialização da aplicação FastAPI.

---

### MEL-05: Separação Metodológica da Base Útil nos Indicadores Analíticos
- **Prioridade:** `P1`
- **Status:** **Implementado** em [`src/analytics.py`](file:///c:/projetos/DesafiosFicDev/fiddevia-desafio-02/src/analytics.py).
- **Problema:** Registros inválidos (com tempo corrompido) e duplicados entravam no cálculo de tempo médio e distribuição por categoria, gerando relatórios corporativos distorcidos.
- **Justificativa:** Indicadores de atendimento ao cliente devem refletir apenas a demanda real e válida.
- **Benefício:** Relatórios precisos, confiáveis e compatíveis com a auditoria de negócios.
- **Esforço Estimado:** 6 horas.
- **Risco:** Baixo.
- **Estratégia de Implementação:** Criar o filtro de `base_util(df)` que segrega `valido` e `incompleto` para as métricas operacionais, destinando `invalido` e `duplicado` estritamente para os indicadores de qualidade de dados.

---

### MEL-06: Mecanismo de RAG Local Determinístico com Corte de Similaridade
- **Prioridade:** `P1`
- **Status:** **Implementado** em [`src/rag.py`](file:///c:/projetos/DesafiosFicDev/fiddevia-desafio-02/src/rag.py).
- **Problema:** Sem chave de API ou em perguntas fora do domínio, o sistema não fornecia respostas baseadas nos dados ou alucinava respostas genéricas.
- **Justificativa:** A aplicação precisa funcionar de forma autônoma e segura em ambientes desconectados da internet.
- **Benefício:** Respostas fundamentadas com citação exata de protocolo e página, com declaração formal de insuficiência caso a similaridade seja inferior a 0.35.
- **Esforço Estimado:** 8 horas.
- **Risco:** Baixo.
- **Estratégia de Implementação:** Algoritmo extrativo que monta síntese estruturada dos Top-K trechos recuperados do ChromaDB, citando metadados.

---

### MEL-07: Fila Assíncrona de Processamento em Segundo Plano
- **Prioridade:** `P2`
- **Status:** **Proposta de Evolução Futura**.
- **Problema:** A ingestão de grandes lotes de PDFs digitalizados via OCR é uma operação pesada e síncrona, bloqueando a thread principal.
- **Justificativa:** Em produção com centenas de documentos diários, o processamento síncrono pode travar o servidor.
- **Benefício:** Escalabilidade horizontal e capacidade de processamento concorrente de múltiplos arquivos.
- **Esforço Estimado:** 20 horas.
- **Risco:** Médio (necessidade de gerenciar *broker* de mensagens e *workers*).
- **Estratégia de Implementação:** Integrar Celery ou Redis Queue (RQ), transformando a rota de upload em uma operação assíncrona que retorna um `task_id` para acompanhamento de status.

---

### MEL-08: Camada de Segurança, Autenticação JWT e Rate Limiting na API
- **Prioridade:** `P2`
- **Status:** **Proposta de Evolução Futura**.
- **Problema:** A API atual não possui controle de acesso, permitindo requisições irrestritas de qualquer origem.
- **Justificativa:** Proteção contra ataques de negação de serviço (DoS) e acesso não autorizado aos registros de suporte.
- **Benefício:** Segurança corporativa e auditoria de usuários.
- **Esforço Estimado:** 10 horas.
- **Risco:** Baixo.
- **Estratégia de Implementação:** Implementar autenticação via cabeçalho `Authorization: Bearer <JWT>` com middleware de *rate limiting* (`slowapi`) para limitar a 60 requisições por minuto por IP.

---

## 4. Análise de Riscos Técnicos e Mitigações

| Risco Técnico Identificado | Impacto | Probabilidade | Mitigação Implementada / Recomendada |
|---|---|---|---|
| **Qualidade da Imagem (150 DPI)** | Alto | Alta | Reconhecimento célula a célula com *whitelist* de caracteres e quorum de 4 passadas; marcação de campos corrompidos como `*_ilegivel` (incompletos) sem inventar dados. |
| **Indisponibilidade de APIs Externas (ViaCEP/OpenAI)** | Médio | Média | Fallback gracioso: o sistema utiliza dados do próprio documento se o ViaCEP falhar, e opera em modo local extrativo se a OpenAI estiver indisponível. |
| **Exposição de Segredos e Chaves de API** | Alto | Baixa | `.env` devidamente incluído no `.gitignore`, variáveis lidas exclusivamente via ambiente e `.env.example` versionado contendo apenas chaves fictícias. |
| **Vazamento de Dados Pessoais via Prompt** | Alto | Média | Recomendação de implementação da melhoria `MEL-03` (anonimização prévia de PII antes de disparar prompts para LLMs de terceiros). |
