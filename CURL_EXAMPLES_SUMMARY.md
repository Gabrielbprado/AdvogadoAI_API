# 🚀 RESUMO DE EXEMPLOS cURL - RAG + Jurisprudência

## 📌 Começar Aqui

Todos os exemplos usam:
- **URL Base:** `http://localhost:8000`
- **Auth:** Substitua `seu-token-jwt-aqui` por um token válido
- **Content-Type:** `application/json`

---

## 1️⃣ Ingerir Documento (Preparar para RAG)

```bash
curl -X POST http://localhost:8000/api/rag/ingest/documento-123 \
  -H "Authorization: Bearer seu-token-jwt-aqui" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Conteúdo completo do documento aqui... pode ser várias páginas de texto"
  }'
```

**O que acontece:**
- Divide o documento em chunks (500 caracteres cada)
- Cria embeddings com OpenAI
- Armazena tudo para futuras buscas

**Resposta esperada:**
```json
{
  "message": "Documento ingerido com sucesso",
  "doc_id": "documento-123",
  "chunks_created": 12,
  "status": "success"
}
```

---

## 2️⃣ Fazer Pergunta com RAG

```bash
curl -X POST http://localhost:8000/api/rag/ask \
  -H "Authorization: Bearer seu-token-jwt-aqui" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quais são os direitos e deveres das partes?",
    "doc_id": "documento-123"
  }'
```

**O que acontece:**
- Procura os trechos mais relevantes do documento
- Envia para o GPT-4o-mini responder
- Extrai termos jurídicos automaticamente
- Gera links Jusbrasil para cada termo

**Resposta esperada:**
```json
{
  "answer": "De acordo com o documento, os direitos das partes incluem...",
  "sources": [
    {
      "text": "Cláusula 5.1: Os direitos do contratante incluem...",
      "similarity": 0.96,
      "doc_id": "documento-123"
    },
    {
      "text": "Cláusula 5.2: Os direitos do contratado incluem...",
      "similarity": 0.92,
      "doc_id": "documento-123"
    }
  ],
  "jurisprudencia": [
    {
      "termo": "direitos",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=direitos",
      "fonte": "Jusbrasil"
    },
    {
      "termo": "contrato",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=contrato",
      "fonte": "Jusbrasil"
    }
  ],
  "status": "success"
}
```

---

## 3️⃣ Obter Resumo com Jurisprudência

```bash
curl -X GET http://localhost:8000/api/rag/summary/documento-123 \
  -H "Authorization: Bearer seu-token-jwt-aqui"
```

**O que acontece:**
- Gera um resumo do documento inteiro
- Extrai os pontos-chave
- Identifica automaticamente termos jurídicos
- Retorna links Jusbrasil

**Resposta esperada:**
```json
{
  "doc_id": "documento-123",
  "summary": "Este é um contrato de prestação de serviços entre as partes... Estabelece obrigações...",
  "key_points": [
    "Prestação de serviços de desenvolvimento de software",
    "Período: 12 meses",
    "Valor: R$ 50.000,00",
    "Rescisão permitida com 30 dias de aviso prévio"
  ],
  "jurisprudencia": [
    {
      "termo": "prestação de serviços",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=presta%C3%A7%C3%A3o%20de%20servi%C3%A7os",
      "fonte": "Jusbrasil"
    },
    {
      "termo": "rescisão",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=rescis%C3%A3o",
      "fonte": "Jusbrasil"
    }
  ],
  "status": "success"
}
```

---

## 4️⃣ Analisar Documento (Endpoint Melhorado)

```bash
curl -X POST http://localhost:8000/api/document/analyze/documento-123 \
  -H "Authorization: Bearer seu-token-jwt-aqui" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_type": "juridico"
  }'
```

**O que é novo:**
- Agora retorna também `jurisprudencia` no resultado
- Mantém compatibilidade com análise anterior
- Jurisprudência é automática e não interfere

**Resposta esperada:**
```json
{
  "analysis": "Análise completa do documento...",
  "document_info": {...},
  "jurisprudencia": [
    {
      "termo": "análise jurídica",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=an%C3%A1lise%20jur%C3%ADdica"
    }
  ],
  "status": "success"
}
```

---

## 💡 Dicas de Uso

### No Frontend JavaScript:
```javascript
const token = localStorage.getItem('token'); // seu token JWT

// Fazer pergunta
const response = await fetch('/api/rag/ask', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    question: "Sua pergunta aqui",
    doc_id: "seu-documento-id"
  })
});

const data = await response.json();
console.log(data.answer);
console.log(data.jurisprudencia);
```

### Tratamento de Erros:
```bash
# Sem token
curl -X POST http://localhost:8000/api/rag/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "...", "doc_id": "..."}'
# Resposta: 403 Unauthorized

# Documento não existe
curl -X POST http://localhost:8000/api/rag/ask \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{"question": "...", "doc_id": "invalido"}'
# Resposta: 404 Not Found
```

---

## 📚 Termos Jurídicos Reconhecidos

O sistema reconhece automaticamente e gera Jusbrasil para:

| Termo | Variações | URL Exemplo |
|-------|-----------|-------------|
| `contrato` | contratação, contratante | `/jurisprudencia/busca?q=contrato` |
| `rescisão` | rescindir, rescindido | `/jurisprudencia/busca?q=rescis%C3%A3o` |
| `direito` | direitos | `/jurisprudencia/busca?q=direito` |
| `dever` | obrigação, deverá | `/jurisprudencia/busca?q=dever` |
| `culpa` | culposo, culpável | `/jurisprudencia/busca?q=culpa` |
| `dolo` | doloso | `/jurisprudencia/busca?q=dolo` |
| `insalubridade` | insalubre | `/jurisprudencia/busca?q=insalubridade` |
| `jornada` | jornada de trabalho | `/jurisprudencia/busca?q=jornada` |
| `férias` | férias remuneradas | `/jurisprudencia/busca?q=f%C3%A9rias` |
| `indenização` | indenizável | `/jurisprudencia/busca?q=indeniza%C3%A7%C3%A3o` |

E mais 10+ termos...

---

## ✅ Checklist para Implementação

- [ ] Backend rodando (`python -m uvicorn app.main:app`)
- [ ] OpenAI API key configurada em `.env`
- [ ] Token JWT obtido via `/auth/login`
- [ ] Copiar um dos 4 cURL examples acima
- [ ] Testar no terminal
- [ ] Integrar resposta no seu frontend
- [ ] Exibir `jurisprudencia` array ao usuário

---

## 📖 Documentação Completa

- **Início Rápido:** [docs/RAG_QUICK_START.md](../docs/RAG_QUICK_START.md)
- **Implementação React:** [docs/rag_frontend_integration.md](../docs/rag_frontend_integration.md)
- **Guia Final:** [docs/FRONTEND_INTEGRATION_FINAL.md](../docs/FRONTEND_INTEGRATION_FINAL.md)
- **Código TypeScript:** [docs/rag_integration_example.ts](../docs/rag_integration_example.ts)

---

**Criado em:** $(date)
**Versão:** RAG + Jurisprudência v1.0
