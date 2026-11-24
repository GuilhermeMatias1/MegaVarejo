from models.cliente import Cliente
from repositories.cliente_repository import ClienteRepository

class ClienteService:
    """
    Camada de serviço para o módulo de Clientes.
    """

    def __init__(self, cliente_repo: ClienteRepository = None):
        self._repo = cliente_repo or ClienteRepository()

    def listar_clientes(self) -> list:
        clientes = self._repo.listar_todos()
        return [c.to_dict() for c in clientes]

    def cadastrar_cliente(self, nome: str, email: str, telefone: str = "", cidade: str = "") -> dict:
        cliente = Cliente(nome=nome, email=email, telefone=telefone, cidade=cidade)
        novo_id = self._repo.salvar(cliente)
        return {"mensagem": "Cliente cadastrado com sucesso!", "id": novo_id}
