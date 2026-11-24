import datetime
from decimal import Decimal
from typing import Optional
from models.pedido import formatar_data_br

class Fornecedor:
    """
    Entidade de domínio Fornecedor.
    Demonstra ENCAPSULAMENTO protegendo dados cadastrais e de contato com credores.
    """
    def __init__(self, razao_social: str, cnpj_cpf: str = "", email: str = "",
                 telefone: str = "", categoria: str = "Geral", criado_em=None, id: int = None):
        self._id = id
        self.razao_social = razao_social
        self.cnpj_cpf = cnpj_cpf
        self.email = email
        self.telefone = telefone
        self.categoria = categoria
        self._criado_em = criado_em or datetime.datetime.now()

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def razao_social(self) -> str:
        return self._razao_social

    @razao_social.setter
    def razao_social(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError("A razão social / nome do fornecedor é obrigatória.")
        self._razao_social = str(valor).strip()

    @property
    def cnpj_cpf(self) -> str:
        return self._cnpj_cpf

    @cnpj_cpf.setter
    def cnpj_cpf(self, valor: str):
        self._cnpj_cpf = str(valor or "").strip()

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, valor: str):
        e = str(valor or "").strip()
        if e and ('@' not in e or '.' not in e):
            raise ValueError("Formato de e-mail do fornecedor inválido.")
        self._email = e

    @property
    def telefone(self) -> str:
        return self._telefone

    @telefone.setter
    def telefone(self, valor: str):
        self._telefone = str(valor or "").strip()

    @property
    def categoria(self) -> str:
        return self._categoria

    @categoria.setter
    def categoria(self, valor: str):
        self._categoria = str(valor or "Geral").strip()

    @property
    def criado_em(self):
        return self._criado_em

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "razao_social": self._razao_social,
            "cnpj_cpf": self._cnpj_cpf or "-",
            "email": self._email or "-",
            "telefone": self._telefone or "-",
            "categoria": self._categoria,
            "criado_em": formatar_data_br(self._criado_em, incluir_hora=False)
        }


class ContaPagar:
    """
    Entidade de domínio ContaPagar.
    Demonstra ENCAPSULAMENTO garantindo integridade de valores monetários,
    cálculo dinâmico de status (Vencido, Parcialmente Pago, Pago, Pendente)
    e rastreamento de quitações.
    """
    STATUS_VALIDOS = {'Pendente', 'Parcialmente Pago', 'Pago', 'Cancelado'}

    def __init__(self, descricao: str, valor_original: float, data_vencimento,
                 fornecedor_id: int = None, fornecedor_nome: str = None,
                 categoria: str = "Operacional", valor_pago: float = 0.0,
                 data_pagamento=None, status: str = "Pendente",
                 forma_pagamento: str = None, comprovante: str = None,
                 responsavel: str = "Financeiro", observacoes: str = "",
                 criado_em=None, id: int = None):
        self._id = id
        self.descricao = descricao
        self._fornecedor_id = fornecedor_id
        self._fornecedor_nome = fornecedor_nome or "Não especificado"
        self.categoria = categoria
        self.valor_original = valor_original
        self.valor_pago = valor_pago
        self.data_vencimento = data_vencimento
        self._data_pagamento = data_pagamento
        self._status = status if status in self.STATUS_VALIDOS else "Pendente"
        self._forma_pagamento = forma_pagamento
        self._comprovante = comprovante
        self._responsavel = responsavel
        self._observacoes = observacoes
        self._criado_em = criado_em or datetime.datetime.now()

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def descricao(self) -> str:
        return self._descricao

    @descricao.setter
    def descricao(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError("A descrição da conta a pagar é obrigatória.")
        self._descricao = str(valor).strip()

    @property
    def valor_original(self) -> float:
        return self._valor_original

    @valor_original.setter
    def valor_original(self, valor):
        v = float(valor or 0.0)
        if v <= 0:
            raise ValueError("O valor original da conta deve ser positivo maior que zero.")
        self._valor_original = round(v, 2)

    @property
    def valor_pago(self) -> float:
        return self._valor_pago

    @valor_pago.setter
    def valor_pago(self, valor):
        v = float(valor or 0.0)
        if v < 0:
            raise ValueError("O valor pago não pode ser negativo.")
        self._valor_pago = round(v, 2)

    @property
    def valor_restante(self) -> float:
        return max(0.0, round(self._valor_original - self._valor_pago, 2))

    @property
    def data_vencimento(self):
        return self._data_vencimento

    @data_vencimento.setter
    def data_vencimento(self, valor):
        if isinstance(valor, str):
            try:
                self._data_vencimento = datetime.datetime.strptime(valor[:10], '%Y-%m-%d').date()
            except ValueError:
                self._data_vencimento = datetime.date.today()
        elif isinstance(valor, datetime.datetime):
            self._data_vencimento = valor.date()
        elif isinstance(valor, datetime.date):
            self._data_vencimento = valor
        else:
            raise ValueError("Data de vencimento inválida.")

    @property
    def status_calculado(self) -> str:
        """
        Retorna o status calculado considerando:
        - Cancelado se marcado como tal
        - Pago se valor_pago >= valor_original
        - Vencido se hoje > data_vencimento e não está pago
        - Parcialmente Pago se valor_pago > 0 e < valor_original
        - Pendente caso contrário
        """
        if self._status == 'Cancelado':
            return 'Cancelado'
        if self._valor_pago >= self._valor_original:
            return 'Pago'
        
        hoje = datetime.date.today()
        if self._data_vencimento < hoje:
            return 'Vencido'
        if self._valor_pago > 0:
            return 'Parcialmente Pago'
        return 'Pendente'

    def registrar_pagamento(self, valor: float, forma_pagamento: str, responsavel: str, comprovante: str = None):
        """
        Registra pagamento parcial ou total da conta a pagar, garantindo consistência.
        """
        v = float(valor or 0.0)
        if v <= 0:
            raise ValueError("O valor a pagar deve ser maior que zero.")
        if v > self.valor_restante + 0.001:
            raise ValueError(f"O valor de R$ {v:.2f} excede o saldo restante de R$ {self.valor_restante:.2f}.")

        self.valor_pago = round(self._valor_pago + v, 2)
        self._forma_pagamento = forma_pagamento
        self._responsavel = responsavel
        self._comprovante = comprovante
        self._data_pagamento = datetime.datetime.now()

        if self._valor_pago >= self._valor_original:
            self._status = 'Pago'
        else:
            self._status = 'Parcialmente Pago'

    def to_dict(self) -> dict:
        venc_str = self._data_vencimento.strftime('%d/%m/%Y') if self._data_vencimento else "-"
        pag_str = formatar_data_br(self._data_pagamento) if self._data_pagamento else "-"
        return {
            "id": self._id,
            "descricao": self._descricao,
            "fornecedor_id": self._fornecedor_id,
            "fornecedor_nome": self._fornecedor_nome,
            "categoria": self.categoria,
            "valor_original": self._valor_original,
            "valor_pago": self._valor_pago,
            "valor_restante": self.valor_restante,
            "data_vencimento": venc_str,
            "data_vencimento_iso": self._data_vencimento.isoformat() if self._data_vencimento else None,
            "data_pagamento": pag_str,
            "status": self._status,
            "status_calculado": self.status_calculado,
            "forma_pagamento": self._forma_pagamento or "-",
            "comprovante": self._comprovante or "-",
            "responsavel": self._responsavel,
            "observacoes": self._observacoes or ""
        }


class TransacaoCaixa:
    """
    Entidade de domínio TransacaoCaixa (Livro-Caixa / Histórico Efetivo).
    Representa uma movimentação financeira efetiva com identificador único (operacao_id)
    para garantia absoluta contra pagamentos ou estornos duplicados.
    """
    TIPOS_VALIDOS = {'Entrada', 'Saída'}
    ORIGENS_VALIDAS = {'Pedido', 'Conta a Pagar', 'Avulso', 'Estorno'}

    def __init__(self, operacao_id: str, tipo: str, origem: str, valor: float,
                 descricao: str, responsavel: str, forma_pagamento: str = "Outros",
                 referencia_id: int = None, data_transacao=None, id: int = None):
        if not operacao_id or not str(operacao_id).strip():
            raise ValueError("O operacao_id é obrigatório para garantir idempotência.")
        if tipo not in self.TIPOS_VALIDOS:
            raise ValueError(f"Tipo inválido: {tipo}. Deve ser 'Entrada' ou 'Saída'.")
        if origem not in self.ORIGENS_VALIDAS:
            raise ValueError(f"Origem inválida: {origem}.")

        v = float(valor or 0.0)
        if v <= 0:
            raise ValueError("O valor da movimentação de caixa deve ser positivo maior que zero.")

        self._id = id
        self._operacao_id = str(operacao_id).strip()
        self._tipo = tipo
        self._origem = origem
        self._referencia_id = referencia_id
        self._valor = round(v, 2)
        self._forma_pagamento = forma_pagamento or "Outros"
        self._descricao = str(descricao or "").strip()
        self._responsavel = str(responsavel or "Sistema").strip()
        self._data_transacao = data_transacao or datetime.datetime.now()

    @property
    def id(self) -> Optional[int]:
        return self._id

    @property
    def operacao_id(self) -> str:
        return self._operacao_id

    @property
    def tipo(self) -> str:
        return self._tipo

    @property
    def origem(self) -> str:
        return self._origem

    @property
    def referencia_id(self) -> Optional[int]:
        return self._referencia_id

    @property
    def valor(self) -> float:
        return self._valor

    @property
    def forma_pagamento(self) -> str:
        return self._forma_pagamento

    @property
    def descricao(self) -> str:
        return self._descricao

    @property
    def responsavel(self) -> str:
        return self._responsavel

    @property
    def data_transacao(self):
        return self._data_transacao

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "operacao_id": self._operacao_id,
            "tipo": self._tipo,
            "origem": self._origem,
            "referencia_id": self._referencia_id,
            "valor": self._valor,
            "forma_pagamento": self._forma_pagamento,
            "descricao": self._descricao,
            "responsavel": self._responsavel,
            "data_transacao": formatar_data_br(self._data_transacao)
        }


class ResumoFinanceiro:
    """
    Objeto de Valor (Value Object) que sintetiza os indicadores gerenciais.
    Diferencia com rigor matemático:
    - Saldo Disponível: calculado exclusivamente a partir do histórico de movimentações efetivas de caixa.
    - Receitas: faturamento de pedidos (competência, excluindo cancelados/recusados).
    - Despesas: total de despesas e contas a pagar incorridas.
    - Resultado Operacional Simplificado: Receitas Totais - Despesas Totais.
    - Valores Pendentes: Contas a Receber e Contas a Pagar em aberto.
    """
    def __init__(self, saldo_disponivel: float, total_entradas_caixa: float,
                 total_saidas_caixa: float, receitas_totais: float,
                 despesas_totais: float, contas_a_receber: float,
                 contas_a_pagar_pendentes: float):
        self.saldo_disponivel = round(float(saldo_disponivel or 0.0), 2)
        self.total_entradas_caixa = round(float(total_entradas_caixa or 0.0), 2)
        self.total_saidas_caixa = round(float(total_saidas_caixa or 0.0), 2)
        self.receitas_totais = round(float(receitas_totais or 0.0), 2)
        self.despesas_totais = round(float(despesas_totais or 0.0), 2)
        self.contas_a_receber = round(float(contas_a_receber or 0.0), 2)
        self.contas_a_pagar_pendentes = round(float(contas_a_pagar_pendentes or 0.0), 2)

    @property
    def resultado_operacional_simplificado(self) -> float:
        """Resultado contábil simplificado (Receitas - Despesas)."""
        return round(self.receitas_totais - self.despesas_totais, 2)

    def to_dict(self) -> dict:
        return {
            "saldo_disponivel": self.saldo_disponivel,
            "total_entradas_caixa": self.total_entradas_caixa,
            "total_saidas_caixa": self.total_saidas_caixa,
            "receitas_totais": self.receitas_totais,
            "despesas_totais": self.despesas_totais,
            "resultado_operacional_simplificado": self.resultado_operacional_simplificado,
            "contas_a_receber": self.contas_a_receber,
            "contas_a_pagar_pendentes": self.contas_a_pagar_pendentes
        }
