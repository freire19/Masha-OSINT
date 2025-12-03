import os
import re
import zipfile
import sqlite3
from typing import List, Optional

import pandas as pd
from colorama import Fore, Style, init

# ============================================================
#  CONFIGURAÇÃO BÁSICA
# ============================================================

init(autoreset=True)

DOWNLOAD_DIR = "downloads"
DATA_DIR = "data"
DB_PATH = os.path.join(DATA_DIR, "cnpj.db")


# ============================================================
#  LAYOUTS OFICIAIS (RESUMIDOS) – Receita Federal
#  (Baseado na documentação pública dos Dados Abertos do CNPJ)
# ============================================================

EMPRESAS_COLUMNS = [
    "CNPJ_BASICO",
    "RAZAO_SOCIAL",
    "NATUREZA_JURIDICA",
    "QUALIF_RESPONSAVEL",
    "CAPITAL_SOCIAL",
    "PORTE_EMPRESA",
    "ENTE_FEDERATIVO"
]

SOCIOS_COLUMNS = [
    "CNPJ_BASICO",
    "IDENTIFICADOR_SOCIO",
    "NOME_SOCIO_RAZAO_SOCIAL",
    "CNPJ_CPF_SOCIO",
    "QUALIFICACAO_SOCIO",
    "DATA_ENTRADA_SOCIEDADE",
    "PAIS",
    "CPF_REPRESENTANTE",
    "NOME_REPRESENTANTE",
    "QUALIFICACAO_REPRESENTANTE",
    "FAIXA_ETARIA"
]


# ============================================================
#  FUNÇÕES AUXILIARES
# ============================================================

def _ensure_dirs() -> None:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)


def _detect_table_type(filename: str) -> str:
    """
    Decide o tipo de tabela com base no nome do arquivo:
    - 'empresas'
    - 'socios'
    - 'raw' (desconhecido)
    """
    name_lower = filename.lower()
    if "empresas" in name_lower:
        return "empresas"
    if "socios" in name_lower or "sócios" in name_lower:
        return "socios"
    return "raw"


def _detect_separator(sample: str) -> str:
    """
    Detecta o separador mais provável entre | ; ,
    com base em algumas linhas de amostra.
    """
    lines = [l for l in sample.splitlines() if l.strip()]
    if not lines:
        return "|"

    candidates = ["|", ";", ","]
    scores = {sep: 0 for sep in candidates}

    for line in lines[:20]:
        for sep in candidates:
            scores[sep] += line.count(sep)

    best = max(scores, key=scores.get)
    return best or "|"


def _open_zip_members(zip_path: str) -> List[str]:
    """
    Retorna a lista de arquivos internos (names) de um ZIP.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        return zf.namelist()


def _create_table_if_not_exists(conn: sqlite3.Connection, table_name: str, columns: List[str]) -> None:
    cols_def = ", ".join(f'"{c}" TEXT' for c in columns)
    sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({cols_def});'
    conn.execute(sql)
    conn.commit()


def _infer_columns(table_type: str, n_cols: int) -> List[str]:
    """
    Decide quais colunas usar, baseado no tipo e na quantidade real de colunas do arquivo.
    Se o layout oficial não bater, cria col_1...col_n.
    """
    if table_type == "empresas" and n_cols == len(EMPRESAS_COLUMNS):
        return EMPRESAS_COLUMNS

    if table_type == "socios" and n_cols == len(SOCIOS_COLUMNS):
        return SOCIOS_COLUMNS

    # Fallback: col_1, col_2, ...
    return [f"col_{i+1}" for i in range(n_cols)]


# ============================================================
#  LEITURA & CARGA DO CSV/TXT PARA SQLITE
# ============================================================

def _load_csv_into_db(
    conn: sqlite3.Connection,
    fileobj,
    table_name: str,
    encoding: str = "latin-1"
) -> None:
    """
    Lê um arquivo CSV/TXT (fileobj vindo do ZipFile.open) em chunks
    e grava no SQLite, usando inferência de separador e schema resiliente.
    """
    # Lê uma amostra pra detectar separador e número de colunas
    sample_bytes = fileobj.read(1024 * 64)  # 64 KB
    sample_text = sample_bytes.decode(encoding, errors="ignore")
    sep = _detect_separator(sample_text)

    # Precisamos reabrir o arquivo dentro do zip, porque já lemos parte
    fileobj.seek(0)

    # Primeiro: amostra pequena com pandas pra descobrir n_colunas
    try:
        sample_df = pd.read_csv(
            fileobj,
            sep=sep,
            header=None,
            nrows=5,
            dtype=str,
            encoding=encoding,
            engine="python"
        )
    except Exception as e:
        print(f"{Fore.RED}[!] Falha ao ler amostra do arquivo: {e}{Style.RESET_ALL}")
        return

    n_cols = sample_df.shape[1]
    # Reposiciona para início de novo
    fileobj.seek(0)

    table_type = _detect_table_type(table_name)
    columns = _infer_columns(table_type, n_cols)

    print(f"{Fore.CYAN}[i] Tabela: {table_name} | Tipo inferido: {table_type} | Colunas: {n_cols} | Sep: '{sep}'{Style.RESET_ALL}")

    _create_table_if_not_exists(conn, table_name, columns)

    # Lê em chunks grandes para não explodir memória
    chunksize = 200_000
    total_rows = 0

    try:
        for chunk in pd.read_csv(
            fileobj,
            sep=sep,
            header=None,
            dtype=str,
            encoding=encoding,
            engine="python",
            chunksize=chunksize
        ):
            # Garante número de colunas igual
            if chunk.shape[1] != len(columns):
                # Ajusta ou corta, se vier com mais/menos colunas
                if chunk.shape[1] > len(columns):
                    chunk = chunk.iloc[:, :len(columns)]
                else:
                    # Se tiver menos colunas, completa com NaN
                    for extra in range(len(columns) - chunk.shape[1]):
                        chunk[f"extra_{extra}"] = None

            chunk.columns = columns

            chunk.to_sql(
                table_name,
                conn,
                if_exists="append",
                index=False
            )
            total_rows += len(chunk)

            print(f"{Fore.GREEN}    [+] Inseridas {len(chunk)} linhas (total: {total_rows}){Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}[!] Erro ao carregar CSV em chunks: {e}{Style.RESET_ALL}")
        return

    print(f"{Fore.GREEN}[✓] Importação concluída para {table_name}. Linhas totais: {total_rows}{Style.RESET_ALL}")


def process_zip_file(zip_path: str, conn: sqlite3.Connection) -> None:
    """
    Processa um .zip da Receita:
    - Identifica arquivos internos .csv/.txt
    - Para cada um, carrega no SQLite
    """
    print(f"\n{Fore.MAGENTA}=== Processando ZIP: {zip_path} ==={Style.RESET_ALL}")

    if not os.path.isfile(zip_path):
        print(f"{Fore.RED}[!] Arquivo não encontrado: {zip_path}{Style.RESET_ALL}")
        return

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            members = _open_zip_members(zip_path)

            csv_like = [m for m in members if m.lower().endswith((".csv", ".txt"))]

            if not csv_like:
                print(f"{Fore.YELLOW}[!] Nenhum .csv ou .txt encontrado dentro do ZIP.{Style.RESET_ALL}")
                return

            for member in csv_like:
                print(f"{Fore.CYAN}[*] Lendo membro interno: {member}{Style.RESET_ALL}")
                with zf.open(member, "r") as fobj:
                    # Nome da tabela baseado no tipo detectado
                    table_name = _detect_table_type(member)
                    if table_name == "raw":
                        # Usa nome do arquivo interno (limpo) como tabela
                        base = os.path.splitext(os.path.basename(member))[0]
                        # remove caracteres estranhos
                        base = re.sub(r"[^a-zA-Z0-9_]", "_", base)
                        table_name = base.lower()

                    _load_csv_into_db(conn, fobj, table_name)

    except Exception as e:
        print(f"{Fore.RED}[!] Erro ao processar ZIP {zip_path}: {e}{Style.RESET_ALL}")


# ============================================================
#  INTERFACE CLI
# ============================================================

def interface_cli() -> None:
    """
    Interface interativa para carregar os ZIPs de CNPJ/Sócios em SQLite.
    """
    _ensure_dirs()

    print(f"{Fore.MAGENTA}=== MASHA CNPJ LOADER (Empresas / Sócios) ==={Style.RESET_ALL}")
    print(f"{Fore.WHITE}Base: {DOWNLOAD_DIR}/  ->  DB: {DB_PATH}{Style.RESET_ALL}\n")

    # Lista ZIPs na pasta downloads
    all_zips = [
        f for f in os.listdir(DOWNLOAD_DIR)
        if f.lower().endswith(".zip")
    ]

    if not all_zips:
        print(f"{Fore.RED}[!] Nenhum arquivo .zip encontrado na pasta '{DOWNLOAD_DIR}'.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}    Dica: primeiro rode o data_ingest.py para baixar os dados da Receita.{Style.RESET_ALL}")
        return

    # Ordena para ficar bonito
    all_zips = sorted(all_zips)

    print(f"{Fore.WHITE}ZIPs encontrados:{Style.RESET_ALL}")
    for i, z in enumerate(all_zips):
        print(f"  {i:02d} - {z}")

    print(f"\n{Fore.CYAN}Digite o número do arquivo para importar ou:{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}'todos'{Style.RESET_ALL}  → importar todos os ZIPs da lista")
    print(f"  {Fore.RED}'q'{Style.RESET_ALL}      → sair sem importar\n")

    escolha = input(f"{Fore.GREEN}Sua escolha: {Style.RESET_ALL}").strip().lower()

    if escolha == "q":
        print(f"{Fore.YELLOW}[i] Operação cancelada pelo usuário.{Style.RESET_ALL}")
        return

    # Abre conexão com SQLite
    conn = sqlite3.connect(DB_PATH)

    try:
        if escolha == "todos":
            print(f"{Fore.MAGENTA}[*] Iniciando importação de TODOS os ZIPs...{Style.RESET_ALL}")
            for z in all_zips:
                zip_full_path = os.path.join(DOWNLOAD_DIR, z)
                process_zip_file(zip_full_path, conn)
            print(f"{Fore.GREEN}[✓] Importação de todos os arquivos concluída.{Style.RESET_ALL}")
            return

        if escolha.isdigit():
            idx = int(escolha)
            if 0 <= idx < len(all_zips):
                selected = all_zips[idx]
                zip_full_path = os.path.join(DOWNLOAD_DIR, selected)
                process_zip_file(zip_full_path, conn)
                print(f"{Fore.GREEN}[✓] Importação concluída para {selected}.{Style.RESET_ALL}")
                return
            else:
                print(f"{Fore.RED}[!] Índice fora da faixa válida.{Style.RESET_ALL}")
                return

        print(f"{Fore.RED}[!] Entrada inválida. Nenhuma importação foi iniciada.{Style.RESET_ALL}")
    finally:
        conn.close()


if __name__ == "__main__":
    interface_cli()
