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

    if r.status_code == 200:
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

    return [], None


def save_seen_songs(songs, sha):
    content = base64.b64encode(
        json.dumps(songs, ensure_ascii=False).encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": "update seen songs",
        "content": content,
    }

    if sha:
        payload["sha"] = sha

    r = requests.put(GITHUB_API, headers=HEADERS, json=payload)

    return r.json().get("content", {}).get("sha")
