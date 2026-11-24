from functools import wraps
from flask import session, jsonify
from models.usuario import UsuarioFactory

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return jsonify({'erro': 'Usuário não autenticado. Efetue o login.'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_permission(modulo):
    """
    Decorador RBAC que utiliza POLIMORFISMO:
    Instancia o objeto de usuário correspondente ao perfil da sessão
    e executa 'usuario.pode_acessar(modulo)'.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session:
                return jsonify({'erro': 'Usuário não autenticado.'}), 401

            perfil_nome = session.get('usuario_perfil')
            # Cria a instância polimórfica especializada (Administrador, Estoquista, Vendedor, Gerente)
            nome_sessao = session.get('usuario_nome') or 'Usuário'
            email_sessao = session.get('usuario_email') or 'usuario@megavarejo.com'
            usuario_obj = UsuarioFactory.criar_usuario(
                perfil_nome=perfil_nome,
                nome=nome_sessao,
                email=email_sessao,
                id=session.get('usuario_id')
            )

            # Chamada polimórfica ao método do objeto
            if not usuario_obj.pode_acessar(modulo):
                return jsonify({'erro': f'Acesso negado. O perfil [{perfil_nome}] não tem permissão para o módulo [{modulo}].'}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator
