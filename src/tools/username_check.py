import concurrent.futures
from curl_cffi import requests
from colorama import Fore, Style

SITES = {
    "Instagram": "https://www.instagram.com/{}",
    "Twitter": "https://twitter.com/{}",
    "Facebook": "https://www.facebook.com/{}",
    "TikTok": "https://www.tiktok.com/@{}",
    "GitHub": "https://github.com/{}",
    "Reddit": "https://www.reddit.com/user/{}",
    "Steam": "https://steamcommunity.com/id/{}",
    "Telegram": "https://t.me/{}",
    "Spotify": "https://open.spotify.com/user/{}",
}


def _check(site, url_template, user):
    url = url_template.format(user)
    try:
        r = requests.get(url, impersonate="chrome110", timeout=7)
        if r.status_code == 200:
            return {"platform": site, "url": url}
    except:
        pass
    return None


def search_username(username: str):
    print(f"{Fore.YELLOW}[*] Sherlock: {username}{Style.RESET_ALL}")

    found = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as exe:
        futures = {exe.submit(_check, s, u, username): s for s, u in SITES.items()}

        for f in concurrent.futures.as_completed(futures):
            r = f.result()
            if r:
                print(f"{Fore.GREEN}[+] {r['platform']}: {r['url']}{Style.RESET_ALL}")
                found.append(r)

    if not found:
        print(f"{Fore.RED}[-] Nenhum perfil encontrado.{Style.RESET_ALL}")

    return found
