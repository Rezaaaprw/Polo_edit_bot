import json
import base64
import requests

from config import GITHUB_REPO, GITHUB_TOKEN

GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents/seen_songs.json"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}


def load_seen_songs():
    r = requests.get(GITHUB_API, headers=HEADERS)

    if r.status_code != 200:
        return [], None

    data = r.json()

    content = base64.b64decode(data["content"]).decode("utf-8")
    raw = json.loads(content)

    songs = []

    for item in raw:
        if isinstance(item, str):
            songs.append({"key": item})
        else:
            songs.append(item)

    return songs, data["sha"]


def save_seen_songs(songs, sha):
    content = base64.b64encode(
        json.dumps(songs, ensure_ascii=False, indent=2).encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": "update seen songs",
        "content": content,
    }

    if sha:
        payload["sha"] = sha

    r = requests.put(GITHUB_API, headers=HEADERS, json=payload)

    if r.status_code == 200:
        return True, r.json()["content"]["sha"]

    return False, None


def add_song(song):
    """
    با مدیریت Conflict آهنگ را ذخیره می‌کند.
    """

    for _ in range(3):

        songs, sha = load_seen_songs()

        if any(s["key"] == song["key"] for s in songs):
            return True, sha

        songs.append(song)

        success, new_sha = save_seen_songs(songs, sha)

        if success:
            return True, new_sha

    return False, None
