// Estado do ERP MegaVarejo S.A.
let usuarioAtual = null;
let produtosCache = [];
let itensNovoPedido = [];
let perfisCache = [];
let usuariosCache = [];

// Formatar moeda brasileira (BRL)
function formatarMoeda(valor) {
    return Number(valor).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

// Formatar data no padrão brasileiro (DD/MM/AAAA ou DD/MM/AAAA HH:MM)
function formatarDataBR(valor, incluirHora = true) {
    if (!valor) return '-';

    // Se já estiver no formato brasileiro DD/MM/AAAA ou DD/MM/AAAA HH:MM
    const regexBR = /^\d{2}\/\d{2}\/\d{4}( \d{2}:\d{2}(:\d{2})?)?$/;
    if (typeof valor === 'string' && regexBR.test(valor.trim())) {
        const partes = valor.trim().split(' ');
        if (!incluirHora) return partes[0];
        if (partes.length > 1) {
            const horaMin = partes[1].substring(0, 5);
            return `${partes[0]} ${horaMin}`;
        }
        return partes[0];
    }

    const d = new Date(valor);
    if (isNaN(d.getTime())) return String(valor);

    const dia = String(d.getDate()).padStart(2, '0');
    const mes = String(d.getMonth() + 1).padStart(2, '0');
    const ano = d.getFullYear();

    if (!incluirHora) {
        return `${dia}/${mes}/${ano}`;
    }

    const horas = String(d.getHours()).padStart(2, '0');
    const minutos = String(d.getMinutes()).padStart(2, '0');
    return `${dia}/${mes}/${ano} ${horas}:${minutos}`;
}

// Exibir alertas amigáveis na interface
function mostrarAlerta(mensagem, tipo = 'sucesso') {
    const alerta = document.getElementById('alerta');
    alerta.textContent = mensagem;
    alerta.className = `alerta ${tipo}`;
    alerta.style.display = 'block';

    setTimeout(() => {
        alerta.style.display = 'none';
    }, 4500);
}

// ----------------------------------------------------
// CONTROLE DE SESSÃO E RBAC
// ----------------------------------------------------
async function checarAutenticacao() {
    try {
        const res = await fetch('/api/auth/me');
        if (!res.ok) {
            window.location.href = '/login';
            return;
        }

        const data = await res.json();
        usuarioAtual = data.usuario;

        // Atualiza cabeçalho do sidebar
        document.getElementById('sidebar-user-name').textContent = usuarioAtual.nome;
        document.getElementById('sidebar-user-role').textContent = usuarioAtual.perfil;
        document.getElementById('sidebar-avatar').textContent = (usuarioAtual.nome || 'U').charAt(0).toUpperCase();

        // Configura visibilidade do menu lateral com base no RBAC
        aplicarPermissoesMenu(usuarioAtual.permissoes);

        // Abre o primeiro módulo permitido (preferencialmente dashboard)
        if (usuarioAtual.permissoes.includes('dashboard')) {
            navegarPara('dashboard');
        } else if (usuarioAtual.permissoes.length > 0) {
            navegarPara(usuarioAtual.permissoes[0]);
        }
    } catch (err) {
        window.location.href = '/login';
    }
}

function aplicarPermissoesMenu(permissoes) {
    const modulos = ['dashboard', 'produtos', 'pedidos', 'clientes', 'usuarios'];
    modulos.forEach(mod => {
        const btn = document.getElementById(`nav-btn-${mod}`);
        if (btn) {
            if (permissoes.includes(mod)) {
                btn.style.display = 'flex';
            } else {
                btn.style.display = 'none';
            }
        }
    });
}

async function fazerLogout() {
    if (!confirm('Deseja realmente sair do sistema?')) return;
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        window.location.href = '/login';
    } catch (err) {
        window.location.href = '/login';
    }
}

// Navegação entre os módulos com validação de permissão
function navegarPara(moduloId) {
    // Compatibilidade: se chamado 'estoque', mapeia para o container de tela 'produtos'
    const containerId = moduloId === 'estoque' ? 'produtos' : moduloId;

    if (usuarioAtual && !usuarioAtual.permissoes.includes(moduloId) && !usuarioAtual.permissoes.includes(containerId)) {
        mostrarAlerta(`Você não tem permissão para acessar o módulo ${moduloId}.`, 'erro');
        return;
    }

    // Esconde todos os módulos
    document.querySelectorAll('.modulo').forEach(sec => sec.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));

    // Mostra o selecionado
    const alvo = document.getElementById(`modulo-${containerId}`);
    if (alvo) alvo.classList.add('active');

    // Destaca o botão correspondente no menu
    const btnAtivo = document.getElementById(`nav-btn-${containerId}`);
    if (btnAtivo) btnAtivo.classList.add('active');

    // Carregar dados frescos da tela
    if (containerId === 'dashboard') carregarDashboard();
    if (containerId === 'produtos') carregarModuloEstoque();
    if (containerId === 'pedidos') {
        carregarProdutosParaPedido();
        carregarPedidos();
    }
    if (containerId === 'clientes') carregarClientes();
    if (containerId === 'usuarios') {
        carregarPerfisParaSelect();
        carregarUsuarios();
    }
}

// ==========================================
// 1. MÓDULO DASHBOARD
// ==========================================
async function carregarDashboard() {
    try {
        const res = await fetch('/api/dashboard');
        if (res.status === 401 || res.status === 403) {
            tratarErroAcesso(res);
            return;
        }
        const dados = await res.json();

        document.getElementById('dash-produtos').textContent = dados.total_produtos || 0;
        document.getElementById('dash-pedidos').textContent = dados.total_pedidos || 0;
        document.getElementById('dash-vendas').textContent = formatarMoeda(dados.total_vendas || 0);
    } catch (err) {
        mostrarAlerta('Erro ao carregar indicadores do dashboard.', 'erro');
    }
}

// ==========================================
// 2. MÓDULO ESTOQUE (PRODUTOS, MOVIMENTAÇÕES E AJUSTES)
// ==========================================

function alternarAbaEstoque(subAbaId) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.sub-estoque-content').forEach(content => content.classList.remove('active'));

    const btnSelecionado = event ? event.target : null;
    if (btnSelecionado && btnSelecionado.classList) btnSelecionado.classList.add('active');

    const container = document.getElementById(`sub-estoque-${subAbaId}`);
    if (container) container.classList.add('active');

    if (subAbaId === 'consulta') carregarProdutos();
    if (subAbaId === 'movimentacoes') popularSelectProdutosMovimentacao();
    if (subAbaId === 'ajustes') popularSelectProdutosAjuste();
    if (subAbaId === 'historico') carregarHistoricoMovimentacoes();
    if (subAbaId === 'relatorios') carregarRelatoriosEstoque();
}

async function carregarModuloEstoque() {
    await carregarResumoEstoque();
    await carregarProdutos();

    // Regra de perfil: Se for Estoquista, oculta campos de preço
    if (usuarioAtual && usuarioAtual.perfil === 'Estoque') {
        const grupoPreco = document.getElementById('grupo-prod-preco');
        if (grupoPreco) {
            const inputPreco = document.getElementById('prod-preco');
            if (inputPreco) {
                inputPreco.required = false;
                inputPreco.value = '0.00';
            }
            grupoPreco.style.display = 'none';
        }
    }
}

async function carregarResumoEstoque() {
    try {
        const res = await fetch('/api/estoque/resumo');
        if (res.status === 401 || res.status === 403) return;
        const dados = await res.json();

        document.getElementById('kpi-estoque-produtos').textContent = dados.total_produtos || 0;
        document.getElementById('kpi-estoque-unidades').textContent = dados.total_unidades || 0;
        document.getElementById('kpi-estoque-criticos').textContent = dados.total_criticos || 0;
    } catch (err) {
        console.error('Erro ao carregar resumo de estoque:', err);
    }
}

async function carregarProdutos() {
    const termoBusca = (document.getElementById('campo-busca-produto')?.value || '').trim();
    const url = termoBusca ? `/api/produtos?busca=${encodeURIComponent(termoBusca)}` : '/api/produtos';

    try {
        const res = await fetch(url);
        if (res.status === 401 || res.status === 403) {
            tratarErroAcesso(res);
            return;
        }
        const produtos = await res.json();
        produtosCache = produtos;

        const tbody = document.getElementById('tabela-produtos-corpo');
        tbody.innerHTML = '';

        if (produtos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">Nenhum produto cadastrado ou encontrado.</td></tr>';
            return;
        }

        produtos.forEach(prod => {
            const tr = document.createElement('tr');
            const isCritico = prod.status_estoque === 'Zerado' || prod.status_estoque === 'Baixo';
            if (isCritico) tr.classList.add('linha-critica');

            let badgeClass = 'badge-estoque-normal';
            if (prod.status_estoque === 'Baixo') badgeClass = 'badge-estoque-baixo';
            if (prod.status_estoque === 'Zerado') badgeClass = 'badge-estoque-zerado';

            const podeExcluir = usuarioAtual && usuarioAtual.perfil !== 'Estoque';

            tr.innerHTML = `
                <td><strong>${prod.codigo || ('#' + prod.id)}</strong></td>
                <td><strong>${prod.nome}</strong></td>
                <td>${prod.categoria || 'Geral'}</td>
                <td>${formatarMoeda(prod.preco)}</td>
                <td><span style="font-weight: 700;">${prod.estoque} un.</span></td>
                <td>${prod.estoque_minimo || 5} un.</td>
                <td><span class="status-badge ${badgeClass}">${prod.status_estoque}</span></td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="prepararEdicaoProduto(${prod.id})">Editar</button>
                    ${podeExcluir ? `<button class="btn btn-danger btn-sm" onclick="excluirProduto(${prod.id})">Excluir</button>` : ''}
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        mostrarAlerta('Erro ao listar produtos do estoque.', 'erro');
    }
}

function filtrarProdutos() {
    clearTimeout(window._timeoutBusca);
    window._timeoutBusca = setTimeout(() => {
        carregarProdutos();
    }, 250);
}

async function salvarProduto(event) {
    event.preventDefault();
    const id = document.getElementById('prod-id').value;
    const codigo = document.getElementById('prod-codigo').value.trim();
    const nome = document.getElementById('prod-nome').value.trim();
    const categoria = document.getElementById('prod-categoria').value.trim();
    const preco = parseFloat(document.getElementById('prod-preco')?.value || 0);
    const estoque = parseInt(document.getElementById('prod-estoque')?.value || 0, 10);
    const estoque_minimo = parseInt(document.getElementById('prod-estoque-minimo')?.value || 5, 10);

    const payload = { codigo, nome, categoria, preco, estoque, estoque_minimo };
    const metodo = id ? 'PUT' : 'POST';
    const url = id ? `/api/produtos/${id}` : '/api/produtos';

    try {
        const res = await fetch(url, {
            method: metodo,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) {
            mostrarAlerta(data.erro || 'Erro ao salvar produto.', 'erro');
            return;
        }

        mostrarAlerta(data.mensagem || 'Produto salvo com sucesso!');
        cancelarEdicaoProduto();
        carregarModuloEstoque();
    } catch (err) {
        mostrarAlerta('Erro de conexão ao salvar produto.', 'erro');
    }
}

function prepararEdicaoProduto(id) {
    const prod = produtosCache.find(p => p.id === id);
    if (!prod) return;

    document.getElementById('prod-id').value = prod.id;
    document.getElementById('prod-codigo').value = prod.codigo || '';
    document.getElementById('prod-nome').value = prod.nome;
    document.getElementById('prod-categoria').value = prod.categoria || 'Geral';
    if (document.getElementById('prod-preco')) document.getElementById('prod-preco').value = prod.preco;
    if (document.getElementById('prod-estoque-minimo')) document.getElementById('prod-estoque-minimo').value = prod.estoque_minimo || 5;

    // Na edição, o campo de estoque inicial fica oculto ou desabilitado para forçar entrada/saída/ajuste
    const grupoEstoque = document.getElementById('grupo-prod-estoque');
    if (grupoEstoque) grupoEstoque.style.display = 'none';

    document.getElementById('form-produto-titulo').textContent = `Editar Produto: ${prod.nome}`;
    document.getElementById('btn-salvar-produto').textContent = 'Atualizar Dados';
    document.getElementById('btn-cancelar-edicao').style.display = 'inline-block';

    // Rola suavemente até o formulário
    document.getElementById('painel-form-produto')?.scrollIntoView({ behavior: 'smooth' });
}

function cancelarEdicaoProduto() {
    document.getElementById('prod-id').value = '';
    document.getElementById('prod-codigo').value = '';
    document.getElementById('prod-nome').value = '';
    document.getElementById('prod-categoria').value = '';
    if (document.getElementById('prod-preco')) document.getElementById('prod-preco').value = '';
    if (document.getElementById('prod-estoque')) document.getElementById('prod-estoque').value = '0';
    if (document.getElementById('prod-estoque-minimo')) document.getElementById('prod-estoque-minimo').value = '5';

    const grupoEstoque = document.getElementById('grupo-prod-estoque');
    if (grupoEstoque) grupoEstoque.style.display = 'flex';

    document.getElementById('form-produto-titulo').textContent = 'Cadastrar Novo Produto';
    document.getElementById('btn-salvar-produto').textContent = 'Salvar Produto';
    document.getElementById('btn-cancelar-edicao').style.display = 'none';
}

async function excluirProduto(id) {
    if (!confirm(`Deseja realmente excluir o produto #${id}?`)) return;

    try {
        const res = await fetch(`/api/produtos/${id}`, { method: 'DELETE' });
        const data = await res.json();

        if (!res.ok) {
            mostrarAlerta(data.erro || 'Erro ao excluir produto.', 'erro');
            return;
        }

        mostrarAlerta(data.mensagem || 'Produto excluído!');
        carregarModuloEstoque();
    } catch (err) {
        mostrarAlerta('Erro de comunicação ao excluir produto.', 'erro');
    }
}

// --- SUB-MÓDULO: ENTRADAS E SAÍDAS ---

function popularSelectProdutosMovimentacao() {
    const select = document.getElementById('mov-produto-id');
    if (!select) return;
    select.innerHTML = '<option value="">-- Selecione o produto --</option>';

    produtosCache.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = `${p.codigo || ('#' + p.id)} - ${p.nome} (Saldo atual: ${p.estoque} un.)`;
        select.appendChild(opt);
    });
    atualizarInfoProdutoMovimentacao();
}

function atualizarInfoProdutoMovimentacao() {
    const prodId = parseInt(document.getElementById('mov-produto-id')?.value, 10);
    const span = document.getElementById('mov-info-saldo');
    if (!span) return;
    const prod = produtosCache.find(p => p.id === prodId);
    span.textContent = prod ? `Saldo Atual no Sistema: ${prod.estoque} un.` : 'Saldo Atual: -';
}

async function executarMovimentacao(e) {
    e.preventDefault();
    const produto_id = parseInt(document.getElementById('mov-produto-id').value, 10);
    const tipo = document.getElementById('mov-tipo').value;
    const quantidade = parseInt(document.getElementById('mov-quantidade').value, 10);
    const motivo = document.getElementById('mov-motivo').value.trim();

    if (!produto_id) {
        mostrarAlerta('Selecione um produto.', 'erro');
        return;
    }

    try {
        const res = await fetch('/api/estoque/movimentacoes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ produto_id, tipo, quantidade, motivo })
        });
        const data = await res.json();
        if (!res.ok) {
            mostrarAlerta(data.erro || 'Falha ao registrar movimentação.', 'erro');
            return;
        }

        mostrarAlerta(data.mensagem);
        document.getElementById('mov-quantidade').value = '1';
        document.getElementById('mov-motivo').value = '';
        await carregarModuloEstoque();
        popularSelectProdutosMovimentacao();
    } catch (err) {
        mostrarAlerta('Erro de conexão ao movimentar estoque.', 'erro');
    }
}

// --- SUB-MÓDULO: AJUSTES DE INVENTÁRIO ---

function popularSelectProdutosAjuste() {
    const select = document.getElementById('ajuste-produto-id');
    if (!select) return;
    select.innerHTML = '<option value="">-- Selecione o produto --</option>';

    produtosCache.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = `${p.codigo || ('#' + p.id)} - ${p.nome} (Saldo registrado: ${p.estoque} un.)`;
        select.appendChild(opt);
    });
    atualizarInfoProdutoAjuste();
}

function atualizarInfoProdutoAjuste() {
    const prodId = parseInt(document.getElementById('ajuste-produto-id')?.value, 10);
    const span = document.getElementById('ajuste-info-saldo');
    if (!span) return;
    const prod = produtosCache.find(p => p.id === prodId);
    span.textContent = prod ? `Saldo Atual no Sistema: ${prod.estoque} un.` : 'Saldo Atual no Sistema: -';
}

async function executarAjuste(e) {
    e.preventDefault();
    const produto_id = parseInt(document.getElementById('ajuste-produto-id').value, 10);
    const novo_saldo = parseInt(document.getElementById('ajuste-novo-saldo').value, 10);
    const justificativa = document.getElementById('ajuste-justificativa').value.trim();

    if (!produto_id) {
        mostrarAlerta('Selecione um produto para ajuste.', 'erro');
        return;
    }

    try {
        const res = await fetch('/api/estoque/ajustes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ produto_id, novo_saldo, justificativa })
        });
        const data = await res.json();
        if (!res.ok) {
            mostrarAlerta(data.erro || 'Falha ao registrar ajuste.', 'erro');
            return;
        }

        mostrarAlerta(data.mensagem);
        document.getElementById('ajuste-novo-saldo').value = '';
        document.getElementById('ajuste-justificativa').value = '';
        await carregarModuloEstoque();
        popularSelectProdutosAjuste();
    } catch (err) {
        mostrarAlerta('Erro de conexão ao ajustar estoque.', 'erro');
    }
}

// --- SUB-MÓDULO: HISTÓRICO DE MOVIMENTAÇÕES ---

async function carregarHistoricoMovimentacoes() {
    const tbody = document.getElementById('tabela-historico-corpo');
    tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">Carregando histórico...</td></tr>';

    try {
        const res = await fetch('/api/estoque/movimentacoes?limite=100');
        if (!res.ok) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">Erro ao carregar movimentações.</td></tr>';
            return;
        }
        const historico = await res.json();
        tbody.innerHTML = '';

        if (historico.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">Nenhuma movimentação registrada até o momento.</td></tr>';
            return;
        }

        historico.forEach(m => {
            const tr = document.createElement('tr');
            let badgeClass = 'badge-tipo-ajuste';
            if (m.tipo === 'Entrada') badgeClass = 'badge-tipo-entrada';
            if (m.tipo === 'Saída') badgeClass = 'badge-tipo-saida';

            tr.innerHTML = `
                <td>#${m.id}</td>
                <td>${m.data_formatada || m.data_movimentacao}</td>
                <td><strong>${m.produto_nome}</strong></td>
                <td><span class="status-badge ${badgeClass}">${m.tipo}</span></td>
                <td><strong>${m.quantidade} un.</strong></td>
                <td>${m.saldo_anterior} un.</td>
                <td><strong>${m.novo_saldo} un.</strong></td>
                <td>${m.motivo}</td>
                <td><small>${m.responsavel}</small></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;">Erro ao carregar dados do servidor.</td></tr>';
    }
}

// --- SUB-MÓDULO: RELATÓRIOS ---

async function carregarRelatoriosEstoque() {
    const tbodyCriticos = document.getElementById('tabela-rel-criticos');
    const tbodyMaisMov = document.getElementById('tabela-rel-mais-movimentados');

    tbodyCriticos.innerHTML = '<tr><td colspan="5" style="text-align: center;">Carregando...</td></tr>';
    tbodyMaisMov.innerHTML = '<tr><td colspan="4" style="text-align: center;">Carregando...</td></tr>';

    try {
        const [resCriticos, resMaisMov] = await Promise.all([
            fetch('/api/estoque/relatorios/criticos'),
            fetch('/api/estoque/relatorios/mais-movimentados')
        ]);

        const criticos = await resCriticos.json();
        const maisMov = await resMaisMov.json();

        // Renderiza Críticos
        tbodyCriticos.innerHTML = '';
        if (criticos.length === 0) {
            tbodyCriticos.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #166534;">Nenhum produto em nível crítico de estoque. Parabéns!</td></tr>';
        } else {
            criticos.forEach(c => {
                const tr = document.createElement('tr');
                tr.classList.add('linha-critica');
                tr.innerHTML = `
                    <td><strong>${c.codigo || ('#' + c.id)}</strong></td>
                    <td>${c.nome}</td>
                    <td><strong style="color: #dc2626;">${c.estoque} un.</strong></td>
                    <td>${c.estoque_minimo || 5} un.</td>
                    <td><span class="status-badge badge-estoque-zerado">${c.status_estoque}</span></td>
                `;
                tbodyCriticos.appendChild(tr);
            });
        }

        // Renderiza Mais Movimentados
        tbodyMaisMov.innerHTML = '';
        if (maisMov.length === 0) {
            tbodyMaisMov.innerHTML = '<tr><td colspan="4" style="text-align: center;">Nenhuma movimentação registrada ainda.</td></tr>';
        } else {
            maisMov.forEach(m => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${m.codigo || ('#' + m.id)}</strong></td>
                    <td>${m.nome}</td>
                    <td><strong>${m.total_movimentacoes} movimentações</strong></td>
                    <td>${m.total_unidades_movimentadas} unidades totais</td>
                `;
                tbodyMaisMov.appendChild(tr);
            });
        }
    } catch (err) {
        console.error('Erro ao carregar relatórios:', err);
    }
}

// ==========================================
// 3. MÓDULO PEDIDOS
// ==========================================
async function carregarProdutosParaPedido() {
    try {
        const res = await fetch('/api/produtos');
        if (!res.ok) return;
        produtosCache = await res.json();

        const select = document.getElementById('pedido-produto-select');
        select.innerHTML = '<option value="">-- Selecione um produto --</option>';

        produtosCache.forEach(prod => {
            const opt = document.createElement('option');
            opt.value = prod.id;
            opt.textContent = `${prod.nome} - ${formatarMoeda(prod.preco)} (Estoque: ${prod.estoque})`;
            if (prod.estoque <= 0) {
                opt.disabled = true;
                opt.textContent += ' [Esgotado]';
            }
            select.appendChild(opt);
        });
    } catch (err) {
        mostrarAlerta('Erro ao carregar lista de produtos para o pedido.', 'erro');
    }
}

function adicionarItemAoPedido() {
    const select = document.getElementById('pedido-produto-select');
    const produtoId = parseInt(select.value, 10);
    const quantidadeInput = document.getElementById('pedido-quantidade');
    const quantidade = parseInt(quantidadeInput.value, 10);

    if (!produtoId) {
        mostrarAlerta('Por favor, selecione um produto.', 'erro');
        return;
    }

    if (isNaN(quantidade) || quantidade <= 0) {
        mostrarAlerta('Informe uma quantidade válida maior que zero.', 'erro');
        return;
    }

    const produto = produtosCache.find(p => p.id === produtoId);
    if (!produto) return;

    const itemExistente = itensNovoPedido.find(i => i.produto_id === produtoId);
    const qtdTotalDesejada = (itemExistente ? itemExistente.quantidade : 0) + quantidade;

    if (qtdTotalDesejada > produto.estoque) {
        mostrarAlerta(`Estoque insuficiente! Disponível: ${produto.estoque}, Tentativa de adicionar: ${qtdTotalDesejada}.`, 'erro');
        return;
    }

    if (itemExistente) {
        itemExistente.quantidade = qtdTotalDesejada;
        itemExistente.subtotal = itemExistente.quantidade * itemExistente.preco_unitario;
    } else {
        itensNovoPedido.push({
            produto_id: produto.id,
            nome: produto.nome,
            preco_unitario: produto.preco,
            quantidade: quantidade,
            subtotal: produto.preco * quantidade
        });
    }

    quantidadeInput.value = 1;
    renderizarItensPedido();
}

function removerItemDoPedido(produtoId) {
    itensNovoPedido = itensNovoPedido.filter(i => i.produto_id !== produtoId);
    renderizarItensPedido();
}

function renderizarItensPedido() {
    const tbody = document.getElementById('tabela-itens-pedido-corpo');
    tbody.innerHTML = '';

    if (itensNovoPedido.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #777;">Nenhum item adicionado ainda.</td></tr>';
        document.getElementById('pedido-valor-total').textContent = formatarMoeda(0);
        return;
    }

    let total = 0;
    itensNovoPedido.forEach(item => {
        total += item.subtotal;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${item.nome}</td>
            <td>${formatarMoeda(item.preco_unitario)}</td>
            <td>${item.quantidade}</td>
            <td>${formatarMoeda(item.subtotal)}</td>
            <td><button class="btn btn-danger btn-sm" onclick="removerItemDoPedido(${item.produto_id})">x</button></td>
        `;
        tbody.appendChild(tr);
    });

    document.getElementById('pedido-valor-total').textContent = formatarMoeda(total);
}

async function finalizarPedido() {
    if (itensNovoPedido.length === 0) {
        mostrarAlerta('Adicione pelo menos um item ao pedido antes de finalizar.', 'erro');
        return;
    }

    const payload = {
        itens: itensNovoPedido.map(i => ({
            produto_id: i.produto_id,
            quantidade: i.quantidade
        }))
    };

    try {
        const res = await fetch('/api/pedidos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) {
            mostrarAlerta(data.erro || 'Erro ao finalizar pedido.', 'erro');
            return;
        }

        mostrarAlerta(`Pedido #${data.pedido_id} criado com sucesso! Estoque descontado.`);
        itensNovoPedido = [];
        renderizarItensPedido();
        carregarProdutosParaPedido();
        carregarPedidos();
    } catch (err) {
        mostrarAlerta('Erro de conexão ao criar pedido.', 'erro');
    }
}

async function carregarPedidos() {
    try {
        const res = await fetch('/api/pedidos');
        if (res.status === 401 || res.status === 403) {
            tratarErroAcesso(res);
            return;
        }
        const pedidos = await res.json();

        const tbody = document.getElementById('tabela-pedidos-corpo');
        tbody.innerHTML = '';

        if (pedidos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">Nenhum pedido realizado até o momento.</td></tr>';
            return;
        }

        pedidos.forEach(p => {
            const tr = document.createElement('tr');
            const statusClass = p.status === 'Concluído' ? 'status-concluido' : (p.status === 'Cancelado' ? 'status-cancelado' : 'status-pendente');
            const dataExibicao = formatarDataBR(p.data_formatada || p.data_pedido, true);

            tr.innerHTML = `
                <td><strong>#${p.id}</strong></td>
                <td>${dataExibicao}</td>
                <td><strong>${formatarMoeda(p.valor_total)}</strong></td>
                <td>
                    <select onchange="atualizarStatusPedido(${p.id}, this.value)" class="status-badge ${statusClass}">
                        <option value="Pendente" ${p.status === 'Pendente' ? 'selected' : ''}>Pendente</option>
                        <option value="Concluído" ${p.status === 'Concluído' ? 'selected' : ''}>Concluído</option>
                        <option value="Cancelado" ${p.status === 'Cancelado' ? 'selected' : ''}>Cancelado</option>
                    </select>
                </td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="verDetalhesPedido(${p.id})">Ver Itens</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        mostrarAlerta('Erro ao carregar histórico de pedidos.', 'erro');
    }
}

async function atualizarStatusPedido(id, novoStatus) {
    try {
        const res = await fetch(`/api/pedidos/${id}/status`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: novoStatus })
        });
        const data = await res.json();

        if (!res.ok) {
            mostrarAlerta(data.erro || 'Erro ao atualizar status.', 'erro');
            return;
        }

        mostrarAlerta('Status do pedido atualizado!');
        carregarPedidos();
    } catch (err) {
        mostrarAlerta('Erro ao comunicar com o servidor.', 'erro');
    }
}

async function verDetalhesPedido(id) {
    try {
        const res = await fetch(`/api/pedidos/${id}`);
        const pedido = await res.json();

        if (!res.ok) {
            mostrarAlerta(pedido.erro || 'Erro ao carregar detalhes.', 'erro');
            return;
        }

        document.getElementById('modal-titulo').textContent = `Itens do Pedido #${pedido.id}`;
        const dataPedidoExibicao = formatarDataBR(pedido.data_formatada || pedido.data_pedido, true);
        let html = `
            <p style="margin-bottom: 12px; color: #475569;">
                <strong>Data:</strong> ${dataPedidoExibicao} | 
                <strong>Status:</strong> ${pedido.status} | 
                <strong>Total:</strong> ${formatarMoeda(pedido.valor_total)}
            </p>
            <table class="tabela compact">
                <thead>
                    <tr>
                        <th>Produto</th>
                        <th>Preço Unit.</th>
                        <th>Qtd</th>
                        <th>Subtotal</th>
                    </tr>
                </thead>
                <tbody>
        `;

        pedido.itens.forEach(item => {
            html += `
                <tr>
                    <td>${item.produto_nome}</td>
                    <td>${formatarMoeda(item.preco_unitario)}</td>
                    <td>${item.quantidade}</td>
                    <td>${formatarMoeda(item.subtotal)}</td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        document.getElementById('modal-corpo').innerHTML = html;
        document.getElementById('modal-detalhes').style.display = 'flex';
    } catch (err) {
        mostrarAlerta('Erro ao buscar detalhes do pedido.', 'erro');
    }
}

function fecharModal() {
    document.getElementById('modal-detalhes').style.display = 'none';
}

// ==========================================
// 4. MÓDULO CLIENTES
// ==========================================
async function carregarClientes() {
    try {
        const res = await fetch('/api/clientes');
        if (res.status === 401 || res.status === 403) {
            tratarErroAcesso(res);
            return;
        }
        const clientes = await res.json();
        const tbody = document.getElementById('tabela-clientes-corpo');
        tbody.innerHTML = '';

        if (clientes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Nenhum cliente cadastrado.</td></tr>';
            return;
        }

        clientes.forEach(cli => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>#${cli.id}</td>
                <td><strong>${cli.nome}</strong></td>
                <td>${cli.email}</td>
                <td>${cli.telefone || '-'}</td>
                <td>${cli.cidade || '-'}</td>
                <td>${formatarDataBR(cli.criado_em, false)}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        mostrarAlerta('Erro ao listar clientes.', 'erro');
    }
}

async function salvarCliente(event) {
    event.preventDefault();
    const nome = document.getElementById('cli-nome').value.trim();
    const email = document.getElementById('cli-email').value.trim();
    const telefone = document.getElementById('cli-telefone').value.trim();
    const cidade = document.getElementById('cli-cidade').value.trim();

    try {
        const res = await fetch('/api/clientes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nome, email, telefone, cidade })
        });
        const data = await res.json();

        if (!res.ok) {
            mostrarAlerta(data.erro || 'Erro ao cadastrar cliente.', 'erro');
            return;
        }

        mostrarAlerta('Cliente cadastrado com sucesso!');
        document.getElementById('form-cliente').reset();
        carregarClientes();
    } catch (err) {
        mostrarAlerta('Erro de conexão ao salvar cliente.', 'erro');
    }
}

// ==========================================
// 5. MÓDULO USUÁRIOS (RBAC)
// ==========================================
async function carregarPerfisParaSelect() {
    try {
        const res = await fetch('/api/perfis');
        if (!res.ok) return;
        perfisCache = await res.json();

        const select = document.getElementById('user-perfil');
        select.innerHTML = '<option value="">-- Selecione o Perfil --</option>';

        perfisCache.forEach(perf => {
            const opt = document.createElement('option');
            opt.value = perf.id;
            opt.textContent = `${perf.nome} - ${perf.descricao}`;
            select.appendChild(opt);
        });
    } catch (err) {
        mostrarAlerta('Erro ao carregar perfis de acesso.', 'erro');
    }
}

async function carregarUsuarios() {
    try {
        const res = await fetch('/api/usuarios');
        if (res.status === 401 || res.status === 403) {
            tratarErroAcesso(res);
            return;
        }
        usuariosCache = await res.json();
        const tbody = document.getElementById('tabela-usuarios-corpo');
        tbody.innerHTML = '';

        if (usuariosCache.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Nenhum usuário cadastrado.</td></tr>';
            return;
        }

        usuariosCache.forEach(user => {
            const tr = document.createElement('tr');
            const statusTexto = user.ativo ? 'Ativo' : 'Inativo';
            const statusBadgeClass = user.ativo ? 'badge-ativo' : 'badge-inativo';
            const btnStatusTexto = user.ativo ? 'Desativar' : 'Ativar';
            const btnStatusClass = user.ativo ? 'btn-danger' : 'btn-success';
            const dataCadastro = formatarDataBR(user.criado_em, false);

            tr.innerHTML = `
                <td>#${user.id}</td>
                <td><strong>${user.nome}</strong></td>
                <td>${user.email}</td>
                <td><span class="status-badge badge-perfil">${user.perfil_nome}</span></td>
                <td><span class="status-badge ${statusBadgeClass}">${statusTexto}</span></td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="prepararEdicaoUsuario(${user.id})">Editar</button>
                    <button class="btn ${btnStatusClass} btn-sm" onclick="alternarStatusUsuario(${user.id}, ${!user.ativo})">${btnStatusTexto}</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        mostrarAlerta('Erro ao listar usuários do sistema.', 'erro');
    }
}

async function salvarUsuario(event) {
    event.preventDefault();
    const id = document.getElementById('user-id').value;
    const nome = document.getElementById('user-nome').value.trim();
    const email = document.getElementById('user-email').value.trim();
    const perfil_id = parseInt(document.getElementById('user-perfil').value, 10);
    const senha = document.getElementById('user-senha').value;

    const payload = { nome, email, perfil_id };
    if (senha) payload.senha = senha;

    const metodo = id ? 'PUT' : 'POST';
    const url = id ? `/api/usuarios/${id}` : '/api/usuarios';

    try {
        const res = await fetch(url, {
            method: metodo,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) {
            mostrarAlerta(data.erro || 'Erro ao salvar usuário.', 'erro');
            return;
        }

        mostrarAlerta(data.mensagem || 'Usuário salvo com sucesso!');
        cancelarEdicaoUsuario();
        carregarUsuarios();
    } catch (err) {
        mostrarAlerta('Erro ao conectar ao servidor para salvar usuário.', 'erro');
    }
}

function prepararEdicaoUsuario(id) {
    const user = usuariosCache.find(u => u.id === id);
    if (!user) return;

    document.getElementById('user-id').value = user.id;
    document.getElementById('user-nome').value = user.nome;
    document.getElementById('user-email').value = user.email;
    document.getElementById('user-perfil').value = user.perfil_id;
    document.getElementById('user-senha').value = '';

    document.getElementById('form-usuario-titulo').textContent = `Editar Usuário #${user.id}`;
    document.getElementById('btn-salvar-usuario').textContent = 'Atualizar Usuário';
    document.getElementById('btn-cancelar-edicao-user').style.display = 'inline-block';
    document.getElementById('dica-senha').style.display = 'block';
}

function cancelarEdicaoUsuario() {
    document.getElementById('user-id').value = '';
    document.getElementById('user-nome').value = '';
    document.getElementById('user-email').value = '';
    document.getElementById('user-perfil').value = '';
    document.getElementById('user-senha').value = '';

    document.getElementById('form-usuario-titulo').textContent = 'Cadastrar Novo Usuário';
    document.getElementById('btn-salvar-usuario').textContent = 'Salvar Usuário';
    document.getElementById('btn-cancelar-edicao-user').style.display = 'none';
    document.getElementById('dica-senha').style.display = 'none';
}

async function alternarStatusUsuario(id, novoStatus) {
    const acao = novoStatus ? 'ativar' : 'desativar';
    if (!confirm(`Deseja realmente ${acao} este usuário?`)) return;

    try {
        const res = await fetch(`/api/usuarios/${id}/status`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ativo: novoStatus })
        });

        const data = await res.json();
        if (!res.ok) {
            mostrarAlerta(data.erro || 'Erro ao alterar status.', 'erro');
            return;
        }

        mostrarAlerta(data.mensagem);
        carregarUsuarios();
    } catch (err) {
        mostrarAlerta('Erro de conexão ao alterar status do usuário.', 'erro');
    }
}

async function tratarErroAcesso(resposta) {
    if (resposta.status === 401) {
        window.location.href = '/login';
    } else if (resposta.status === 403) {
        const dados = await resposta.json().catch(() => ({}));
        mostrarAlerta(dados.erro || 'Acesso negado a este recurso.', 'erro');
    }
}

// Iniciar verificando autenticação do usuário
document.addEventListener('DOMContentLoaded', () => {
    checarAutenticacao();
});
