import datetime
from models.pedido import formatar_data_br

class MovimentacaoEstoque:
    """
    Representa o registro de movimentação de estoque para fins operacionais e auditoria.
    Demonstra ENCAPSULAMENTO validando tipos permitidos (Entrada, Saída, Ajuste) e consistência.
    """

    TIPOS_VALIDOS = ['Entrada', 'Saída', 'Ajuste', 'Reserva', 'Liberação']

    def __init__(self, produto_id: int, tipo: str, quantidade: int,
                 saldo_anterior: int, novo_saldo: int, motivo: str,
                 responsavel: str, data_movimentacao=None, produto_nome: str = "", id: int = None):
        self._id = id
        self._produto_id = int(produto_id)
        self.tipo = tipo
        self.quantidade = quantidade
        self.saldo_anterior = saldo_anterior
        self.novo_saldo = novo_saldo
        self.motivo = motivo
        self.responsavel = responsavel
        self._data_movimentacao = data_movimentacao or datetime.datetime.now()
        self._produto_nome = produto_nome

    @property
    def id(self):
        return self._id

    @property
    def produto_id(self):
        return self._produto_id

    @property
    def produto_nome(self):
        return self._produto_nome

    @property
    def tipo(self):
        return self._tipo

    @tipo.setter
    def tipo(self, valor: str):
        val = str(valor).strip().capitalize()
        if val not in self.TIPOS_VALIDOS:
            raise ValueError(f"Tipo de movimentação inválido. Permitidos: {', '.join(self.TIPOS_VALIDOS)}")
        self._tipo = val

    @property
    def quantidade(self):
        return self._quantidade

    @quantidade.setter
    def quantidade(self, valor: int):
        val = int(valor)
        if val <= 0:
            raise ValueError("A quantidade movimentada deve ser maior que zero.")
        self._quantidade = val

    @property
    def saldo_anterior(self):
        return self._saldo_anterior

    @saldo_anterior.setter
    def saldo_anterior(self, valor: int):
        self._saldo_anterior = int(valor)

    @property
    def novo_saldo(self):
        return self._novo_saldo

    @novo_saldo.setter
    def novo_saldo(self, valor: int):
        val = int(valor)
        if val < 0:
            raise ValueError("O novo saldo não pode ser negativo.")
        self._novo_saldo = val

    @property
    def motivo(self):
        return self._motivo

    @motivo.setter
    def motivo(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError("O motivo da movimentação é obrigatório.")
        self._motivo = str(valor).strip()

    @property
    def responsavel(self):
        return self._responsavel

    @responsavel.setter
    def responsavel(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError("O responsável pela movimentação é obrigatório.")
        self._responsavel = str(valor).strip()

    @property
    def data_movimentacao(self):
        return self._data_movimentacao

    def to_dict(self):
        data_formatada = formatar_data_br(self._data_movimentacao, incluir_hora=True)
        return {
            "id": self._id,
            "produto_id": self._produto_id,
            "produto_nome": self._produto_nome,
            "tipo": self._tipo,
            "quantidade": self._quantidade,
            "saldo_anterior": self._saldo_anterior,
            "novo_saldo": self._novo_saldo,
            "motivo": self._motivo,
            "responsavel": self._responsavel,
            "data_movimentacao": data_formatada,
            "data_formatada": data_formatada
        }
