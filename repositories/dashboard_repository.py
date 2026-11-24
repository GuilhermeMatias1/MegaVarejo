import datetime
from decimal import Decimal
from database.connection import DatabaseConnection
from repositories.base_repository import BaseRepository
from models.pedido import formatar_data_br

class DashboardRepository(BaseRepository):
    """
    Repositório de dados para agregação analítica do Dashboard Gerencial.
    Centraliza as consultas parametrizadas para KPIs comerciais, resumo financeiro,
    evolução temporal de faturamento, distribuição de pedidos, alertas e histórico de atividades.
    """

    def __init__(self, connection=None):
        self._connection = connection

    def _get_connection(self):
        if self._connection:
            return self._connection
        return DatabaseConnection.get_connection()

    def buscar_por_id(self, id: int):
        raise NotImplementedError("DashboardRepository não possui entidade por ID singular.")

    def listar_todos(self) -> list:
        raise NotImplementedError("DashboardRepository utiliza métodos específicos de agregação analítica.")

    # -------------------------------------------------------------
    # 1. INDICADORES COMERCIAIS (KPIS) COM COMPARAÇÃO HISTÓRICA
    # -------------------------------------------------------------
    def obter_kpis_comerciais(self, data_inicio: datetime.date, data_fim: datetime.date,
                              data_inicio_anterior: datetime.date, data_fim_anterior: datetime.date) -> dict:
        """
        Calcula faturamento, pedidos e ticket médio desconsiderando pedidos cancelados/recusados.
        Calcula também novos clientes cadastrados no intervalo.
        Compara com o período anterior equivalente.
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                # Período Atual
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(valor_total), 0.00) AS faturamento,
                        COUNT(id) AS qtd_pedidos
                    FROM pedidos
                    WHERE status NOT IN ('Cancelado', 'Recusado')
                      AND data_pedido >= %s AND data_pedido <= %s
                """, (f"{data_inicio} 00:00:00", f"{data_fim} 23:59:59"))
                row_atual = cursor.fetchone() or {}

                # Novos clientes no período
                cursor.execute("""
                    SELECT COUNT(id) AS novos_clientes
                    FROM clientes
                    WHERE criado_em >= %s AND criado_em <= %s
                """, (f"{data_inicio} 00:00:00", f"{data_fim} 23:59:59"))
                row_cli_atual = cursor.fetchone() or {}

                # Período Anterior
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(valor_total), 0.00) AS faturamento,
                        COUNT(id) AS qtd_pedidos
                    FROM pedidos
                    WHERE status NOT IN ('Cancelado', 'Recusado')
                      AND data_pedido >= %s AND data_pedido <= %s
                """, (f"{data_inicio_anterior} 00:00:00", f"{data_fim_anterior} 23:59:59"))
                row_ant = cursor.fetchone() or {}

                cursor.execute("""
                    SELECT COUNT(id) AS novos_clientes
                    FROM clientes
                    WHERE criado_em >= %s AND criado_em <= %s
                """, (f"{data_inicio_anterior} 00:00:00", f"{data_fim_anterior} 23:59:59"))
                row_cli_ant = cursor.fetchone() or {}

            fat_atual = float(row_atual.get('faturamento') or 0.0)
            ped_atual = int(row_atual.get('qtd_pedidos') or 0)
            ticket_atual = round(fat_atual / ped_atual, 2) if ped_atual > 0 else 0.0
            novos_cli_atual = int(row_cli_atual.get('novos_clientes') or 0)

            fat_ant = float(row_ant.get('faturamento') or 0.0)
            ped_ant = int(row_ant.get('qtd_pedidos') or 0)
            ticket_ant = round(fat_ant / ped_ant, 2) if ped_ant > 0 else 0.0
            novos_cli_ant = int(row_cli_ant.get('novos_clientes') or 0)

            def calcular_variacao(atual, anterior):
                if anterior == 0:
                    return 100.0 if atual > 0 else 0.0
                return round(((atual - anterior) / anterior) * 100.0, 1)

            return {
                "faturamento": fat_atual,
                "faturamento_anterior": fat_ant,
                "faturamento_variacao_pct": calcular_variacao(fat_atual, fat_ant),
                "pedidos": ped_atual,
                "pedidos_anterior": ped_ant,
                "pedidos_variacao_pct": calcular_variacao(ped_atual, ped_ant),
                "ticket_medio": ticket_atual,
                "ticket_medio_anterior": ticket_ant,
                "ticket_medio_variacao_pct": calcular_variacao(ticket_atual, ticket_ant),
                "novos_clientes": novos_cli_atual,
                "novos_clientes_anterior": novos_cli_ant,
                "novos_clientes_variacao_pct": calcular_variacao(novos_cli_atual, novos_cli_ant)
            }
        finally:
            if not self._connection:
                conn.close()

    # -------------------------------------------------------------
    # 2. EVOLUÇÃO TEMPORAL DE FATURAMENTO E DISTRIBUIÇÃO DE STATUS
    # -------------------------------------------------------------
    def obter_evolucao_faturamento(self, data_inicio: datetime.date, data_fim: datetime.date, agrupamento: str = 'dia') -> list:
        """
        Retorna a evolução temporal do faturamento (pedidos não cancelados).
        agrupamento: 'dia', 'semana' ou 'mes'
        """
        conn = self._get_connection()
        try:
            if agrupamento == 'mes':
                formato_sql = "%%%%Y-%%%%m"
                formato_label = "DATE_FORMAT(data_pedido, '%%%%m/%%%%Y')"
            elif agrupamento == 'semana':
                formato_sql = "%%%%Y-%%%%u"
                formato_label = "CONCAT('Sem ', WEEK(data_pedido, 1), '/', YEAR(data_pedido))"
            else:
                formato_sql = "%%%%Y-%%%%m-%%%%d"
                formato_label = "DATE_FORMAT(data_pedido, '%%%%d/%%%%m')"

            sql = f"""
                SELECT 
                    {formato_label} AS rotulo,
                    DATE_FORMAT(MIN(data_pedido), '%%%%Y-%%%%m-%%%%d') AS chave_ordenacao,
                    COALESCE(SUM(valor_total), 0.00) AS faturamento,
                    COUNT(id) AS total_pedidos
                FROM pedidos
                WHERE status NOT IN ('Cancelado', 'Recusado')
                  AND data_pedido >= %s AND data_pedido <= %s
                GROUP BY DATE_FORMAT(data_pedido, '{formato_sql}'), rotulo
                ORDER BY MIN(data_pedido) ASC
            """

            with conn.cursor() as cursor:
                cursor.execute(sql, (f"{data_inicio} 00:00:00", f"{data_fim} 23:59:59"))
                linhas = cursor.fetchall() or []

            return [
                {
                    "rotulo": str(l.get('rotulo')),
                    "faturamento": float(l.get('faturamento') or 0.0),
                    "pedidos": int(l.get('total_pedidos') or 0)
                }
                for l in linhas
            ]
        finally:
            if not self._connection:
                conn.close()

    def obter_distribuicao_status_pedidos(self, data_inicio: datetime.date, data_fim: datetime.date) -> list:
        """Retorna distribuição dos pedidos por status no período selecionado."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT status, COUNT(id) AS quantidade, COALESCE(SUM(valor_total), 0.00) AS valor
                    FROM pedidos
                    WHERE data_pedido >= %s AND data_pedido <= %s
                    GROUP BY status
                    ORDER BY quantidade DESC
                """, (f"{data_inicio} 00:00:00", f"{data_fim} 23:59:59"))
                linhas = cursor.fetchall() or []

            return [
                {
                    "status": str(l.get('status')),
                    "quantidade": int(l.get('quantidade') or 0),
                    "valor": float(l.get('valor') or 0.0)
                }
                for l in linhas
            ]
        finally:
            if not self._connection:
                conn.close()

    # -------------------------------------------------------------
    # 3. ALERTAS GERENCIAIS
    # -------------------------------------------------------------
    def obter_alertas_gerenciais(self) -> dict:
        """
        Recupera contagens e itens críticos:
        - Pedidos atrasados: data_prevista_entrega < hoje e status não entregue/cancelado
        - Produtos com estoque baixo ou zerado: estoque <= estoque_minimo
        - Contas a receber vencidas: data_vencimento < hoje e status != 'Pago' e != 'Cancelado'
        - Contas a pagar próximas do vencimento: vencimento entre hoje e hoje + 3 dias, status pendente/parcial
        - Entregas em atraso: enviadas ou em transporte com prazo extrapolado
        """
        conn = self._get_connection()
        hoje = datetime.date.today()
        proximos_dias = hoje + datetime.timedelta(days=3)

        try:
            with conn.cursor() as cursor:
                # 1. Pedidos atrasados gerais (não entregues e data prevista expirada)
                cursor.execute("""
                    SELECT COUNT(id) AS qtd
                    FROM pedidos
                    WHERE data_prevista_entrega IS NOT NULL
                      AND data_prevista_entrega < %s
                      AND status NOT IN ('Entregue', 'Cancelado', 'Devolvido', 'Recusado')
                """, (hoje,))
                pedidos_atrasados = int((cursor.fetchone() or {}).get('qtd') or 0)

                # 2. Entregas em transporte/enviadas atrasadas
                cursor.execute("""
                    SELECT COUNT(id) AS qtd
                    FROM pedidos
                    WHERE status IN ('Enviado', 'Em Transporte')
                      AND data_prevista_entrega IS NOT NULL
                      AND data_prevista_entrega < %s
                """, (hoje,))
                entregas_atrasadas = int((cursor.fetchone() or {}).get('qtd') or 0)

                # 3. Produtos em estoque crítico ou zerado
                cursor.execute("""
                    SELECT COUNT(id) AS qtd
                    FROM produtos
                    WHERE estoque <= estoque_minimo
                """)
                produtos_criticos = int((cursor.fetchone() or {}).get('qtd') or 0)

                # 4. Contas a receber vencidas (com saldo pendente)
                cursor.execute("""
                    SELECT COUNT(id) AS qtd, COALESCE(SUM(valor_original - valor_recebido), 0.00) AS valor_total
                    FROM contas_receber
                    WHERE data_vencimento < %s
                      AND status NOT IN ('Pago', 'Cancelado')
                      AND (valor_original - valor_recebido) > 0.01
                """, (hoje,))
                row_rec = cursor.fetchone() or {}
                receber_vencidas = int(row_rec.get('qtd') or 0)
                valor_receber_vencido = float(row_rec.get('valor_total') or 0.0)

                # 5. Contas a pagar próximas do vencimento (próximos 3 dias)
                cursor.execute("""
                    SELECT COUNT(id) AS qtd, COALESCE(SUM(valor_original - valor_pago), 0.00) AS valor_total
                    FROM contas_pagar
                    WHERE data_vencimento >= %s AND data_vencimento <= %s
                      AND status NOT IN ('Pago', 'Cancelado')
                """, (hoje, proximos_dias))
                row_pag = cursor.fetchone() or {}
                pagar_vencendo = int(row_pag.get('qtd') or 0)
                valor_pagar_vencendo = float(row_pag.get('valor_total') or 0.0)

            return {
                "pedidos_atrasados": pedidos_atrasados,
                "entregas_atrasadas": entregas_atrasadas,
                "produtos_estoque_critico": produtos_criticos,
                "contas_receber_vencidas": {
                    "quantidade": receber_vencidas,
                    "valor": valor_receber_vencido
                },
                "contas_pagar_proximas_vencimento": {
                    "quantidade": pagar_vencendo,
                    "valor": valor_pagar_vencendo
                }
            }
        finally:
            if not self._connection:
                conn.close()

    # -------------------------------------------------------------
    # 4. DESEMPENHO OPERACIONAL
    # -------------------------------------------------------------
    def obter_pedidos_recentes(self, limite: int = 6) -> list:
        """Retorna os pedidos mais recentes com detalhes essenciais."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        p.id, p.numero_pedido, p.data_pedido, p.valor_total,
                        p.status, p.status_pagamento, p.responsavel,
                        c.nome AS cliente_nome
                    FROM pedidos p
                    LEFT JOIN clientes c ON p.cliente_id = c.id
                    ORDER BY p.data_pedido DESC, p.id DESC
                    LIMIT %s
                """, (limite,))
                linhas = cursor.fetchall() or []

            return [
                {
                    "id": l.get('id'),
                    "numero_pedido": l.get('numero_pedido') or f"PED-{l.get('id'):04d}",
                    "data": formatar_data_br(l.get('data_pedido')),
                    "cliente": l.get('cliente_nome') or "Consumidor Final",
                    "valor": float(l.get('valor_total') or 0.0),
                    "status": l.get('status'),
                    "status_pagamento": l.get('status_pagamento'),
                    "responsavel": l.get('responsavel')
                }
                for l in linhas
            ]
        finally:
            if not self._connection:
                conn.close()

    def obter_produtos_mais_vendidos(self, data_inicio: datetime.date, data_fim: datetime.date, limite: int = 5) -> list:
        """Retorna os produtos com maior volume vendido e receita gerada no período."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        p.id AS produto_id,
                        p.nome AS produto_nome,
                        p.categoria,
                        COALESCE(SUM(it.quantidade), 0) AS total_vendido,
                        COALESCE(SUM(it.subtotal), 0.00) AS receita_total
                    FROM itens_pedido it
                    JOIN pedidos ped ON it.pedido_id = ped.id
                    JOIN produtos p ON it.produto_id = p.id
                    WHERE ped.status NOT IN ('Cancelado', 'Recusado')
                      AND ped.data_pedido >= %s AND ped.data_pedido <= %s
                    GROUP BY p.id, p.nome, p.categoria
                    ORDER BY total_vendido DESC, receita_total DESC
                    LIMIT %s
                """, (f"{data_inicio} 00:00:00", f"{data_fim} 23:59:59", limite))
                linhas = cursor.fetchall() or []

            return [
                {
                    "produto_id": l.get('produto_id'),
                    "nome": l.get('produto_nome'),
                    "categoria": l.get('categoria') or "Geral",
                    "quantidade_vendida": int(l.get('total_vendido') or 0),
                    "receita_total": float(l.get('receita_total') or 0.0)
                }
                for l in linhas
            ]
        finally:
            if not self._connection:
                conn.close()

    def obter_entregas_em_andamento(self, limite: int = 5) -> list:
        """Retorna os pedidos que estão em separação, prontos ou em transporte."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        p.id, p.numero_pedido, p.status, p.data_prevista_entrega,
                        c.nome AS cliente_nome, p.endereco_entrega, c.cidade, c.uf
                    FROM pedidos p
                    LEFT JOIN clientes c ON p.cliente_id = c.id
                    WHERE p.status IN ('Em Separação', 'Pronto para Envio', 'Enviado', 'Em Transporte')
                    ORDER BY p.data_prevista_entrega ASC, p.id DESC
                    LIMIT %s
                """, (limite,))
                linhas = cursor.fetchall() or []

            return [
                {
                    "id": l.get('id'),
                    "numero_pedido": l.get('numero_pedido') or f"PED-{l.get('id'):04d}",
                    "status": l.get('status'),
                    "cliente": l.get('cliente_nome') or "Cliente",
                    "destino": f"{l.get('cidade') or '-'}/{l.get('uf') or '-'}" if l.get('cidade') else (l.get('endereco_entrega') or "-"),
                    "previsao_entrega": formatar_data_br(l.get('data_prevista_entrega'), incluir_hora=False) if l.get('data_prevista_entrega') else "Não informada",
                    "atrasado": bool(l.get('data_prevista_entrega') and l.get('data_prevista_entrega') < datetime.date.today())
                }
                for l in linhas
            ]
        finally:
            if not self._connection:
                conn.close()

    # -------------------------------------------------------------
    # 5. ATIVIDADES RECENTES (AUDITORIA E HISTÓRICO REAL)
    # -------------------------------------------------------------
    def obter_atividades_recentes(self, limite: int = 8) -> list:
        """
        Coleta registros reais unificados de auditoria:
        - Histórico de pedidos (mudanças de status e pagamentos)
        - Movimentações de estoque
        - Transações de caixa recentes
        """
        conn = self._get_connection()
        atividades = []

        try:
            with conn.cursor() as cursor:
                # 1. Histórico de pedidos
                cursor.execute("""
                    SELECT 
                        hp.id, hp.pedido_id, hp.tipo_alteracao, hp.status_anterior,
                        hp.status_novo, hp.observacao, hp.responsavel, hp.data_registro,
                        p.numero_pedido
                    FROM historico_pedidos hp
                    JOIN pedidos p ON hp.pedido_id = p.id
                    ORDER BY hp.data_registro DESC
                    LIMIT %s
                """, (limite,))
                for r in cursor.fetchall() or []:
                    atividades.append({
                        "tipo": "Pedido",
                        "icone": "🛒",
                        "titulo": f"Pedido #{r.get('numero_pedido') or r.get('pedido_id')}: {r.get('tipo_alteracao')}",
                        "descricao": f"{r.get('status_anterior') or 'Início'} ➔ {r.get('status_novo')}. {r.get('observacao') or ''}".strip(),
                        "responsavel": r.get('responsavel'),
                        "data_raw": r.get('data_registro'),
                        "data_formatada": formatar_data_br(r.get('data_registro'))
                    })

                # 2. Movimentações de estoque relevantes
                cursor.execute("""
                    SELECT 
                        me.id, me.tipo, me.quantidade, me.motivo, me.responsavel,
                        me.data_movimentacao, p.nome AS produto_nome
                    FROM movimentacoes_estoque me
                    JOIN produtos p ON me.produto_id = p.id
                    ORDER BY me.data_movimentacao DESC
                    LIMIT %s
                """, (limite,))
                for r in cursor.fetchall() or []:
                    atividades.append({
                        "tipo": "Estoque",
                        "icone": "📦",
                        "titulo": f"Estoque [{r.get('tipo')}]: {r.get('produto_nome')}",
                        "descricao": f"Qtd: {r.get('quantidade')} un. Motivo: {r.get('motivo')}",
                        "responsavel": r.get('responsavel'),
                        "data_raw": r.get('data_movimentacao'),
                        "data_formatada": formatar_data_br(r.get('data_movimentacao'))
                    })

                # 3. Transações de Caixa
                cursor.execute("""
                    SELECT 
                        tc.id, tc.tipo, tc.origem, tc.valor, tc.descricao,
                        tc.responsavel, tc.data_transacao
                    FROM transacoes_caixa tc
                    ORDER BY tc.data_transacao DESC
                    LIMIT %s
                """, (limite,))
                for r in cursor.fetchall() or []:
                    tipo_trans = r.get('tipo')
                    icone = "💵" if tipo_trans == 'Entrada' else "💸"
                    atividades.append({
                        "tipo": "Financeiro",
                        "icone": icone,
                        "titulo": f"Caixa [{tipo_trans}]: R$ {float(r.get('valor') or 0.0):.2f}",
                        "descricao": f"{r.get('descricao')} (Origem: {r.get('origem')})",
                        "responsavel": r.get('responsavel'),
                        "data_raw": r.get('data_transacao'),
                        "data_formatada": formatar_data_br(r.get('data_transacao'))
                    })

            # Ordena decrescente pela data_raw e limita
            atividades.sort(key=lambda x: x['data_raw'] or datetime.datetime.min, reverse=True)
            for a in atividades:
                a.pop('data_raw', None)

            return atividades[:limite]
        finally:
            if not self._connection:
                conn.close()
