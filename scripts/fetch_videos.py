"""channels.json の各チャンネルの全動画を YouTube Data API で取得し、videos.json に書き出す。

環境変数 YT_API_KEY に API キーが必要。GitHub Actions から定期実行する想定。
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/youtube/v3/"
KEY = os.environ.get("YT_API_KEY")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def call(endpoint, **params):
    params["key"] = KEY
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as res:
        return json.load(res)


def iso_duration_to_sec(s):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return 0
    d, h, mi, se = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


def fetch_channel(channel_id):
    playlist = "UU" + channel_id[2:]  # アップロード動画のプレイリスト
    items, token = [], None
    while True:
        params = dict(part="snippet,contentDetails", playlistId=playlist, maxResults=50)
        if token:
            params["pageToken"] = token
        data = call("playlistItems", **params)
        for it in data.get("items", []):
            sn = it["snippet"]
            if sn.get("title") in ("Private video", "Deleted video"):
                continue
            items.append({
                "id": it["contentDetails"]["videoId"],
                "title": sn["title"],
                "date": it["contentDetails"].get("videoPublishedAt") or sn["publishedAt"],
            })
        token = data.get("nextPageToken")
        if not token:
            break

    # 動画の長さ（ショートの判別用）を50件ずつ取得
    for i in range(0, len(items), 50):
        chunk = items[i:i + 50]
        data = call("videos", part="contentDetails", id=",".join(v["id"] for v in chunk))
        dur = {v["id"]: iso_duration_to_sec(v["contentDetails"].get("duration")) for v in data.get("items", [])}
        for v in chunk:
            v["sec"] = dur.get(v["id"], 0)

    items.sort(key=lambda v: v["date"], reverse=True)
    return items


def main():
    if not KEY:
        sys.exit("YT_API_KEY が設定されていません")
    with open(os.path.join(ROOT, "channels.json"), encoding="utf-8") as f:
        channels = json.load(f)
    out = {}
    for ch in channels:
        out[ch["id"]] = fetch_channel(ch["id"])
        print(f'{ch["name"]}: {len(out[ch["id"]])}本')
    with open(os.path.join(ROOT, "videos.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
