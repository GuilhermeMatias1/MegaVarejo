# MegaVarejo S.A. — Sistema ERP

Sistema de Planejamento de Recursos Empresariais (ERP) desenvolvido para a MegaVarejo S.A., uma empresa fictícia do setor varejista que busca integrar suas operações físicas e digitais.

O projeto centraliza informações e processos de diferentes setores da empresa, permitindo o controle de clientes, produtos, estoque, pedidos, fornecedores, entregas e operações financeiras.

Sobre o projeto

A expansão da MegaVarejo S.A. para o comércio eletrônico trouxe desafios para a gestão da empresa:

- Divergências entre o estoque físico e as vendas online.
- Dificuldade para acompanhar pedidos e entregas.
- Falta de integração entre vendas e financeiro.
- Controle limitado de fornecedores e compras.
- Informações distribuídas em diferentes sistemas e planilhas.

O ERP foi desenvolvido para reduzir esses problemas por meio de uma aplicação web integrada.

Funcionalidades

Gestão de usuários e permissões

- Autenticação de usuários.
- Controle de acesso por perfil.
- Permissões específicas para cada setor.
- Proteção de rotas e operações.

Gestão de clientes

- Cadastro e consulta de clientes.
- Validação de CPF.
- Registro de informações de contato e endereço.
- Associação de clientes aos pedidos.

Gestão de produtos e estoque

- Cadastro e consulta de produtos.
- Controle de quantidades disponíveis.
- Reserva de estoque para pedidos.
- Acompanhamento de movimentações.
- Identificação de produtos com estoque baixo.

Gestão de pedidos

- Criação e consulta de pedidos.
- Associação de clientes e produtos.
- Controle de status dos pedidos.
- Atualização de informações de pagamento.
- Integração com estoque e financeiro.

Gestão financeira

- Controle de contas a pagar.
- Controle de contas a receber.
- Registro de pagamentos.
- Fluxo de caixa com entradas e saídas.
- Consulta de indicadores financeiros.

Dashboard gerencial

- Indicadores de vendas.
- Acompanhamento de pedidos.
- Resumo financeiro.
- Alertas operacionais.
- Informações para apoiar decisões gerenciais.

O acesso ao dashboard gerencial é restrito aos perfis autorizados.

Tecnologias utilizadas

Tecnologia| Finalidade
Python| Linguagem principal
Flask| Framework web e API
MySQL| Banco de dados relacional
PyMySQL| Comunicação com o banco
HTML5| Estrutura das páginas
CSS3| Estilização
JavaScript| Interatividade no frontend
Gunicorn| Servidor WSGI em produção
Docker| Empacotamento da aplicação
Railway| Hospedagem e deploy
