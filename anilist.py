import requests
import time
import re
from rapidfuzz import fuzz, process
from config import ANILIST_TOKEN, DEFAULT_STATUS
from settings import SETTINGS
from utils.constants import ALIASES_FILE, CACHE_FILE
from utils.file_utils import load_json, save_json
from rich.table import Table

from utils.ui import ask, console, warning
from urllib.parse import quote

URL = "https://graphql.anilist.co"

HEADERS = {
    "Authorization": f"Bearer {ANILIST_TOKEN}",
    "Content-Type": "application/json"
}

MAX_RETRIES = SETTINGS["max_retries"]
DEBUG = SETTINGS["debug"]


def normalize(text):
    text = text.lower()
    # Remove apostrophes and quotes
    text = re.sub(r"[\"'`]", "", text)
    # Replace punctuation with spaces
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    # Remove extra spaces
    text = re.sub(r"\s+", " ", text)
    return text.strip()


STOP_WORDS = {
    "a", "an", "the", "of", "to", "who", "at",
    "in", "on", "is", "and", "for", "with",
    "my", "your", "our"
}


def extract_keywords(title):
    words = normalize(title).split()
    keywords = []
    for word in words:
        if word in STOP_WORDS:
            continue
        if len(word) < 4:
            continue
        keywords.append(word)
    return keywords


def generate_aliases(title):
    variants = set()
    variants.add(normalize(title))

    keywords = extract_keywords(title)
    variants.add(" ".join(keywords))

    words = normalize(title).split()
    if len(words) >= 2:
        variants.add(" ".join(words[:2]))
    if len(words) >= 3:
        variants.add(" ".join(words[:3]))

    return variants


def save_alias(user_title, anime):
    for alias in generate_aliases(user_title):
        ALIASES[alias] = {
            "id": anime["id"],
            "idMal": anime.get("idMal"),
            "episodes": anime.get("episodes"),
            "title": (
                anime["title"]["english"]
                or anime["title"]["romaji"]
                or anime["title"]["native"]
            )
        }
    save_json(ALIASES_FILE, ALIASES)



SEARCH_CACHE = load_json(CACHE_FILE, {})
ALIASES = load_json(ALIASES_FILE, {})



def save_cache():
    save_json(CACHE_FILE, SEARCH_CACHE)


def find_best_match(media, title):
    best = None
    best_score = 0
    title_lower = normalize(title)
    for anime in media:
        titles = [
            anime["title"]["romaji"],
            anime["title"]["english"],
            anime["title"]["native"]
        ]
        for t in titles:
            if not t:
                continue
            t_lower = normalize(t)
            score = max(
                fuzz.partial_ratio(title_lower, t_lower),
                fuzz.token_set_ratio(title_lower, t_lower),
                fuzz.token_sort_ratio(title_lower, t_lower),
                fuzz.ratio(title_lower, t_lower)
            )
            if score > best_score:
                best_score = score
                best = anime
                if score == 100:
                    return best, best_score
    return best, best_score


def rank_candidates(candidates, title):
    ranked = []
    for anime in candidates.values():
        best_score = 0
        for t in [
            anime["title"]["romaji"],
            anime["title"]["english"],
            anime["title"]["native"]
        ]:
            if not t:
                continue
            t_lower = normalize(t)
            score = max(
                fuzz.partial_ratio(normalize(title), t_lower),
                fuzz.token_set_ratio(normalize(title), t_lower),
                fuzz.token_sort_ratio(normalize(title), t_lower),
                fuzz.ratio(normalize(title), t_lower)
            )
            best_score = max(best_score, score)
        ranked.append((best_score, anime))
    ranked.sort(reverse=True, key=lambda x: x[0])
    return ranked[:5]


def graphql_request(query, variables=None):
    wait = 5
    for _ in range(MAX_RETRIES):
        response = requests.post(
            URL,
            json={
                "query": query,
                "variables": variables or {}
            },
            headers=HEADERS,
            timeout=30
        )

        if response.status_code == 429:
            print(f"Rate limited. Waiting {wait} seconds...")
            time.sleep(wait)
            wait = min(wait * 2, 60)
            continue

        try:
            data = response.json()
        except Exception:
            print(response.text)
            raise

        if "errors" in data:
            statuses = [e.get("status") for e in data["errors"]]
            if 429 in statuses:
                print(f"GraphQL rate limited. Waiting {wait} seconds...")
                time.sleep(wait)
                wait = min(wait * 2, 60)
                continue

        return data

    raise Exception("AniList API failed after maximum retries.")


def test_connection():
    query = """
    query {
      Viewer {
        id
        name
      }
    }
    """

    data = graphql_request(query)

    if "errors" in data:
        return None

    viewer = data["data"]["Viewer"]
    return viewer["name"]


def search_candidates(title):
    if title in SEARCH_CACHE:
        cached = SEARCH_CACHE[title]
        if isinstance(cached, list):
            return cached
        if cached:
            return [(100.0, cached)]
        return []

    alias = ALIASES.get(normalize(title))
    if not alias:
        alias = ALIASES.get(title.lower())
    if alias:
        if "idMal" not in alias or "episodes" not in alias:
            query = """
            query ($id: Int) {
              Media(id: $id) {
                id
                idMal
                episodes
                title {
                  english
                  romaji
                  native
                }
              }
            }
            """
            data = graphql_request(
                query,
                {"id": alias["id"]}
            )
            media = data["data"]["Media"]
            alias["idMal"] = media["idMal"]
            alias["episodes"] = media["episodes"]
            save_json(ALIASES_FILE, ALIASES)

        result = {
            "id": alias["id"],
            "idMal": alias["idMal"],
            "episodes": alias["episodes"],
            "title": {
                "english": None,
                "romaji": None,
                "native": None,
            },
        }

        result["title"]["english"] = alias.get("title")
        result["title"]["romaji"] = alias.get("title")
        result["title"]["native"] = alias.get("title")

        SEARCH_CACHE[title] = [(100.0, result)]
        save_cache()
        return [(100.0, result)]

    print("\nSearching AniList...")

    # Clean markdown only
    title = re.sub(r"\*\*|__", "", title).strip()
    search_title = title

    query = """
    query ($search: String, $perPage: Int) {
      Page(page: 1, perPage: $perPage) {
        media(search: $search, type: ANIME) {
          id
          idMal
          episodes
          title {
            romaji
            english
            native
          }
        }
      }
    }
    """

    searches = []
    searches.append(search_title)

    if ":" in search_title:
        searches.append(search_title.split(":")[0].strip())
    if "-" in search_title:
        searches.append(search_title.split("-")[0].strip())
    if search_title.lower().startswith("the "):
        searches.append(search_title[4:].strip())

    words = search_title.split()
    if len(words) >= 4:
        searches.append(" ".join(words[:4]))
    if len(words) >= 2:
        searches.append(" ".join(words[:2]))

    searches = list(dict.fromkeys(searches))
    all_candidates = {}

    for st in searches:
        if DEBUG:
            print(f"Trying search: {st}")

        variables = {
            "search": st,
            "perPage": SETTINGS["anilist_per_page"]
        }
        data = graphql_request(query, variables)

        if "errors" in data:
            print(data["errors"])
            continue

        new_media = data["data"]["Page"]["media"]
        if not new_media:
            continue

        for anime in new_media:
            if anime.get("status") == "NOT_YET_RELEASED":
                continue
            all_candidates[anime["id"]] = anime

        best, best_score = find_best_match(new_media, title)
        if DEBUG:
            print(f"Best Match Score: {best_score}%")
        if best_score >= SETTINGS["search_threshold"]:
            SEARCH_CACHE[title] = best
            save_cache()
            return [(best_score, best)]

    print("Candidates:", len(all_candidates))
    if not all_candidates:
        if DEBUG:
            print("No candidates. Trying keyword search...")
        keywords = extract_keywords(title)
        for keyword in keywords[:3]:
            variables = {
                "search": keyword
            }
            data = graphql_request(query, variables)
            if "errors" in data:
                continue
            for anime in data["data"]["Page"]["media"]:
                all_candidates[anime["id"]] = anime

    if all_candidates:
        top = rank_candidates(all_candidates, title)
        if top:
            return top

    SEARCH_CACHE[title] = None
    save_cache()
    return []


def search_anime(title):
    if title in SEARCH_CACHE:
        return SEARCH_CACHE[title]

    alias = ALIASES.get(normalize(title))
    if not alias:
        alias = ALIASES.get(title.lower())
    if alias:
        print(
            f'\n✓ Using learned alias'
            f'\n  "{title}"'
            f'\n   → {alias["title"]}\n'
        )
        if "idMal" not in alias or "episodes" not in alias:
            print("Updating old alias...")
            query = """
            query ($id: Int) {
              Media(id: $id) {
                id
                idMal
                episodes
                title {
                  english
                  romaji
                  native
                }
              }
            }
            """
            data = graphql_request(
                query,
                {
                    "id": alias["id"]
                }
            )
            media = data["data"]["Media"]
            alias["idMal"] = media["idMal"]
            alias["episodes"] = media["episodes"]
            save_json(ALIASES_FILE, ALIASES)

        result = {
            "id": alias["id"],
            "idMal": alias["idMal"],
            "episodes": alias["episodes"]
        }
        SEARCH_CACHE[title] = result
        return result

    print("\nSearching AniList...")

    title = re.sub(r"\*\*|__", "", title).strip()

    search_title = title

    query = """
    query ($search: String, $perPage: Int) {
      Page(page: 1, perPage: $perPage) {
        media(search: $search, type: ANIME) {
          id
          idMal
          episodes
          status
          title {
            romaji
            english
            native
          }
        }
      }
    }
    """

    searches = []
    searches.append(search_title)

    if ":" in search_title:
        searches.append(search_title.split(":")[0].strip())

    if "-" in search_title:
        searches.append(search_title.split("-")[0].strip())

    if search_title.lower().startswith("the "):
        searches.append(search_title[4:].strip())

    words = search_title.split()

    if len(words) >= 4:
        searches.append(" ".join(words[:4]))

    if len(words) >= 2:
        searches.append(" ".join(words[:2]))

    searches = list(dict.fromkeys(searches))
    all_candidates = {}

    for st in searches:
        if DEBUG:
            print(f"Trying search: {st}")

        variables = {
            "search": st,
            "perPage": SETTINGS["anilist_per_page"]
        }

        data = graphql_request(query, variables)

        if "errors" in data:
            print(data["errors"])
            continue

        new_media = data["data"]["Page"]["media"]
        if not new_media:
            continue

        for anime in new_media:
            all_candidates[anime["id"]] = anime

        best, best_score = find_best_match(new_media, title)

        if DEBUG:
            print(f"Best Match Score: {best_score}%")

        if (
            best
            and best.get("status") != "NOT_YET_RELEASED"
            and best_score >= SETTINGS["search_threshold"]
        ):
            SEARCH_CACHE[title] = best
            save_cache()
            return best

    print("Candidates:", len(all_candidates))
    if not all_candidates:
        if DEBUG:
            print("No candidates. Trying keyword search...")
        keywords = extract_keywords(title)
        for anime in data["data"]["Page"]["media"]:
            if anime.get("status") == "NOT_YET_RELEASED":
                continue

            all_candidates[anime["id"]] = anime

    if all_candidates:
        top = rank_candidates(all_candidates, title)
        if top:
            table = Table(
                show_header=True,
                header_style="bold cyan",
                box=None,
            )
            table.add_column("", width=3)
            table.add_column("Title", style="white")
            table.add_column("Match", justify="right", style="green", width=8)
            for i, (score, anime) in enumerate(top, 1):
                display_title = (
                    anime["title"]["english"]
                    or anime["title"]["romaji"]
                    or anime["title"]["native"]
                )
                table.add_row(str(i), display_title, f"{score:.1f}%")
            console.print("\nPossible Matches\n")
            console.print(table)
            choice = ask("Choose (1-5, 0=Skip):")
            if choice == "0":
                SEARCH_CACHE[title] = None
                save_cache()
                return None
            if not choice.isdigit():
                warning("Invalid choice.")
                SEARCH_CACHE[title] = None
                save_cache()
                return None
            choice = int(choice)
            if choice < 1 or choice > len(top):
                warning("Invalid choice.")
                SEARCH_CACHE[title] = None
                save_cache()
                return None
            score, anime = top[choice - 1]
            display_title = (
                anime["title"]["english"]
                or anime["title"]["romaji"]
                or anime["title"]["native"]
            )
            print(f"\nYou selected:\n{display_title}")
            confirm = ask("Confirm? (Y/N):").lower()
            if confirm != "y":
                warning("Selection cancelled.")
                SEARCH_CACHE[title] = None
                save_cache()
                return None
            save_alias(title, anime)
            SEARCH_CACHE[title] = anime
            save_cache()
            print("✓ Alias learned.")
            return anime

    SEARCH_CACHE[title] = None
    save_cache()
    return None


def add_to_list(media_id):
    mutation = """
    mutation ($mediaId: Int, $status: MediaListStatus) {
      SaveMediaListEntry(mediaId: $mediaId, status: $status) {
        id
        status
      }
    }
    """

    variables = {
        "mediaId": media_id,
        "status": DEFAULT_STATUS
    }

    data = graphql_request(mutation, variables)

    if "errors" in data:
        for error in data["errors"]:
            message = error.get("message", "")
            status = error.get("status", 0)
            if message == "Invalid token":
                print("AniList returned 'Invalid token'. Retrying...")
                time.sleep(5)
                data = graphql_request(mutation, variables)
                if "errors" not in data:
                    return True
            print(error)
        return False

    return True




def get_media_with_relations(media_id):
    query = """
    query ($id: Int) {
      Media(id: $id, type: ANIME) {
        id
        idMal
        episodes
        status
        title {
          romaji
          english
          native
        }
        relations {
          edges {
            relationType
            node {
              id
              idMal
              episodes
              status
              type
              title {
                romaji
                english
                native
              }

              relations {
                edges {
                  relationType
                  node {
                    id
                    idMal
                    episodes
                    status
                    type
                    title {
                      romaji
                      english
                      native
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    data = graphql_request(
        query,
        {
            "id": media_id
        }
    )

    if "errors" in data:
        print(data["errors"])
        return None, []

    media = data["data"]["Media"]

    related = []
    seen_ids = {media["id"]}

    def add_node(node):
        if not node:
            return

        if node.get("type") != "ANIME":
            return
        
        if node.get("status") == "NOT_YET_RELEASED":
            return

        if node["id"] in seen_ids:
            return

        seen_ids.add(node["id"])
        related.append(node)

    # Level 1 + Level 2 relations
    for edge in media.get("relations", {}).get("edges", []):
        node = edge.get("node")

        add_node(node)

        for edge2 in node.get("relations", {}).get("edges", []):
            add_node(edge2.get("node"))

    return media, related



def get_completed_anime():
    viewer_query = """
    query {
      Viewer {
        id
      }
    }
    """
    viewer_data = graphql_request(viewer_query)
    if "errors" in viewer_data:
        print(viewer_data["errors"])
        return set()

    user_id = viewer_data["data"]["Viewer"]["id"]

    collection_query = """
    query ($userId: Int) {
      MediaListCollection(userId: $userId, type: ANIME) {
        lists {
          entries {
            mediaId
            status
            progress
            media {
              id
              idMal
              episodes
              seasonYear
              season
              studios {
                nodes {
                  name
                }
              }
              genres
              title {
                english
                romaji
                native
              }
            }
          }
        }
      }
    }
    """

    collection_data = graphql_request(
        collection_query,
        {"userId": user_id}
    )
    if "errors" in collection_data:
        print(collection_data["errors"])
        return []

    anime = []
    seen_ids = set()

    for anime_list in collection_data["data"]["MediaListCollection"]["lists"]:
        for entry in anime_list["entries"]:
            media = entry.get("media") or {}
            media_id = media.get("id") or entry.get("mediaId")

            if media_id in seen_ids:
                continue

            seen_ids.add(media_id)
            title = media.get("title") or {}

            season_order = {"WINTER": 0, "SPRING": 1, "SUMMER": 2, "FALL": 3}

            studios = media.get("studios", {}).get("nodes", []) or []
            studio_names = [
                s["name"]
                for s in studios
                if isinstance(s, dict) and s.get("name")
            ]

            anime.append({
                "id": media_id,
                "idMal": media.get("idMal"),
                "title": (
                    title.get("english")
                    or title.get("romaji")
                    or title.get("native")
                    or "Unknown title"
                ),
                "episodes": media.get("episodes"),
                "season_year": media.get("seasonYear"),
                "season": media.get("season"),
                "season_order": season_order.get(media.get("season"), 0),
                "studios": studio_names,
                "genres": media.get("genres") or [],
                "status": entry.get("status"),
                "progress": entry.get("progress"),
            })

    return anime


def get_completed_ids():
    return {
        anime["id"]
        for anime in get_completed_anime()
        if anime.get("id") is not None
    }


def find_similar_aliases(title, limit=5):
    if not ALIASES:
        return []

    matches = process.extract(
        normalize(title),
        ALIASES.keys(),
        limit=limit,
        score_cutoff=70
    )

    results = []

    for key, score, _ in matches:
        results.append({
            "score": score,
            "alias": key,
            "data": ALIASES[key]
        })

    return results


