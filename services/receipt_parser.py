"""
Parser simples para extrair dados estruturados de recibos em PT/EN.

Regras:
- Detecção de idioma: heurística por palavras‑chave (PT/EN) e meses.
- Valor: suporta R$, US$, $, EUR, €, BRL, USD, EUR e formatos 1.234,56 ou 1,234.56.
- Número de recibo: padrões comuns como #XXXX-XXXX-XXXX, n.º XXXX-XXXX, INV-XXXX, etc.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple, Dict, Any


PT_KEYWORDS = [
    r"recibo", r"fatura", r"pagamento", r"cobran[çc]a", r"transa[çc][aã]o",
    r"seu recibo", r"per[ií]odo", r"assinatura", r"n\.?º", r"n\.?o"
]

EN_KEYWORDS = [
    r"receipt", r"invoice", r"payment", r"billing", r"transaction",
    r"your receipt", r"period", r"subscription", r"invoice no\.", r"inv-"
]

PT_MONTHS = r"janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro"
EN_MONTHS = r"january|february|march|april|may|june|july|august|september|october|november|december"


def detect_language(text: str) -> str:
    """Detecta idioma PT/EN por heurística simples.

    Returns: "pt" | "en"
    """
    t = (text or "").lower()
    pt_score = len(re.findall(PT_MONTHS, t)) + sum(1 for k in PT_KEYWORDS if re.search(k, t))
    en_score = len(re.findall(EN_MONTHS, t)) + sum(1 for k in EN_KEYWORDS if re.search(k, t))
    return "pt" if pt_score >= en_score else "en"


_CURRENCY_PATTERNS = [
    # Símbolos e códigos antes/depois
    r"(?P<currency>R\$|US\$|\$|USD|BRL|EUR|€)\s*(?P<amount>\d{1,3}(?:[\.,]\d{3})*[\.,]\d{2})",
    r"(?P<amount>\d{1,3}(?:[\.,]\d{3})*[\.,]\d{2})\s*(?P<currency>R\$|US\$|\$|USD|BRL|EUR|€)",
]


def _normalize_amount_str(amount_str: str, currency: str) -> float:
    """Normaliza string numérica para float, lidando com , e . como separadores.
    Não converte moeda; apenas retorna valor numérico.
    """
    s = amount_str.strip()
    # Se tem vírgula e ponto, decidir pelo último como separador decimal
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s and "." not in s:
        # Formato brasileiro 1.234,56 -> trocar vírgula por ponto
        s = s.replace(".", "").replace(",", ".")
    else:
        # Formato 1,234.56 -> remover vírgulas de milhar
        s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return 0.0


def extract_amount(text: str) -> Optional[Tuple[float, str, str]]:
    """Extrai o primeiro valor monetário encontrado.

    Returns: (valor, moeda, match_str) ou None
    """
    t = text or ""
    for pat in _CURRENCY_PATTERNS:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if m:
            currency = m.group("currency").upper().replace("US$", "USD").replace("R$", "BRL").replace("€", "EUR").replace("$", "USD")
            amount_raw = m.group("amount")
            value = _normalize_amount_str(amount_raw, currency)
            return value, currency, m.group(0)
    return None


_INVOICE_PATTERNS = [
    r"(#|n\.?º|n\.?o|no\.|nf\.|inv[-\s]?)\s*([A-Z]{0,4}-?\d{3,6}(?:-\d{2,6}){0,3})",
    r"\bINV[-_ ]?\d{3,8}\b",
    r"\b\d{3,6}-\d{2,6}-\d{2,6}\b",
]


def extract_invoice_number(text: str) -> Optional[str]:
    """Extrai número de recibo/fatura em formatos comuns."""
    t = text or ""
    for pat in _INVOICE_PATTERNS:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if m:
            # Se houver grupo 2, retorna ele; senão, o match completo
            return (m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(0)).strip()
    return None


def parse_receipt_basic(subject: str, body: str) -> Dict[str, Any]:
    """Extrai idioma, valor e número de recibo de subject/body.

    Retorna dict com: language, amount, currency, amount_match, invoice_number
    """
    combined = f"{subject}\n{body}"
    lang = detect_language(combined)
    amt = extract_amount(combined)
    inv = extract_invoice_number(combined)

    result: Dict[str, Any] = {
        "language": lang,
        "amount": amt[0] if amt else None,
        "currency": amt[1] if amt else None,
        "amount_match": amt[2] if amt else None,
        "invoice_number": inv,
    }
    return result


