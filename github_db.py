* GITHUB_API
* HEADERS
* load_seen_songs()
* save_seen_songs()

import json
import base64
import requests

from config import GITHUB_REPO, GITHUB_TOKEN

GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents/seen_songs.json"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}
