# Integracao Front-end: Auth, Modelos e Analise

## Endpoints essenciais
- `POST /auth/register` (JSON `{email, password, full_name?}`) -> `{access_token, token_type}`.
- `POST /auth/login` (form `username`, `password`) -> `{access_token, token_type}`.
- `GET /auth/me` / `PUT /auth/me` (Bearer token) -> perfil `{id, email, full_name, instructions, avisos, created_at}`.
- `POST /auth/templates` / `GET /auth/templates` / `DELETE /auth/templates/{id}` -> CRUD de modelos de prompt.
- `POST /document/upload` (multipart `file`) -> `{doc_id, filename}`.
- `POST /document/analyze/{doc_id}` (Bearer token, JSON opcional `DocumentAnalysisRequest`) -> `FinalAnalysisResponse` com `extracao`, `analise`, `parecer`.

## Como montar o corpo de analise
`DocumentAnalysisRequest` opcional:
```json
{
  "template_id": 12,
  "custom_request": "Liste partes contratantes e riscos de SLA",
  "instructions_override": "Responda em bullets curtos",
  "avisos_override": "Priorizar clausula de rescisao e multas"
}
```
- Se `template_id` não vier, a análise usa apenas perfil + overrides + `custom_request`.
- `instructions_override`/`avisos_override` prevalecem sobre o perfil para esta chamada.

## Fluxo de UI sugerido
1) **Sessão**: guardar `access_token` em memória ou `sessionStorage`; evitar `localStorage` se possível; incluir `Authorization: Bearer <token>` em todas as chamadas protegidas.
2) **Perfil**: tela para editar `instructions` (como a IA deve responder) e `avisos` (itens críticos a destacar). Salvar via `PUT /auth/me`.
3) **Modelos**: CRUD simples listando `name` e snippet; botão "usar" no envio de documento preenche `template_id`.
4) **Envio de documento**: upload PDF; depois selecionar modelo salvo ou escrever `custom_request` ad-hoc e, se necessário, overrides de instruções/avisos.
5) **Exibição de resultado**: o backend retorna JSON estruturado, mas o conteúdo textual pode variar conforme modelo/instruções:
   - `extracao.topicos_principais` (array de strings)
   - `extracao.clausulas` (objeto com `numero`, `titulo`, `texto`)
   - `extracao.informacoes_extraidas` (`partes`, `valores`, `datas`)
   - `analise` (`riscos`, `inconsistencias`, `clausulas_abusivas`, `melhorias_recomendadas`)
   - `parecer` (`parecer_resumido`, `parecer_detalhado`, `contra_proposta`)
6) **Fallback de formato**: mesmo com modelo, o texto pode vir longo ou curto. Use componentes que aceitam strings livres (ex.: `<pre>` ou área scrollable) e exibam listas apenas se arrays não vazios. Campos ausentes podem vir vazios.

## Layout/UX para respostas variaveis
- Use cartões por seção: "Tópicos", "Cláusulas", "Partes", "Valores", "Datas", "Riscos", "Parecer".
- Para cláusulas longas, renderize acordeões ou blocos colapsáveis.
- Para avisos críticos, destaque (badge/alert) se alguma string contiver palavras-chave relevantes.
- Permita exportar/baixar o JSON bruto da resposta para reprocessamento no front.

## Exemplos de chamadas (fetch)
```javascript
// login
const login = await fetch('/auth/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/x-www-form-urlencoded'},
  body: new URLSearchParams({ username: email, password }),
});
const { access_token } = await login.json();

// upload
const fd = new FormData();
fd.append('file', fileInput.files[0]);
const uploadResp = await fetch('/document/upload', {
  method: 'POST',
  headers: { Authorization: `Bearer ${access_token}` },
  body: fd,
});
const { doc_id } = await uploadResp.json();

// analyze with template
const analysis = await fetch(`/document/analyze/${doc_id}`, {
  method: 'POST',
  headers: {
    Authorization: `Bearer ${access_token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ template_id: 12, custom_request: 'Quero lei aplicavel e riscos' }),
});
const result = await analysis.json();
```

## Erros comuns a tratar no front
- 401: token expirado ou ausente -> redirecionar para login.
- 404 em `/document/analyze/{id}`: documento não pertence ao usuário ou não existe.
- 404 em `template_id`: modelo não encontrado (exibir aviso e limpar seleção).
- 422: payload inválido (campos obrigatórios ou tipos).

## Adaptacao para respostas em formatos livres
- Sempre apresentar o JSON bruto em painel lateral para debug.
- Converter strings longas em markdown simples para legibilidade, mas sem quebrar HTML (sanitize se renderizar).
- Permitir ao usuário salvar um novo modelo a partir da resposta (ex.: copiar `parecer_detalhado` e editar no modal de template).
