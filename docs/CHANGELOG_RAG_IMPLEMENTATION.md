# Resumo de Alterações - Implementação de RAG e Jurisprudência

## Versão: 1.0
## Data: 22 de dezembro de 2025

---

## 📋 Visão Geral

Este documento descreve todas as mudanças implementadas para adicionar um sistema completo de RAG (Retrieval-Augmented Generation) ao LawerAI, com suporte para jurisprudência do Jusbrasil.

## ✨ Funcionalidades Implementadas

### 1. **Sistema RAG Completo**
- ✅ Ingestão de documentos com chunking automático
- ✅ Geração de embeddings usando OpenAI Text-Embedding-3-small
- ✅ Recuperação semântica de contexto usando similaridade de cosseno
- ✅ Geração de respostas usando GPT-4o-mini
- ✅ Armazenamento persistente de embeddings e chunks em JSON

### 2. **Integração de Jurisprudência**
- ✅ Geração automática de links Jusbrasil
- ✅ Parametrização inteligente de termos jurídicos
- ✅ Mapeamento de variações comuns de termos (português)
- ✅ Integração com análise de documentos existente
- ✅ Integração com endpoints de RAG

### 3. **Endpoints RESTful**
- ✅ POST `/rag/ask` - Fazer perguntas sobre documentos
- ✅ POST `/rag/ingest/{doc_id}` - Ingerir documento no RAG
- ✅ GET `/rag/summary/{doc_id}` - Obter resumo com jurisprudência
- ✅ Integração de jurisprudência em `/document/analyze/{doc_id}`

## 📁 Arquivos Criados

### Backend Services

#### 1. `/app/domain/services/rag_service.py` (NEW)
**Tamanho**: ~450 linhas
**Responsabilidades**:
- Classe `RAGStore`: Gerencia armazenamento de embeddings e chunks
- Classe `RAGService`: Orquestra embeddings, recuperação e geração de respostas
- Métodos principais:
  - `ingest_document()`: Chunking + geração de embeddings
  - `retrieve_context()`: Busca semântica com similaridade de cosseno
  - `answer_question()`: Responde perguntas com contexto
  - `get_document_summary()`: Gera resumo via LLM
  - `_extract_legal_terms()`: Extrai termos jurídicos para jurisprudência

#### 2. `/app/domain/services/jurisprudence_service.py` (NEW)
**Tamanho**: ~350 linhas
**Responsabilidades**:
- Classe `JurisprudenceService`: Gerencia jurisprudência
- Funcionalidades principais:
  - `generate_jurisprudence_link()`: Cria URLs Jusbrasil parametrizadas
  - `extract_jurisprudence_terms()`: Identifica termos jurídicos em textos
  - `create_jurisprudence_response()`: Formata resposta com links
  - Mapeamento de ~20 termos jurídicos comuns em português
  - Detecção automática de documentos jurídicos

#### 3. `/app/api/routers/rag_router.py` (NEW)
**Tamanho**: ~400 linhas
**Endpoints**:
- `POST /rag/ask`: Pergunta com contexto RAG
- `POST /rag/ingest/{doc_id}`: Ingestão de documento
- `GET /rag/summary/{doc_id}`: Resumo + jurisprudência
- Autenticação JWT integrada
- Validação de autorização por documento

### Frontend Documentation

#### 4. `/docs/rag_frontend_integration.md` (NEW)
**Tamanho**: ~600 linhas
**Conteúdo**:
- Visão geral do RAG
- Documentação completa de endpoints
- Exemplos de uso em JavaScript/TypeScript
- Componente React exemplo completo
- CSS base para integração
- Troubleshooting e dicas de performance
- Fluxos de integração visual

#### 5. `/docs/rag_integration_example.ts` (NEW)
**Tamanho**: ~500 linhas
**Conteúdo**:
- Classe `RAGService` pronta para usar
- Hook React `useRAG` customizado
- Componentes React exemplo:
  - `RAGQuestionSection`
  - `RAGSummarySection`
  - `DocumentAnalysisPage` completa
- Utilities de formatação
- Tipos TypeScript completos

## 🔧 Arquivos Modificados

### 1. `/app/main.py`
**Mudanças**:
```python
# Imports adicionados
from app.api.routers.rag_router import build_rag_router
from app.domain.services.rag_service import RAGService
from app.domain.services.jurisprudence_service import JurisprudenceService

# ServiceContainer - Adicionado inicialização dos serviços
self.rag_service = RAGService(
    openai_api_key=openai_api_key,
    openai_model=self.settings.openai_model,
    storage_dir=self.settings.storage_dir / "rag_store",
    logger=self.logger,
)
self.jurisprudence_service = JurisprudenceService(logger=self.logger)

# create_app() - Adicionado registro do RAG router
application.include_router(
    build_rag_router(
        rag_service=container.rag_service,
        jurisprudence_service=container.jurisprudence_service,
        repository=container.repository,
        session_factory=container.session_factory,
        auth_service=container.auth_service,
        user_service=container.user_service,
    )
)
```

### 2. `/app/api/routers/document_router.py`
**Mudanças**: Integração de jurisprudência no endpoint existente
```python
# Import adicionado
from app.domain.services.jurisprudence_service import JurisprudenceService

# Parâmetro adicionado em build_document_router()
jurisprudence_service: JurisprudenceService | None = None

# Lógica adicionada em analyze_document():
if jurisprudence_service:
    try:
        legal_terms = jurisprudence_service.extract_jurisprudence_terms(
            document_content=analysis_text
        )
        jurisprudence_links = jurisprudence_service.create_jurisprudence_response(legal_terms)
        result.jurisprudencia = [...]  # Adiciona jurisprudência à resposta
    except Exception as jur_exc:
        logger.warning(f"Error adding jurisprudence: {jur_exc}")
```

**O que muda para o frontend:**
- ✅ Campo novo na resposta: `jurisprudencia` (array)
- ✅ Compatibilidade mantida: campos anteriores intactos
- ✅ Jurisprudência é automática: não requer alteração no body da request

**Exemplo de resposta antiga (antes):**
```json
{
  "analysis": "Análise do documento...",
  "extracao": {...},
  "analise": {...},
  "parecer": "..."
}
```

**Exemplo de resposta nova (agora):**
```json
{
  "analysis": "Análise do documento...",
  "extracao": {...},
  "analise": {...},
  "parecer": "...",
  "jurisprudencia": [
    {
      "termo": "contrato",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=contrato",
      "fonte": "Jusbrasil"
    }
  ]
}
```

### 3. `/requirements.txt`
**Mudanças**: Adicionado suporte OpenAI
```
# Adicionado
openai>=1.3.0
```

## 🏗️ Arquitetura

### Fluxo de Dados - RAG

```
┌──────────────────────────────────────────────────────────────┐
│                    DOCUMENT INGESTION                        │
├──────────────────────────────────────────────────────────────┤
│  1. POST /rag/ingest/{doc_id}                               │
│  2. Extract PDF → PDFService                                │
│  3. Split into chunks (default: 500 chars)                  │
│  4. Generate embeddings → OpenAI Embedding API              │
│  5. Store in RAGStore (JSON persistence)                    │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│                    QUESTION ANSWERING                        │
├──────────────────────────────────────────────────────────────┤
│  1. POST /rag/ask {question, doc_id?}                       │
│  2. Generate query embedding → OpenAI Embedding API         │
│  3. Calculate cosine similarity with stored embeddings      │
│  4. Retrieve top-5 relevant chunks                          │
│  5. Build prompt with context                              │
│  6. Call LLM → GPT-4o-mini                                  │
│  7. Extract legal terms from query + answer                 │
│  8. Generate Jusbrasil URLs                                 │
│  9. Return response + sources + jurisprudence               │
└──────────────────────────────────────────────────────────────┘
```

### Arquitetura de Camadas

```
Frontend (React/TypeScript)
        ↓
[API Layer]
    ├── /rag/ask
    ├── /rag/ingest/{doc_id}
    ├── /rag/summary/{doc_id}
    └── /document/analyze/{doc_id} [enhanced]
        ↓
[Service Layer]
    ├── RAGService
    │   ├── RAGStore (persistence)
    │   ├── OpenAI Embeddings
    │   ├── Retrieval (cosine similarity)
    │   └── LLM (GPT-4o-mini)
    │
    └── JurisprudenceService
        ├── Legal term extraction
        ├── URL generation
        └── Jusbrasil parametrization
        ↓
[External APIs]
    ├── OpenAI API (embeddings + chat)
    └── Jusbrasil (links only)
```

## 📊 Models de Dados

### RAG Response Model
```python
class RAGAnswerResponse:
    answer: str                      # Resposta do LLM
    sources: List[RAGSourceChunk]   # Trechos do documento
    legal_context: Optional[str]    # Contexto jurídico
    jurisprudencia: List[JurisprudenceLink]  # Links Jusbrasil
```

### Jurisprudence Link Model
```python
class JurisprudenceLink:
    termo: str          # "rescisão", "dolo", etc
    url: str           # https://www.jusbrasil.com.br/jurisprudencia/busca?q=...
    descricao: str     # "Jurisprudência sobre rescisão"
    fonte: str         # "Jusbrasil"
```

## 🔐 Segurança

- ✅ Autenticação JWT obrigatória em todos os endpoints RAG
- ✅ Validação de autorização por documento (owner_id)
- ✅ Sanitização de entrada (termos jurídicos)
- ✅ Rate limiting: Gerenciado por limite de API OpenAI

## ⚙️ Configuração

### Variáveis de Ambiente Necessárias
```env
LAWERAI_OPENAI_API_KEY=sk-...     # Sua chave OpenAI
LAWERAI_OPENAI_MODEL=gpt-4o-mini  # Modelo LLM (default)
LAWERAI_STORAGE_DIR=data/uploads   # Diretório base
```

### Customizações Possíveis
- **Chunk Size**: Configurável ao ingerir documentos
- **Top-K Results**: Número de chunks retornados (default: 5)
- **Temperature LLM**: Ajustável para mais/menos criatividade
- **Embedding Model**: Pode trocar por outro modelo OpenAI
- **Termos Jurídicos**: Adicionar/modificar mapeamento em `jurisprudence_service.py`

## 📈 Performance

| Operação | Tempo Esperado | Limitações |
|----------|----------------|-----------|
| Ingestão (100KB) | 2-5s | API OpenAI rate limit |
| Query + Resposta | 1-3s | API OpenAI rate limit |
| Resumo documento | 2-4s | Tamanho do documento |
| Retrieval (in-memory) | <100ms | N/A |

### Otimizações
- Embeddings armazenados em JSON (cache local)
- Cosine similarity em Python puro (sem deps externas)
- Chunks persistidos (não re-processam)
- Batch processing possível (não implementado, mas fácil de adicionar)

## 🐛 Tratamento de Erros

### Validações Implementadas
- Pergunta vazia → 400 Bad Request
- Token inválido → 401 Unauthorized
- Documento não encontrado → 404 Not Found
- Acesso negado → 403 Forbidden
- Erro na OpenAI → 502 Bad Gateway (com detalhes)
- Erro geral → 500 Internal Server Error

## 🧪 Como Testar

### 1. Setup Inicial
```bash
# Instalar dependências
pip install -r requirements.txt

# Verificar variáveis de ambiente
echo $LAWERAI_OPENAI_API_KEY
```

### 2. Testar Endpoints com cURL

#### 2.1 Ingerir Documento
```bash
curl -X POST http://localhost:8000/api/rag/ingest/documento-123 \
  -H "Authorization: Bearer seu-token-jwt" \
  -H "Content-Type: application/json" \
  -d '{"content": "Conteúdo completo do documento..."}'

# Resposta:
# {
#   "message": "Documento ingerido com sucesso",
#   "doc_id": "documento-123",
#   "chunks_created": 12,
#   "status": "success"
# }
```

#### 2.2 Fazer Pergunta
```bash
curl -X POST http://localhost:8000/api/rag/ask \
  -H "Authorization: Bearer seu-token-jwt" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quais são as obrigações do fornecedor?",
    "doc_id": "documento-123"
  }'

# Resposta:
# {
#   "answer": "De acordo com o documento, as obrigações incluem...",
#   "sources": [...],
#   "jurisprudencia": [
#     {"termo": "obrigações", "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=obriga%C3%A7%C3%B5es"}
#   ],
#   "status": "success"
# }
```

#### 2.3 **NOVO: Análise de Documento (Agora com Jurisprudência)**
```bash
curl -X POST http://localhost:8000/api/document/analyze/documento-123 \
  -H "Authorization: Bearer seu-token-jwt" \
  -H "Content-Type: application/json" \
  -d '{"analysis_type": "juridico"}'

# Resposta (NOVO CAMPO: jurisprudencia):
# {
#   "analysis": "Análise completa do documento...",
#   "extracao": {...},
#   "analise": {...},
#   "parecer": "...",
#   "jurisprudencia": [
#     {
#       "termo": "contrato",
#       "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=contrato",
#       "fonte": "Jusbrasil"
#     },
#     {
#       "termo": "rescisão",
#       "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=rescis%C3%A3o",
#       "fonte": "Jusbrasil"
#     }
#   ],
#   "status": "success"
# }
```

#### 2.4 Obter Resumo com Jurisprudência
```bash
curl -X GET http://localhost:8000/api/rag/summary/documento-123 \
  -H "Authorization: Bearer seu-token-jwt"

# Resposta:
# {
#   "summary": "Este documento é um contrato que estabelece...",
#   "key_points": ["Ponto 1", "Ponto 2"],
#   "jurisprudencia": [...],
#   "status": "success"
# }
```

### 3. Testar via Frontend (React)
Ver exemplos em `/docs/rag_integration_example.ts`

## 📚 Referências

### OpenAI Models
- **Text-Embedding-3-small**: Embeddings (dimensionalidade: 1536)
- **GPT-4o-mini**: LLM para geração de respostas

### Jusbrasil
- Base URL: `https://www.jusbrasil.com.br/jurisprudencia/busca`
- Parâmetro: `?q=termo+jurídico+url+encoded`

### Documentação Relacionada
- [RAG Frontend Integration](./rag_frontend_integration.md)
- [RAG Integration Example](./rag_integration_example.ts)
- [Backend Auth and Prompts](./backend_auth_and_prompts.md)

## 🚀 Próximos Passos (Futuro)

### Melhorias Planejadas
- [ ] Suporte a múltiplos idiomas (EN, ES)
- [ ] Implementar vector database (Pinecone, Weaviate)
- [ ] Cache de resultados frequentes
- [ ] Análise de sentimento em respostas
- [ ] Interface de administração para termos jurídicos
- [ ] Webhooks para eventos de jurisprudência
- [ ] Integração com mais fontes de jurisprudência
- [ ] Fine-tuning de modelo específico para direito

## 📝 Notas Importantes

1. **Embedding Dimensions**: OpenAI 3-small usa 1536 dimensões, não mudar para 384 (será necessário re-ingerir todos os documentos)

2. **Jurisprudência**: Links apontam apenas para Jusbrasil, adicionar outras fontes conforme necessário

3. **Storage**: Embeddings armazenados em JSON (não escalável para produção), considerar Vector DB para muitos documentos

4. **Rate Limiting**: OpenAI tem rate limits, implementar retry com backoff exponencial se necessário

5. **LLM Temperatura**: Mantida em 0.3 para consistência jurídica, aumentar para mais criatividade se necessário

## ✅ Checklist de Validação

- [x] RAG Service implementado e testado
- [x] Jurisprudence Service implementado e testado
- [x] RAG Router criado com todos os endpoints
- [x] Document Router integrado com jurisprudência
- [x] Main.py atualizado com serviços e routers
- [x] Requirements.txt atualizado
- [x] Documentação frontend completa
- [x] Exemplos TypeScript funcionais
- [x] Tipos TypeScript completos
- [x] Tratamento de erros robusto
- [x] Autenticação e autorização em todos endpoints

## 📞 Suporte

Para problemas:
1. Verificar logs: `app/utils/logger.py`
2. Validar chave OpenAI
3. Verificar tamanho do documento
4. Testar com pergunta simples primeiro
5. Revisar documentação em `/docs/rag_frontend_integration.md`

---

**Implementado por**: GitHub Copilot
**Data**: 22 de dezembro de 2025
