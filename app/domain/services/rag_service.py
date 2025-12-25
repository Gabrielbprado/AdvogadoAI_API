"""RAG (Retrieval-Augmented Generation) service using OpenAI embeddings and LLM."""
from __future__ import annotations

import json
from typing import Optional, List
from logging import Logger
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("openai package is required. Install it with: pip install openai")


class RAGStore:
    """Manages document storage and retrieval for RAG system."""

    def __init__(self, storage_dir: Path = Path("data/rag_store"), logger: Logger | None = None):
        """Initialize RAG store.
        
        Args:
            storage_dir: Directory to store embeddings and document chunks
            logger: Optional logger instance
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self.embeddings_file = self.storage_dir / "embeddings.json"
        self.chunks_file = self.storage_dir / "chunks.json"
        self._load_data()

    def _load_data(self) -> None:
        """Load existing embeddings and chunks from disk."""
        self.embeddings_db = {}
        self.chunks_db = {}
        
        if self.embeddings_file.exists():
            try:
                with open(self.embeddings_file, "r", encoding="utf-8") as f:
                    self.embeddings_db = json.load(f)
                if self.logger:
                    self.logger.info(f"Loaded {len(self.embeddings_db)} embeddings from disk")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error loading embeddings: {e}")
        
        if self.chunks_file.exists():
            try:
                with open(self.chunks_file, "r", encoding="utf-8") as f:
                    self.chunks_db = json.load(f)
                if self.logger:
                    self.logger.info(f"Loaded {len(self.chunks_db)} chunks from disk")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error loading chunks: {e}")

    def _save_data(self) -> None:
        """Persist embeddings and chunks to disk."""
        try:
            with open(self.embeddings_file, "w", encoding="utf-8") as f:
                json.dump(self.embeddings_db, f, ensure_ascii=False, indent=2)
            with open(self.chunks_file, "w", encoding="utf-8") as f:
                json.dump(self.chunks_db, f, ensure_ascii=False, indent=2)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error saving data: {e}")

    def add_document(self, doc_id: str, chunks: List[str], embeddings: List[List[float]]) -> None:
        """Store document chunks and their embeddings.
        
        Args:
            doc_id: Document identifier
            chunks: List of text chunks
            embeddings: List of embedding vectors
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{doc_id}_{i}"
            self.embeddings_db[chunk_id] = embedding
            self.chunks_db[chunk_id] = {
                "doc_id": doc_id,
                "chunk_index": i,
                "text": chunk
            }
        
        self._save_data()
        if self.logger:
            self.logger.info(f"Stored {len(chunks)} chunks for document {doc_id}")

    def get_chunks_by_doc_id(self, doc_id: str) -> List[dict]:
        """Retrieve all chunks for a specific document."""
        return [
            chunk for chunk in self.chunks_db.values() 
            if chunk["doc_id"] == doc_id
        ]

    def get_all_chunks(self) -> dict:
        """Get all stored chunks."""
        return self.chunks_db


class RAGService:
    """Main RAG service combining embeddings and LLM for legal document analysis."""

    def __init__(
        self,
        openai_api_key: str,
        openai_model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
        storage_dir: Path = Path("data/rag_store"),
        logger: Logger | None = None,
    ):
        """Initialize RAG service.
        
        Args:
            openai_api_key: OpenAI API key
            openai_model: LLM model to use (default: gpt-4o-mini)
            embedding_model: Embedding model to use (default: text-embedding-3-small)
            storage_dir: Directory for storing embeddings
            logger: Optional logger instance
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.openai_model = openai_model
        self.embedding_model = embedding_model
        self.store = RAGStore(storage_dir, logger)
        self.logger = logger

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for a text using OpenAI."""
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a ** 2 for a in vec1) ** 0.5
        magnitude2 = sum(b ** 2 for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)

    def ingest_document(self, doc_id: str, text: str, chunk_size: int = 500) -> None:
        """Ingest a document by chunking it and creating embeddings.
        
        Args:
            doc_id: Document identifier
            text: Full document text
            chunk_size: Size of each chunk in characters
        """
        # Split text into chunks
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i:i + chunk_size].strip())
        
        # Remove empty chunks
        chunks = [c for c in chunks if c]
        
        if not chunks:
            raise ValueError("No valid chunks created from document")
        
        # Create embeddings
        embeddings = []
        for i, chunk in enumerate(chunks):
            if self.logger:
                self.logger.debug(f"Creating embedding {i+1}/{len(chunks)} for document {doc_id}")
            embedding = self._get_embedding(chunk)
            embeddings.append(embedding)
        
        # Store in RAG store
        self.store.add_document(doc_id, chunks, embeddings)
        if self.logger:
            self.logger.info(f"Successfully ingested document {doc_id} with {len(chunks)} chunks")

    def retrieve_context(self, query: str, doc_id: str | None = None, top_k: int = 5) -> List[dict]:
        """Retrieve most relevant chunks for a query.
        
        Args:
            query: User query
            doc_id: Optional document ID to limit search scope
            top_k: Number of top results to return
            
        Returns:
            List of relevant chunks with similarity scores
        """
        query_embedding = self._get_embedding(query)
        
        # Get candidates
        if doc_id:
            chunks = self.store.get_chunks_by_doc_id(doc_id)
            chunk_ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        else:
            chunk_ids = list(self.store.embeddings_db.keys())
        
        # Calculate similarities
        results = []
        for chunk_id in chunk_ids:
            if chunk_id not in self.store.embeddings_db:
                continue
                
            embedding = self.store.embeddings_db[chunk_id]
            similarity = self._cosine_similarity(query_embedding, embedding)
            chunk_data = self.store.chunks_db.get(chunk_id, {})
            
            results.append({
                "chunk_id": chunk_id,
                "text": chunk_data.get("text", ""),
                "similarity": similarity,
                "doc_id": chunk_data.get("doc_id", "")
            })
        
        # Sort by similarity and return top_k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def answer_question(
        self,
        query: str,
        doc_id: str | None = None,
        system_prompt: str | None = None,
        include_sources: bool = True
    ) -> dict:
        """Answer a question about document(s) using RAG.
        
        Args:
            query: User question
            doc_id: Optional document ID to limit search
            system_prompt: Optional custom system prompt for legal context
            include_sources: Whether to include source chunks in response
            
        Returns:
            Dictionary containing answer, sources, and metadata
        """
        # Retrieve relevant context
        retrieved_chunks = self.retrieve_context(query, doc_id, top_k=5)
        
        if not retrieved_chunks:
            return {
                "answer": "Não foram encontrados documentos relevantes para sua pergunta.",
                "sources": [],
                "legal_context": None,
                "jurisprudence_terms": []
            }
        
        # Prepare context for LLM
        context_text = "\n\n".join([
            f"[Documento {i+1} - Similaridade: {chunk['similarity']:.2%}]\n{chunk['text']}"
            for i, chunk in enumerate(retrieved_chunks)
        ])
        
        # Extract key legal terms for jurisprudence
        jurisprudence_terms = self._extract_legal_terms(query, context_text)
        
        # Default legal system prompt
        if system_prompt is None:
            system_prompt = """Você é um assistente jurídico especializado em análise de documentos legais.
            
Suas responsabilidades:
1. Responder perguntas com base ESTRITAMENTE no documento fornecido
2. Citar as cláusulas e seções específicas do documento
3. Manter objetividade e precisão jurídica
4. Se a informação não estiver no documento, informar claramente
5. Estruturar respostas de forma clara e profissional

Sempre cite as fontes do documento ao responder."""
        
        # Create messages for LLM
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"""Com base no seguinte contexto do documento, responda a pergunta:

CONTEXTO DO DOCUMENTO:
{context_text}

PERGUNTA:
{query}

Forneça uma resposta estruturada, citando as partes relevantes do documento."""
            }
        ]
        
        # Call LLM
        response = self.client.chat.completions.create(
            model=self.openai_model,
            messages=messages,
            temperature=0.3,  # Low temperature for consistency in legal analysis
            max_tokens=1500
        )
        
        answer = response.choices[0].message.content
        
        return {
            "answer": answer,
            "sources": [
                {
                    "text": chunk["text"],
                    "similarity": chunk["similarity"],
                    "doc_id": chunk["doc_id"]
                }
                for chunk in retrieved_chunks
            ] if include_sources else [],
            "legal_context": "Análise baseada em documentos jurídicos",
            "jurisprudence_terms": jurisprudence_terms
        }

    def _extract_legal_terms(self, query: str, context: str) -> List[str]:
        """Extract legal terms from query and context for jurisprudence search.
        
        Args:
            query: User query
            context: Document context
            
        Returns:
            List of key legal terms
        """
        # Call LLM to extract key legal terms
        messages = [
            {
                "role": "system",
                "content": """Você é um especialista em extrair termos jurídicos relevantes.
                
Extraia apenas os termos jurídicos, nomes de leis, crimes, ou conceitos legais principais.
Retorne como uma lista JSON simples de strings.
Exemplo: ["roubo", "dolo", "prescrito", "insalubridade"]"""
            },
            {
                "role": "user",
                "content": f"""Extraia os termos jurídicos principais desta pergunta e contexto:

PERGUNTA: {query}

CONTEXTO: {context[:500]}  (primeiros 500 caracteres)

Retorne como JSON array de strings, apenas os termos jurídicos relevantes."""
            }
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                temperature=0.3,
                max_tokens=200
            )
            
            response_text = response.choices[0].message.content
            # Try to parse JSON from response
            if "[" in response_text:
                json_start = response_text.find("[")
                json_end = response_text.rfind("]") + 1
                terms = json.loads(response_text[json_start:json_end])
                return terms if isinstance(terms, list) else []
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error extracting legal terms: {e}")
        
        return []

    def get_document_summary(self, doc_id: str) -> dict:
        """Get a summary of a stored document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Summary with key information
        """
        chunks = self.store.get_chunks_by_doc_id(doc_id)
        if not chunks:
            return {"error": f"Document {doc_id} not found"}
        
        # Combine all chunks
        full_text = "\n\n".join([chunk["text"] for chunk in chunks])
        
        # Call LLM to create summary
        messages = [
            {
                "role": "system",
                "content": """Você é um especialista jurídico em sumarização de documentos.
                
Crie um resumo estruturado que inclua:
1. Tipo de documento
2. Partes envolvidas
3. Objetivo principal
4. Cláusulas importantes
5. Prazos e datas relevantes
6. Termos chave para jurisprudência

Mantenha o resumo conciso mas informativo."""
            },
            {
                "role": "user",
                "content": f"""Resuma o seguinte documento jurídico de forma estruturada:

{full_text}"""
            }
        ]
        
        response = self.client.chat.completions.create(
            model=self.openai_model,
            messages=messages,
            temperature=0.3,
            max_tokens=1000
        )
        
        return {
            "doc_id": doc_id,
            "summary": response.choices[0].message.content,
            "chunk_count": len(chunks)
        }
