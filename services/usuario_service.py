from models.usuario import Usuario, UsuarioFactory
from repositories.usuario_repository import UsuarioRepository

class UsuarioService:
    """
    Camada de serviço para Autenticação e Administração de Usuários.
    Aplica os métodos polimórficos de Usuario para autorização e listagem de permissões.
    """

    def __init__(self, usuario_repo: UsuarioRepository = None):
        self._repo = usuario_repo or UsuarioRepository()

    def autenticar(self, email: str, senha: str) -> Usuario:
        if not email or not senha:
            raise ValueError("Email e senha são obrigatórios.")

        usuario = self._repo.buscar_por_email(email)
        if not usuario:
            raise PermissionError("Credenciais inválidas.")

        if not usuario.ativo:
            raise PermissionError("Usuário desativado. Contate o administrador.")

        if not usuario.verificar_senha(senha):
            raise PermissionError("Credenciais inválidas.")

        return usuario

    def listar_usuarios(self) -> list:
        usuarios = self._repo.listar_todos()
        return [u.to_dict() for u in usuarios]

    def listar_perfis(self) -> list:
        return self._repo.listar_perfis()

    def cadastrar_usuario(self, nome: str, email: str, senha: str, perfil_id: int, ativo: bool = True) -> dict:
        if not perfil_id:
            raise ValueError("O perfil é obrigatório.")

        # Obtém o nome do perfil
        perfis = self.listar_perfis()
        perfil_match = next((p for p in perfis if p['id'] == int(perfil_id)), None)
        perfil_nome = perfil_match['nome'] if perfil_match else "Vendas"

        usuario = UsuarioFactory.criar_usuario(
            perfil_nome=perfil_nome,
            nome=nome,
            email=email,
            ativo=ativo,
            perfil_id=int(perfil_id)
        )
        usuario.definir_senha(senha)

        novo_id = self._repo.salvar(usuario)
        return {"mensagem": "Usuário cadastrado com sucesso!", "id": novo_id}

    def atualizar_usuario(self, id: int, nome: str, email: str, perfil_id: int, senha: str = None) -> dict:
        perfis = self.listar_perfis()
        perfil_match = next((p for p in perfis if p['id'] == int(perfil_id)), None)
        perfil_nome = perfil_match['nome'] if perfil_match else "Vendas"

        usuario = UsuarioFactory.criar_usuario(
            perfil_nome=perfil_nome,
            nome=nome,
            email=email,
            id=id,
            perfil_id=int(perfil_id)
        )

        atualizar_senha = False
        if senha and str(senha).strip():
            usuario.definir_senha(senha)
            atualizar_senha = True

        atualizado = self._repo.atualizar(usuario, atualizar_senha=atualizar_senha)
        if not atualizado:
            raise KeyError("Usuário não encontrado.")

        return {"mensagem": "Usuário atualizado com sucesso!"}

    def alternar_status(self, id: int, ativo: bool, usuario_sessao_id: int = None) -> dict:
        if usuario_sessao_id and id == usuario_sessao_id and not ativo:
            raise ValueError("Você não pode desativar seu próprio usuário.")

        atualizado = self._repo.alterar_status(id, ativo)
        if not atualizado:
            raise KeyError("Usuário não encontrado.")

        msg = "Usuário ativado com sucesso!" if ativo else "Usuário desativado com sucesso!"
        return {"mensagem": msg}
