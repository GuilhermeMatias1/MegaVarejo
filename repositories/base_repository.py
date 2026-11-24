from abc import ABC, abstractmethod

class BaseRepository(ABC):
    """
    Interface/Classe Abstrata base para repositórios de dados.
    Demonstra ABSTRAÇÃO isolando as rotinas e contratos de persistência do domínio da aplicação.
    """

    @abstractmethod
    def buscar_por_id(self, id: int):
        pass

    @abstractmethod
    def listar_todos(self) -> list:
        pass
