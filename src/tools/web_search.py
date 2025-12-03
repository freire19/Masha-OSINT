import os
import requests
from typing import List, Dict, Any, Union
from dotenv import load_dotenv
from colorama import Fore, Style

load_dotenv()

def search_google(query: str, num_results: int = 5,
                  country: str = "us", lang: str = "en") -> Union[List[Dict[str, Any]], Dict[str, str]]:

    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return {"error": "CRITICAL: SERPAPI_KEY não encontrado no .env"}

    print(f"{Fore.YELLOW}[*] Search ({country.upper()}): {query}{Style.RESET_ALL}")

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": num_results,
        "gl": country,
        "hl": lang
    }

    try:
        response = requests.get("https://serpapi.com/search.json",
                                params=params, timeout=20)

        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}: {response.text}"}

        data = response.json()
        if "error" in data:
            return {"error": data["error"]}

        clean = []

        if "organic_results" in data:
            for item in data["organic_results"]:
                clean.append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet", "")
                })

        return clean if clean else {"warning": "No results."}

    except Exception as e:
        return {"error": f"Connection Failed: {str(e)}"}
