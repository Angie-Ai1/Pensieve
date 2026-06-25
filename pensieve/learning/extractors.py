"""學習吸收來源解析：YouTube 逐字稿、網頁文章、PDF。"""

import asyncio
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
)

YOUTUBE_HOSTS = ("youtube.com", "youtu.be")
YOUTUBE_TRANSCRIPT_LANGUAGES = ("zh-Hant", "zh", "en")
WEBPAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}


class ExtractionError(Exception):
    """擷取失敗，訊息為使用者可讀的繁中說明。"""


def is_youtube_url(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return any(host == h or host.endswith(f".{h}") for h in YOUTUBE_HOSTS)


def _extract_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.hostname or ""

    if host.endswith("youtu.be"):
        video_id = parsed.path.strip("/")
        return video_id or None

    query = parse_qs(parsed.query)
    if "v" in query:
        return query["v"][0]

    match = re.match(r"^/(shorts|embed|live)/([^/?]+)", parsed.path)
    if match:
        return match.group(2)

    return None


async def _fetch_youtube_title(url: str, video_id: str) -> str:
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(
                "https://www.youtube.com/oembed", params={"url": url, "format": "json"}
            )
            response.raise_for_status()
            return response.json()["title"]
        except httpx.HTTPError:
            return f"YouTube {video_id}"


def _fetch_transcript(video_id: str):
    """先找偏好語言的字幕；找不到就改抓任一可用語言（YouTube 的語言代碼變體很多，
    例如繁中可能是 zh-Hant 也可能是 zh-TW，與其窮舉不如直接 fallback）。"""
    transcript_list = YouTubeTranscriptApi().list(video_id)
    try:
        transcript = transcript_list.find_transcript(YOUTUBE_TRANSCRIPT_LANGUAGES)
    except NoTranscriptFound:
        transcript = next(iter(transcript_list))
    return transcript.fetch()


async def extract_youtube(url: str) -> tuple[str, str]:
    """逐字稿：youtube-transcript-api；標題：oEmbed。"""
    video_id = _extract_video_id(url)
    if video_id is None:
        raise ExtractionError("無法從連結中解析 YouTube 影片 ID。")

    try:
        transcript = await asyncio.to_thread(_fetch_transcript, video_id)
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as exc:
        raise ExtractionError("這部影片沒有可用的字幕/逐字稿，無法擷取內容。") from exc

    content = " ".join(snippet.text for snippet in transcript)
    title = await _fetch_youtube_title(url, video_id)
    return title, content


async def extract_webpage(url: str) -> tuple[str, str]:
    """擷取網頁標題與正文（移除 script/style/nav/header/footer/aside）。"""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=WEBPAGE_HEADERS) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ExtractionError(f"無法擷取網頁內容：{exc}") from exc

    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else url

    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    content = soup.get_text(separator="\n", strip=True)
    if not content:
        raise ExtractionError("網頁內容為空，可能需要 JavaScript 渲染，無法擷取。")

    return title, content


def extract_pdf(file_path: Path, fallback_title: str) -> tuple[str, str]:
    """逐頁取出 PDF 文字；title 用檔名（去副檔名）。同步函式，呼叫端用 asyncio.to_thread。"""
    reader = PdfReader(file_path)
    pages_text = [page.extract_text() or "" for page in reader.pages]
    content = "\n".join(pages_text).strip()
    if not content:
        raise ExtractionError("PDF 內容為空或無法擷取文字（可能是掃描檔）。")

    return fallback_title, content
