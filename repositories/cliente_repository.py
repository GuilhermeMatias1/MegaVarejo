from repositories.base_repository import BaseRepository
from models.cliente import Cliente
from database.connection import DatabaseConnection

class ClienteRepository(BaseRepository):
    """
    Repositório de persistência para a entidade Cliente.
    """

    def __init__(self, connection=None):
        self._connection = connection

    def _get_connection(self):
        return self._connection if self._connection else DatabaseConnection.get_connection()

    def listar_todos(self) -> list:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, nome, email, telefone, cidade, criado_em FROM clientes ORDER BY id DESC;")
                linhas = cursor.fetchall()
                return [Cliente(id=l['id'], nome=l['nome'], email=l['email'], telefone=l['telefone'], cidade=l['cidade'], criado_em=l['criado_em']) for l in linhas]
        finally:
            if should_close:
                conn.close()

    def buscar_por_id(self, id: int) -> Cliente:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, nome, email, telefone, cidade, criado_em FROM clientes WHERE id = %s;", (id,))
                linha = cursor.fetchone()
                if not linha:
                    return None
                return Cliente(id=linha['id'], nome=linha['nome'], email=linha['email'], telefone=linha['telefone'], cidade=linha['cidade'], criado_em=linha['criado_em'])
        finally:
            if should_close:
                conn.close()

    def salvar(self, cliente: Cliente) -> int:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO clientes (nome, email, telefone, cidade) VALUES (%s, %s, %s, %s);",
                    (cliente.nome, cliente.email, cliente.telefone, cliente.cidade)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise
        finally:
            if should_close:
                conn.close()
