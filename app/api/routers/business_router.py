"""API Router for business entities (Empresas, Pedidos, Produtos)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status

from app.domain.models.business_models import (
    BusinessRepository,
    Empresa,
    Pedido,
    Produto,
)


def build_business_router() -> APIRouter:
    """Create and return the business router."""
    router = APIRouter(prefix="/business", tags=["negocios"])
    repo = BusinessRepository()

    # --- Empresas ---
    @router.get("/empresas", response_model=List[Empresa])
    async def list_empresas() -> List[Empresa]:
        """Listar todas as empresas cadastradas."""
        return repo.list_empresas()

    @router.get("/empresas/{empresa_id}", response_model=Empresa)
    async def get_empresa(empresa_id: str) -> Empresa:
        """Obter detalhes de uma empresa específica."""
        empresa = repo.get_empresa(empresa_id)
        if not empresa:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
        return empresa

    # --- Produtos ---
    @router.get("/produtos", response_model=List[Produto])
    async def list_produtos() -> List[Produto]:
        """Listar todos os produtos disponíveis."""
        return repo.list_produtos()

    @router.get("/produtos/{produto_id}", response_model=Produto)
    async def get_produto(produto_id: str) -> Produto:
        """Obter detalhes de um produto específico."""
        produto = repo.get_produto(produto_id)
        if not produto:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
        return produto

    # --- Pedidos ---
    @router.get("/pedidos", response_model=List[Pedido])
    async def list_pedidos() -> List[Pedido]:
        """Listar todos os pedidos realizados."""
        return repo.list_pedidos()

    @router.get("/pedidos/{pedido_id}", response_model=Pedido)
    async def get_pedido(pedido_id: str) -> Pedido:
        """Obter detalhes de um pedido específico."""
        pedido = repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido não encontrado")
        return pedido

    return router
