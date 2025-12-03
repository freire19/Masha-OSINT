import os
import sys
import json
import time
from typing import List, Dict, Any, Optional

from colorama import Fore, Style, init

from src.config.masha_config import HAS_LOCAL_CNPJ
from src.utils.detect_target_type import detect_target_type
from src.agents.brain import CerebroDeepSeek
from src.tools.web_search import search_google
from src.tools.web_crawler import extract_contacts
from src.tools.username_check import search_username  # Sherlock


BANNER = r"""
   ******        ******         ************           ********
   *******      *******        ******  ******        ************
   ********    ********       ******    ******                **** 
   ****  ***  ***  ****      ******************      ************ 
   ****   ******   ****     ********************    *****
   ****            ****    ******          ******    *****    ****
   ****            ****  *******            *******   **********   

        MASHA OSINT v3.0 – Full Spectrum
        DeepSeek + SerpAPI + Crawler + Sherlock
"""

HELP_TARGET_FORMS = """
FORMAS DE ALVO SUPORTADAS (EXEMPLOS):
  • Nome pessoa:            João da Silva
  • E-mail:                 alvo.exemplo@gmail.com
  • Telefone BR:            (92) 99999-9999  ou  92 99999-9999
  • Telefone Internacional: +1 202 555 0199
  • CPF:                    123.456.789-00
  • CNPJ:                   12.345.678/0001-90
  • Domínio/Site:           exemplo.com  |  www.exemplo.com
  • Username:               eujonatasfreire, johndoe2025
"""

MENU_TEXT = """
=== MENU PRINCIPAL ===
  [1] e-mail
  [2] pessoa (nome completo)
  [3] domínio / site
  [4] telefone (BR ou internacional)
  [5] documento (CPF / CNPJ)
  [6] Modo livre(qualquer coisa)
  [9] Modo automação (JSON-only para um alvo)
  [0] Sair
"""


def parse_cli_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="MASHA OSINT v3.0 – Full Spectrum OSINT Agent"
    )
    parser.add_argument(
        "-t",
        "--target",
        help="Alvo direto para investigação (pula o menu interativo)",
    )
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Modo silencioso (sem prints de progresso)",
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Imprimir apenas o JSON final do dossiê no stdout",
    )
    return parser.parse_args()


def run_investigation(
    target: str,
    bot: CerebroDeepSeek,
    has_local_cnpj: bool,
    silent: bool = False,
    json_output: bool = False,
) -> Dict[str, Any]:
    """
    Executa o pipeline completo de OSINT para um alvo.
    Retorna o dossiê (dict).
    """
    collected_data: List[Dict[str, Any]] = []

    if not silent:
        print(f"\n>>> Iniciando investigação sobre: {target}")

    # -------------------------------------------------------
    # Detecção de tipo de alvo
    # -------------------------------------------------------
    target_info = detect_target_type(target)
    target_type = target_info.get("type", "generic")
    clean_value = target_info.get("clean", target)

    if not silent:
        print(
            f"{Fore.CYAN}[i] Tipo detectado: {target_type} | "
            f"Valor normalizado: {clean_value}{Style.RESET_ALL}"
        )

        # Info sobre base local de CNPJ
        if has_local_cnpj:
            print(
                f"{Fore.CYAN}[i] Base local de CNPJ detectada. "
                f"(Futuras versões usarão Data Lake para enriquecimento){Style.RESET_ALL}"
            )
        else:
            print(
                f"{Fore.CYAN}[i] Base de CNPJ local não encontrada. "
                f"Pulando Fase 0 (Consulta Receita).{Style.RESET_ALL}"
            )

    # =========================================================
    # FASE 1: PLANEJAMENTO (Google Dorks)
    # =========================================================
    if not silent:
        print(f"\n{Fore.WHITE}--- FASE 1: Planejamento (DeepSeek) ---{Style.RESET_ALL}")

    plan_prompt = (
        f"Alvo bruto: {target}\n"
        f"Tipo detectado: {target_type}\n"
        f"Valor normalizado: {clean_value}\n"
    )

    plan = bot.plan(plan_prompt)

    if plan.get("error"):
        if not silent:
            print(f"{Fore.RED}[!] Erro no Brain: {plan.get('message')}{Style.RESET_ALL}")
        return plan

    dorks = plan.get("dorks", [])
    thought_process = plan.get("thought_process", "")

    if not silent:
        if thought_process:
            print(
                f"{Fore.MAGENTA}[*] Thought process (resumido): "
                f"{thought_process}{Style.RESET_ALL}"
            )
        print(f"{Fore.YELLOW}Dorks geradas:{Style.RESET_ALL}")
        for q in dorks:
            print(f"  - {q}")

    # =========================================================
    # FASE 2: VARREDURA GLOBAL (Google Search)
    # =========================================================
    if not silent:
        print(f"\n{Fore.WHITE}--- FASE 2: Varredura Google (SerpAPI) ---{Style.RESET_ALL}")

    search_results_raw: List[Dict[str, Any]] = []

    for query in dorks:
        results = search_google(query)

        if isinstance(results, dict) and ("error" in results or "warning" in results):
            if not silent:
                msg = results.get("error") or results.get("warning")
                print(
                    f"{Fore.RED}[-] Falha na busca '{query}': "
                    f"{msg}{Style.RESET_ALL}"
                )
        else:
            if isinstance(results, list):
                if not silent:
                    print(
                        f"{Fore.GREEN}[+] Resultados para '{query}': "
                        f"{len(results)}{Style.RESET_ALL}"
                    )
                search_results_raw.extend(results)
            else:
                if not silent:
                    print(
                        f"{Fore.YELLOW}[?] Formato inesperado de resultados para "
                        f"'{query}'{Style.RESET_ALL}"
                    )

        time.sleep(1)

    collected_data.append(
        {
            "type": "google_search",
            "data": search_results_raw,
        }
    )

    # =========================================================
    # FASE 2.5: SHERLOCK (Busca de Username)
    # =========================================================
    potential_username: Optional[str] = None

    # Se for e-mail, extrai parte antes de @
    if target_type == "email":
        local_part = clean_value.split("@")[0]
        potential_username = local_part
    # Se foi classificado como username ou generic sem espaço/ponto, aproveita
    elif target_type in ("username", "generic"):
        if " " not in clean_value and "." not in clean_value:
            potential_username = clean_value

    if potential_username:
        if not silent:
            print(
                f"\n{Fore.WHITE}--- FASE 2.5: Caça ao Username "
                f"'{potential_username}' (Sherlock) ---{Style.RESET_ALL}"
            )
        social_profiles = search_username(potential_username)
        if social_profiles:
            collected_data.append(
                {
                    "type": "social_profiles",
                    "data": social_profiles,
                }
            )

    # =========================================================
    # FASE 3: INFILTRAÇÃO (Crawler)
    # =========================================================
    if search_results_raw:
        if not silent:
            print(f"\n{Fore.WHITE}--- FASE 3: Infiltração (Crawler) ---{Style.RESET_ALL}")

        top_results = search_results_raw[:10]
        decision = bot.filter_urls(top_results)

        if decision.get("error"):
            if not silent:
                print(
                    f"{Fore.RED}[!] Erro ao filtrar URLs: "
                    f"{decision.get('message')}{Style.RESET_ALL}"
                )
            targets_to_crawl: List[str] = []
        else:
            targets_to_crawl = decision.get("selected_urls", [])

        if targets_to_crawl:
            if not silent:
                print(
                    f"{Fore.RED}[!] Alvos Selecionados para Crawler: "
                    f"{len(targets_to_crawl)}{Style.RESET_ALL}"
                )
            for url in targets_to_crawl:
                if not silent:
                    print(f"{Fore.YELLOW}   -> Crawler atacando: {url}{Style.RESET_ALL}")
                crawl_data = extract_contacts(url)

                if isinstance(crawl_data, dict) and "error" not in crawl_data:
                    emails = crawl_data.get("emails", [])
                    phones = crawl_data.get("phones", [])

                    if not silent:
                        if emails or phones:
                            print(
                                f"{Fore.GREEN}      SUCESSO! Emails: {len(emails)} | "
                                f"Telefones: {len(phones)}{Style.RESET_ALL}"
                            )
                        else:
                            print(
                                f"{Fore.YELLOW}      Acesso ok, mas sem contatos "
                                f"visíveis.{Style.RESET_ALL}"
                            )

                    collected_data.append(
                        {
                            "type": "website_crawl",
                            "data": crawl_data,
                        }
                    )
                else:
                    err_msg = (
                        crawl_data.get("error")
                        if isinstance(crawl_data, dict)
                        else "Erro desconhecido"
                    )
                    if not silent:
                        print(
                            f"{Fore.RED}      Falha ao acessar {url}: "
                            f"{err_msg}{Style.RESET_ALL}"
                        )
        else:
            if not silent:
                print(
                    f"{Fore.CYAN}[i] Masha decidiu não invadir nenhum site nesta rodada."
                    f"{Style.RESET_ALL}"
                )
    else:
        if not silent:
            print(
                f"{Fore.YELLOW}[!] Nenhum resultado de busca para usar na Fase 3."
                f"{Style.RESET_ALL}"
            )

    # =========================================================
    # FASE 4: ANÁLISE FINAL (Dossiê)
    # =========================================================
    if not silent:
        print(f"\n{Fore.WHITE}--- FASE 4: Dossiê Final (DeepSeek Reasoner) ---{Style.RESET_ALL}")

    analysis_payload = {
        "target": {
            "raw_input": target,
            "type": target_type,
            "clean": clean_value,
        },
        "context": {
            "has_local_cnpj": has_local_cnpj,
            "potential_username": potential_username,
        },
        "collected": collected_data,
    }

    dossier = bot.analyze(analysis_payload)

    # Se houve erro no Brain
    if dossier.get("error"):
        if not silent:
            print(
                f"{Fore.RED}[!] Erro ao gerar dossiê: "
                f"{dossier.get('message')}{Style.RESET_ALL}"
            )
        return dossier

    # -------------------------------------------------------
    # Saída normal (não silenciosa)
    # -------------------------------------------------------
    if not silent:
        print(
            f"\n{Fore.MAGENTA}=== RESUMO EXECUTIVO ==={Style.RESET_ALL}\n"
            f"{Fore.WHITE}{dossier.get('summary', '')}{Style.RESET_ALL}"
        )

        print(f"\n{Fore.GREEN}>> Contatos extraídos:{Style.RESET_ALL}")
        for contact in dossier.get("extracted_contacts", []):
            print(f"  [+] {contact}")

        print(f"\n{Fore.YELLOW}>> Fatos chave:{Style.RESET_ALL}")
        for fact in dossier.get("key_facts", []):
            print(f"  - {fact}")

        score = dossier.get("confidence_score", 0)
        print(
            f"\n{Fore.CYAN}>> Nível de confiança: {score} / 100"
            f"{Style.RESET_ALL}"
        )

        # Exibe perfis sociais encontrados pelo Sherlock
        if potential_username:
            print(
                f"\n{Fore.CYAN}[Pegada Digital - Username "
                f"'{potential_username}']:{Style.RESET_ALL}"
            )
            for item in collected_data:
                if item.get("type") == "social_profiles":
                    for perfil in item.get("data", []):
                        print(
                            f"  - {perfil.get('platform')}: "
                            f"{perfil.get('url')}"
                        )

    # -------------------------------------------------------
    # Log em arquivo
    # -------------------------------------------------------
    safe_target = (
        clean_value.replace("@", "_at_")
        .replace(" ", "_")
        .replace("/", "_")
        .replace(".", "_")
    )
    os.makedirs("logs", exist_ok=True)
    filename = os.path.join("logs", f"Masha_{safe_target}_FULL.json")
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "target": analysis_payload["target"],
                    "context": analysis_payload["context"],
                    "dossier": dossier,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        if not silent:
            print(f"\n[i] Dossiê salvo em: {filename}")
    except Exception as e:
        if not silent:
            print(f"{Fore.RED}[!] Falha ao salvar log: {e}{Style.RESET_ALL}")

    # -------------------------------------------------------
    # Saída JSON-only (para automação / integração)
    # -------------------------------------------------------
    if json_output:
        print(
            json.dumps(
                {
                    "target": analysis_payload["target"],
                    "context": analysis_payload["context"],
                    "dossier": dossier,
                },
                ensure_ascii=False,
            )
        )

    return dossier


def interactive_menu(bot: CerebroDeepSeek, has_local_cnpj: bool) -> None:
    while True:
        os.system("clear")
        print(Fore.MAGENTA + BANNER + Style.RESET_ALL)
        print(HELP_TARGET_FORMS)
        print(MENU_TEXT)

        choice = input("Selecione uma opção: ").strip()

        if choice == "0":
            print("Saindo...")
            break

        # Mapeia opção -> prompt específico
        if choice == "1":
            target = input("Digite o e-mail do alvo: ").strip()
        elif choice == "2":
            target = input("Digite o NOME COMPLETO da pessoa: ").strip()
        elif choice == "3":
            target = input("Digite o domínio ou URL (ex: exemplo.com): ").strip()
        elif choice == "4":
            target = input("Digite o telefone (BR ou internacional): ").strip()
        elif choice == "5":
            target = input("Digite o CPF ou CNPJ (com pontos e traços): ").strip()
        elif choice == "6":
            target = input("Digite o alvo (qualquer formato): ").strip()
        elif choice == "9":
            target = input("Digite o alvo para modo automação (JSON-only): ").strip()
            if not target:
                input("\n[!] Alvo vazio. Pressione ENTER para voltar ao menu...")
                continue
            # Aqui usamos modo silencioso + JSON-only
            run_investigation(
                target=target,
                bot=bot,
                has_local_cnpj=has_local_cnpj,
                silent=True,
                json_output=True,
            )
            input("\nPressione ENTER para voltar ao menu...")
            continue
        else:
            print(f"{Fore.RED}[!] Opção inválida.{Style.RESET_ALL}")
            time.sleep(1.5)
            continue

        if not target:
            input("\n[!] Alvo vazio. Pressione ENTER para voltar ao menu...")
            continue

        run_investigation(
            target=target,
            bot=bot,
            has_local_cnpj=has_local_cnpj,
            silent=False,
            json_output=False,
        )

        input("\nPressione ENTER para voltar ao menu...")


def main():
    init(autoreset=True)
    args = parse_cli_args()

    # Usa flag de config OU existência do arquivo local
    has_local_cnpj = HAS_LOCAL_CNPJ or os.path.exists("data/cnpj.db")

    # Instancia o cérebro uma única vez
    bot = CerebroDeepSeek()

    # -------------------------------------------
    # MODO CLI (automação): alvo direto por parâmetro
    # -------------------------------------------
    if args.target:
        run_investigation(
            target=args.target,
            bot=bot,
            has_local_cnpj=has_local_cnpj,
            silent=args.silent,
            json_output=args.json_output,
        )
        return

    # -------------------------------------------
    # MODO INTERATIVO (menu)
    # -------------------------------------------
    interactive_menu(bot, has_local_cnpj)


if __name__ == "__main__":
    main()
