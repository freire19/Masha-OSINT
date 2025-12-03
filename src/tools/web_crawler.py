import re
import io
from bs4 import BeautifulSoup
from colorama import Fore, Style

import pdfplumber
import pandas as pd
from curl_cffi import requests


def _clean_text(t: str):
    return re.sub(r"\s+", " ", t).strip()


def _extract_emails(t: str):
    return sorted(set(re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', t)))


def _extract_documents(t: str):
    docs = set()

    for cpf in re.findall(r'\d{3}\.\d{3}\.\d{3}-\d{2}', t):
        docs.add(f"CPF: {cpf}")

    for cnpj in re.findall(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', t):
        docs.add(f"CNPJ: {cnpj}")

    for rg in re.findall(r'\d{1,2}\.\d{3}\.\d{3}-[\dX]', t):
        docs.add(f"RG: {rg}")

    for ssn in re.findall(r'\d{3}-\d{2}-\d{4}', t):
        docs.add(f"SSN(EUA): {ssn}")

    for vat in re.findall(r'[A-Z]{2}\d{8,12}', t):
        docs.add(f"VAT: {vat}")

    return sorted(docs)


def _extract_phones(t: str):
    phones = set()

    intl = re.findall(r'(?:\+|00)[0-9][0-9 \-\(\)]{7,20}', t)
    for p in intl: phones.add(p.strip())

    br = re.findall(r'(?:\(?\d{2}\)?\s?)?(?:9\d{4}|[2-9]\d{3})-?\d{4}', t)
    for p in br: phones.add(p.strip())

    return sorted(phones)


def _download(url: str) -> bytes:
    resp = requests.get(url, impersonate="chrome110", timeout=15)
    return resp.content if resp.status_code == 200 else b""


def _parse_pdf(content: bytes):
    try:
        text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                text += "\n" + t
        return _clean_text(text)
    except:
        return ""


def _parse_other(url: str, content: bytes):
    if url.endswith(".txt"):
        return content.decode(errors="ignore")

    if url.endswith(".csv"):
        try:
            df = pd.read_csv(io.BytesIO(content))
            return df.to_string()
        except:
            return ""

    if url.endswith(".xlsx"):
        try:
            df = pd.read_excel(io.BytesIO(content))
            return df.to_string()
        except:
            return ""

    return ""


def extract_contacts(url: str):
    print(f"{Fore.YELLOW}[*] Crawler: {url}{Style.RESET_ALL}")

    out = {
        "url": url,
        "title": "",
        "emails": [],
        "phones": [],
        "documents": [],
        "social_links": [],
        "raw_text": ""
    }

    try:
        # ARQUIVOS
        if any(url.endswith(ext) for ext in [".pdf", ".csv", ".xlsx", ".txt"]):
            c = _download(url)

            if url.endswith(".pdf"):
                text = _parse_pdf(c)
            else:
                text = _parse_other(url, c)

            out["raw_text"] = text
            out["emails"] = _extract_emails(text)
            out["phones"] = _extract_phones(text)
            out["documents"] = _extract_documents(text)
            return out

        # HTML
        resp = requests.get(url, impersonate="chrome110", timeout=15)

        if resp.status_code == 403:
            return {"error": "403 Firewall/Cloudflare"}

        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}"}

        soup = BeautifulSoup(resp.text, "html.parser")

        for bad in soup(["script", "style", "noscript"]):
            bad.decompose()

        text = _clean_text(soup.get_text(" ", strip=True))

        out["title"] = soup.title.string if soup.title else ""
        out["raw_text"] = text
        out["emails"] = _extract_emails(text)
        out["phones"] = _extract_phones(text)
        out["documents"] = _extract_documents(text)

        socials = ["instagram.com", "facebook.com", "linkedin.com",
                   "twitter.com", "tiktok.com", "youtube.com"]

        links = []
        for a in soup.find_all("a", href=True):
            if any(s in a["href"] for s in socials):
                links.append(a["href"])

        out["social_links"] = sorted(set(links))

        return out

    except Exception as e:
        return {"error": str(e)}
