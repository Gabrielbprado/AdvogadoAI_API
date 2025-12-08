# Integração do Front-end com o LawerAI

Este guia resume o fluxo necessário para conectar qualquer client web/mobile ao backend FastAPI + CrewAI do LawerAI.

## 1. Visão geral
- Base URL local: `http://127.0.0.1:8000` (ajuste conforme o deploy).
- Todas as respostas vêm em português formal e seguem o schema `FinalAnalysisResponse`.
- O upload aceita **apenas PDFs**; após o envio, a análise é acionada com o `doc_id` retornado.

## 2. Pré-requisitos
- Backend rodando via `uvicorn app.main:app --reload` (ou em produção com o servidor escolhido).
- Variáveis `.env` configuradas para o provedor de LLM (OpenAI, Gemini, Groq ou Ollama) e diretórios de armazenamento.
- Se o front estiver em outro domínio, habilite CORS no `app/main.py` conforme necessário (FastAPI `CORSMiddleware`).

## 3. Endpoints essenciais

### 3.1 Upload de documento
```
POST /document/upload
Content-Type: multipart/form-data (campo `file`)
```
Resposta (201):
```json
{
  "doc_id": "doc-123",
  "filename": "contrato.pdf"
}
```
> Salve o `doc_id`; ele será usado na etapa seguinte.

### 3.2 Análise
```
POST /document/analyze/{doc_id}
```
Resposta (200) — `FinalAnalysisResponse`:
```json
{
  "extracao": {
    "topicos_principais": ["Objeto", "Vigência"],
    "clausulas_relevantes": [
      {"numero": "1", "descricao": "Do Objeto", "detalhes": "..."}
    ],
    "pontos_chave": ["Multa de 25%"],
    "informacoes_extraidas": {
      "partes": [{"tipo": "Contratante", "nome": "Empresa Alpha"}],
      "valores": [{"descricao": "Valor total", "valor": "R$ 24.000,00"}],
      "datas": [{"descricao": "Prazo de entrega", "prazo": "90 dias"}]
    }
  },
  "analise": {
    "riscos": ["Renovação automática"],
    "inconsistencias": ["Vigência 12 vs. 18 meses"],
    "clausulas_abusivas": ["Multa de 25%"],
    "melhorias_recomendadas": ["Reduzir multa para 10%"]
  },
  "parecer": {
    "parecer_resumido": "Síntese...",
    "parecer_detalhado": "Análise completa...",
    "contra_proposta": {
      "clausula_vigencia": "Manter 12 meses...",
      "clausula_multa": "Limitar a 10%",
      "clausula_obrigacoes": "Especificar SLAs",
      "clausula_resolucao_conflitos": "Adicionar mediação"
    }
  }
}
```

## 4. Fluxo sugerido no front
1. **Selecionar arquivo** e chamar `/document/upload` via `FormData`.
2. Exibir feedback (barra de progresso, estado de envio).
3. Após o 201, armazenar `doc_id` no estado global/router.
4. Chamar `/document/analyze/{doc_id}` e mostrar um indicador de processamento (pipeline leva alguns segundos).
5. Renderizar cards para cada bloco (`extração`, `análise`, `parecer`), permitindo copiar trechos ou baixar o JSON bruto.
6. Em caso de erro 502/500, exibir mensagem amigável e permitir reprocessar.

## 5. Tratamento de erros
- `400` (upload): arquivo não é PDF.
- `404` (analyze): `doc_id` desconhecido/expirado.
- `502`: saída do LLM inválida (o backend já tenta normalizar, mas é bom sugerir reprocessar).
- `500`: falha não tratada; logar o `trace_id` quando possível.

## 6. Boas práticas de UI
- Mostre o **status da análise** (ex.: "Extraindo PDF", "Executando IA").
- Permita baixar o JSON completo para auditoria.
- Destaque os campos críticos (multas, prazos, valores) em cards ou tabelas interativas.
- Mantenha o layout responsivo: em mobile, empilhe as seções; no desktop, use colunas.

## 7. Ambientação para produção
- Use HTTPS e autenticação (token/Bearer) conforme política interna.
- Armazene PDFs em um bucket seguro e forneça o caminho via `DocumentRepository`.
- Configure observabilidade (logs + tracing CrewAI) e monitore os warnings emitidos pelo parser (`app.infrastructure.crew.tasks`).

Com isso, o front pode consumir o LawerAI de forma previsível, exibindo insights jurídicos completos mesmo quando o modelo não retorna JSON perfeito.