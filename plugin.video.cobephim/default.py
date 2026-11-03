# -*- coding: utf-8 -*-
import json
import re
import sys
import time
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin


ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
PLUGIN_URL = sys.argv[0]
USER_AGENT = "Kodi/21 CobePhim/1.3"
REMOTE_CONFIG_URL = "https://raw.githubusercontent.com/TNB88/cobephim-kodi/main/config.json"
DEFAULT_CONFIG = {
    "web_origin": "https://cobephim.fun",
    "api_base": "https://egluy2hhb21vaw5ndw9pbmhl.darkbytes.xyz/api/v1",
    "embed_base": "https://egluy2hhb21vaw5ndw9pbmhl.darkbytes.xyz/embed/",
}
XOR_KEY = "mySecretKey2024"


def safe_remote_url(value, fallback):
    value = str(value or "").strip()
    if value.startswith("https://"):
        return value.rstrip("/")
    return fallback.rstrip("/")


def load_remote_config():
    config = dict(DEFAULT_CONFIG)
    try:
        cache_buster = int(time.time() // 60)
        request = Request(
            REMOTE_CONFIG_URL + "?minute=" + str(cache_buster),
            headers={
                "Accept": "application/json",
                "Cache-Control": "no-cache",
                "User-Agent": USER_AGENT,
            },
        )
        with urlopen(request, timeout=4) as response:
            remote = json.loads(response.read().decode("utf-8", "replace"))
        if isinstance(remote, dict):
            config.update(remote)
    except Exception as error:
        xbmc.log("[plugin.video.cobephim] Dùng cấu hình dự phòng: " + str(error), xbmc.LOGWARNING)
    return config


REMOTE_CONFIG = load_remote_config()
WEB_ORIGIN = safe_remote_url(REMOTE_CONFIG.get("web_origin"), DEFAULT_CONFIG["web_origin"])
API_BASE = safe_remote_url(REMOTE_CONFIG.get("api_base"), DEFAULT_CONFIG["api_base"])
EMBED_BASE = safe_remote_url(REMOTE_CONFIG.get("embed_base"), DEFAULT_CONFIG["embed_base"]) + "/"


def log(message, level=xbmc.LOGINFO):
    xbmc.log("[plugin.video.cobephim] " + str(message), level)


def notify(message):
    xbmcgui.Dialog().notification("Cô Bé Phim", message, xbmcgui.NOTIFICATION_ERROR, 6000)


def request_text(url, referer=None):
    headers = {
        "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
        "Origin": WEB_ORIGIN,
        "Referer": referer or WEB_ORIGIN + "/",
        "User-Agent": USER_AGENT,
    }
    request = Request(url, headers=headers)
    with urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8", "replace")


def request_json(url):
    return json.loads(request_text(url))


def plugin_url(action, **params):
    data = {"action": action}
    data.update({key: str(value) for key, value in params.items() if value is not None})
    return PLUGIN_URL + "?" + urlencode(data)


def add_folder(label, action, art=None, **params):
    item = xbmcgui.ListItem(label=label)
    item.setArt(art or {"icon": "DefaultFolder.png"})
    item.setProperty("IsPlayable", "false")
    xbmcplugin.addDirectoryItem(HANDLE, plugin_url(action, **params), item, True)


def movie_art(movie):
    thumb = movie.get("thumbnail") or movie.get("poster") or ""
    poster = movie.get("poster") or thumb
    return {"thumb": thumb, "poster": poster, "icon": thumb, "fanart": poster}


def add_movie(movie):
    name = movie.get("name") or "Không tên"
    episode = str(movie.get("episode_current") or "").strip()
    quality = str(movie.get("quality") or "HD").strip()
    label = name
    if episode:
        label += "  [COLOR gold]• {}[/COLOR]".format(episode)
    item = xbmcgui.ListItem(label=label)
    item.setArt(movie_art(movie))
    item.setInfo("video", {
        "title": name,
        "originaltitle": movie.get("origin_name") or "",
        "plot": re.sub(r"<[^>]+>", "", movie.get("description") or ""),
        "year": int(movie.get("publish_year") or 0),
        "mediatype": "tvshow" if movie.get("type") == "series" else "movie",
        "status": movie.get("status") or "",
        "tagline": "{} • {}".format(quality, movie.get("language") or "").strip(" •"),
    })
    xbmcplugin.addDirectoryItem(
        HANDLE,
        plugin_url("episodes", movie_id=movie.get("id"), slug=movie.get("slug"), name=name),
        item,
        True,
    )


def extract_movies(payload):
    result = payload.get("result", payload) if isinstance(payload, dict) else payload
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        movies = result.get("movies")
        if isinstance(movies, list):
            return movies
    return []


def extract_collections(payload):
    result = payload.get("result", {}) if isinstance(payload, dict) else {}
    collections = result.get("collections", []) if isinstance(result, dict) else []
    return collections if isinstance(collections, list) else []


def catalog_movies(pages=1, mode="all"):
    movies = []
    seen = set()
    for page in range(1, pages + 1):
        payload = request_json(API_BASE + "/lists/homepageLists?page={}&limit=3".format(page))
        for collection in extract_collections(payload):
            for movie in collection.get("movies") or []:
                movie_id = movie.get("id")
                if not movie_id or movie_id in seen:
                    continue
                movie_type = str(movie.get("type") or "").lower()
                total = movie.get("episode_total")
                try:
                    total = int(total or 0)
                except (TypeError, ValueError):
                    total = 0
                if mode == "movie" and movie_type != "movie":
                    continue
                if mode == "series" and movie_type == "movie":
                    continue
                if mode == "short" and not (movie_type == "movie" or (0 < total <= 6)):
                    continue
                seen.add(movie_id)
                movies.append(movie)
    return movies


def extract_web_page(page_html):
    chunks = []
    pattern = r"<script[^>]*>self\.__next_f\.push\((.*?)\)</script>"
    for raw_payload in re.findall(pattern, page_html, re.DOTALL):
        try:
            payload = json.loads(unescape(raw_payload))
            if isinstance(payload, list) and len(payload) > 1 and isinstance(payload[1], str):
                chunks.append(payload[1])
        except (TypeError, ValueError):
            continue

    blob = "\n".join(chunks)
    decoder = json.JSONDecoder()
    movies = []
    seen = set()
    for match in re.finditer(r'\{"id":\d+,"name":', blob):
        try:
            movie, _ = decoder.raw_decode(blob[match.start():])
        except ValueError:
            continue
        if not isinstance(movie, dict):
            continue
        if not movie.get("origin_name") or not movie.get("slug"):
            continue
        if not (movie.get("thumbnail") or movie.get("poster")):
            continue
        movie_id = movie.get("id")
        if movie_id in seen:
            continue
        seen.add(movie_id)
        movies.append(movie)

    total_match = re.search(r'"totalPages":(\d+)', blob)
    total_pages = int(total_match.group(1)) if total_match else 1
    return movies, total_pages


def web_catalog_page(kind, page):
    routes = []
    if kind in ("all", "series"):
        routes.append("phim-bo")
    if kind in ("all", "movie"):
        routes.append("phim-le")

    movies = []
    seen = set()
    total_pages = 1
    for route in routes:
        url = WEB_ORIGIN + "/{}?page={}".format(route, page)
        route_movies, route_pages = extract_web_page(request_text(url, WEB_ORIGIN + "/"))
        total_pages = max(total_pages, route_pages)
        for movie in route_movies:
            if movie.get("id") not in seen:
                seen.add(movie.get("id"))
                movies.append(movie)
    return movies, total_pages


def show_movies(endpoint, title):
    xbmcplugin.setPluginCategory(HANDLE, title)
    xbmcplugin.setContent(HANDLE, "movies")
    try:
        movies = extract_movies(request_json(endpoint))
        for movie in movies:
            add_movie(movie)
        if not movies:
            notify("Không có phim")
    except (HTTPError, URLError, ValueError) as error:
        log(error, xbmc.LOGERROR)
        notify("Không tải được danh sách phim")
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def show_home():
    xbmcplugin.setPluginCategory(HANDLE, "Cô Bé Phim")
    xbmcplugin.setContent(HANDLE, "movies")
    add_folder("[B]🔍 Tìm kiếm phim[/B]", "search", {"icon": "DefaultAddonsSearch.png"})
    add_folder("[B]🎬 Tất cả phim trên web[/B]", "web_catalog", kind="all", page=1, title="Tất cả phim")
    add_folder("[B]🍿 Phim lẻ (1 tập)[/B]", "web_catalog", kind="movie", page=1, title="Phim lẻ")
    add_folder("[B]📺 Phim bộ[/B]", "web_catalog", kind="series", page=1, title="Phim bộ")
    add_folder("[B]⏱ Phim ngắn / ít tập[/B]", "catalog", mode="short", title="Phim ngắn / ít tập")
    try:
        movies = catalog_movies(pages=1)
        for movie in movies:
            add_movie(movie)
    except (HTTPError, URLError, ValueError) as error:
        log(error, xbmc.LOGERROR)
        notify("Không tải được phim hot")
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def show_catalog(mode, title):
    xbmcplugin.setPluginCategory(HANDLE, title)
    xbmcplugin.setContent(HANDLE, "movies")
    try:
        movies = catalog_movies(pages=5, mode=mode)
        for movie in movies:
            add_movie(movie)
        if not movies:
            notify("Không có phim")
    except (HTTPError, URLError, ValueError) as error:
        log(error, xbmc.LOGERROR)
        notify("Không tải được kho phim")
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def show_web_catalog(kind, page, title):
    xbmcplugin.setPluginCategory(HANDLE, "{} - Trang {}".format(title, page))
    xbmcplugin.setContent(HANDLE, "movies")
    try:
        movies, total_pages = web_catalog_page(kind, page)
        if page > 1:
            add_folder("[B]◀ Trang trước ({})[/B]".format(page - 1), "web_catalog", kind=kind, page=page - 1, title=title)
        for movie in movies:
            add_movie(movie)
        if page < total_pages:
            add_folder("[B]Trang sau ({}/{}) ▶[/B]".format(page + 1, total_pages), "web_catalog", kind=kind, page=page + 1, title=title)
        if not movies:
            notify("Không có phim ở trang này")
    except (HTTPError, URLError, ValueError) as error:
        log(error, xbmc.LOGERROR)
        notify("Không tải được kho phim đầy đủ")
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def show_search():
    query = xbmcgui.Dialog().input("Tìm phim Cô Bé Phim", type=xbmcgui.INPUT_ALPHANUM)
    if not query:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False, cacheToDisc=False)
        return
    endpoint = API_BASE + "/movies/search?keyword=" + quote(query)
    show_movies(endpoint, "Kết quả: " + query)


def episode_number(name):
    match = re.search(r"\d+(?:\.\d+)?", str(name or ""))
    return float(match.group(0)) if match else 0.0


def episode_label(name):
    value = str(name or "").strip()
    return re.sub(r"^tập\s+", "", value, flags=re.IGNORECASE)


def server_rank(server):
    value = str(server or "").lower()
    if "song ngữ" in value:
        return 0
    if "hà nội" in value:
        return 1
    if "#1" not in value:
        return 2
    return 3


def show_episodes(movie_id, slug, movie_name):
    xbmcplugin.setPluginCategory(HANDLE, movie_name)
    xbmcplugin.setContent(HANDLE, "episodes")
    try:
        episodes = request_json(API_BASE + "/episodes/by-idMovie/" + str(movie_id))
        episodes.sort(key=lambda item: (-episode_number(item.get("name")), server_rank(item.get("server")), item.get("server", "")))
        for episode in episodes:
            ep_name = episode_label(episode.get("name"))
            server = str(episode.get("server") or "")
            label = "Tập {}  [COLOR gold]• {}[/COLOR]".format(ep_name, server)
            item = xbmcgui.ListItem(label=label)
            item.setProperty("IsPlayable", "true")
            item.setInfo("video", {
                "title": "{} - Tập {}".format(movie_name, ep_name),
                "tvshowtitle": movie_name,
                "episode": int(episode_number(ep_name)),
                "mediatype": "episode",
                "studio": server,
            })
            xbmcplugin.addDirectoryItem(
                HANDLE,
                plugin_url(
                    "play",
                    episode_id=episode.get("id"),
                    movie_id=movie_id,
                    episode_name=ep_name,
                    movie_name=movie_name,
                    server=server,
                ),
                item,
                False,
            )
    except (HTTPError, URLError, ValueError) as error:
        log(error, xbmc.LOGERROR)
        notify("Không tải được danh sách tập")
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def extract_episode_json(html):
    marker = "var episode = "
    marker_index = html.find(marker)
    if marker_index < 0:
        raise ValueError("Không thấy dữ liệu tập phim")
    start = html.find("{", marker_index + len(marker))
    if start < 0:
        raise ValueError("Dữ liệu tập phim bị thiếu")
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(html)):
        char = html[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(html[start:index + 1])
    raise ValueError("Dữ liệu tập phim không hoàn chỉnh")


def xor_decrypt(encrypted):
    if not encrypted or len(encrypted) % 2:
        return ""
    output = []
    for offset in range(0, len(encrypted), 2):
        value = int(encrypted[offset:offset + 2], 16)
        key_value = ord(XOR_KEY[(offset // 2) % len(XOR_KEY)])
        output.append(chr(value ^ key_value))
    return "".join(output)


def resolve_episode(episode_id):
    html = request_text(EMBED_BASE + str(episode_id))
    episode = extract_episode_json(html)
    encrypted = episode.get("encrypted_url") or ""
    stream = xor_decrypt(encrypted) if encrypted else (
        episode.get("stream_url") or episode.get("video_url") or episode.get("link") or ""
    )
    return episode, stream


def is_native_stream(url):
    lower = str(url or "").lower()
    return ".m3u8" in lower or ".mpd" in lower or ".mp4" in lower


def same_episode(left, right):
    return episode_number(left) == episode_number(right) and episode_number(left) > 0


def choose_stream(episode_id, movie_id, episode_name):
    attempted = set()
    candidates = [(int(episode_id), "Nguồn đã chọn")]
    episodes = request_json(API_BASE + "/episodes/by-idMovie/" + str(movie_id))
    alternatives = [item for item in episodes if same_episode(item.get("name"), episode_name)]
    alternatives.sort(key=lambda item: (server_rank(item.get("server")), item.get("server", "")))
    candidates.extend((int(item.get("id")), item.get("server") or "Nguồn khác") for item in alternatives)
    for candidate_id, label in candidates:
        if candidate_id in attempted:
            continue
        attempted.add(candidate_id)
        try:
            episode, stream = resolve_episode(candidate_id)
            if is_native_stream(stream):
                return episode, stream, label
        except Exception as error:
            log("Nguồn {} lỗi: {}".format(candidate_id, error), xbmc.LOGWARNING)
    raise ValueError("Tập này chưa có nguồn phát native")


def kodi_headers(referer, stream):
    ref = referer or "{}://{}/".format(urlparse(stream).scheme, urlparse(stream).netloc)
    origin = "{}://{}".format(urlparse(ref).scheme, urlparse(ref).netloc)
    return urlencode({"Referer": ref, "Origin": origin, "User-Agent": USER_AGENT})


def play_episode(params):
    episode_id = int(params.get("episode_id", ["0"])[0])
    movie_id = int(params.get("movie_id", ["0"])[0])
    episode_name = params.get("episode_name", [""])[0]
    try:
        episode, stream, source_label = choose_stream(episode_id, movie_id, episode_name)
        headers = kodi_headers(episode.get("http_referer"), stream)
        playable_url = stream + "|" + headers
        item = xbmcgui.ListItem(path=playable_url)
        item.setProperty("IsPlayable", "true")
        item.setProperty("inputstream.adaptive.stream_headers", headers)
        if ".m3u8" in stream.lower():
            item.setMimeType("application/vnd.apple.mpegurl")
            item.setContentLookup(False)
        subtitle_urls = []
        for subtitle in episode.get("subtitles") or []:
            subtitle_url = subtitle.get("url") or subtitle.get("file")
            if subtitle_url:
                subtitle_urls.append(subtitle_url + "|" + headers)
        if subtitle_urls:
            item.setSubtitles(subtitle_urls)
        item.setInfo("video", {
            "title": "{} - Tập {}".format(params.get("movie_name", [""])[0], episode_name),
            "studio": source_label,
            "mediatype": "episode",
        })
        log("Phát episode={} source={} url={}".format(episode_id, source_label, stream))
        xbmcplugin.setResolvedUrl(HANDLE, True, item)
    except Exception as error:
        log(error, xbmc.LOGERROR)
        notify(str(error))
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def dispatch():
    params = parse_qs(sys.argv[2][1:] if len(sys.argv) > 2 else "")
    action = params.get("action", ["home"])[0]
    if action == "home":
        show_home()
    elif action == "hot":
        show_movies(API_BASE + "/movies/hot", "Phim hot")
    elif action == "search":
        show_search()
    elif action == "catalog":
        show_catalog(
            params.get("mode", ["all"])[0],
            params.get("title", ["Kho phim"])[0],
        )
    elif action == "web_catalog":
        show_web_catalog(
            params.get("kind", ["all"])[0],
            int(params.get("page", ["1"])[0]),
            params.get("title", ["Kho phim"])[0],
        )
    elif action == "episodes":
        show_episodes(
            params.get("movie_id", ["0"])[0],
            params.get("slug", [""])[0],
            params.get("name", ["Phim"])[0],
        )
    elif action == "play":
        play_episode(params)
    else:
        show_home()


if __name__ == "__main__":
    dispatch()
