from repositories.base_repository import BaseRepository
from models.usuario import Usuario, UsuarioFactory
from database.connection import DatabaseConnection

class UsuarioRepository(BaseRepository):
    """
    Repositório de persistência para Usuários e Perfis.
    Utiliza o UsuarioFactory para retornar objetos especializados polimórficos.
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
                cursor.execute("""
                    SELECT 
                        u.id, 
                        u.nome, 
                        u.email, 
                        u.senha_hash,
                        u.perfil_id, 
                        p.nome AS perfil_nome, 
                        u.ativo,
                        u.criado_em
                    FROM usuarios u
                    JOIN perfis p ON u.perfil_id = p.id
                    ORDER BY u.id ASC;
                """)
                linhas = cursor.fetchall()
                usuarios = []
                for l in linhas:
                    u = UsuarioFactory.criar_usuario(
                        perfil_nome=l.get('perfil_nome'),
                        nome=l.get('nome'),
                        email=l.get('email'),
                        senha_hash=l.get('senha_hash'),
                        ativo=bool(l.get('ativo', True)),
                        criado_em=l.get('criado_em'),
                        id=l.get('id'),
                        perfil_id=l.get('perfil_id', 1)
                    )
                    usuarios.append(u)
                return usuarios
        finally:
            if should_close:
                conn.close()

    def buscar_por_id(self, id: int) -> Usuario:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        u.id, 
                        u.nome, 
                        u.email, 
                        u.senha_hash,
                        u.perfil_id, 
                        p.nome AS perfil_nome, 
                        u.ativo,
                        u.criado_em
                    FROM usuarios u
                    JOIN perfis p ON u.perfil_id = p.id
                    WHERE u.id = %s;
                """, (id,))
                l = cursor.fetchone()
                if not l:
                    return None
                return UsuarioFactory.criar_usuario(
                    perfil_nome=l.get('perfil_nome'),
                    nome=l.get('nome'),
                    email=l.get('email'),
                    senha_hash=l.get('senha_hash'),
                    ativo=bool(l.get('ativo', True)),
                    criado_em=l.get('criado_em'),
                    id=l.get('id'),
                    perfil_id=l.get('perfil_id', 1)
                )
        finally:
            if should_close:
                conn.close()

    def buscar_por_email(self, email: str) -> Usuario:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        u.id, 
                        u.nome, 
                        u.email, 
                        u.senha_hash, 
                        u.perfil_id, 
                        p.nome AS perfil_nome, 
                        u.ativo,
                        u.criado_em
                    FROM usuarios u
                    JOIN perfis p ON u.perfil_id = p.id
                    WHERE LOWER(u.email) = %s;
                """, (str(email).strip().lower(),))
                l = cursor.fetchone()
                if not l:
                    return None
                return UsuarioFactory.criar_usuario(
                    perfil_nome=l.get('perfil_nome'),
                    nome=l.get('nome'),
                    email=l.get('email'),
                    senha_hash=l.get('senha_hash'),
                    ativo=bool(l.get('ativo', True)),
                    criado_em=l.get('criado_em'),
                    id=l.get('id'),
                    perfil_id=l.get('perfil_id', 1)
                )
        finally:
            if should_close:
                conn.close()

    def salvar(self, usuario: Usuario) -> int:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO usuarios (nome, email, senha_hash, perfil_id, ativo) VALUES (%s, %s, %s, %s, %s);",
                    (usuario.nome, usuario.email, usuario.senha_hash, usuario.perfil_id, 1 if usuario.ativo else 0)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise
        finally:
            if should_close:
                conn.close()

    def atualizar(self, usuario: Usuario, atualizar_senha: bool = False) -> bool:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                if atualizar_senha and usuario.senha_hash:
                    cursor.execute(
                        "UPDATE usuarios SET nome = %s, email = %s, perfil_id = %s, senha_hash = %s WHERE id = %s;",
                        (usuario.nome, usuario.email, usuario.perfil_id, usuario.senha_hash, usuario.id)
                    )
                else:
                    cursor.execute(
                        "UPDATE usuarios SET nome = %s, email = %s, perfil_id = %s WHERE id = %s;",
                        (usuario.nome, usuario.email, usuario.perfil_id, usuario.id)
                    )
                if cursor.rowcount == 0:
                    cursor.execute("SELECT id FROM usuarios WHERE id = %s;", (usuario.id,))
                    if not cursor.fetchone():
                        return False
                conn.commit()
                return True
        except Exception:
            conn.rollback()
            raise
        finally:
            if should_close:
                conn.close()

    def alterar_status(self, id: int, ativo: bool) -> bool:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE usuarios SET ativo = %s WHERE id = %s;", (1 if ativo else 0, id))
                if cursor.rowcount == 0:
                    cursor.execute("SELECT id FROM usuarios WHERE id = %s;", (id,))
                    if not cursor.fetchone():
                        return False
                conn.commit()
                return True
        except Exception:
            conn.rollback()
            raise
        finally:
            if should_close:
                conn.close()

    def listar_perfis(self) -> list:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, nome, descricao FROM perfis ORDER BY id ASC;")
                return cursor.fetchall()
        finally:
            if should_close:
                conn.close()
