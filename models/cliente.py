import datetime
import re
from models.pedido import formatar_data_br

def validar_cpf(cpf_str: str) -> str:
    """
    Valida os dígitos verificadores de um CPF e retorna apenas os 11 dígitos numéricos limpos.
    Lança ValueError se o formato for inválido ou se os dígitos verificadores falharem.
    """
    if not cpf_str:
        raise ValueError("O CPF do cliente é obrigatório.")

    # Remove pontuações e caracteres não numéricos
    digitos = re.sub(r'\D', '', str(cpf_str).strip())

    if len(digitos) != 11:
        raise ValueError(f"CPF inválido: deve conter exatamente 11 dígitos (informado: {len(digitos)}).")

    # Rejeita CPFs formados por dígitos repetidos conhecidos (ex: 111.111.111-11)
    if digitos == digitos[0] * 11:
        raise ValueError("CPF inválido: sequência de números repetidos não permitida.")

    # Cálculo do primeiro dígito verificador
    soma_1 = sum(int(digitos[i]) * (10 - i) for i in range(9))
    resto_1 = (soma_1 * 10) % 11
    digito_esperado_1 = 0 if resto_1 == 10 else resto_1

    if int(digitos[9]) != digito_esperado_1:
        raise ValueError("CPF inválido: primeiro dígito verificador incorreto.")

    # Cálculo do segundo dígito verificador
    soma_2 = sum(int(digitos[i]) * (11 - i) for i in range(10))
    resto_2 = (soma_2 * 10) % 11
    digito_esperado_2 = 0 if resto_2 == 10 else resto_2

    if int(digitos[10]) != digito_esperado_2:
        raise ValueError("CPF inválido: segundo dígito verificador incorreto.")

    return digitos

def formatar_cpf_br(cpf_limpo: str) -> str:
    """Formata 11 dígitos como XXX.XXX.XXX-XX."""
    if not cpf_limpo:
        return "-"
    d = re.sub(r'\D', '', str(cpf_limpo))
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return cpf_limpo

class Endereco:
    """
    Objeto de Valor (Value Object) que encapsula os dados de endereço do Cliente.
    Demonstra ENCAPSULAMENTO e coesão de dados de localização.
    """
    def __init__(self, cep: str = "", logradouro: str = "", numero: str = "",
                 complemento: str = "", bairro: str = "", cidade: str = "", uf: str = ""):
        self.cep = cep
        self.logradouro = logradouro
        self.numero = numero
        self.complemento = complemento
        self.bairro = bairro
        self.cidade = cidade
        self.uf = uf

    @property
    def cep(self):
        return self._cep

    @cep.setter
    def cep(self, valor: str):
        v = re.sub(r'\D', '', str(valor or ""))
        self._cep = f"{v[:5]}-{v[5:8]}" if len(v) == 8 else (v or "")

    @property
    def logradouro(self):
        return self._logradouro

    @logradouro.setter
    def logradouro(self, valor: str):
        self._logradouro = str(valor or "").strip()

    @property
    def numero(self):
        return self._numero

    @numero.setter
    def numero(self, valor: str):
        self._numero = str(valor or "").strip()

    @property
    def complemento(self):
        return self._complemento

    @complemento.setter
    def complemento(self, valor: str):
        self._complemento = str(valor or "").strip()

    @property
    def bairro(self):
        return self._bairro

    @bairro.setter
    def bairro(self, valor: str):
        self._bairro = str(valor or "").strip()

    @property
    def cidade(self):
        return self._cidade

    @cidade.setter
    def cidade(self, valor: str):
        self._cidade = str(valor or "").strip()

    @property
    def uf(self):
        return self._uf

    @uf.setter
    def uf(self, valor: str):
        self._uf = str(valor or "").strip().upper()[:2]

    def texto_completo(self) -> str:
        """Monta a string textual formatada para entrega."""
        partes = []
        if self._logradouro:
            p = self._logradouro
            if self._numero:
                p += f", {self._numero}"
            if self._complemento:
                p += f" - {self._complemento}"
            partes.append(p)
        if self._bairro:
            partes.append(self._bairro)
        cid_uf = []
        if self._cidade: cid_uf.append(self._cidade)
        if self._uf: cid_uf.append(self._uf)
        if cid_uf:
            partes.append(" - ".join(cid_uf))
        if self._cep:
            partes.append(f"CEP {self._cep}")
        return ", ".join(partes) if partes else ""

    def to_dict(self):
        return {
            "cep": self._cep,
            "logradouro": self._logradouro,
            "numero": self._numero,
            "complemento": self._complemento,
            "bairro": self._bairro,
            "cidade": self._cidade,
            "uf": self._uf,
            "texto_completo": self.texto_completo()
        }


class Cliente:
    """
    Representa a entidade de domínio Cliente.
    Demonstra ENCAPSULAMENTO validando e normalizando e-mails, contatos, CPF obrigatório com dígitos e endereço completo.
    """

    def __init__(self, nome: str, email: str, cpf: str, telefone: str = "",
                 cep: str = "", logradouro: str = "", numero: str = "", complemento: str = "",
                 bairro: str = "", cidade: str = "", uf: str = "", endereco: str = "",
                 criado_em=None, id: int = None):
        self._id = id
        self.nome = nome
        self.email = email
        self.cpf = cpf
        self.telefone = telefone

        # Se foi passado um endereço textual legado sem partes, mas temos cidade
        if endereco and not logradouro and not cep:
            # Compatibilidade com dados legados
            self._endereco_obj = Endereco(cidade=cidade or "", logradouro=endereco)
        else:
            self._endereco_obj = Endereco(
                cep=cep,
                logradouro=logradouro,
                numero=numero,
                complemento=complemento,
                bairro=bairro,
                cidade=cidade,
                uf=uf
            )

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
        return self._cpf_limpo

    @property
    def cpf_formatado(self):
        return formatar_cpf_br(self._cpf_limpo)

    @cpf.setter
    def cpf(self, valor: str):
        # Validação obrigatória dos dígitos verificadores
        self._cpf_limpo = validar_cpf(valor)

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError("O e-mail do cliente é obrigatório.")
        e = str(valor).strip().lower()
        if '@' not in e or '.' not in e:
            raise ValueError("Formato de e-mail inválido.")
        self._email = e

    @property
    def telefone(self):
        return self._telefone

    @telefone.setter
    def telefone(self, valor: str):
        self._telefone = str(valor).strip() if valor else ""

    @property
    def endereco(self) -> Endereco:
        return self._endereco_obj

    @property
    def cidade(self):
        return self._endereco_obj.cidade

    @cidade.setter
    def cidade(self, valor: str):
        self._endereco_obj.cidade = valor

    @property
    def criado_em(self):
        return self._criado_em

    def to_dict(self):
        end_texto = self._endereco_obj.texto_completo()
        return {
            "id": self._id,
            "nome": self._nome,
            "cpf": self._cpf_limpo,
            "cpf_formatado": self.cpf_formatado,
            "email": self._email,
            "telefone": self._telefone or "-",
            "cidade": self._endereco_obj.cidade or "-",
            "uf": self._endereco_obj.uf or "-",
            "cep": self._endereco_obj.cep or "-",
            "logradouro": self._endereco_obj.logradouro or "-",
            "numero": self._endereco_obj.numero or "-",
            "complemento": self._endereco_obj.complemento or "",
            "bairro": self._endereco_obj.bairro or "-",
            "endereco": end_texto or "-",
            "endereco_completo": end_texto or "-",
            "criado_em": formatar_data_br(self._criado_em, incluir_hora=False)
        }
