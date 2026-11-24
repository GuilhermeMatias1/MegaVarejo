# 🛒 ERP Acadêmico - MegaVarejo S.A.

Sistema Integrado de Gestão Empresarial (ERP) com controle de estoque avançado (**Kardex / Auditoria**), regras de negócio comerciais, autenticação com sessões protegidas, controle de acesso baseado em papéis (**RBAC - Role-Based Access Control**) e arquitetura orientada a objetos (**POO**).

---

## 📑 Sumário
1. [Visão Geral e Arquitetura](#-visão-geral-e-arquitetura)
2. [Módulos do Sistema](#-módulos-do-sistema)
3. [Módulo Estoque (Reformulado)](#-módulo-estoque-reformulado)
4. [Controle de Acesso e Matriz RBAC](#-controle-de-acesso-e-matriz-rbac)
5. [Estrutura do Banco de Dados](#-estrutura-do-banco-de-dados)
6. [Credenciais de Demonstração](#-credenciais-de-demonstração)
7. [Instalação e Execução Local](#-instalação-e-execução-local)
8. [Hospedagem na Nuvem (Render / Railway)](#-hospedagem-na-nuvem-render--railway)
9. [Testes Automatizados](#-testes-automatizados)

---

## 🏗️ Visão Geral e Arquitetura

O sistema adota uma arquitetura em camadas orientada a objetos, sem frameworks pesados ou ORMs de terceiros:

- **Frontend:** HTML5, CSS3 responsivo e JavaScript puro (Vanilla JS).
- **Backend:** Python com Flask estruturado em **Models**, **Repositories**, **Services** e **Controllers**.
- **Servidor WSGI:** Gunicorn em produção.
- **Banco de Dados:** **MySQL** via `PyMySQL` com consultas SQL diretas, locks transacionais (`FOR UPDATE`) e controle de concorrência.
- **Segurança:** Senhas com hash `scrypt` (`werkzeug.security`) e sessões `HttpOnly` com cookies protegidos.

---

## 📦 Módulos do Sistema

1. **📊 Dashboard Corporativo:** Total de produtos, pedidos e faturamento consolidado.
2. **📦 Estoque (Reformulado):** Gestão de catálogo, saldo físico, entradas, saídas, ajustes de inventário e auditoria.
3. **🛒 Pedidos:** Criação de pedidos com baixa atômica de estoque e registro automático de saída no Kardex.
4. **👥 Clientes:** Cadastro e gestão de clientes para o funil comercial.
5. **🔐 Usuários (Admin):** Gestão de colaboradores com perfis de acesso e ativação/desativação.

---

## 📦 Módulo Estoque (Reformulado)

A aba **Produtos** foi reformulada para o módulo completo de **Estoque** sem criar abas secundárias, reaproveitando integralmente os dados e cadastros existentes:

### 1. Indicadores (Dashboard de Estoque)
- Total de produtos cadastrados.
- Total de unidades físicas disponíveis no almoxarifado.
- Alerta em tempo real de produtos com **Estoque Baixo** ou **Zerado**.

### 2. Consulta de Estoque e Pesquisa
- Listagem com Código/SKU, Nome, Categoria, Preço, Saldo Disponível, Estoque Mínimo e Status.
- Campo de busca instantâneo com filtragem por nome, código ou categoria.
- Destaque visual em vermelho para itens em nível crítico.

### 3. Entradas e Saídas Manuais
- Registro de entradas (compras, devoluções) e saídas manuais (consumo interno, perdas).
- Informação obrigatória de quantidade, motivo e responsável da sessão.
- **Validação de Domínio:** Bloqueia qualquer saída superior ao saldo disponível.

### 4. Ajustes de Inventário
- Permite corrigir a contagem física do estoque após auditoria ou balanço.
- Exige justificativa obrigatória e armazena o saldo anterior e o novo saldo.

### 5. Histórico de Movimentações (Kardex de Auditoria)
- Registro cronológico imutável de todas as entradas, saídas (incluindo vendas por pedidos) e ajustes.
- Exibe data/hora, produto, tipo, quantidade, saldo anterior, novo saldo, motivo e responsável.

### 6. Relatórios
- Listagem filtrada de produtos críticos (estoque baixo ou zerado).
- Ranking dos produtos com maior volume e frequência de movimentações.

### 7. Regras Específicas do Perfil Estoquista
- O operador com perfil **Estoque** tem acesso exclusivo ao Dashboard e Estoque.
- **Restrições de Segurança:** O Estoquista não pode alterar preços de produtos, excluir cadastros ou acessar dados financeiros de vendas e administração de usuários.

---

## 🛡️ Controle de Acesso e Matriz RBAC

| Perfil | Dashboard | Estoque | Pedidos | Clientes | Usuários (Admin) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Administrador** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Estoque** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Vendas** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Gerência** | ✅ | ✅ | ✅ | ✅ | ❌ |

---

## 🔑 Credenciais de Demonstração

> **Senha padrão para todos os perfis:** `admin123`

- **Administrador:** `admin@megavarejo.com`
- **Estoque:** `estoque@megavarejo.com`
- **Vendas:** `vendas@megavarejo.com`
- **Gerência:** `gerencia@megavarejo.com`

---

## 🧪 Testes Automatizados

O sistema conta com 5 suítes de testes unitários automatizados cobrindo todas as camadas:

```bash
# 1. Testes do Módulo de Estoque (Entradas, Saídas, Ajustes e Permissões)
python test_estoque.py

# 2. Testes dos 4 Pilares da POO (Encapsulamento, Abstração, Herança e Polimorfismo)
python test_poo.py

# 3. Testes de Autenticação e RBAC
python test_rbac.py

# 4. Testes de Formatação de Datas Brasileiras
python test_dates.py

# 5. Testes de Configuração de Produção (Railway / Render)
python test_production.py
```

**Resultado consolidado:** 28 testes executados com 100% de sucesso.
