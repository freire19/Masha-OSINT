import os
import json
from typing import Any, Dict, List, Optional

from openai import OpenAI
from dotenv import load_dotenv
from colorama import Fore, Style

from src.utils.detect_target_type import detect_target_type

load_dotenv()


class CerebroDeepSeek:
    """
    Núcleo de raciocínio da Masha usando DeepSeek.

    Métodos principais:
      - plan(target, target_info?)    → Gera dorks avançadas para Google/SerpApi
      - filter_urls(search_results)   → Escolhe quais links valem crawler
      - analyze(analysis_payload)     → Gera dossiê final (summary, key_facts, etc.)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            print(f"{Fore.RED}[!] DEEPSEEK_API_KEY não encontrado no .env{Style.RESET_ALL}")
            raise RuntimeError("DEEPSEEK_API_KEY ausente. Configure no .env.")

        # Modelo padrão pode vir do env, mas com fallback
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")

        self.client = OpenAI(
            base_url=base_url,
            api_key=self.api_key,
        )

    # ============================================================
    #  UTILITÁRIO INTERNO DE CHAMADA
    # ============================================================
    def _chat_json(
        self,
        system_instruction: str,
        user_content: str,
        temperature: float = 0.4,
    ) -> Dict[str, Any]:
        """
        Faz uma chamada ao modelo DeepSeek esperando um JSON válido.
        Retorna:
          - dict com o JSON parseado
          - OU dict de erro {"error": True, "message": "...", "raw_response": "..."}
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            print(f"{Fore.RED}[!] Erro na chamada DeepSeek: {e}{Style.RESET_ALL}")
            return {
                "error": True,
                "message": "Falha na chamada à API DeepSeek.",
                "exception": str(e),
            }

        raw = response.choices[0].message.content
        try:
            return json.loads(raw)
        except json.JSONDecodeError as je:
            print(f"{Fore.RED}[!] DeepSeek retornou JSON inválido{Style.RESET_ALL}")
            return {
                "error": True,
                "message": "Falha ao decodificar JSON retornado pelo modelo.",
                "raw_response": raw,
                "json_error": str(je),
            }

    # ============================================================
    #  FASE 1 – PLANEJAMENTO (DORKS AVANÇADAS)
    # ============================================================
    def plan(
        self,
        target: str,
        target_info: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Gera Google Dorks avançadas com base no tipo de alvo detectado.

        Retorno esperado (sem erro):
        {
          "thought_process": "...",
          "dorks": ["query1", "query2", ...]
        }
        """
        # Detecta tipo de alvo se não foi passado de fora
        info = target_info or detect_target_type(target)
        target_type = info.get("type", "generic")
        clean_value = info.get("clean", target).strip()

        print(
            f"{Fore.CYAN}[*] Masha (Brain: {self.model}) planejando dorks..."
            f" [tipo={target_type}, clean='{clean_value}']{Style.RESET_ALL}"
        )

        # Prompt especializado para dorks avançadas
        system_instruction = """
Você é a Masha, uma agente OSINT GLOBAL especialista em Google Dorks.

Sua tarefa: receber informações sobre um ALVO (pessoa, e-mail, telefone, domínio, cpf/cnpj, username, etc.)
e gerar consultas avançadas extremamente eficazes para uso no Google (via SerpApi).

REGRAS GERAIS:
- Seja estratégico: prefira 4 a 8 dorks BEM diferentes, em vez de 20 variações quase iguais.
- Use operadores como: site:, intext:, intitle:, inurl:, filetype:, OR, "" (aspas) quando fizer sentido.
- Foque em ALTA PRECISÃO, não volume.
- Considere contexto de língua:
  - Para CPF/CNPJ e coisas brasileiras: use .br, gov.br, jusbrasil, etc., com termos em PT-BR.
  - Para vazamentos globais: use termos em EN: leak, breach, paste, database, dump, etc.
- Evite dorks redundantes (mesmo padrão com uma palavra trocada apenas).

ESTRATÉGIAS POR TIPO DE ALVO:

1) Se o tipo for "email":
   - Buscar em:
       • páginas que mencionam exatamente esse email (intext:"email")
       • PDFs, TXTs, CSVs (filetype:pdf, filetype:txt, filetype:csv)
       • leaks: pastebin, throwbin, ghostbin, etc.
   - Exemplos de ideias (NÃO copie literalmente, apenas se inspire):
       • intext:"<email>" -site:facebook.com
       • filetype:pdf "<email>"
       • "<email>" site:linkedin.com
       • "<email>" (leak OR breach OR paste OR password)

2) Se o tipo for "cpf" ou "cnpj":
   - Se possivel varra qualquer lugar na internet , incluindo deep web. 
   - Foque em:
       • filetype:pdf, filetype:xls, filetype:xlsx, filetype:csv
       • sites .br, gov.br, jusbrasil.com.br, tribunais (tj, trt), diários oficiais.
   - Idéias:
       • filetype:pdf "<documento>"
       • filetype:xls OR filetype:xlsx "<documento>"
       • site:.br "<documento>"
       • "CPF <documento>" OR "CNPJ <documento>"
       • "<documento>" (cadastro OR contrato OR edital OR processo OR "diário oficial")

3) Se o tipo for "phone_br" ou "phone_intl":
   - Normalize o número e crie dorks que:
       • Busquem exatamente o número com formatações diferentes (com/sem DDD, com +55, espaços e traços).
       • Use filetype:pdf, filetype:txt, filetype:xlsx para listas/planilhas.
       • Foque em contextos de cadastro, contato, currículo, anúncios.
   - Idéias:
       • "<telefone>" filetype:pdf
       • "<telefone>" (cadastro OR "ficha" OR "contato" OR currículo)
       • "<telefone>" site:.br
       • "<telefone_sem_formatação>" (leak OR "data breach" OR dump)

4) Se o tipo for "domain" ou "url":
   - Misture OSINT de infra + exposição de dados:
       • site:<domínio> com intext:, intitle:
       • subdomínios: site:*.dominio.com -www.dominio.com
       • arquivos internos: filetype:pdf, xls, txt no domínio
       • leaks envolvendo o domínio
   - Idéias:
       • site:<dominio> intext:"CPF" OR intext:"CNPJ"
       • site:<dominio> filetype:pdf
       • "dominio.com" (leak OR breach OR "data leak")
       • inurl:"dominio.com" (admin OR painel OR login)
       • "dominio.com" filetype:txt

5) Se o tipo for "nome":
   - Trate como pessoa física:
       • use aspas com nome completo.
       • combine com cidade, estado, profissão quando possível (se souber).
       • combine com termos: cpf, cnpj, sócio, contrato, associação, currículo, LinkedIn, Lattes.
   - Idéias:
       • "<nome>" (cpf OR cnpj OR "documento" OR "diário oficial")
       • "<nome>" site:linkedin.com
       • "<nome>" site:jusbrasil.com.br
       • "<nome>" filetype:pdf (currículo OR curriculum OR resume)

6) Se o tipo for "username":
   - Foque em redes sociais, paste sites, leaks.
   - Idéias:
       • "<username>" site:instagram.com OR site:twitter.com OR site:tiktok.com
       • "<username>" ("github" OR "gitlab" OR "bitbucket")
       • "<username>" (pastebin OR throwbin OR ghostbin OR pastesite)
       • "<username>" ("steam" OR "epic games" OR "psn" OR "xbox")

7) Se o tipo for "generic":
   - Use o bom senso: combine o termo principal com:
       • filetype:pdf,xls,xlsx,txt
       • "cpf", "cnpj", "contato", "sócio", "parceiro", "cliente", "fornecedor" dependendo do contexto.

FORMATO DE RESPOSTA (OBRIGATÓRIO):
Retorne APENAS um JSON no formato:

{
  "thought_process": "Explique em 2-5 frases curtas sua estratégia para este alvo.",
  "dorks": [
    "primeira consulta avançada",
    "segunda consulta",
    "terceira consulta"
  ]
}

- Não use markdown.
- Não adicione nenhum texto fora do JSON.
"""

        # Pacote que vai no "user"
        user_payload = {
            "target_raw": target,
            "target_type": target_type,
            "clean_value": clean_value,
        }

        data = self._chat_json(
            system_instruction=system_instruction,
            user_content=json.dumps(user_payload, ensure_ascii=False),
            temperature=0.5,
        )

        # Garantir campos mínimos
        if not data.get("error"):
            data.setdefault("thought_process", "")
            data.setdefault("dorks", [])

        return data

    # ============================================================
    #  FASE 2.5 – FILTRO DE URLS PARA CRAWLER
    # ============================================================
    def filter_urls(self, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Recebe a lista de resultados de busca (cada item com title, link, snippet, source)
        e retorna JSON:

        {
          "selected_urls": ["url1", "url2", ...],
          "reasoning": "texto explicando por que escolheu essas"
        }
        """
        print(f"{Fore.CYAN}[*] Masha (Brain) filtrando URLs para crawler...{Style.RESET_ALL}")

        system_instruction = """
Você é a Masha, agente OSINT. Sua tarefa é SELECIONAR quais URLs devem ser visitadas
por um crawler que extrai emails, telefones e documentos.

Você receberá uma lista de resultados de busca Google (title, link, snippet, source).

REGRAS:
- Priorize:
  • sites oficiais do alvo (domínio do próprio alvo, homepages, /contato, /sobre, /quem-somos).
  • páginas de "contato", "fale conosco", "trabalhe conosco", "cadastro".
  • PDFs, TXTs, XLS/XLSX se o link parecer direto para arquivo.
  • redes sociais principais do alvo (quando o foco for pessoa ou empresa específica).
- Evite:
  • Notícias genéricas que apenas mencionam o nome.
  • Sites de perguntas e respostas sem dados de contato.
  • Páginas que claramente não têm nada a ver com o alvo (outros homônimos irrelevantes).

FORMATO DE RESPOSTA:
Retorne APENAS um JSON:

{
  "selected_urls": ["url1", "url2", ... no máximo 5],
  "reasoning": "Explique em 2-4 frases como escolheu esses links."
}

- Não use markdown.
- Não escreva nada fora do JSON.
"""

        # Mandamos só os campos que importam
        compact_results = [
            {
                "title": r.get("title"),
                "link": r.get("link"),
                "snippet": r.get("snippet"),
                "source": r.get("source", "google"),
            }
            for r in search_results
        ]

        user_content = json.dumps({"results": compact_results}, ensure_ascii=False)

        data = self._chat_json(
            system_instruction=system_instruction,
            user_content=user_content,
            temperature=0.3,
        )

        if not data.get("error"):
            data.setdefault("selected_urls", [])
            data.setdefault("reasoning", "")

        return data

    # ============================================================
    #  FASE 4 – ANÁLISE FINAL / DOSSIÊ
    # ============================================================
    def analyze(self, analysis_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recebe um pacote agregando tudo:

        {
          "target": {
            "raw_input": "...",
            "type": "email|cpf|cnpj|nome|domain|url|phone_br|phone_intl|username|generic"
          },
          "collected": [
            {"type": "google_search", "data": [...]},
            {"type": "website_crawl", "data": {...}},
            {"type": "social_profiles", "data": [...]}
          ]
        }

        Retorna JSON:

        {
          "summary": "texto corrido PT-BR",
          "key_facts": ["fato1", "fato2"],
          "extracted_contacts": ["email / telefone / doc"],
          "confidence_score": 0-100
        }
        """
        print(f"{Fore.CYAN}[*] Masha (Brain) gerando dossiê final...{Style.RESET_ALL}")

        system_instruction = """
Você é a Masha, analista OSINT sênior.

Você receberá um PACOTE com:
  - target: dados sobre o alvo (tipo, valor bruto)
  - collected: lista de blocos de dados
      • google_search: resultados de busca
      • website_crawl: páginas já "invadidas" pelo crawler (com emails, telefones, documentos)
      • social_profiles: contas encontradas por username (Instagram, GitHub, etc.)

Sua tarefa:
  1) Ler tudo.
  2) Produzir um dossiê curto, CLARO e objetivo em PT-BR.
  3) Destacar:
      - quem/qual é o alvo (interpretação OSINT)
      - principais vínculos (empresas, perfis, sites)
      - contatos confirmados (emails, telefones, documentos relevantes)
      - eventuais inconsistências ou homônimos (nomes iguais com pessoas diferentes)

REGRAS:
- Seja factual, não invente dados.
- Se tiver pouca informação, deixe isso explícito.
- Se surgirem homônimos, explique a ambiguidade.
- Priorize dados que venham de crawler (emails, telefones, documentos) e social_profiles.

FORMATO DE RESPOSTA (OBRIGATÓRIO):
Retorne APENAS um JSON:

{
  "summary": "Resumo executivo em 1-3 parágrafos curtos em PT-BR.",
  "key_facts": ["fato1", "fato2", "fato3"],
  "extracted_contacts": ["lista de emails, telefones ou docs importantes"],
  "confidence_score": 0-100
}

- key_facts deve ser uma lista de frases curtas em PT-BR.
- extracted_contacts deve ser uma lista (pode estar vazia).
- confidence_score:
    • 0-30  → quase nada confiável / pouca informação
    • 31-60 → confiança média
    • 61-85 → boa confiança
    • 86-100→ alta confiança

- Não use markdown.
- Não adicione NENHUMA explicação fora do JSON.
"""

        user_content = json.dumps(analysis_payload, ensure_ascii=False)

        data = self._chat_json(
            system_instruction=system_instruction,
            user_content=user_content,
            temperature=0.35,
        )

        if not data.get("error"):
            data.setdefault("summary", "")
            data.setdefault("key_facts", [])
            data.setdefault("extracted_contacts", [])
            data.setdefault("confidence_score", 0)

        return data


if __name__ == "__main__":
    # Teste rápido de dorks
    brain = CerebroDeepSeek()
    alvo = "eujonatasfreire@gmail.com"
    info = detect_target_type(alvo)
    res = brain.plan(alvo, target_info=info)
    print(json.dumps(res, indent=2, ensure_ascii=False))
