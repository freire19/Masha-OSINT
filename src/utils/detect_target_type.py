import re
from typing import Dict


def _only_digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def _format_cpf(digits: str) -> str:
    # Recebe 11 dígitos
    return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"


def _format_cnpj(digits: str) -> str:
    # Recebe 14 dígitos
    return (
        f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/"
        f"{digits[8:12]}-{digits[12:14]}"
    )


def _format_phone_br(digits: str) -> str:
    """
    Formata telefone BR em algo como:
      (92) 99999-9999  ou  (11) 2345-6789
    """
    if len(digits) < 8:
        return digits

    # Tenta separar DDD + número
    if len(digits) in (10, 11):
        ddd = digits[0:2]
        rest = digits[2:]
    else:
        # Sem DDD claro
        ddd = ""
        rest = digits

    if len(rest) == 9:  # prov. celular 9xxxx-xxxx
        primeira = rest[0:5]
        segunda = rest[5:]
    elif len(rest) == 8:
        primeira = rest[0:4]
        segunda = rest[4:]
    else:
        return digits

    if ddd:
        return f"({ddd}) {primeira}-{segunda}"
    return f"{primeira}-{segunda}"


def _format_phone_intl(digits: str) -> str:
    """
    Normaliza telefone internacional como +<digits>,
    sem espaços, só pra deixar consistente.
    """
    if digits.startswith("00"):
        digits = digits[2:]
    if not digits.startswith("+"):
        digits = "+" + digits
    return digits


def detect_target_type(raw: str) -> Dict[str, str]:
    """
    Detecta e normaliza o tipo de alvo.

    Possíveis tipos:
      - email
      - cpf
      - cnpj
      - phone_br
      - phone_intl
      - domain
      - url
      - nome
      - username
      - generic

    Retorno:
      {
        "type": "<tipo>",
        "clean": "<valor_normalizado>",
        "raw": "<entrada_original>"
      }
    """
    original = raw
    s = raw.strip()

    result = {
        "type": "generic",
        "clean": s,
        "raw": original,
    }

    if not s:
        return result

    # --------------------------------------------------
    # 1. E-MAIL
    # --------------------------------------------------
    email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if re.match(email_pattern, s):
        result["type"] = "email"
        result["clean"] = s.lower()
        return result

    # --------------------------------------------------
    # 2. CPF / CNPJ
    # --------------------------------------------------
    digits = _only_digits(s)

    if len(digits) == 11:
        # CPF
        result["type"] = "cpf"
        result["clean"] = _format_cpf(digits)
        return result

    if len(digits) == 14:
        # CNPJ
        result["type"] = "cnpj"
        result["clean"] = _format_cnpj(digits)
        return result

    # --------------------------------------------------
    # 3. TELEFONE (BR / INTERNACIONAL)
    # --------------------------------------------------
    # Critérios:
    #  - Se começa com + ou 00  → phone_intl
    #  - Senão, se 8–11 dígitos → phone_br
    #  - Senão, ignora e segue
    if re.match(r"^\+|\A00", s):
        # Telefone internacional
        only_d = _only_digits(s)
        if len(only_d) >= 7:
            result["type"] = "phone_intl"
            result["clean"] = _format_phone_intl("+" + only_d)
            return result

    if 8 <= len(digits) <= 11:
        # Provavelmente telefone BR
        result["type"] = "phone_br"
        result["clean"] = _format_phone_br(digits)
        return result

    # --------------------------------------------------
    # 4. URL / DOMÍNIO
    # --------------------------------------------------
    lower = s.lower()

    # URL completa (http/https)
    if lower.startswith("http://") or lower.startswith("https://"):
        result["type"] = "url"
        result["clean"] = lower
        return result

    # Domínio simples: tem ponto, não tem espaço, não é email
    if (" " not in s) and ("." in s):
        # Tira http(s):// se o usuário passou sem querer
        clean_domain = re.sub(r"^https?://", "", lower).strip("/")
        result["type"] = "domain"
        result["clean"] = clean_domain
        return result

    # --------------------------------------------------
    # 5. NOME vs USERNAME vs GENÉRICO
    # --------------------------------------------------
    # Se tem espaço e letras → provavelmente nome
    if " " in s and re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ]", s):
        result["type"] = "nome"
        result["clean"] = " ".join(s.split())
        return result

    # Sem espaço, só letras/números/._- → username
    if re.match(r"^[A-Za-z0-9._\-]+$", s) and " " not in s:
        result["type"] = "username"
        result["clean"] = s
        return result

    # --------------------------------------------------
    # 6. GENÉRICO (fallback)
    # --------------------------------------------------
    result["type"] = "generic"
    result["clean"] = s
    return result


# Teste rápido (roda só se chamar diretamente)
if __name__ == "__main__":
    testes = [
        "eujonatasfreire@gmail.com",
        "  123.456.789-00  ",
        "12.345.678/0001-90",
        "(92) 99999-9999",
        "+1 202 555 0199",
        "www.exemplo.com",
        "exemplo.com",
        "https://site.com.br/teste",
        "João da Silva",
        "eujonatasfreire",
        "coisa aleatória 123",
    ]

    for t in testes:
        info = detect_target_type(t)
        print(f"IN: {t!r} -> {info}")
