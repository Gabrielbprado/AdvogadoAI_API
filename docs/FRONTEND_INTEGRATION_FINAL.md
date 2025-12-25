# 📖 GUIA FINAL - Integração RAG no Frontend

## 🎯 Objetivo
Este documento fornece o passo-a-passo final para integrar o sistema RAG + Jurisprudência no seu frontend React.

---

## 📋 PRÉ-REQUISITOS

- ✅ Backend LawerAI rodando (`npm run dev` ou `uvicorn`)
- ✅ Token JWT válido (obtenha via `/auth/login`)
- ✅ Documento já analisado no backend

---

## ⚡ INÍCIO RÁPIDO - cURL

Se você quer testar os endpoints rapidamente sem implementar nada ainda:

### 1️⃣ Fazer uma Pergunta
```bash
curl -X POST http://localhost:8000/api/rag/ask \
  -H "Authorization: Bearer seu-token-jwt-aqui" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quais são as cláusulas principais?",
    "doc_id": "seu-documento-id"
  }'
```

**Resposta esperada:**
```json
{
  "answer": "De acordo com o documento...",
  "sources": [
    {"text": "Cláusula...", "similarity": 0.96}
  ],
  "jurisprudencia": [
    {
      "termo": "cláusula",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=cl%C3%A1usula"
    }
  ],
  "status": "success"
}
```

### 2️⃣ Ingerir Documento
```bash
curl -X POST http://localhost:8000/api/rag/ingest/seu-documento-id \
  -H "Authorization: Bearer seu-token-jwt-aqui" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Conteúdo completo do documento aqui..."
  }'
```

### 3️⃣ Obter Resumo
```bash
curl -X GET http://localhost:8000/api/rag/summary/seu-documento-id \
  -H "Authorization: Bearer seu-token-jwt-aqui"
```

---

## 🚀 IMPLEMENTAÇÃO EM JAVASCRIPT/REACT

Se preferir implementar nos seus componentes React, continue abaixo:

---

## 🚀 PASSO 1: Copiar Código do Serviço

Copie o arquivo `/docs/rag_integration_example.ts` e salve no seu projeto frontend:

```
src/
  services/
    rag.service.ts    ← Copie para aqui
  components/
    RAG/
      RAGQuestions.tsx
      RAGSummary.tsx
```

---

## 🚀 PASSO 2: Criar Componentes

### Arquivo 1: `src/components/RAG/RAGQuestions.tsx`

```typescript
import React, { useState } from 'react';
import { useRAG } from '../../services/rag.service';
import './rag.css';

interface RAGQuestionsProps {
  docId: string;
  token: string;
}

export const RAGQuestions: React.FC<RAGQuestionsProps> = ({ docId, token }) => {
  const [question, setQuestion] = useState('');
  const { response, loading, error, askQuestion, clearError } = useRAG(token);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    try {
      await askQuestion(question, docId);
      setQuestion('');
    } catch (error) {
      console.error('Error:', error);
    }
  };

  return (
    <div className="rag-questions-container">
      <h2>Faça uma Pergunta sobre o Documento</h2>

      {error && (
        <div className="alert alert-error">
          <p>{error}</p>
          <button onClick={clearError} className="btn-close">✕</button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="question-form">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Exemplo: Quais são as obrigações do fornecedor? Qual é o prazo de pagamento?"
          disabled={loading}
          rows={4}
          className="question-input"
        />
        <button 
          type="submit" 
          disabled={loading || !question.trim()}
          className="btn-primary"
        >
          {loading ? '⏳ Processando...' : '🔍 Enviar Pergunta'}
        </button>
      </form>

      {response && (
        <div className="response-container">
          {/* Resposta Principal */}
          <div className="answer-section">
            <h3>💡 Resposta</h3>
            <div className="answer-content">
              {response.answer}
            </div>
          </div>

          {/* Fontes do Documento */}
          {response.sources.length > 0 && (
            <div className="sources-section">
              <h3>📄 Fontes do Documento ({response.sources.length})</h3>
              <div className="sources-list">
                {response.sources.map((source, idx) => (
                  <div key={idx} className="source-card">
                    <div className="source-header">
                      <span className="similarity-badge">
                        {(source.similarity * 100).toFixed(0)}% relevância
                      </span>
                    </div>
                    <p className="source-text">
                      "{source.text.substring(0, 300)}..."
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Jurisprudência - DESTAQUE ESPECIAL */}
          {response.jurisprudencia.length > 0 && (
            <div className="jurisprudence-section">
              <h3>⚖️ Jurisprudência Relacionada (Jusbrasil)</h3>
              <div className="jurisprudence-grid">
                {response.jurisprudencia.map((jur, idx) => (
                  <a
                    key={idx}
                    href={jur.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="jurisprudence-card"
                  >
                    <div className="jur-header">
                      <h4>{jur.termo}</h4>
                      <span className="jur-source">{jur.fonte}</span>
                    </div>
                    <p>{jur.descricao}</p>
                    <span className="jur-link">Ver no Jusbrasil →</span>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RAGQuestions;
```

### Arquivo 2: `src/components/RAG/RAGSummary.tsx`

```typescript
import React, { useState } from 'react';
import { useRAG } from '../../services/rag.service';
import './rag.css';

interface RAGSummaryProps {
  docId: string;
  token: string;
}

export const RAGSummary: React.FC<RAGSummaryProps> = ({ docId, token }) => {
  const { summary, loading, error, getSummary, clearError } = useRAG(token);
  const [requested, setRequested] = useState(false);

  const handleGetSummary = async () => {
    try {
      await getSummary(docId);
      setRequested(true);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  return (
    <div className="rag-summary-container">
      <h2>Resumo do Documento</h2>

      {error && (
        <div className="alert alert-error">
          <p>{error}</p>
          <button onClick={clearError} className="btn-close">✕</button>
        </div>
      )}

      {!requested && (
        <button 
          onClick={handleGetSummary} 
          disabled={loading}
          className="btn-primary"
        >
          {loading ? '⏳ Gerando resumo...' : '📝 Gerar Resumo com IA'}
        </button>
      )}

      {summary && (
        <div className="summary-content">
          {/* Resumo */}
          <div className="summary-section">
            <h3>📋 Resumo</h3>
            <p>{summary.summary}</p>
            <small className="summary-meta">
              Baseado em {summary.chunk_count} seções do documento
            </small>
          </div>

          {/* Jurisprudência */}
          {summary.jurisprudencia.length > 0 && (
            <div className="jurisprudence-section">
              <h3>⚖️ Jurisprudência Identificada</h3>
              <div className="jurisprudence-list">
                {summary.jurisprudencia.map((jur, idx) => (
                  <div key={idx} className="jur-list-item">
                    <strong className="jur-term">{jur.termo}</strong>
                    <a 
                      href={jur.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="jur-link-btn"
                    >
                      Buscar no {jur.fonte} →
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RAGSummary;
```

### Arquivo 3: `src/components/RAG/rag.css`

```css
/* Container Principal */
.rag-questions-container,
.rag-summary-container {
  max-width: 900px;
  margin: 20px auto;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Títulos */
h2 {
  color: #1a1a1a;
  margin-bottom: 20px;
  font-size: 24px;
  border-bottom: 3px solid #007bff;
  padding-bottom: 10px;
}

h3 {
  color: #333;
  margin-top: 20px;
  margin-bottom: 15px;
  font-size: 18px;
}

h4 {
  margin: 0;
  font-size: 14px;
}

/* Alertas */
.alert {
  padding: 15px;
  border-radius: 6px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert p {
  margin: 0;
}

.alert-error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.btn-close {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #721c24;
}

/* Formulário */
.question-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.question-input {
  padding: 12px;
  border: 2px solid #ddd;
  border-radius: 6px;
  font-family: inherit;
  font-size: 14px;
  resize: vertical;
  transition: border-color 0.3s;
}

.question-input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.question-input:disabled {
  background: #e9ecef;
  cursor: not-allowed;
}

/* Botões */
.btn-primary,
button {
  padding: 12px 20px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s;
}

.btn-primary:hover {
  background: #0056b3;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
}

.btn-primary:disabled {
  background: #6c757d;
  cursor: not-allowed;
  transform: none;
}

button:active {
  transform: translateY(0);
}

/* Resposta */
.response-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.answer-section {
  background: white;
  padding: 20px;
  border-radius: 6px;
  border-left: 4px solid #007bff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.answer-content {
  color: #333;
  line-height: 1.6;
  font-size: 14px;
  white-space: pre-wrap;
  word-wrap: break-word;
}

/* Fontes */
.sources-section {
  background: white;
  padding: 20px;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.source-card {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  border-left: 3px solid #28a745;
  transition: all 0.3s;
}

.source-card:hover {
  background: #f0f1f2;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.source-header {
  margin-bottom: 10px;
}

.similarity-badge {
  display: inline-block;
  background: #28a745;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.source-text {
  margin: 0;
  color: #555;
  font-size: 13px;
  line-height: 1.5;
}

/* Jurisprudência */
.jurisprudence-section {
  background: white;
  padding: 20px;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.jurisprudence-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 15px;
}

.jurisprudence-card {
  background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%);
  border: 2px solid #ddd;
  padding: 16px;
  border-radius: 6px;
  text-decoration: none;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
  cursor: pointer;
}

.jurisprudence-card:hover {
  border-color: #007bff;
  box-shadow: 0 4px 12px rgba(0, 123, 255, 0.2);
  transform: translateY(-4px);
}

.jur-header {
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.jur-header h4 {
  color: #007bff;
  font-size: 15px;
  flex: 1;
}

.jur-source {
  background: #e7f3ff;
  color: #0056b3;
  padding: 3px 8px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.jurisprudence-card p {
  color: #666;
  font-size: 13px;
  margin: 0 0 12px 0;
  line-height: 1.4;
  flex: 1;
}

.jur-link {
  color: #007bff;
  font-weight: 600;
  font-size: 13px;
  display: inline-block;
}

.jurisprudence-card:hover .jur-link {
  text-decoration: underline;
}

/* Lista de Jurisprudência */
.jurisprudence-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.jur-list-item {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.jur-term {
  color: #333;
  font-size: 14px;
  flex: 1;
}

.jur-link-btn {
  background: #007bff;
  color: white;
  padding: 6px 12px;
  border-radius: 4px;
  text-decoration: none;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  transition: all 0.3s;
}

.jur-link-btn:hover {
  background: #0056b3;
}

/* Resumo */
.summary-section {
  background: #f8f9fa;
  padding: 16px;
  border-radius: 6px;
  border-left: 4px solid #ffc107;
}

.summary-section p {
  margin: 10px 0 0 0;
  color: #555;
  line-height: 1.6;
  font-size: 14px;
}

.summary-meta {
  display: block;
  color: #999;
  font-size: 12px;
  margin-top: 10px;
}

/* Responsivo */
@media (max-width: 768px) {
  .rag-questions-container,
  .rag-summary-container {
    margin: 10px;
    padding: 15px;
  }

  .jurisprudence-grid {
    grid-template-columns: 1fr;
  }

  h2 {
    font-size: 20px;
  }

  h3 {
    font-size: 16px;
  }
}

/* Dark Mode (Opcional) */
@media (prefers-color-scheme: dark) {
  .rag-questions-container,
  .rag-summary-container {
    background: #1e1e1e;
    color: #e0e0e0;
  }

  .answer-section,
  .sources-section,
  .jurisprudence-section {
    background: #2d2d2d;
    color: #e0e0e0;
  }

  .question-input {
    background: #333;
    color: #e0e0e0;
    border-color: #444;
  }

  .source-card {
    background: #333;
  }

  .jurisprudence-card {
    background: #2d2d2d;
    border-color: #444;
  }
}
```

---

## 🚀 PASSO 3: Usar nos seus componentes

### Na página de análise de documento:

```typescript
import { RAGQuestions } from './components/RAG/RAGQuestions';
import { RAGSummary } from './components/RAG/RAGSummary';

function DocumentPage() {
  const docId = "seu-doc-id";
  const token = "seu-token-jwt";

  return (
    <div>
      <h1>Documento Jurídico</h1>
      
      {/* Tabs ou seções */}
      <div className="tabs">
        <div className="tab-content">
          <RAGQuestions docId={docId} token={token} />
        </div>
        
        <div className="tab-content">
          <RAGSummary docId={docId} token={token} />
        </div>
      </div>
    </div>
  );
}
```

---

## ✅ CHECKLIST DE INTEGRAÇÃO

- [ ] Copiar `/docs/rag_integration_example.ts` → `src/services/rag.service.ts`
- [ ] Criar `src/components/RAG/RAGQuestions.tsx`
- [ ] Criar `src/components/RAG/RAGSummary.tsx`
- [ ] Criar `src/components/RAG/rag.css`
- [ ] Importar componentes em sua página de documentos
- [ ] Testar com um documento
- [ ] Verificar se jurisprudência aparece
- [ ] Clicar em um link de jurisprudência (deve abrir Jusbrasil)
- [ ] Testar com perguntas variadas
- [ ] Ajustar CSS conforme necessário

---

## 🧪 TESTES

### Teste 1: Pergunta Simples
```
Pergunta: "Qual é o valor do contrato?"
Resultado esperado: Resposta + fontes + jurisprudência
```

### Teste 2: Jurisprudência
```
Pergunta: "Fale sobre rescisão"
Link esperado: https://www.jusbrasil.com.br/jurisprudencia/busca?q=rescis%C3%A3o
```

### Teste 3: Resumo
```
Clique em "Gerar Resumo"
Resultado esperado: Resumo gerado + termos jurídicos identificados
```

---

## 🐛 PROBLEMAS COMUNS

### Jurisprudência não aparece
```
Solução:
1. Verifique se a pergunta contém termos jurídicos
2. Veja a lista em legal_terms_mapping (rag_service.py)
3. Adicione novos termos se necessário
```

### CORS Error
```
Solução:
1. Verifique se backend está em http://localhost:8000
2. Verifique CORS_ALLOWED_ORIGINS em .env
3. Adicione seu frontend: LAWERAI_CORS_ALLOWED_ORIGINS=http://localhost:3000
```

### Token expirado
```
Solução:
1. Faça login novamente
2. Obtenha novo token em /auth/login
3. Passe como prop aos componentes
```

---

## 📞 SUPORTE

Veja documentação completa em:
- `/docs/rag_frontend_integration.md` - Guia detalhado
- `/docs/RAG_QUICK_START.md` - Resumo rápido
- `/docs/CHANGELOG_RAG_IMPLEMENTATION.md` - Detalhes técnicos

---

## 🎉 PRONTO!

Seu frontend RAG está integrado e pronto para usar!

**Teste e divirta-se! 🚀**
