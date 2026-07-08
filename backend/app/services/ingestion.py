import httpx
from bs4 import BeautifulSoup

from app.errors import EmptyContentError, UrlFetchError
from app.logging_config import get_logger

logger = get_logger(__name__)

FETCH_TIMEOUT_SECONDS = 10.0
USER_AGENT = "AIKnowledgeInbox/1.0 (+https://github.com)"


def fetch_url_content(url: str) -> tuple[str | None, str]:
    """Fetch a URL server-side and extract readable text + a best-effort title.

    Raises UrlFetchError on network failure, non-2xx status, or unparseable content.
    """
    try:
        response = httpx.get(
            url,
            timeout=FETCH_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise UrlFetchError(f"Timed out fetching URL: {url}") from exc
    except httpx.HTTPStatusError as exc:
        raise UrlFetchError(
            f"URL returned HTTP {exc.response.status_code}: {url}"
        ) from exc
    except httpx.RequestError as exc:
        raise UrlFetchError(f"Failed to fetch URL: {url} ({exc})") from exc

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "text" not in content_type:
        raise UrlFetchError(
            f"Unsupported content-type '{content_type}' for URL: {url}"
        )

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else None

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)

    if not cleaned:
        raise UrlFetchError(f"No readable text content found at URL: {url}")

    logger.info("url_fetched url=%s chars=%d title=%r", url, len(cleaned), title)
    return title, cleaned


def normalize_note_content(content: str) -> str:
    cleaned = content.strip()
    if not cleaned:
        raise EmptyContentError("Note content cannot be empty")
    return cleaned
