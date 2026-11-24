from services.estoque_service import EstoqueService

class ProdutoService(EstoqueService):
    """
    Subclasse / alias mantido para compatibilidade com o código existente.
    Delega e reutiliza integralmente a lógica unificada do EstoqueService.
    """
    def cadastrar_produto(self, nome: str, preco, estoque, **kwargs) -> dict:
        dados = {"nome": nome, "preco": preco, "estoque": estoque}
        dados.update(kwargs)
        return super().cadastrar_produto(dados)

    def atualizar_produto(self, id: int, nome: str, preco, estoque, **kwargs) -> dict:
        dados = {"nome": nome, "preco": preco, "estoque": estoque}
        dados.update(kwargs)
        return super().atualizar_produto(id, dados)
