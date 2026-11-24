from models.cliente import Cliente, validar_cpf
from models.pedido import formatar_data_br
from repositories.cliente_repository import ClienteRepository

class ClienteService:
    """
    Camada de serviço para o módulo de Clientes.
    Implementa regras de negócio para:
    - Validação estrita de CPF obrigatório e verificação de duplicidade.
    - Endereço completo detalhado.
    - CRUD completo (cadastro, consulta, edição e exclusão com integridade).
    - Histórico de pedidos associados.
    """

    def __init__(self, cliente_repo: ClienteRepository = None):
        self._repo = cliente_repo or ClienteRepository()

    def listar_clientes(self, busca: str = None) -> list:
        clientes = self._repo.listar_todos(busca=busca)
        resultado = []
        for c in clientes:
            d = c.to_dict()
            d['total_pedidos'] = getattr(c, 'total_pedidos', 0)
            resultado.append(d)
        return resultado

    def obter_cliente(self, id: int, incluir_pedidos: bool = True) -> dict:
        cliente = self._repo.buscar_por_id(id)
        if not cliente:
            return None
        dados = cliente.to_dict()
        if incluir_pedidos:
            pedidos_brutos = self._repo.listar_pedidos_cliente(id)
            pedidos_formatados = []
            for p in pedidos_brutos:
                p_dict = dict(p)
                p_dict['data_formatada'] = formatar_data_br(p_dict.get('data_pedido'), incluir_hora=True)
                pedidos_formatados.append(p_dict)
            dados['pedidos'] = pedidos_formatados
            dados['total_pedidos'] = len(pedidos_formatados)
        return dados

    def cadastrar_cliente(self, nome: str, email: str, cpf: str, telefone: str = "",
                          cep: str = "", logradouro: str = "", numero: str = "", complemento: str = "",
                          bairro: str = "", cidade: str = "", uf: str = "") -> dict:
        """
        Cadastra novo cliente garantindo CPF válido e único, além de e-mail único.
        """
        # Validação obrigatória dos dígitos do CPF no domínio
        cpf_limpo = validar_cpf(cpf)

        # Regra de negócio: Unicidade de CPF
        existente_cpf = self._repo.buscar_por_cpf(cpf_limpo)
        if existente_cpf:
            raise ValueError(f"Já existe um cliente cadastrado com o CPF '{existente_cpf.cpf_formatado}'.")

        # Regra de negócio: Unicidade de E-mail
        existente_email = self._repo.buscar_por_email(email)
        if existente_email:
            raise ValueError(f"Já existe um cliente cadastrado com o e-mail '{email}'.")

        cliente = Cliente(
            nome=nome,
            email=email,
            cpf=cpf_limpo,
            telefone=telefone,
            cep=cep,
            logradouro=logradouro,
            numero=numero,
            complemento=complemento,
            bairro=bairro,
            cidade=cidade,
            uf=uf
        )

        novo_id = self._repo.salvar(cliente)
        return {
            "mensagem": "Cliente cadastrado com sucesso!",
            "id": novo_id,
            "cpf": cliente.cpf_formatado,
            "endereco_sugerido": cliente.endereco.texto_completo()
        }

    def atualizar_cliente(self, id: int, nome: str, email: str, cpf: str, telefone: str = "",
                          cep: str = "", logradouro: str = "", numero: str = "", complemento: str = "",
                          bairro: str = "", cidade: str = "", uf: str = "") -> dict:
        """
        Atualiza dados do cliente existente validando CPF e verificando que novos dados não colidam com outros clientes.
        """
        cliente_atual = self._repo.buscar_por_id(id)
        if not cliente_atual:
            raise KeyError("Cliente não encontrado.")

        cpf_limpo = validar_cpf(cpf)

        # Verifica unicidade de CPF (se for alterado)
        existente_cpf = self._repo.buscar_por_cpf(cpf_limpo)
        if existente_cpf and existente_cpf.id != id:
            raise ValueError(f"Outro cliente já está cadastrado com o CPF '{existente_cpf.cpf_formatado}'.")

        # Verifica unicidade de E-mail (se for alterado)
        existente_email = self._repo.buscar_por_email(email)
        if existente_email and existente_email.id != id:
            raise ValueError(f"Outro cliente já está cadastrado com o e-mail '{email}'.")

        cliente_atual.nome = nome
        cliente_atual.email = email
        cliente_atual.cpf = cpf_limpo
        cliente_atual.telefone = telefone

        # Atualiza o objeto de valor Endereco
        end = cliente_atual.endereco
        end.cep = cep
        end.logradouro = logradouro
        end.numero = numero
        end.complemento = complemento
        end.bairro = bairro
        end.cidade = cidade
        end.uf = uf

        self._repo.atualizar(cliente_atual)
        return {
            "mensagem": "Cliente atualizado com sucesso!",
            "id": id,
            "cpf": cliente_atual.cpf_formatado,
            "endereco_sugerido": end.texto_completo()
        }

    def excluir_cliente(self, id: int) -> dict:
        """
        Integridade referencial: Impede exclusão se o cliente possuir pedidos cadastrados.
        """
        cliente = self._repo.buscar_por_id(id)
        if not cliente:
            raise KeyError("Cliente não encontrado.")

        total_pedidos = self._repo.contar_pedidos_cliente(id)
        if total_pedidos > 0:
            raise ValueError(f"Não é permitido excluir o cliente '{cliente.nome}' pois existem {total_pedidos} pedido(s) vinculados a ele.")

        self._repo.excluir(id)
        return {"mensagem": f"Cliente '{cliente.nome}' excluído com sucesso!"}
