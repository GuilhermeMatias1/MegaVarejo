from repositories.produto_repository import ProdutoRepository
from repositories.pedido_repository import PedidoRepository

class DashboardService:
    """
    Camada de serviço para agregar indicadores do Dashboard.
    """

    def __init__(self, produto_repo: ProdutoRepository = None, pedido_repo: PedidoRepository = None):
        self._produto_repo = produto_repo or ProdutoRepository()
        self._pedido_repo = pedido_repo or PedidoRepository()

    def obter_metricas(self) -> dict:
        total_produtos = self._produto_repo.contar_total()
        total_pedidos = self._pedido_repo.contar_total()
        total_vendas = self._pedido_repo.somar_vendas_totais()

        return {
            "total_produtos": total_produtos,
            "total_pedidos": total_pedidos,
            "total_vendas": total_vendas
        }
