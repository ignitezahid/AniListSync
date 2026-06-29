import requests
import webbrowser
import urllib.parse
import secrets
import string
import time

from config import MAL_CLIENT_ID, MAL_CLIENT_SECRET
from utils.file_utils import load_json, save_json
AUTH_URL = "https://myanimelist.net/v1/oauth2/authorize"
TOKEN_URL = "https://myanimelist.net/v1/oauth2/token"

REDIRECT_URI = "http://localhost"
TOKEN_FILE = "mal_tokens.json"


def generate_code_verifier():

    alphabet = string.ascii_letters + string.digits + "-._~"

    return "".join(
        secrets.choice(alphabet)
        for _ in range(64)
    )


def get_auth_url():

    verifier = generate_code_verifier()

    params = {

        "response_type": "code",

        "client_id": MAL_CLIENT_ID,

        "redirect_uri": REDIRECT_URI,

        "code_challenge": verifier,

        "code_challenge_method": "plain"

    }

    url = AUTH_URL + "?" + urllib.parse.urlencode(params)

    return url, verifier


def get_tokens(code, verifier):

    data = {
        "client_id": MAL_CLIENT_ID,
        "client_secret": MAL_CLIENT_SECRET,
        "code": code,
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI
    }

    response = requests.post(TOKEN_URL, data=data)

    print(response.json())

    return response.json()


def save_tokens(tokens):

    tokens["expires_at"] = int(time.time()) + tokens["expires_in"]

    save_json(TOKEN_FILE, tokens)


def load_tokens():

    return load_json(TOKEN_FILE)


def refresh_access_token():
    tokens = load_tokens()
    if not tokens:
        return False

    data = {
        "client_id": MAL_CLIENT_ID,
        "client_secret": MAL_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"]
    }

    response = requests.post(
        TOKEN_URL,
        data=data
    )
    if response.status_code != 200:
        return False

    new_tokens = response.json()
    save_tokens(new_tokens)
    return True


def get_access_token():

    tokens = load_tokens()

    if not tokens:
        raise Exception("Not authenticated.")

    if time.time() >= tokens["expires_at"]:
        print("Refreshing MAL token...")
        if not refresh_access_token():
            raise Exception("Could not refresh token.")
        tokens = load_tokens()

    return tokens["access_token"]


def get_completed_mal_anime():
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    url = (
        "https://api.myanimelist.net/v2/users/@me/"
        "animelist"
        "?fields=list_status,num_episodes"
        "&limit=1000"
    )
    anime_list = []
    seen_ids = set()

    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(response.text)
            return anime_list

        data = response.json()
        for anime in data["data"]:
            node = anime.get("node", {})
            list_status = anime.get("list_status", {})
            mal_id = node.get("id")

            if mal_id is None:
                continue

            if mal_id in seen_ids:
                continue

            seen_ids.add(mal_id)
            anime_list.append({
                "id": None,
                "idMal": mal_id,
                "title": node.get("title") or "Unknown title",
                "episodes": node.get("num_episodes"),
                "status": list_status.get("status"),
                "progress": list_status.get("num_episodes_watched"),
            })

        url = None
        if "paging" in data:
            url = data["paging"].get("next")

    return anime_list


def get_completed_mal_ids():
    return {
        anime["idMal"]
        for anime in get_completed_mal_anime()
        if anime.get("idMal") is not None
    }


def get_list_status(mal_id):

    access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    url = (
        f"https://api.myanimelist.net/v2/anime/"
        f"{mal_id}"
        "?fields=my_list_status"
    )

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return None

    data = response.json()

    return data.get("my_list_status")


def add_to_list(
    mal_id,
    status="completed",
    episodes=None
):
    existing = get_list_status(mal_id)

    access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    data = {
        "status": status
    }
    if status == "completed" and episodes:
        data["num_watched_episodes"] = episodes

    url = f"https://api.myanimelist.net/v2/anime/{mal_id}/my_list_status"

    response = requests.put(
        url,
        headers=headers,
        data=data
    )

    if response.status_code == 200:
        if existing:
            return "updated"
        return "added"

    print(f"MAL Error {response.status_code}")
    print(response.text)
    return "failed"
