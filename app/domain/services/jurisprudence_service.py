"""Jurisprudence service for generating Jusbrasil search links and managing legal references."""
from __future__ import annotations

from typing import List, Optional
from urllib.parse import quote
from logging import Logger


class JurisprudenceService:
    """Service for handling jurisprudence-related operations for legal documents."""

    # Base URL for Jusbrasil jurisprudence search
    JUSBRASIL_BASE_URL = "https://www.jusbrasil.com.br/jurisprudencia/busca"

    def __init__(self, logger: Logger | None = None):
        """Initialize jurisprudence service.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger
        # Common legal terms in Portuguese for normalization
        self.legal_terms_mapping = {
            "insalubridade": "insalubridade",
            "insolubilidade": "insalubridade",  # Common misspelling
            "dolo": "dolo",
            "culpa": "culpa",
            "prescricao": "prescrição",
            "usucapiao": "usucapião",
            "comodato": "comodato",
            "mutuo": "mútuo",
            "contrato": "contrato",
            "rescisao": "rescisão",
            "indenizacao": "indenização",
            "responsabilidade": "responsabilidade",
            "roubo": "roubo",
            "furto": "furto",
            "estelionato": "estelionato",
            "homicidio": "homicídio",
            "lesao corporal": "lesão corporal",
            "difamacao": "difamação",
            "injuria": "injúria",
            "calumnia": "calúnia",
            "direito do trabalho": "direito do trabalho",
            "justa causa": "justa causa",
            "aviso previo": "aviso prévio",
            "fgts": "FGTS",
            "inpc": "INPC",
            "salario minimo": "salário mínimo",
        }

    def generate_jurisprudence_link(self, search_terms: List[str] | str) -> str:
        """Generate a Jusbrasil jurisprudence search link.
        
        Args:
            search_terms: Single term or list of legal terms to search
            
        Returns:
            Complete Jusbrasil search URL
        """
        # Normalize input
        if isinstance(search_terms, str):
            search_terms = [search_terms]
        
        # Process and normalize terms
        normalized_terms = []
        for term in search_terms:
            normalized = self._normalize_term(term)
            if normalized:
                normalized_terms.append(normalized)
        
        if not normalized_terms:
            # Default search if no terms provided
            return f"{self.JUSBRASIL_BASE_URL}?q=jurisprudência"
        
        # Build search query
        search_query = " ".join(normalized_terms)
        
        # URL encode the query
        encoded_query = quote(search_query, safe='')
        
        return f"{self.JUSBRASIL_BASE_URL}?q={encoded_query}"

    def _normalize_term(self, term: str) -> str:
        """Normalize a legal term for search.
        
        Args:
            term: Legal term to normalize
            
        Returns:
            Normalized term
        """
        if not term or not isinstance(term, str):
            return ""
        
        # Remove extra spaces and convert to lowercase for lookup
        term = term.strip().lower()
        
        # Check mapping
        if term in self.legal_terms_mapping:
            return self.legal_terms_mapping[term]
        
        # If no mapping, return as-is (but clean)
        # Remove special characters but keep spaces
        cleaned = "".join(c if c.isalnum() or c.isspace() else "" for c in term)
        return " ".join(cleaned.split())  # Normalize spaces

    def extract_jurisprudence_terms(
        self,
        document_content: str,
        question: str | None = None
    ) -> List[str]:
        """Extract legal terms that could have jurisprudence from document/question.
        
        Args:
            document_content: Document text or extracted terms
            question: Optional user question for context
            
        Returns:
            List of identified legal terms (prioritizing specific compound terms)
        """
        # Combine content for analysis
        content_to_analyze = document_content
        if question:
            content_to_analyze = f"{question}\n{document_content}"
        
        # Convert to lowercase for matching
        content_lower = content_to_analyze.lower()
        
        # Found terms with priority scoring
        found_terms_with_priority = []
        
        # PRIORITY 1: Compound/specific legal terms (more valuable)
        compound_terms = [
            "rescisão contratual", "rescisão amigável", "rescisão por justa causa",
            "responsabilidade técnica", "responsabilidade digital", "responsabilidade civil",
            "falha de prestação de serviço", "falha no cumprimento contratual",
            "danos morais", "danos materiais", "danos emergentes",
            "lucros cessantes", "perdas e danos",
            "cláusula abusiva", "cláusula penal", "cláusula de confidencialidade",
            "cláusula de quitação", "cláusula resolutiva",
            "integração de api", "manutenção de plataforma digital",
            "serviços digitais", "prestação de serviços",
            "compensação financeira", "indenização por descumprimento",
            "acordo extrajudicial", "acordo amigável",
            "inadimplemento contratual", "mora contratual",
            "multa contratual", "penalidade contratual",
            "prazo de entrega", "prazo contratual",
            "vício do serviço", "defeito na prestação",
            "revisão contratual", "aditivo contratual",
            "contrato de prestação de serviços", "contrato digital",
            "força maior", "caso fortuito",
            "onerosidade excessiva", "teoria da imprevisão",
            "boa-fé contratual", "função social do contrato"
        ]
        
        for term in compound_terms:
            if term in content_lower:
                found_terms_with_priority.append((term, 10))  # High priority
        
        # PRIORITY 2: Specific single terms (medium value)
        specific_terms = {
            "rescisao": "rescisão",
            "rescisão": "rescisão",
            "indenizacao": "indenização",
            "indenização": "indenização",
            "inadimplencia": "inadimplência",
            "inadimplência": "inadimplência",
            "confidencialidade": "confidencialidade",
            "quitacao": "quitação",
            "quitação": "quitação",
            "multa": "multa",
            "penalidade": "penalidade",
            "api": "integração de API",
            "sla": "SLA (Service Level Agreement)",
            "mora": "mora contratual",
            "vicio": "vício do serviço",
            "defeito": "defeito na prestação"
        }
        
        for variant, canonical in specific_terms.items():
            if variant in content_lower and canonical not in [t[0] for t in found_terms_with_priority]:
                found_terms_with_priority.append((canonical, 5))  # Medium priority
        
        # PRIORITY 3: Generic terms (only if no specific terms found)
        generic_terms = {
            "contrato": "contrato",
            "responsabilidade": "responsabilidade",
            "servico": "serviço",
            "serviço": "serviço",
            "obrigacao": "obrigação",
            "obrigação": "obrigação"
        }
        
        # Only add generic if we have less than 3 specific terms
        if len(found_terms_with_priority) < 3:
            for variant, canonical in generic_terms.items():
                if variant in content_lower and canonical not in [t[0] for t in found_terms_with_priority]:
                    found_terms_with_priority.append((canonical, 1))  # Low priority
        
        # Sort by priority (descending) and extract terms
        found_terms_with_priority.sort(key=lambda x: x[1], reverse=True)
        
        # Return top 5 most relevant terms
        final_terms = [term for term, _ in found_terms_with_priority[:5]]
        
        if self.logger and final_terms:
            self.logger.info(f"Extracted {len(final_terms)} specific jurisprudence terms: {final_terms}")
        
        return final_terms

    def create_jurisprudence_response(
        self,
        legal_terms: List[str],
        document_content: str | None = None
    ) -> List[dict]:
        """Create a list of jurisprudence links for legal terms.
        
        Args:
            legal_terms: List of legal terms identified
            document_content: Optional document content for additional context
            
        Returns:
            List of jurisprudence objects with links and descriptions
        """
        jurisprudence_list = []
        
        for term in legal_terms:
            if not term:
                continue
            
            link = self.generate_jurisprudence_link(term)
            
            jurisprudence_list.append({
                "term": term,
                "url": link,
                "description": f"Jurisprudência sobre {term}",
                "source": "Jusbrasil"
            })
        
        if self.logger and jurisprudence_list:
            self.logger.info(f"Generated {len(jurisprudence_list)} jurisprudence links")
        
        return jurisprudence_list

    def format_jurisprudence_for_response(
        self,
        legal_terms: List[str],
        document_id: str | None = None
    ) -> dict:
        """Format jurisprudence data for API response.
        
        Args:
            legal_terms: List of legal terms
            document_id: Optional document ID for context
            
        Returns:
            Formatted jurisprudence data
        """
        jurisprudence_links = self.create_jurisprudence_response(legal_terms)
        
        return {
            "document_id": document_id,
            "jurisprudencia": [
                {
                    "termo": item["term"],
                    "url": item["url"],
                    "descricao": item["description"],
                    "fonte": item["source"]
                }
                for item in jurisprudence_links
            ],
            "total_termos": len(legal_terms),
            "observacao": "Links para jurisprudência do Jusbrasil referentes aos termos identificados no documento"
        }

    def combine_legal_terms(
        self,
        extracted_terms: List[str],
        rag_terms: List[str],
        user_terms: List[str] | None = None
    ) -> List[str]:
        """Combine multiple sources of legal terms into a deduplicated list.
        
        Args:
            extracted_terms: Terms from document extraction
            rag_terms: Terms from RAG analysis
            user_terms: Optional terms from user input
            
        Returns:
            Deduplicated list of legal terms
        """
        # Combine all sources
        all_terms = extracted_terms + rag_terms
        if user_terms:
            all_terms += user_terms
        
        # Deduplicate and normalize
        unique_terms = set()
        for term in all_terms:
            normalized = self._normalize_term(term)
            if normalized:
                unique_terms.add(normalized)
        
        return list(unique_terms)

    def is_legal_document(self, content: str) -> bool:
        """Determine if content appears to be a legal document.
        
        Args:
            content: Document content
            
        Returns:
            True if appears to be legal document
        """
        legal_indicators = [
            "cláusula",
            "artigo",
            "lei",
            "decreto",
            "contrato",
            "acordo",
            "termo",
            "rescisão",
            "rescissão",
            "juízo",
            "juizo",
            "sentença",
            "sentenca",
            "condenado",
            "condenada",
            "responsabilidade",
            "obrigação",
            "obrigacao"
        ]
        
        content_lower = content.lower()
        indicator_count = sum(1 for indicator in legal_indicators if indicator in content_lower)
        
        # If we find multiple indicators, it's likely a legal document
        return indicator_count >= 3
