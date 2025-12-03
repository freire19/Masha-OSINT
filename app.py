import os
import json
import time

import streamlit as st

from src.config.masha_config import HAS_LOCAL_CNPJ
from src.agents.brain import CerebroDeepSeek
from src.tools.web_search import search_google
from src.tools.web_crawler import extract_contacts
from src.tools.username_check import search_username
from src.utils.detect_target_type import detect_target_type

# === Integração com Streamlit Secrets (para rodar na nuvem) ===
try:
    if "DEEPSEEK_API_KEY" in st.secrets:
        os.environ["DEEPSEEK_API_KEY"] = st.secrets["DEEPSEEK_API_KEY"]
    if "SERPAPI_KEY" in st.secrets:
        os.environ["SERPAPI_KEY"] = st.secrets["SERPAPI_KEY"]
except Exception:
    # Localmente, se não tiver st.secrets configurado, ignora
    pass

# Configuração da Página (Título, Ícone)
st.set_page_config(
    page_title="Masha OSINT Panel",
    page_icon="🕵️‍♀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilo CSS Customizado (Modo Hacker/Dark)
st.markdown(
    """
<style>
    .stButton>button {
        width: 100%;
        background-color: #00ff00;
        color: black;
        font-weight: bold;
    }
    .reportview-container, .stApp {
        background: #0e1117;
    }
</style>
""",
    unsafe_allow_html=True,
)

# --- BARRA LATERAL (Controles) ---
with st.sidebar:
    st.image("https://img.icons8.com/ios-filled/100/4a90e2/spy.png", width=80)
    st.title("Masha Control")
    st.markdown("---")

    mode = st.radio(
        "Modo de Operação",
        ["Investigação Completa", "Apenas Busca", "Apenas Crawler"],
    )

    st.markdown("### 🔒 Segurança")
    senha = st.text_input("Chave de Acesso", type="password")

    # Senha pode vir de variável de ambiente no futuro
    expected_password = "bodofrito"

    if senha != expected_password:
        st.warning("Acesso bloqueado. Informe a chave correta.")
        st.stop()
    else:
        st.success("Sistema Ativo")

    st.markdown("---")
    if HAS_LOCAL_CNPJ:
        st.success(
            "Base local de CNPJ detectada (modo híbrido pronto, ainda não ativado)."
        )
    else:
        st.info("Modo atual: OSINT online (sem base local de CNPJ).")

# --- TELA PRINCIPAL ---

st.title("🕵️‍♀️ Masha OSINT v3.0 (Web)")
st.markdown("### Central de Inteligência Autônoma – DeepSeek + SerpAPI + Crawler + Sherlock")

# Formas suportadas (ajuda visual)
with st.expander("📌 Formas de alvo suportadas (exemplos)", expanded=True):
    st.markdown(
        """
- **Nome pessoa:** João da Silva  
- **E-mail:** alvo.exemplo@gmail.com  
- **Telefone BR:** (92) 99999-9999  ou  92 99999-9999  
- **Telefone Internacional:** +1 202 555 0199  
- **CPF:** 123.456.789-00  
- **CNPJ:** 12.345.678/0001-90  
- **Domínio/Site:** exemplo.com  |  www.exemplo.com  
- **Username:** eujonatasfreire, johndoe2025  
        """
    )

# Input do Alvo
col1, col2 = st.columns([3, 1])
with col1:
    target = st.text_input(
        "Alvo (Email, Nome, Site, Username, CPF/CNPJ, Telefone)",
        placeholder="Ex: joao.silva@gmail.com, 123.456.789-00, exemplo.com",
    )
with col2:
    st.write("")  # Espaçamento
    start_btn = st.button("INICIAR VARREDURA")

# --- LÓGICA DE EXECUÇÃO ---
if start_btn and target:
    bot = CerebroDeepSeek()
    collected_data = []

    # Detecta tipo de alvo logo no início
    target_info = detect_target_type(target)
    target_type = target_info["type"]
    clean_value = target_info["clean"]

    # username inferido (vai ser usado no contexto e possivelmente no Sherlock)
    potential_username = None

    # Container para logs em tempo real
    status_log = st.empty()

    # Cabeçalho com tipo detectado
    with status_log.container():
        st.info(
            f"🎯 Alvo: **{target}**  |  Tipo detectado: **{target_type}**  "
            f"| Normalizado: **{clean_value}**"
        )

    # Abas para organizar os resultados
    tab1, tab2, tab3, tab4 = st.tabs(
        ["🗺️ Planejamento", "🔎 Buscas & Social", "🕷️ Crawler", "📑 Dossiê Final"]
    )

    # =========================================================
    # FASE 1: PLANEJAMENTO (DeepSeek)
    # =========================================================
    with tab1:
        st.subheader("🧠 Planejamento de Dorks (DeepSeek)")
        st.caption(f"Modelo: {bot.model}")

        st.info("Masha (DeepSeek) está planejando as consultas de busca...")

        # mesmíssima ideia do main.py: alvo + metadados
        plan_prompt = (
            f"Alvo bruto: {target}\n"
            f"Tipo detectado: {target_type}\n"
            f"Valor normalizado: {clean_value}\n"
        )
        plan = bot.plan(plan_prompt)

        if plan.get("error"):
            st.error(plan["message"])
            st.stop()

        st.markdown("#### Thought process")
        st.write(plan.get("thought_process", ""))

        dorks = plan.get("dorks", [])
        st.markdown("#### Dorks geradas")
        st.json(dorks)

    # =========================================================
    # FASE 2: BUSCAS (Google + Sherlock)
    # =========================================================
    search_results_raw = []

    if mode in ["Investigação Completa", "Apenas Busca"]:
        with tab2:
            st.subheader("🔎 Varredura Global (SerpAPI + Sherlock)")
            progress_bar = st.progress(0.0)

            # 2.1 Busca Google
            total_dorks = len(dorks) if dorks else 1
            for i, query in enumerate(dorks):
                status_log.info(f"🔎 Buscando: {query}...")
                results = search_google(query)

                if isinstance(results, list):
                    st.success(f"Encontrados: {len(results)} resultados para '{query}'")
                    search_results_raw.extend(results)
                    with st.expander(f"Ver resultados de: {query}"):
                        st.table(results)
                else:
                    err = results.get("error") or results.get("warning")
                    st.warning(f"Falha/sem resultados para '{query}': {err}")

                progress_bar.progress((i + 1) / total_dorks)
                time.sleep(0.5)

            collected_data.append({"type": "google_search", "data": search_results_raw})

            # 2.2 Sherlock (Username) se fizer sentido
            username = None
            if target_type == "email":
                username = clean_value.split("@")[0]
            elif target_type in ("username", "generic") and " " not in clean_value and "." not in clean_value:
                username = clean_value

            potential_username = username  # guarda pra contexto da análise

            if username:
                st.markdown("---")
                st.subheader(f"🕵️ Pegada Digital (Username: {username})")
                status_log.info(f"🕵️ Buscando perfis para username: {username}...")
                profiles = search_username(username)
                if profiles:
                    cols = st.columns(3)
                    for idx, perfil in enumerate(profiles):
                        with cols[idx % 3]:
                            st.link_button(perfil["platform"], perfil["url"])
                    collected_data.append({"type": "social_profiles", "data": profiles})
                else:
                    st.warning("Nenhum perfil social encontrado para esse username.")
    else:
        # Se o modo for "Apenas Crawler", não faz buscas (por enquanto)
        search_results_raw = []

    # =========================================================
    # FASE 3: CRAWLER
    # =========================================================
    if mode in ["Investigação Completa", "Apenas Crawler"]:
        with tab3:
            st.subheader("🕷️ Infiltração em Sites (Crawler)")

            if mode == "Investigação Completa":
                if not search_results_raw:
                    st.info("Nenhum resultado do Google para usar no Crawler.")
                else:
                    status_log.info("🧠 Selecionando alvos para invasão...")
                    decision = bot.filter_urls(search_results_raw[:8])
                    if decision.get("error"):
                        st.error(f"Erro ao filtrar URLs: {decision['message']}")
                        targets = []
                    else:
                        targets = decision.get("selected_urls", [])
            else:
                # Placeholder: no futuro podemos permitir passar URLs manuais aqui
                st.info("Modo Apenas Crawler ainda não implementado totalmente.")
                targets = []

            if targets:
                for url in targets:
                    status_log.warning(f"🕷️ Crawling: {url}...")
                    data = extract_contacts(url)

                    if isinstance(data, dict) and "error" not in data:
                        with st.expander(f"✅ Dados extraídos de: {url}", expanded=True):
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.write("**Emails:**")
                                st.write(data.get("emails", []))
                                st.write("**Documentos:**")
                                st.write(data.get("documents", []))
                            with col_b:
                                st.write("**Telefones:**")
                                st.write(data.get("phones", []))
                                st.write("**Redes Sociais:**")
                                st.write(data.get("social_links", []))
                        collected_data.append({"type": "website_crawl", "data": data})
                    else:
                        err_msg = (
                            data.get("error") if isinstance(data, dict) else "Erro desconhecido"
                        )
                        st.error(f"Falha em {url}: {err_msg}")
            else:
                st.info("Nenhum alvo selecionado para o Crawler.")

    # =========================================================
    # FASE 4: ANÁLISE (Dossiê)
    # =========================================================
    with tab4:
        status_log.info("📑 Gerando Dossiê Final (DeepSeek Reasoner)...")

        analysis_payload = {
            "target": {
                "raw_input": target,
                "type": target_type,
                "clean": clean_value,
            },
            "context": {
                "has_local_cnpj": HAS_LOCAL_CNPJ,
                "potential_username": potential_username,
                "mode": mode,
            },
            "collected": collected_data,
        }

        dossier = bot.analyze(analysis_payload)

        st.markdown("## 📂 RELATÓRIO DE INTELIGÊNCIA")

        if dossier and not dossier.get("error"):
            st.success(f"Nível de confiança da IA: {dossier.get('confidence_score', 0)}%")

            st.markdown(f"### 📝 Resumo Executivo\n{dossier.get('summary', '')}")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### 🔑 Fatos Chave")
                for fact in dossier.get("key_facts", []):
                    st.markdown(f"- {fact}")

            with c2:
                st.markdown("### 📞 Contatos Confirmados")
                for contact in dossier.get("extracted_contacts", []):
                    st.code(contact)

            # Download do JSON (só o dossiê ou o pacote todo – aqui vou de dossiê puro)
            json_str = json.dumps(dossier, indent=4, ensure_ascii=False)
            st.download_button(
                "Baixar Dossiê Completo (.json)",
                json_str,
                f"dossier_{clean_value or target}.json",
            )
        else:
            st.error("Falha ao gerar o dossiê.")

    status_log.success("✅ OPERAÇÃO CONCLUÍDA")
