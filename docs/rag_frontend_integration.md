# Integração do RAG (Retrieval-Augmented Generation) no Frontend

## Visão Geral

Este documento descreve como integrar o sistema RAG (Retrieval-Augmented Generation) baseado em documentos jurídicos no seu frontend. O RAG permite que os usuários façam perguntas sobre documentos jurídicos e recebam respostas fundamentadas nos documentos, com links para jurisprudência relevante no Jusbrasil.

## Arquitetura do RAG

O sistema RAG funciona em três etapas:

1. **Ingestão de Documentos**: Quando um documento é analisado, ele é dividido em chunks (pedaços de texto) e suas embeddings (representações vetoriais) são criadas usando o modelo de embeddings da OpenAI.

2. **Recuperação de Contexto**: Quando o usuário faz uma pergunta, o sistema busca os chunks mais relevantes usando similaridade de cosseno.

3. **Geração de Resposta**: O sistema usa o LLM (GPT-4o-mini) para gerar uma resposta baseada nos chunks recuperados.

4. **Jurisprudência**: Termos jurídicos relevantes são identificados e links para jurisprudência no Jusbrasil são gerados automaticamente.

## Endpoints Disponíveis

### 1. Fazer uma Pergunta (RAG Query)

**Endpoint**: `POST /rag/ask`

**Autenticação**: Requer token Bearer JWT

**Request Body**:
```json
{
  "question": "Quais são as cláusulas de rescisão deste contrato?",
  "doc_id": "documento-id-opcional"
}
```

**Parâmetros**:
- `question` (obrigatório): A pergunta sobre o documento jurídico
- `doc_id` (opcional): ID do documento para limitar a busca. Se omitido, busca em todos os documentos do usuário.

**Response** (200 OK):
```json
{
  "answer": "De acordo com a cláusula 8.2 do contrato, a rescisão pode ocorrer por...",
  "sources": [
    {
      "text": "8.2 - Rescisão por Justa Causa: A rescisão por justa causa...",
      "similarity": 0.95,
      "doc_id": "documento-id"
    },
    {
      "text": "8.3 - Aviso Prévio: Qualquer das partes pode rescindir...",
      "similarity": 0.87,
      "doc_id": "documento-id"
    }
  ],
  "legal_context": "Análise baseada em documentos jurídicos",
  "jurisprudencia": [
    {
      "termo": "rescisão",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=rescis%C3%A3o",
      "descricao": "Jurisprudência sobre rescisão",
      "fonte": "Jusbrasil"
    },
    {
      "termo": "justa causa",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=justa+causa",
      "descricao": "Jurisprudência sobre justa causa",
      "fonte": "Jusbrasil"
    }
  ]
}
```

### 2. Ingerir Documento no RAG

**Endpoint**: `POST /rag/ingest/{doc_id}`

**Autenticação**: Requer token Bearer JWT

**URL Parameters**:
- `doc_id`: ID do documento a ingerir

**Response** (200 OK):
```json
{
  "status": "success",
  "doc_id": "documento-id",
  "message": "Documento documento-id ingerido com sucesso no sistema RAG"
}
```

**Notas**:
- Este endpoint é chamado automaticamente quando você analisa um documento
- Processa o PDF, extrai o texto, divide em chunks e cria embeddings
- A ingestão pode levar alguns segundos dependendo do tamanho do documento

### 3. Obter Resumo do Documento

**Endpoint**: `GET /rag/summary/{doc_id}`

**Autenticação**: Requer token Bearer JWT

**URL Parameters**:
- `doc_id`: ID do documento

**Response** (200 OK):
```json
{
  "doc_id": "documento-id",
  "summary": "Contrato de Compra e Venda: Este contrato estabelece os termos para venda de...",
  "chunk_count": 5,
  "jurisprudencia": [
    {
      "termo": "compra e venda",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=compra+e+venda",
      "descricao": "Jurisprudência sobre compra e venda",
      "fonte": "Jusbrasil"
    }
  ]
}
```

## Como Usar o RAG no Frontend

### Fluxo 1: Fazer Perguntas sobre Documentos (RAG)

#### Request com cURL:
```bash
curl -X POST http://localhost:8000/api/rag/ask \
  -H "Authorization: Bearer seu-token-jwt-aqui" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quais são as obrigações do fornecedor?",
    "doc_id": "documento-id-123"
  }'
```

#### Response (200 OK):
```json
{
  "answer": "De acordo com as cláusulas 5.1 e 5.2 do contrato, as obrigações do fornecedor incluem: 1) Entregar os produtos conforme especificação técnica; 2) Garantir qualidade compatível com normas ISO; 3) Fornecer suporte técnico por 12 meses; 4) Assumir custos de transporte.",
  "sources": [
    {
      "text": "5.1 - Obrigações do Fornecedor: O fornecedor fica obrigado a entregar os produtos de acordo com as especificações técnicas fornecidas pela Contratante, em prazos estabelecidos neste contrato.",
      "similarity": 0.97,
      "doc_id": "documento-id-123"
    },
    {
      "text": "5.2 - Qualidade: Os produtos fornecidos deverão estar em conformidade com as normas técnicas ISO 9001 e ABNT aplicáveis.",
      "similarity": 0.94,
      "doc_id": "documento-id-123"
    },
    {
      "text": "5.3 - Suporte Técnico: O fornecedor garantirá suporte técnico gratuito por um período de 12 meses a partir da data de entrega.",
      "similarity": 0.92,
      "doc_id": "documento-id-123"
    }
  ],
  "legal_context": "Análise baseada em documentos jurídicos",
  "jurisprudencia": [
    {
      "termo": "obrigação",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=obriga%C3%A7%C3%A3o",
      "descricao": "Jurisprudência sobre obrigação",
      "fonte": "Jusbrasil"
    },
    {
      "termo": "contrato",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=contrato",
      "descricao": "Jurisprudência sobre contrato",
      "fonte": "Jusbrasil"
    }
  ]
}
```

#### Como chamar no Frontend:
```javascript
// JavaScript/Fetch API
const askQuestion = async (question, docId, token) => {
  const response = await fetch('/api/rag/ask', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      question: question,
      doc_id: docId
    })
  });
  
  if (!response.ok) throw new Error(response.statusText);
  return response.json();
};

// Uso
const result = await askQuestion(
  'Quais são as obrigações do fornecedor?',
  'documento-id-123',
  'seu-token'
);

console.log(result.answer);
result.jurisprudencia.forEach(jur => {
  console.log(`${jur.termo}: ${jur.url}`);
});
```

### Fluxo 2: Ingerir Documento no RAG

#### Request com cURL:
```bash
curl -X POST http://localhost:8000/api/rag/ingest/documento-id-123 \
  -H "Authorization: Bearer seu-token-jwt-aqui"
```

#### Response (200 OK):
```json
{
  "status": "success",
  "doc_id": "documento-id-123",
  "message": "Documento documento-id-123 ingerido com sucesso no sistema RAG"
}
```

#### Como chamar no Frontend:
```javascript
const ingestDocument = async (docId, token) => {
  const response = await fetch(`/api/rag/ingest/${docId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (!response.ok) throw new Error(response.statusText);
  return response.json();
};

const result = await ingestDocument('documento-id-123', 'seu-token');
console.log(result.message);
```

### Fluxo 3: Obter Resumo com Jurisprudência

#### Request com cURL:
```bash
curl -X GET http://localhost:8000/api/rag/summary/documento-id-123 \
  -H "Authorization: Bearer seu-token-jwt-aqui"
```

#### Response (200 OK):
```json
{
  "doc_id": "documento-id-123",
  "summary": "Contrato de Compra e Venda de Produtos\n\nEste contrato estabelece os termos e condições para a compra e venda de produtos eletrônicos entre a empresa XYZ Fornecedora e a Contratante. O contrato especifica:\n\n1. Objeto: Fornecimento de 100 unidades de controladores programáveis modelo CP2000\n2. Preço Total: R$ 250.000,00 (duzentos e cinquenta mil reais)\n3. Prazo de Entrega: 30 dias a partir da assinatura\n4. Condições de Pagamento: 50% na assinatura, 50% na entrega\n5. Garantia: 12 meses contra defeitos de fabricação\n6. Penalidades: Multa de 0,5% ao dia por atraso\n7. Rescisão: Possível com 30 dias de aviso prévio\n\nAs cláusulas principais cobrem obrigações das partes, prazos, valores, qualidade, suporte técnico e disposições gerais.",
  "chunk_count": 8,
  "jurisprudencia": [
    {
      "termo": "compra e venda",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=compra+e+venda",
      "descricao": "Jurisprudência sobre compra e venda",
      "fonte": "Jusbrasil"
    },
    {
      "termo": "contrato",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=contrato",
      "descricao": "Jurisprudência sobre contrato",
      "fonte": "Jusbrasil"
    },
    {
      "termo": "rescisão",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=rescis%C3%A3o",
      "descricao": "Jurisprudência sobre rescisão",
      "fonte": "Jusbrasil"
    }
  ]
}
```

#### Como chamar no Frontend:
```javascript
const getDocumentSummary = async (docId, token) => {
  const response = await fetch(`/api/rag/summary/${docId}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (!response.ok) throw new Error(response.statusText);
  return response.json();
};

const summary = await getDocumentSummary('documento-id-123', 'seu-token');
console.log(summary.summary);
summary.jurisprudencia.forEach(jur => {
  console.log(`${jur.termo}: ${jur.url}`);
});
```

### Fluxo 4: Análise de Documento Melhorada (Com Jurisprudência)

#### Request com cURL:
```bash
curl -X POST http://localhost:8000/api/document/analyze/documento-id-123 \
  -H "Authorization: Bearer seu-token-jwt-aqui" \
  -H "Content-Type: application/json" \
  -d '{
    "instructions_override": "Foque em análise de riscos",
    "avisos_override": "Atenção especial a cláusulas de penalidade",
    "custom_request": "Verifique conformidade com normas ISO"
  }'
```

#### Response (200 OK):
```json
{
  "analise_final": "Análise Jurídica Completa do Contrato\n\nEste contrato de compra e venda apresenta estrutura apropriada com as cláusulas essenciais...",
  "extracao": {
    "topicos_principais": ["Compra e Venda", "Condições de Pagamento", "Prazo de Entrega"],
    "clausulas": [
      {
        "numero": "1",
        "titulo": "DO OBJETO",
        "texto": "Fica estabelecido o fornecimento de 100 unidades..."
      }
    ],
    "pontos_chave": ["R$ 250.000,00", "30 dias", "12 meses garantia"],
    "informacoes_extraidas": {
      "partes": [
        {"tipo": "Fornecedor", "nome": "XYZ Fornecedora LTDA", "cnpj": "12.345.678/0001-90"},
        {"tipo": "Contratante", "nome": "ABC Empresa LTDA", "cnpj": "98.765.432/0001-10"}
      ],
      "valores": [
        {"descricao": "Preço Total", "valor": "R$ 250.000,00"}
      ],
      "datas": [
        {"descricao": "Prazo de Entrega", "prazo": "30 dias"}
      ]
    }
  },
  "jurisprudencia": [
    {
      "termo": "compra e venda",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=compra+e+venda",
      "descricao": "Jurisprudência sobre compra e venda",
      "fonte": "Jusbrasil"
    },
    {
      "termo": "risco",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=risco",
      "descricao": "Jurisprudência sobre risco",
      "fonte": "Jusbrasil"
    }
  ]
}
```

#### Como chamar no Frontend:
```javascript
const analyzeDocument = async (docId, token, options = {}) => {
  const response = await fetch(`/api/document/analyze/${docId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(options)
  });
  
  if (!response.ok) throw new Error(response.statusText);
  return response.json();
};

const result = await analyzeDocument('documento-id-123', 'seu-token', {
  instructions_override: 'Foque em riscos',
  custom_request: 'Conformidade ISO'
});

console.log(result.analise_final);
console.log('Jurisprudência:', result.jurisprudencia);
```

## Componente React Exemplo

Aqui está um exemplo simples de componente React para integrar as funcionalidades de RAG:

```typescript
import React, { useState } from 'react';
import axios from 'axios';

interface RAGResponse {
  answer: string;
  sources: Array<{text: string; similarity: number}>;
  jurisprudencia: Array<{
    termo: string;
    url: string;
    descricao: string;
    fonte: string;
  }>;
}

const RAGComponent: React.FC<{ docId: string; token: string }> = ({ docId, token }) => {
  const [question, setQuestion] = useState('');
  const [response, setResponse] = useState<RAGResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handleAsk = async () => {
    setLoading(true);
    try {
      const res = await axios.post<RAGResponse>(
        '/api/rag/ask',
        { question, doc_id: docId },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setResponse(res.data);
    } catch (error) {
      console.error('Erro:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Faça uma pergunta..."
      />
      <button onClick={handleAsk} disabled={loading}>
        {loading ? 'Processando...' : 'Enviar'}
      </button>

      {response && (
        <div>
          <h3>Resposta</h3>
          <p>{response.answer}</p>

          <h3>Jurisprudência</h3>
          {response.jurisprudencia.map((jur, i) => (
            <a key={i} href={jur.url} target="_blank" rel="noopener noreferrer">
              {jur.termo} - {jur.fonte}
            </a>
          ))}
        </div>
      )}
    </div>
  );
};

export default RAGComponent;
```

### CSS Exemplo

```css
.rag-container {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
}

.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.tabs button {
  padding: 10px 20px;
  border: 1px solid #ccc;
  background: #f5f5f5;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.3s;
}

.tabs button.active {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

.question-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.question-form textarea {
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: inherit;
  resize: vertical;
}

.question-form button,
button {
  padding: 10px 20px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

button:disabled,
.question-form button:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.error-message {
  padding: 15px;
  background: #f8d7da;
  color: #721c24;
  border-radius: 4px;
  margin-bottom: 20px;
}

.response-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.answer-section {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  border-left: 4px solid #007bff;
}

.answer-section h3 {
  margin-top: 0;
  color: #007bff;
}

.sources-section h3,
.jurisprudence-section h3 {
  color: #333;
  margin-bottom: 15px;
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.source-item {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  border-left: 3px solid #28a745;
}

.source-item .similarity {
  font-size: 12px;
  color: #666;
  margin: 0 0 8px 0;
}

.source-item .text {
  font-size: 14px;
  color: #333;
  margin: 0;
  line-height: 1.5;
}

.jurisprudence-links {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 15px;
}

.jur-item {
  background: #fff;
  border: 1px solid #ddd;
  padding: 15px;
  border-radius: 4px;
  transition: all 0.3s;
}

.jur-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-color: #007bff;
}

.jur-item h4 {
  margin: 0 0 8px 0;
  color: #007bff;
  font-size: 14px;
}

.jur-item p {
  margin: 0 0 10px 0;
  font-size: 13px;
  color: #666;
  line-height: 1.4;
}

.jur-item a {
  color: #007bff;
  text-decoration: none;
  font-weight: 500;
  display: inline-block;
}

.jur-item a:hover {
  text-decoration: underline;
}
```

## Requisitos de Ambiente

### Variáveis de Ambiente Necessárias

Certifique-se de que as seguintes variáveis estão configuradas no seu `.env`:

```env
# OpenAI Configuration
LAWERAI_OPENAI_API_KEY=sua_chave_de_api_openai_aqui
LAWERAI_OPENAI_MODEL=gpt-4o-mini

# Diretório de armazenamento do RAG
LAWERAI_STORAGE_DIR=data/uploads
```

### Instalação de Dependências

Execute o comando para instalar as novas dependências:

```bash
pip install -r requirements.txt
```

A principal nova dependência é:
- **openai** (>=1.3.0): Cliente Python para OpenAI API com suporte a embeddings e chat completions

## Fluxo de Integração Completo

### 1. Upload e Análise de Documento

```
┌─────────────────────────┐
│ Usuário Faz Upload      │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ POST /document/upload               │
│ (salva PDF, cria DocumentRecord)    │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ POST /document/analyze/{doc_id}     │
│ (executa análise CrewAI)            │
└────────────┬────────────────────────┘
             │
             ├─► Análise do documento
             │   (extraia cláusulas, valores, etc)
             │
             ├─► Identificar termos jurídicos
             │
             └─► Gerar links de jurisprudência
                 (Jusbrasil)
```

### 2. RAG Query (Perguntas sobre Documentos)

```
┌─────────────────────────────┐
│ Usuário Faz Pergunta        │
└────────────┬────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ POST /rag/ask                    │
│ (Pergunta + Doc ID)              │
└────────────┬─────────────────────┘
             │
             ├─► Gerar embedding da pergunta
             │   (OpenAI Text-Embedding-3-small)
             │
             ├─► Recuperar chunks similares
             │   (Cosine Similarity)
             │
             ├─► Passar contexto ao LLM
             │   (GPT-4o-mini)
             │
             ├─► Extrair termos jurídicos
             │   da resposta
             │
             └─► Gerar URLs de jurisprudência
                 (Jusbrasil)
```

## Tratamento de Erros

### Status Code 400: Bad Request
Causas comuns:
- Pergunta vazia ou inválida
- Parâmetros malformados

### Status Code 401: Unauthorized
Causas comuns:
- Token JWT inválido ou expirado
- Usuário não autenticado

### Status Code 403: Forbidden
Causas comuns:
- Usuário tentando acessar documento de outro usuário

### Status Code 404: Not Found
Causas comuns:
- Documento não existe
- Documento não foi ingerido no RAG ainda

### Status Code 500: Internal Server Error
Causas comuns:
- Erro na chamada da OpenAI API
- Falha no processamento de embeddings
- Erro na extração de texto do PDF

## Dicas de Performance

1. **Cache de Embeddings**: O sistema armazena embeddings em JSON para evitar recálculos
2. **Chunk Size**: Tamanho padrão de 500 caracteres, pode ser ajustado conforme necessário
3. **Top-K Results**: Por padrão, retorna 5 chunks mais relevantes (configurável)
4. **Temperature do LLM**: Definida em 0.3 para consistência em análises jurídicas

## Limites e Considerações

- **Rate Limit OpenAI**: Verificar limites da sua conta na OpenAI
- **Tamanho de Documento**: Documentos muito grandes podem levar mais tempo para ingestão
- **Qualidade de Resposta**: Depende da qualidade e clareza do documento
- **Termos Jurídicos**: Sistema reconhece termos em português, com mapeamento de variações comuns

## Troubleshooting

### Jurisprudência não aparece
1. Verifique se a resposta contém termos jurídicos reconhecidos
2. Veja o arquivo `jurisprudence_service.py` para a lista de termos mapeados
3. Adicione novos termos ao dicionário `legal_terms_mapping`

### Respostas muito genéricas
1. Verifique se o documento foi ingerido corretamente (`POST /rag/ingest/{doc_id}`)
2. Teste com perguntas mais específicas
3. Verifique se o documento contém o contexto necessário

### Erros de API OpenAI
1. Verifique se a chave de API é válida
2. Verifique se sua conta tem créditos disponíveis
3. Verifique os logs para detalhes de erro

## Exemplo de Integração Completa

Veja o arquivo [rag_integration_example.ts](./rag_integration_example.ts) para um exemplo completo de integração incluindo:
- Upload de documento
- Análise com jurisprudência
- Fazer perguntas com RAG
- Exibição de resultados com links para Jusbrasil

## Support

Para problemas ou dúvidas:
1. Verifique os logs da aplicação (`app/utils/logger.py`)
2. Revise as respostas do endpoint `/rag/ask` para mensagens de erro
3. Valide sua chave de API OpenAI
4. Teste com documentos simples primeiro
