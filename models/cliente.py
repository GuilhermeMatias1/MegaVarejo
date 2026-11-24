import datetime
from models.pedido import formatar_data_br

class Cliente:
    """
    Representa a entidade de domínio Cliente.
    Demonstra ENCAPSULAMENTO validando e normalizando e-mails, contatos, CPF e endereço.
    """

    def __init__(self, nome: str, email: str, telefone: str = "", cidade: str = "",
                 cpf: str = "", endereco: str = "", criado_em=None, id: int = None):
        self._id = id
        self.nome = nome
        self.email = email
        self.telefone = telefone
        self.cidade = cidade
        self.cpf = cpf
        self.endereco = endereco
        self._criado_em = criado_em or datetime.datetime.now()

    @property
    def id(self):
        return self._id

    @property
    def nome(self):
        return self._nome

    @nome.setter
    def nome(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError("O nome do cliente é obrigatório.")
        self._nome = str(valor).strip()

    @property
    def cpf(self):
        return self._cpf

    @cpf.setter
    def cpf(self, valor: str):
        self._cpf = str(valor).strip() if valor else ""

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError("O e-mail do cliente é obrigatório.")
        self._email = str(valor).strip().lower()

    @property
    def telefone(self):
        return self._telefone

    @telefone.setter
    def telefone(self, valor: str):
        self._telefone = str(valor).strip() if valor else ""

    @property
    def cidade(self):
        return self._cidade

    @cidade.setter
    def cidade(self, valor: str):
        self._cidade = str(valor).strip() if valor else ""

    @property
    def endereco(self):
        return self._endereco

    @endereco.setter
    def endereco(self, valor: str):
        self._endereco = str(valor).strip() if valor else ""

    @property
    def criado_em(self):
        return self._criado_em

    def to_dict(self):
        return {
            "id": self._id,
            "nome": self._nome,
            "cpf": self._cpf or "-",
            "email": self._email,
            "telefone": self._telefone or "-",
            "cidade": self._cidade or "-",
            "endereco": self._endereco or "-",
            "criado_em": formatar_data_br(self._criado_em, incluir_hora=False)
        }
