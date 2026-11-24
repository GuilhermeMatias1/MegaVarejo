import datetime
from repositories.produto_repository import ProdutoRepository
from repositories.pedido_repository import PedidoRepository
from repositories.financeiro_repository import FinanceiroRepository
from repositories.cliente_repository import ClienteRepository
from repositories.dashboard_repository import DashboardRepository

class DashboardService:
    """
    Camada de serviço do Dashboard Gerencial.
    Orquestra os dados comerciais, financeiros e operacionais com filtros de período dinâmicos:
    - Interpreta e valida filtros temporais (hoje, 7 dias, 30 dias, este mês, ano ou intervalo personalizado).
    - Calcula faturamento e compara com o período anterior equivalente.
    - Reutiliza a lógica financeira estrita (saldo disponível, entradas e saídas efetivas, contas a pagar e receber em aberto).
    - Agrega alertas em tempo real e auditoria de atividades.
    """

    def __init__(self, dashboard_repo: DashboardRepository = None,
                 financeiro_repo: FinanceiroRepository = None,
                 pedido_repo: PedidoRepository = None,
                 produto_repo: ProdutoRepository = None):
        self._dashboard_repo = dashboard_repo or DashboardRepository()
        self._financeiro_repo = financeiro_repo or FinanceiroRepository()
        self._pedido_repo = pedido_repo or PedidoRepository()
        self._produto_repo = produto_repo or ProdutoRepository()

    def _resolver_intervalo(self, periodo: str, data_inicio_str: str = None, data_fim_str: str = None):
        """
        Calcula as datas de início e fim do período selecionado e do período anterior equivalente.
        """
        hoje = datetime.date.today()

        if periodo == 'hoje':
            inicio = hoje
            fim = hoje
            duracao = datetime.timedelta(days=1)
            inicio_ant = inicio - duracao
            fim_ant = fim - duracao
            agrupamento = 'dia'
        elif periodo == '7dias':
            inicio = hoje - datetime.timedelta(days=6)
            fim = hoje
            duracao = datetime.timedelta(days=7)
            inicio_ant = inicio - duracao
            fim_ant = fim - duracao
            agrupamento = 'dia'
        elif periodo == 'mes_atual':
            inicio = hoje.replace(day=1)
            fim = hoje
            # Mês anterior equivalente
            primeiro_dia_mes_ant = (inicio - datetime.timedelta(days=1)).replace(day=1)
            dias_corridos = (fim - inicio).days
            inicio_ant = primeiro_dia_mes_ant
            fim_ant = primeiro_dia_mes_ant + datetime.timedelta(days=dias_corridos)
            agrupamento = 'dia'
        elif periodo == 'ano_atual':
            inicio = hoje.replace(month=1, day=1)
            fim = hoje
            inicio_ant = inicio.replace(year=inicio.year - 1)
            fim_ant = fim.replace(year=fim.year - 1)
            agrupamento = 'mes'
        elif periodo == 'personalizado' and data_inicio_str and data_fim_str:
            try:
                inicio = datetime.date.fromisoformat(data_inicio_str)
                fim = datetime.date.fromisoformat(data_fim_str)
            except Exception:
                inicio = hoje - datetime.timedelta(days=29)
                fim = hoje
            if inicio > fim:
                inicio, fim = fim, inicio
            dias = (fim - inicio).days + 1
            duracao = datetime.timedelta(days=dias)
            inicio_ant = inicio - duracao
            fim_ant = fim - duracao
            agrupamento = 'mes' if dias > 90 else ('semana' if dias > 30 else 'dia')
        else: # padrão 30dias
            inicio = hoje - datetime.timedelta(days=29)
            fim = hoje
            duracao = datetime.timedelta(days=30)
            inicio_ant = inicio - duracao
            fim_ant = fim - duracao
            agrupamento = 'dia'

        return inicio, fim, inicio_ant, fim_ant, agrupamento

    def obter_metricas(self, periodo: str = '30dias', data_inicio: str = None, data_fim: str = None, agrupamento_forcado: str = None) -> dict:
        """
        Retorna o pacote analítico completo para o Dashboard Gerencial:
        1. Cabeçalho e metadados de atualização e intervalo.
        2. KPIs Comerciais com comparativo histórico.
        3. Resumo Financeiro respeitando regras de livro-caixa vs contas em aberto.
        4. Evolução temporal de faturamento e distribuição de status.
        5. Alertas Gerenciais com contadores de pendências e links.
        6. Desempenho Operacional (pedidos recentes, mais vendidos, entregas em andamento).
        7. Atividades recentes reais (auditoria de eventos).
        """
        dt_inicio, dt_fim, dt_inicio_ant, dt_fim_ant, agrupamento = self._resolver_intervalo(periodo, data_inicio, data_fim)
        if agrupamento_forcado in ['dia', 'semana', 'mes']:
            agrupamento = agrupamento_forcado

        # 1. KPIs Comerciais
        kpis_comerciais = self._dashboard_repo.obter_kpis_comerciais(dt_inicio, dt_fim, dt_inicio_ant, dt_fim_ant)

        # 2. Resumo Financeiro (Integrado com regras estritas de Fluxo de Caixa e Contas a Receber/Pagar)
        resumo_fin_global = self._financeiro_repo.obter_resumo_financeiro()
        
        # Filtra entradas e saídas de caixa específicas do período selecionado
        transacoes_periodo = self._financeiro_repo.listar_transacoes_caixa(
            data_inicio=dt_inicio.isoformat(),
            data_fim=dt_fim.isoformat()
        )
        entradas_periodo = sum(float(t['valor']) for t in transacoes_periodo if t.get('tipo') == 'Entrada')
        saidas_periodo = sum(float(t['valor']) for t in transacoes_periodo if t.get('tipo') == 'Saída')

        resumo_financeiro = {
            "saldo_disponivel_caixa": float(resumo_fin_global.saldo_disponivel),
            "entradas_no_periodo": round(entradas_periodo, 2),
            "saidas_no_periodo": round(saidas_periodo, 2),
            "contas_receber_aberto": float(resumo_fin_global.contas_a_receber),
            "contas_pagar_aberto": float(resumo_fin_global.contas_a_pagar_pendentes),
            "resultado_operacional_simplificado": float(resumo_fin_global.resultado_operacional_simplificado)
        }

        # 3. Evolução de Faturamento e Distribuição
        grafico_evolucao = self._dashboard_repo.obter_evolucao_faturamento(dt_inicio, dt_fim, agrupamento=agrupamento)
        distribuicao_status = self._dashboard_repo.obter_distribuicao_status_pedidos(dt_inicio, dt_fim)

        # 4. Alertas Gerenciais
        alertas = self._dashboard_repo.obter_alertas_gerenciais()

        # 5. Desempenho Operacional
        pedidos_recentes = self._dashboard_repo.obter_pedidos_recentes(limite=6)
        produtos_mais_vendidos = self._dashboard_repo.obter_produtos_mais_vendidos(dt_inicio, dt_fim, limite=5)
        entregas_em_andamento = self._dashboard_repo.obter_entregas_em_andamento(limite=5)

        # 6. Atividades Recentes (Auditoria real)
        atividades = self._dashboard_repo.obter_atividades_recentes(limite=8)

        # Compatibilidade com chaves legadas se alguém consultar
        total_produtos = self._produto_repo.contar_total()
        total_pedidos = self._pedido_repo.contar_total()
        total_vendas = self._pedido_repo.somar_vendas_totais()

        return {
            "periodo": {
                "chave": periodo,
                "data_inicio": dt_inicio.strftime('%d/%m/%Y'),
                "data_fim": dt_fim.strftime('%d/%m/%Y'),
                "data_inicio_iso": dt_inicio.isoformat(),
                "data_fim_iso": dt_fim.isoformat(),
                "agrupamento": agrupamento,
                "ultima_atualizacao": datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            },
            "kpis_comerciais": kpis_comerciais,
            "resumo_financeiro": resumo_financeiro,
            "grafico_evolucao": grafico_evolucao,
            "distribuicao_status": distribuicao_status,
            "alertas": alertas,
            "operacional": {
                "pedidos_recentes": pedidos_recentes,
                "produtos_mais_vendidos": produtos_mais_vendidos,
                "entregas_em_andamento": entregas_em_andamento
            },
            "atividades_recentes": atividades,
            # Chaves legadas preservadas
            "total_produtos": total_produtos,
            "total_pedidos": total_pedidos,
            "total_vendas": total_vendas
        }
