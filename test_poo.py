"""
Testes específicos para validar os 4 pilares da POO no MegaVarejo ERP:
1. Encapsulamento
2. Abstração
3. Herança
4. Polimorfismo
"""

import unittest
from models.produto import Produto
from models.pedido import Pedido, ItemPedido
from models.cliente import Cliente
from models.usuario import (
    Usuario, Administrador, Estoquista, Vendedor, Gerente, UsuarioFactory
)
from repositories.base_repository import BaseRepository
from repositories.produto_repository import ProdutoRepository

class TestPOOPilares(unittest.TestCase):

    # ---------------------------------------------------------
    # 1. PILAR: ENCAPSULAMENTO
    # ---------------------------------------------------------
    def test_encapsulamento_produto(self):
        """Valida que Produto protege seus atributos com getters/setters e regras de negócio."""
        prod = Produto(nome="Teclado Gamer", preco=250.00, estoque=10)

        # Atributos protegidos
        self.assertEqual(prod.nome, "Teclado Gamer")
        self.assertEqual(prod.preco, 250.00)
        self.assertEqual(prod.estoque, 10)

        # Regra de negócio: não aceita preço negativo
        with self.assertRaises(ValueError):
            prod.preco = -50.0

        # Regra de negócio: não aceita estoque negativo
        with self.assertRaises(ValueError):
            prod.estoque = -2

        # Regra de negócio: débito de estoque consistente
        self.assertTrue(prod.possui_estoque(5))
        prod.debitar_estoque(4)
        self.assertEqual(prod.estoque, 6)

        with self.assertRaises(ValueError):
            prod.debitar_estoque(10) # Acima do estoque atual (6)

    def test_encapsulamento_pedido_calculo_total(self):
        """Valida que Pedido calcula seu valor total automaticamente através da agregação de seus itens."""
        pedido = Pedido(status="Concluído")
        item1 = ItemPedido(produto_id=1, produto_nome="Mouse", quantidade=2, preco_unitario=50.00)
        item2 = ItemPedido(produto_id=2, produto_nome="Teclado", quantidade=1, preco_unitario=150.00)

        pedido.adicionar_item(item1)
        pedido.adicionar_item(item2)

        self.assertEqual(item1.subtotal, 100.00)
        self.assertEqual(item2.subtotal, 150.00)
        self.assertEqual(pedido.valor_total, 250.00)

    # ---------------------------------------------------------
    # 2. PILAR: ABSTRAÇÃO
    # ---------------------------------------------------------
    def test_abstracao_usuario_e_repositorio(self):
        """Valida que classes abstratas definem contratos e não podem ser instanciadas diretamente."""
        # Usuario é ABC com método abstrato 'pode_acessar'
        with self.assertRaises(TypeError):
            Usuario("Nome", "email@teste.com", 1, "Admin")

        # BaseRepository é ABC
        with self.assertRaises(TypeError):
            BaseRepository()

        # ProdutoRepository é uma implementação concreta de BaseRepository
        self.assertTrue(issubclass(ProdutoRepository, BaseRepository))

    # ---------------------------------------------------------
    # 3. PILAR: HERANÇA
    # ---------------------------------------------------------
    def test_heranca_usuarios(self):
        """Valida a hierarquia de herança a partir da classe base Usuario."""
        admin = Administrador("Admin", "admin@teste.com")
        estoque = Estoquista("Estoquista", "estoque@teste.com")
        vendedor = Vendedor("Vendedor", "vendas@teste.com")
        gerente = Gerente("Gerente", "gerente@teste.com")

        self.assertIsInstance(admin, Usuario)
        self.assertIsInstance(estoque, Usuario)
        self.assertIsInstance(vendedor, Usuario)
        self.assertIsInstance(gerente, Usuario)

        self.assertTrue(issubclass(Administrador, Usuario))
        self.assertTrue(issubclass(Estoquista, Usuario))
        self.assertTrue(issubclass(Vendedor, Usuario))
        self.assertTrue(issubclass(Gerente, Usuario))

    # ---------------------------------------------------------
    # 4. PILAR: POLIMORFISMO
    # ---------------------------------------------------------
    def test_polimorfismo_permissao_acesso(self):
        """
        Valida que cada especialização de Usuario responde de forma polimórfica
        ao método 'pode_acessar(modulo)'.
        """
        admin = UsuarioFactory.criar_usuario("Administrador", "Admin", "admin@teste.com")
        estoque = UsuarioFactory.criar_usuario("Estoque", "Estoquista", "estoque@teste.com")
        vendas = UsuarioFactory.criar_usuario("Vendas", "Vendedor", "vendas@teste.com")
        gerencia = UsuarioFactory.criar_usuario("Gerência", "Gerente", "gerente@teste.com")

        usuarios = [admin, estoque, vendas, gerencia]

        # Invocação polimórfica em lista de objetos Usuario:
        # Módulo 'usuarios' (administração) só pode ser acessado pelo Administrador
        permissoes_modulo_usuarios = [u.pode_acessar('usuarios') for u in usuarios]
        self.assertEqual(permissoes_modulo_usuarios, [True, False, False, False])

        # Módulo 'pedidos' pode ser acessado por Administrador, Vendas e Gerência, mas NÃO por Estoque
        permissoes_modulo_pedidos = [u.pode_acessar('pedidos') for u in usuarios]
        self.assertEqual(permissoes_modulo_pedidos, [True, False, True, True])

        # Módulo 'dashboard' e 'produtos' são acessíveis por todos
        for u in usuarios:
            self.assertTrue(u.pode_acessar('dashboard'))
            self.assertTrue(u.pode_acessar('produtos'))

if __name__ == '__main__':
    unittest.main()
