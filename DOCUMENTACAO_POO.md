# 🎓 Documentação Acadêmica: Refatoração para Programação Orientada a Objetos (POO)
**Projeto:** ERP MegaVarejo S.A.  
**Disciplina:** Programação Orientada a Objetos / Engenharia de Software  

---

## 1. Como a Arquitetura Anterior Funcionava

Na versão procedural inicial:
- O arquivo `app.py` centralizava praticamente todas as responsabilidades do sistema: roteamento HTTP, autenticação de sessão, validação de entradas, consultas SQL diretas com strings concatenadas ou formatadas, regras de negócio de estoque e lógica de autorização RBAC baseada em dicionários e conjuntos primitivos (`dict` e `set`).
- A manipulação de dados utilizava dicionários brutos retornados pelo cursor do `PyMySQL` (`DictCursor`), sem tipagem ou encapsulamento de comportamentos.
- Alterações em regras de negócio (como cálculo do valor total de pedidos ou validação de estoque) exigiam intervenção direta nas rotas Flask, ferindo os princípios de Responsabilidade Única (SRP) e Separação de Preocupações (SoC).

---

## 2. Como a Nova Arquitetura foi Organizada

A nova arquitetura adota o padrão em camadas desacopladas (**Layered Architecture / MVC adaptado para APIs**):

```text
erp_megavarejo/
├── models/             <- Camada de Domínio (Entidades e Regras de Negócio)
│   ├── produto.py      <- Classe Produto (Encapsulamento de estoque e preço)
│   ├── pedido.py       <- Classes Pedido e ItemPedido (Cálculo de subtotais e agregações)
│   ├── cliente.py      <- Classe Cliente (Normalização e integridade)
│   └── usuario.py      <- Hierarquia Usuario, Administrador, Estoquista, Vendedor, Gerente
├── repositories/       <- Camada de Persistência (Padrão Repository)
│   ├── base_repository.py    <- Interface Abstrata BaseRepository (ABC)
│   ├── produto_repository.py <- CRUD e SQL direto de produtos
│   ├── pedido_repository.py  <- Operações transacionais e joins de pedidos e itens
│   ├── cliente_repository.py <- Persistência e listagem de clientes
│   └── usuario_repository.py <- Mapeamento relacional e Factory de usuários
├── services/           <- Camada de Serviços (Casos de Uso)
│   ├── produto_service.py    <- Fluxos e validações de produtos
│   ├── pedido_service.py     <- Criação transacional atômica com baixa de estoque
│   ├── cliente_service.py    <- Operações com clientes
│   ├── dashboard_service.py  <- Consolidação de métricas e indicadores
│   └── usuario_service.py    <- Autenticação, hash e administração de perfis
├── controllers/        <- Interceptadores e Segurança
│   └── auth_middleware.py    <- Decoradores @login_required e @require_permission (Polimorfismo)
├── database/           <- Infraestrutura de Banco de Dados
│   └── connection.py         <- Gerenciador de conexões MySQL / Pool / SSL
├── templates/ e static/<- Apresentação (HTML, CSS e JavaScript puro mantidos intactos)
└── app.py              <- Ponto de entrada Flask (Apenas orquestração HTTP e retorno JSON)
```

---

## 3. Classes Criadas e suas Responsabilidades

| Camada | Classe | Arquivo | Responsabilidade |
| :--- | :--- | :--- | :--- |
| **Domínio** | `Produto` | `models/produto.py` | Controla o estado de um produto, validando preços, estoques e realizando débitos consistentes. |
| **Domínio** | `ItemPedido` | `models/pedido.py` | Representa a associação de um produto ao pedido, calculando seu subtotal dinamicamente. |
| **Domínio** | `Pedido` | `models/pedido.py` | Agrega instâncias de `ItemPedido`, calcula o valor total e gerencia o ciclo de vida do status. |
| **Domínio** | `Cliente` | `models/cliente.py` | Mantém os dados cadastrais do cliente comercial com normalização. |
| **Domínio** | `Usuario` (ABC) | `models/usuario.py` | Classe base abstrata para colaboradores, controlando hash de senhas e contrato de autorização. |
| **Domínio** | `Administrador` | `models/usuario.py` | Especialização com acesso irrestrito ao sistema e administração de usuários. |
| **Domínio** | `Estoquista` | `models/usuario.py` | Especialização com acesso restrito ao Dashboard e Produtos. |
| **Domínio** | `Vendedor` | `models/usuario.py` | Especialização com acesso ao Dashboard, Produtos, Pedidos e Clientes. |
| **Domínio** | `Gerente` | `models/usuario.py` | Especialização com acesso a todos os módulos operacionais (sem gestão de usuários). |
| **Criação** | `UsuarioFactory` | `models/usuario.py` | Fábrica responsável por instanciar a especialização correta conforme o perfil. |
| **Persistência** | `BaseRepository` (ABC) | `repositories/base_repository.py` | Define a interface padrão para os repositórios do sistema. |
| **Persistência** | `ProdutoRepository` | `repositories/produto_repository.py` | Executa consultas SQL diretas, persistência e bloqueio com lock (`FOR UPDATE`). |
| **Persistência** | `PedidoRepository` | `repositories/pedido_repository.py` | Executa queries SQL diretas de pedidos, itens e métricas financeiras. |
| **Persistência** | `ClienteRepository` | `repositories/cliente_repository.py` | Executa inserções e consultas SQL de clientes. |
| **Persistência** | `UsuarioRepository` | `repositories/usuario_repository.py` | Busca e persiste usuários mapeando-os para objetos do domínio via `UsuarioFactory`. |
| **Serviço** | `ProdutoService` | `services/produto_service.py` | Coordena regras de negócio de produtos. |
| **Serviço** | `PedidoService` | `services/pedido_service.py` | Executa o fluxo de compra com validação de saldo e transação atômica. |
| **Serviço** | `ClienteService` | `services/cliente_service.py` | Coordena regras de negócio de clientes. |
| **Serviço** | `DashboardService` | `services/dashboard_service.py` | Agrega indicadores operacionais do dashboard. |
| **Serviço** | `UsuarioService` | `services/usuario_service.py` | Gerencia autenticação, verificação de hash e manutenção de contas. |
| **Conexão** | `DatabaseConnection` | `database/connection.py` | Centraliza conexão com o MySQL e parseamento de strings de nuvem (`DATABASE_URL`). |

---

## 4. Onde o Encapsulamento foi Aplicado

O encapsulamento foi aplicado para proteger o estado interno dos objetos através de atributos privados (`_atributo`) combinados com decorators `@property` e `@setter`, impedindo estados inválidos e garantindo consistência.

### Exemplos Reais no Código:

1. **Validação de Preço e Quantidade em `Produto`:**
   - **Arquivo:** [models/produto.py](file:///C:/Users/guilherme/.gemini/antigravity/scratch/erp_megavarejo/models/produto.py)
   - **Classe:** `Produto`
   - **Métodos:** `@preco.setter`, `@estoque.setter`, `debitar_estoque(quantidade)`
   ```python
   @preco.setter
   def preco(self, valor: float):
       val = float(valor)
       if val < 0:
           raise ValueError("O preço do produto não pode ser negativo.")
       self._preco = val

   def debitar_estoque(self, quantidade: int):
       if quantidade <= 0:
           raise ValueError("A quantidade a debitar deve ser maior que zero.")
       if not self.possui_estoque(quantidade):
           raise ValueError(f"Estoque insuficiente para o produto '{self._nome}'.")
       self._estoque -= quantidade
   ```

2. **Cálculo Automático do Total em `Pedido`:**
   - **Arquivo:** [models/pedido.py](file:///C:/Users/guilherme/.gemini/antigravity/scratch/erp_megavarejo/models/pedido.py)
   - **Classe:** `Pedido`
   - **Método:** `@property def valor_total(self) -> float`
   ```python
   @property
   def valor_total(self) -> float:
       if self._itens:
           return round(sum(item.subtotal for item in self._itens), 2)
       return self._valor_total_informado
   ```

3. **Proteção e Hash de Senha em `Usuario`:**
   - **Arquivo:** [models/usuario.py](file:///C:/Users/guilherme/.gemini/antigravity/scratch/erp_megavarejo/models/usuario.py)
   - **Classe:** `Usuario`
   - **Métodos:** `definir_senha(senha)`, `verificar_senha(senha)`
   ```python
   def definir_senha(self, senha: str):
       if not senha or len(str(senha).strip()) < 6:
           raise ValueError("A senha deve conter no mínimo 6 caracteres.")
       self._senha_hash = generate_password_hash(str(senha).strip())
   ```

---

## 5. Onde a Abstração foi Aplicada

A abstração oculta complexidades de persistência e estabelece contratos estritos utilizando o módulo nativo `abc` (`ABC` e `@abstractmethod`).

### Exemplos Reais no Código:

1. **Contrato de Autorização em `Usuario`:**
   - **Arquivo:** [models/usuario.py](file:///C:/Users/guilherme/.gemini/antigravity/scratch/erp_megavarejo/models/usuario.py)
   - **Classe:** `Usuario(ABC)`
   - **Métodos Abstratos:** `pode_acessar(modulo)`, `obter_permissoes()`
   ```python
   class Usuario(ABC):
       @abstractmethod
       def pode_acessar(self, modulo: str) -> bool:
           pass

       @abstractmethod
       def obter_permissoes(self) -> list:
           pass
   ```
   *Efeito:* A classe base não pode ser instanciada diretamente sem que uma especialização implemente as permissões.

2. **Contrato de Persistência em `BaseRepository`:**
   - **Arquivo:** [repositories/base_repository.py](file:///C:/Users/guilherme/.gemini/antigravity/scratch/erp_megavarejo/repositories/base_repository.py)
   - **Classe:** `BaseRepository(ABC)`
   - **Métodos Abstratos:** `buscar_por_id(id)`, `listar_todos()`
   ```python
   class BaseRepository(ABC):
       @abstractmethod
       def buscar_por_id(self, id: int):
           pass

       @abstractmethod
       def listar_todos(self) -> list:
           pass
   ```
   *Efeito:* Define a interface para repositórios concretos como `ProdutoRepository`, `PedidoRepository` e `UsuarioRepository`.

---

## 6. Onde a Herança foi Aplicada

A herança estabelece relações ontológicas reais do domínio de segurança e acesso corporativo ("É um").

### Exemplos Reais no Código:
- **Arquivo:** [models/usuario.py](file:///C:/Users/guilherme/.gemini/antigravity/scratch/erp_megavarejo/models/usuario.py)
- **Superclasse:** `Usuario`
- **Subclasses Especializadas:**
  - `Administrador(Usuario)`
  - `Estoquista(Usuario)`
  - `Vendedor(Usuario)`
  - `Gerente(Usuario)`

```python
class Administrador(Usuario):
    PERMISSOES = {'dashboard', 'produtos', 'pedidos', 'clientes', 'usuarios'}

    def __init__(self, nome, email, senha_hash=None, ativo=True, criado_em=None, id=None, perfil_id=1):
        super().__init__(nome, email, perfil_id, "Administrador", senha_hash, ativo, criado_em, id)

class Estoquista(Usuario):
    PERMISSOES = {'dashboard', 'produtos'}

    def __init__(self, nome, email, senha_hash=None, ativo=True, criado_em=None, id=None, perfil_id=2):
        super().__init__(nome, email, perfil_id, "Estoque", senha_hash, ativo, criado_em, id)
```
*Herança de atributos e comportamentos:* Todas as subclasses herdam automaticamente `nome`, `email`, `senha_hash`, `ativo`, `definir_senha()` e `verificar_senha()`.

---

## 7. Onde o Polimorfismo foi Aplicado

O polimorfismo permite que diferentes especializações de `Usuario` respondam à mesma chamada de método (`pode_acessar` e `obter_permissoes`), mas executem lógicas de autorização específicas para cada papel.

### Exemplos Reais no Código:

1. **Implementações Polimórficas de `pode_acessar`:**
   - **Arquivo:** [models/usuario.py](file:///C:/Users/guilherme/.gemini/antigravity/scratch/erp_megavarejo/models/usuario.py)
   ```python
   # Na classe Administrador:
   def pode_acessar(self, modulo: str) -> bool:
       return modulo in {'dashboard', 'produtos', 'pedidos', 'clientes', 'usuarios'}

   # Na classe Estoquista:
   def pode_acessar(self, modulo: str) -> bool:
       return modulo in {'dashboard', 'produtos'}

   # Na classe Vendedor:
   def pode_acessar(self, modulo: str) -> bool:
       return modulo in {'dashboard', 'produtos', 'pedidos', 'clientes'}
   ```

2. **Consumo Polimórfico no Middleware RBAC:**
   - **Arquivo:** [controllers/auth_middleware.py](file:///C:/Users/guilherme/.gemini/antigravity/scratch/erp_megavarejo/controllers/auth_middleware.py)
   - **Função:** `require_permission(modulo)`
   ```python
   # O middleware não sabe se o objeto é um Administrador, Estoquista ou Vendedor.
   # Ele apenas sabe que se trata de um 'Usuario' e chama o método polimórfico:
   usuario_obj = UsuarioFactory.criar_usuario(perfil_nome, nome_sessao, email_sessao, id=sess_id)

   if not usuario_obj.pode_acessar(modulo):
       return jsonify({'erro': f'Acesso negado. O perfil [{perfil_nome}] não tem permissão para o módulo [{modulo}].'}), 403
   ```

3. **Consumo Polimórfico nas Rotas de Login e Perfil:**
   - **Arquivo:** [app.py](file:///C:/Users/guilherme/.gemini/antigravity/scratch/erp_megavarejo/app.py)
   - **Rotas:** `/api/auth/login` e `/api/auth/me`
   ```python
   # Invocação polimórfica que retorna as permissões do perfil concreto do usuário logado:
   permissoes = usuario_obj.obter_permissoes()
   ```

---

## 8. Verificação e Testes Automatizados

A refatoração foi validada por 4 baterias de testes automatizados com 100% de aprovação:

```bash
# 1. Validação dos 4 Pilares da POO (Encapsulamento, Abstração, Herança e Polimorfismo)
python test_poo.py

# 2. Validação de Autenticação e Restrições de Acesso RBAC
python test_rbac.py

# 3. Validação de Formatação de Datas no Padrão Brasileiro
python test_dates.py

# 4. Validação de Configuração para Hospedagem em Produção (Render / Railway)
python test_production.py
```

**Resultado consolidado dos testes:**
```text
Ran 5 tests in 0.000s - OK (test_poo.py)
Ran 7 tests in 1.344s - OK (test_rbac.py)
Ran 5 tests in 0.097s - OK (test_dates.py)
Ran 4 tests in 0.117s - OK (test_production.py)
Total: 21 testes executados, 0 falhas, 0 erros.
```
