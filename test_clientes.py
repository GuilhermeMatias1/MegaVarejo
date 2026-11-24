import unittest
from unittest.mock import MagicMock, patch
from app import app
from models.cliente import Cliente, validar_cpf, formatar_cpf_br, Endereco
from services.cliente_service import ClienteService

class TestModuloClientes(unittest.TestCase):
    """
    Testes específicos do Módulo de Clientes:
    - Validação de CPF com dígitos verificadores e rejeição de repetidos.
    - Encapsulamento de Endereço completo.
    - Unicidade de CPF e e-mail.
    - Edição e consulta com histórico de pedidos.
    - Integridade referencial (bloqueio de exclusão quando há pedidos vinculados).
    - Integração de endereço sugerido com Pedidos.
    """

    def setUp(self):
        self.client = app.test_client()

    # 1. VALIDAÇÃO DE CPF (Dígitos verificadores e formatos)
    def test_validacao_cpf_digitos_corretos(self):
        # CPFs matematicamente válidos
        cpf_valido_1 = "123.456.789-09"
        cpf_valido_2 = "987.654.321-00"
        cpf_valido_3 = "52998224725" # gerado com dígitos verificadores válidos

        self.assertEqual(validar_cpf(cpf_valido_1), "12345678909")
        self.assertEqual(validar_cpf(cpf_valido_2), "98765432100")
        self.assertEqual(validar_cpf(cpf_valido_3), "52998224725")

    def test_validacao_cpf_digitos_incorretos(self):
        # CPF com dígito verificador errado
        with self.assertRaises(ValueError) as ctx:
            validar_cpf("123.456.789-00")
        self.assertIn("dígito verificador incorreto", str(ctx.exception))

        # CPF com sequência repetida
        with self.assertRaises(ValueError) as ctx:
            validar_cpf("111.111.111-11")
        self.assertIn("sequência de números repetidos", str(ctx.exception))

        # CPF com tamanho menor ou vazio
        with self.assertRaises(ValueError):
            validar_cpf("12345")
        with self.assertRaises(ValueError):
            validar_cpf("")

    # 2. ENCAPSULAMENTO DE ENDEREÇO E FORMATAÇÃO
    def test_encapsulamento_endereco_completo(self):
        end = Endereco(
            cep="01310100",
            logradouro="Avenida Paulista",
            numero="1000",
            complemento="Apto 50",
            bairro="Bela Vista",
            cidade="São Paulo",
            uf="SP"
        )
        self.assertEqual(end.cep, "01310-100")
        texto = end.texto_completo()
        self.assertIn("Avenida Paulista, 1000 - Apto 50", texto)
        self.assertIn("Bela Vista", texto)
        self.assertIn("São Paulo - SP", texto)
        self.assertIn("CEP 01310-100", texto)

    # 3. CRIAÇÃO DE CLIENTE COM CPF E ENDEREÇO
    def test_dominio_cliente_instanciacao_e_to_dict(self):
        cliente = Cliente(
            nome="Carlos Alberto",
            email="carlos@empresa.com",
            cpf="123.456.789-09",
            telefone="(11) 98888-7777",
            cep="01310-100",
            logradouro="Av. Paulista",
            numero="1500",
            bairro="Bela Vista",
            cidade="São Paulo",
            uf="SP"
        )
        d = cliente.to_dict()
        self.assertEqual(d["nome"], "Carlos Alberto")
        self.assertEqual(d["cpf"], "12345678909")
        self.assertEqual(d["cpf_formatado"], "123.456.789-09")
        self.assertIn("Av. Paulista, 1500", d["endereco_completo"])

    # 4. UNICIDADE DE CPF E E-MAIL NO SERVICE
    def test_service_impede_duplicidade_de_cpf_e_email(self):
        mock_repo = MagicMock()
        service = ClienteService(cliente_repo=mock_repo)

        # Simula que o CPF já existe
        mock_repo.buscar_por_cpf.return_value = Cliente(nome="Outro", email="outro@mail.com", cpf="12345678909")
        mock_repo.buscar_por_email.return_value = None

        with self.assertRaises(ValueError) as ctx:
            service.cadastrar_cliente(
                nome="Novo",
                email="novo@mail.com",
                cpf="123.456.789-09"
            )
        self.assertIn("Já existe um cliente cadastrado com o CPF", str(ctx.exception))

        # Simula que o CPF é novo, mas o e-mail já existe
        mock_repo.buscar_por_cpf.return_value = None
        mock_repo.buscar_por_email.return_value = Cliente(nome="Outro", email="existente@mail.com", cpf="98765432100")

        with self.assertRaises(ValueError) as ctx:
            service.cadastrar_cliente(
                nome="Novo",
                email="existente@mail.com",
                cpf="123.456.789-09"
            )
        self.assertIn("Já existe um cliente cadastrado com o e-mail", str(ctx.exception))

    # 5. EDIÇÃO DE CLIENTE
    def test_service_atualizacao_cliente(self):
        mock_repo = MagicMock()
        cliente_existente = Cliente(
            id=10,
            nome="Nome Antigo",
            email="antigo@mail.com",
            cpf="12345678909",
            cidade="Curitiba"
        )
        mock_repo.buscar_por_id.return_value = cliente_existente
        mock_repo.buscar_por_cpf.return_value = cliente_existente
        mock_repo.buscar_por_email.return_value = cliente_existente

        service = ClienteService(cliente_repo=mock_repo)
        res = service.atualizar_cliente(
            id=10,
            nome="Nome Atualizado",
            email="atualizado@mail.com",
            cpf="123.456.789-09",
            cidade="Florianópolis",
            uf="SC"
        )
        self.assertIn("Cliente atualizado com sucesso", res["mensagem"])
        self.assertEqual(cliente_existente.nome, "Nome Atualizado")
        self.assertEqual(cliente_existente.email, "atualizado@mail.com")
        self.assertEqual(cliente_existente.cidade, "Florianópolis")
        mock_repo.atualizar.assert_called_once()

    # 6. INTEGRIDADE REFERENCIAL NA EXCLUSÃO
    def test_service_impede_exclusao_de_cliente_com_pedidos(self):
        mock_repo = MagicMock()
        cliente = Cliente(id=5, nome="Cliente Com Pedidos", email="compra@mail.com", cpf="12345678909")
        mock_repo.buscar_por_id.return_value = cliente
        # Cliente possui 3 pedidos
        mock_repo.contar_pedidos_cliente.return_value = 3

        service = ClienteService(cliente_repo=mock_repo)
        with self.assertRaises(ValueError) as ctx:
            service.excluir_cliente(5)

        self.assertIn("Não é permitido excluir o cliente 'Cliente Com Pedidos'", str(ctx.exception))
        self.assertIn("3 pedido(s) vinculados", str(ctx.exception))
        mock_repo.excluir.assert_not_called()

    def test_service_permite_exclusao_de_cliente_sem_pedidos(self):
        mock_repo = MagicMock()
        cliente = Cliente(id=6, nome="Cliente Sem Pedidos", email="limpo@mail.com", cpf="12345678909")
        mock_repo.buscar_por_id.return_value = cliente
        mock_repo.contar_pedidos_cliente.return_value = 0

        service = ClienteService(cliente_repo=mock_repo)
        res = service.excluir_cliente(6)
        self.assertIn("excluído com sucesso", res["mensagem"])
        mock_repo.excluir.assert_called_once_with(6)

    # 7. HISTÓRICO DE PEDIDOS ASSOCIADOS AO CLIENTE
    def test_service_obter_cliente_com_pedidos(self):
        mock_repo = MagicMock()
        cliente = Cliente(id=1, nome="Ana Clara", email="ana@mail.com", cpf="12345678909")
        mock_repo.buscar_por_id.return_value = cliente
        mock_repo.listar_pedidos_cliente.return_value = [
            {
                "id": 101,
                "numero_pedido": "PED-0101",
                "status": "Entregue",
                "status_pagamento": "Confirmado",
                "valor_total": 850.00,
                "data_pedido": "2026-11-20 14:00:00"
            }
        ]

        service = ClienteService(cliente_repo=mock_repo)
        dados = service.obter_cliente(1, incluir_pedidos=True)

        self.assertEqual(dados["nome"], "Ana Clara")
        self.assertEqual(dados["total_pedidos"], 1)
        self.assertEqual(len(dados["pedidos"]), 1)
        self.assertEqual(dados["pedidos"][0]["numero_pedido"], "PED-0101")

    # 8. TESTE DE ROTAS HTTP DA API (/api/clientes)
    def test_rota_api_clientes_crud_completo(self):
        with self.client.session_transaction() as sess:
            sess['usuario_id'] = 3
            sess['usuario_perfil'] = 'Vendas'
            sess['usuario_nome'] = 'Vendedor'

        # Teste GET /api/clientes com busca
        with patch('app.cliente_service.listar_clientes') as mock_list:
            mock_list.return_value = [{'id': 1, 'nome': 'Teste', 'cpf': '12345678909'}]
            res = self.client.get('/api/clientes?busca=Teste')
            self.assertEqual(res.status_code, 200)
            mock_list.assert_called_with(busca='Teste')

        # Teste POST /api/clientes com CPF inválido
        res_post_invalido = self.client.post('/api/clientes', json={
            'nome': 'Nome',
            'email': 'email@valido.com',
            'cpf': '000.000.000-00'
        })
        self.assertEqual(res_post_invalido.status_code, 400)
        self.assertIn("sequência de números repetidos", res_post_invalido.get_json()['erro'])

if __name__ == '__main__':
    unittest.main()
