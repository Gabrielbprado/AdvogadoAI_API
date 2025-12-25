# Backend: Auth, Perfis e Modelos de Prompt

## Visao geral
- Novo pipeline adiciona autenticação segura (JWT + bcrypt), perfis de usuário com instruções/avisos e modelos de prompt reutilizáveis para direcionar a análise de documentos.
- SQLite (`sqlite:///./data/app.db`) guarda usuários e modelos; documentos continuam em memória, mas agora com vinculação ao proprietário.
- Ao analisar um documento, a API concatena: instruções do perfil, avisos prioritários, modelo selecionado e pedido ad-hoc, injetando tudo nos prompts dos agentes CrewAI.

## Camadas e arquivos
- `app/config/settings.py`: configura `database_url`, `jwt_secret_key`, `jwt_algorithm`, `access_token_expire_minutes`.
- `app/infrastructure/db/database.py`: engine SQLite, `Session` factory, criação de tabelas; diretórios criados automaticamente.
- `app/infrastructure/db/entities.py`: tabelas `User` (email único, senha hash, instruções, avisos) e `PromptTemplate` (nome, conteúdo, FK para usuário).
- `app/domain/services/auth_service.py`: hashing (bcrypt), verificação, emissão/decodificação de JWT, criação de usuário.
- `app/domain/services/user_service.py`: CRUD de perfil (instruções/avisos/nome) e modelos de prompt.
- `app/domain/models/user_models.py`: esquemas Pydantic para auth, perfil, templates e `DocumentAnalysisRequest` (template_id, custom_request, overrides de instruções/avisos).
- `app/api/security.py`: esquema OAuth2 (`/auth/login`).
- `app/api/routers/auth_router.py`: endpoints de registro, login, perfil e templates (token Bearer obrigatório, exceto registro/login).
- `app/domain/models/document_models.py`: `DocumentRecord` recebe `owner_id`; `DocumentRepository.get` checa pertencimento.
- `app/api/routers/document_router.py`: upload/análise protegidos; grava `owner_id`; em análise, monta contexto do usuário e passa para o grafo.
- `app/infrastructure/langgraph/graph_builder.py`: `run(doc_id, owner_id, user_context)`; injeta `user_context` no estado e valida dono.
- `app/domain/services/analysis_service.py`: aceita `user_context` e repassa ao workflow.
- `app/infrastructure/crew/tasks.py`: insere `Diretrizes do usuário` em cada task (Reader, Analyst, Writer).
- `app/infrastructure/crew/workflows.py`: repassa `user_context` às tasks; prompts preservam as diretivas.
- `app/main.py`: inicializa DB, serviços de auth/profile, inclui routers de auth e documentos.

## Fluxo de autenticacao e perfil
1) Registro (`POST /auth/register`): valida email único, hash de senha, retorna token JWT.
2) Login (`POST /auth/login` com `username`/`password` via form): retorna token JWT.
3) Perfil (`GET /auth/me`, `PUT /auth/me`): ler/atualizar `full_name`, `instructions`, `avisos`.
4) Modelos (`POST/GET/DELETE /auth/templates`): CRUD de prompts por usuário. Cada template contém texto livre que será embutido nos prompts dos agentes.

## Fluxo de documento com contexto do usuario
- Upload (`POST /document/upload`): exige token; persiste arquivo em `data/uploads`, registra `owner_id` em memória.
- Análise (`POST /document/analyze/{doc_id}`): exige token; corpo opcional `DocumentAnalysisRequest`:
  - `template_id`: usa modelo salvo do usuário.
  - `custom_request`: pedido pontual para esta análise.
  - `instructions_override`/`avisos_override`: sobrescrevem perfil nesta requisição.
  - ✨ **NOVO**: Resposta agora inclui `jurisprudencia` array com links Jusbrasil automáticos
- Construção do contexto do usuário (em `document_router`): concatena instruções/avisos/template/pedido.
- Grafo LangGraph lê PDF, limpa texto, gera chunks; `AnalysisService` roda Reader em cada chunk, agrega, e roda Analyst/Writer com o mesmo `user_context`.
- `tasks.py` coloca o bloco "Diretrizes do usuário" dentro de cada descrição de task, garantindo que avisos e formato sejam priorizados.

**Exemplo de cURL da análise melhorada (com jurisprudência):**
```bash
curl -X POST http://localhost:8000/api/document/analyze/documento-123 \
  -H "Authorization: Bearer seu-token-jwt" \
  -H "Content-Type: application/json" \
  -d '{"analysis_type": "juridico"}'

# Resposta agora inclui jurisprudencia:
# {
#   "analysis": "...",
#   "extracao": {...},
#   "analise": {...},
#   "parecer": "...",
#   "jurisprudencia": [
#     {"termo": "contrato", "url": "https://www.jusbrasil.com.br/..."},
#     {"termo": "rescisão", "url": "https://www.jusbrasil.com.br/..."}
#   ]
# }
```

## Seguranca aplicada
- Hash de senha com `bcrypt` via `passlib`; nunca armazena senha em claro.
- JWT com expiração configurável (default 60 min); algoritmo `HS256`; segredo em `LAWERAI_JWT_SECRET_KEY` deve ser forte.
- Email único com checagem antes de criar; erro 400 se duplicado.
- Endpoints sensíveis usam `OAuth2PasswordBearer`; respostas 401 em token inválido ou usuário inexistente.
- Documentos associados a `owner_id`; análise e leitura falham se dono não bater.
- Inputs de prompt do usuário são inseridos como texto plano em `user_context`; se precisar sanitizar mais (ex.: limitar tamanho), ajustar em `document_router`.

## Configuracao e variaveis recomendadas
- `.env` exemplo:
  - `LAWERAI_JWT_SECRET_KEY="super-long-random-secret"`
  - `LAWERAI_ACCESS_TOKEN_EXPIRE_MINUTES=60`
  - `LAWERAI_DATABASE_URL="sqlite:///./data/app.db"`
  - `LAWERAI_APP_NAME="LawerAI"`
- Para produção, considere mover para Postgres e usar TLS no host.

## Extensoes futuras
- Persistir documentos e metadados em banco (hoje em memória) com vínculo forte ao usuário.
- Auditoria de uso de prompts por documento.
- Limitar tamanho de `instructions`/`avisos`/`templates` e aplicar validação de conteúdo.
- Suporte a refresh tokens e revogação.
