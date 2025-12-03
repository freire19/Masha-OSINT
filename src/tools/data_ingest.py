import os
import requests
from typing import List
from bs4 import BeautifulSoup
from colorama import Fore, Style, init

# Inicializa colorama para cores funcionarem em qualquer terminal
init(autoreset=True)

# URL oficial de dados abertos da Receita Federal (CNPJ)
BASE_URL = "http://200.152.38.155/CNPJ/"


def listar_arquivos() -> List[str]:
    """
    Lista todos os arquivos .zip disponíveis no servidor da Receita Federal.
    Retorna uma lista de nomes de arquivos.
    """
    print(f"{Fore.CYAN}[*] Conectando ao servidor da Receita Federal...{Style.RESET_ALL}")

    try:
        response = requests.get(BASE_URL, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"{Fore.RED}[!] Erro ao conectar ao servidor: {e}{Style.RESET_ALL}")
        return []

    try:
        soup = BeautifulSoup(response.text, "html.parser")
        arquivos: List[str] = []

        for link in soup.find_all("a"):
            href = link.get("href") or ""
            if href.lower().endswith(".zip"):
                arquivos.append(href)

        if not arquivos:
            print(f"{Fore.YELLOW}[!] Nenhum arquivo .zip encontrado no índice.{Style.RESET_ALL}")

        return sorted(arquivos)

    except Exception as e:
        print(f"{Fore.RED}[!] Erro ao processar HTML da listagem: {e}{Style.RESET_ALL}")
        return []


def baixar_arquivo(nome_arquivo: str) -> str:
    """
    Baixa um arquivo específico da base de CNPJ para a pasta 'downloads/'.
    Retorna o caminho local do arquivo baixado ou string vazia em caso de erro.
    """
    url = BASE_URL + nome_arquivo
    os.makedirs("downloads", exist_ok=True)
    local_path = os.path.join("downloads", nome_arquivo)

    print(f"{Fore.YELLOW}[*] Baixando {nome_arquivo}... (isso pode demorar){Style.RESET_ALL}")
    print(f"{Fore.CYAN}    URL: {url}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}    Destino: {local_path}{Style.RESET_ALL}")

    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = 0
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total += len(chunk)

        tamanho_mb = total / (1024 * 1024)
        print(f"{Fore.GREEN}[+] Download concluído: {local_path} ({tamanho_mb:.2f} MB){Style.RESET_ALL}")
        return local_path

    except Exception as e:
        print(f"{Fore.RED}[!] Falha ao baixar {nome_arquivo}: {e}{Style.RESET_ALL}")
        return ""


def interface_cli() -> None:
    """
    Interface de linha de comando para ingestão de dados da Receita.
    Foca em arquivos de EMPRESAS e SÓCIOS.
    """
    print(f"{Fore.MAGENTA}=== MASHA DATA INGESTION (CNPJ / SÓCIOS) ==={Style.RESET_ALL}")

    arquivos = listar_arquivos()
    if not arquivos:
        print(f"{Fore.RED}[!] Não foi possível obter a lista de arquivos.{Style.RESET_ALL}")
        return

    # Filtra apenas arquivos de Socios e Empresas
    alvos = [f for f in arquivos if "Socios" in f or "Empresas" in f]

    if not alvos:
        print(f"{Fore.YELLOW}[!] Nenhum arquivo de 'Socios' ou 'Empresas' encontrado na listagem.{Style.RESET_ALL}")
        return

    print(f"\n{Fore.WHITE}Arquivos relevantes encontrados (Socios / Empresas):{Style.RESET_ALL}")
    for i, arq in enumerate(alvos):
        print(f"  {i:02d} - {arq}")

    print(f"\n{Fore.CYAN}Digite o número do arquivo para baixar ou:{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}'todos'{Style.RESET_ALL}  → baixar todos os arquivos acima")
    print(f"  {Fore.RED}'q'{Style.RESET_ALL}      → sair sem baixar nada\n")

    escolha = input(f"{Fore.GREEN}Sua escolha: {Style.RESET_ALL}").strip().lower()

    if escolha == "q":
        print(f"{Fore.YELLOW}[i] Operação cancelada pelo usuário.{Style.RESET_ALL}")
        return

    if escolha == "todos":
        print(f"{Fore.MAGENTA}[*] Iniciando download de TODOS os arquivos selecionados...{Style.RESET_ALL}")
        for arq in alvos:
            baixar_arquivo(arq)
        print(f"{Fore.GREEN}[✓] Todos os downloads solicitados foram processados.{Style.RESET_ALL}")
        return

    if escolha.isdigit():
        idx = int(escolha)
        if 0 <= idx < len(alvos):
            nome_arquivo = alvos[idx]
            baixar_arquivo(nome_arquivo)
            return
        else:
            print(f"{Fore.RED}[!] Índice fora da faixa válida.{Style.RESET_ALL}")
            return

    print(f"{Fore.RED}[!] Entrada inválida. Nenhum download foi iniciado.{Style.RESET_ALL}")


if __name__ == "__main__":
    interface_cli()
