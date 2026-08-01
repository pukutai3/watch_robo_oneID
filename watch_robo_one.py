import json
import os
import re
import sys
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


BASE_URL = "https://www.robo-one.com/rankings/view/{robot_id}"
SEARCH_URL = "https://www.robo-one.com/rankings/search/"
STATE_FILE = Path("state.json")
USER_AGENT = "robo-one-watch/1.0 (+https://github.com/)"
DEFAULT_TIMEOUT = 20
LOCAL_ENV_FILE = Path(".env.local")


@dataclass
class RobotPage:
    robot_id: int
    exists: bool
    name: str = ""
    team_name: str = ""
    country: str = ""
    comment: str = ""
    url: str = ""
    image_url: str = ""


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"last_seen_id": 1929}
    with STATE_FILE.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_local_env() -> None:
    if not LOCAL_ENV_FILE.exists():
        return

    for raw_line in LOCAL_ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def fetch_url(url: str, timeout: int) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        if exc.code == 404:
            return ""
        raise
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc}") from exc


def fetch_html(robot_id: int, timeout: int) -> str:
    return fetch_url(BASE_URL.format(robot_id=robot_id), timeout=timeout)


def strip_tags(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    value = value.replace("&nbsp;", " ")
    return unescape(value).strip()


def extract_cell(html: str, label: str) -> str:
    pattern = (
        r"<tr>\s*<td[^>]*>\s*"
        + re.escape(label)
        + r"\s*</td>\s*<td[^>]*>(.*?)</td>\s*</tr>"
    )
    match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return strip_tags(match.group(1))


def extract_comment(html: str) -> str:
    match = re.search(
        r"<h2[^>]*>\s*Comment\s*</h2>\s*<div[^>]*>\s*<div>(.*?)</div>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return ""
    return strip_tags(match.group(1))


def extract_image_url(html: str) -> str:
    match = re.search(
        r'<div class="robotInfoImg">\s*<img src="([^"]+)"',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return ""

    image_url = urljoin("https://www.robo-one.com", match.group(1).strip())
    if "/img/noimage.png" in image_url:
        return ""
    return image_url


def parse_robot_page(robot_id: int, html: str) -> RobotPage:
    url = BASE_URL.format(robot_id=robot_id)
    if not html:
        return RobotPage(robot_id=robot_id, exists=False, url=url)

    parsed_id = extract_cell(html, "Robot ID")
    name = extract_cell(html, "Robot name")
    team_name = extract_cell(html, "Team name")
    country = extract_cell(html, "Country")
    comment = extract_comment(html)
    image_url = extract_image_url(html)

    exists = parsed_id == str(robot_id) and any(
        [name, team_name, country, comment, image_url]
    )
    return RobotPage(
        robot_id=robot_id,
        exists=exists,
        name=name,
        team_name=team_name,
        country=country,
        comment=comment,
        url=url,
        image_url=image_url,
    )


def fetch_robot_page(robot_id: int, timeout: int) -> RobotPage:
    html = fetch_html(robot_id, timeout=timeout)
    return parse_robot_page(robot_id, html)


def extract_latest_robot_id(search_html: str) -> int:
    robot_ids = [
        int(value)
        for value in re.findall(r'/rankings/view/(\d+)', search_html)
    ]
    if not robot_ids:
        raise RuntimeError("No robot IDs found on the ROBO-ONE search page")
    return max(robot_ids)


def fetch_latest_robot_id(timeout: int) -> int:
    first_page = fetch_url(SEARCH_URL, timeout=timeout)
    page_numbers = [
        int(value)
        for value in re.findall(r'/rankings/search/page:(\d+)', first_page)
    ]
    last_page_number = max(page_numbers, default=1)
    last_page = (
        first_page
        if last_page_number == 1
        else fetch_url(f"{SEARCH_URL}page:{last_page_number}", timeout=timeout)
    )
    return extract_latest_robot_id(last_page)


def format_notification(page: RobotPage) -> str:
    lines = [
        "ROBO-ONEで新しいロボットガレージが作成されました",
        "ーーーーーーーーーー",
        f"URL: {page.url}",
        "",
        f"Robot ID: {page.robot_id}",
    ]
    if page.name:
        lines.append(f"ロボット名: {page.name}")
    if page.team_name:
        lines.append(f"チーム名: {page.team_name}")
    return "\n".join(lines)


def send_discord_notification(
    webhook_url: str,
    message: str,
    timeout: int,
    image_url: str = "",
) -> None:
    payload_dict: dict[str, Any] = {"content": message}
    if image_url:
        payload_dict["embeds"] = [{"image": {"url": image_url}}]

    payload = json.dumps(payload_dict).encode("utf-8")
    request = Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        response.read()


def post_generic_webhook(webhook_url: str, page: RobotPage, timeout: int) -> None:
    payload = json.dumps(
        {
            "robot_id": page.robot_id,
            "name": page.name,
            "team_name": page.team_name,
            "country": page.country,
            "comment": page.comment,
            "url": page.url,
            "image_url": page.image_url,
        }
    ).encode("utf-8")
    request = Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        response.read()


def notify(page: RobotPage, timeout: int) -> None:
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    generic_webhook = os.getenv("NOTIFY_WEBHOOK_URL", "").strip()
    message = format_notification(page)

    if discord_webhook:
        send_discord_notification(
            discord_webhook,
            message,
            timeout,
            image_url=page.image_url,
        )
    elif generic_webhook:
        post_generic_webhook(generic_webhook, page, timeout)
    else:
        print(message)


def notification_target_is_configured() -> bool:
    return bool(
        os.getenv("DISCORD_WEBHOOK_URL", "").strip()
        or os.getenv("NOTIFY_WEBHOOK_URL", "").strip()
    )


def scan_for_new_pages(start_id: int, end_id: int, timeout: int) -> list[RobotPage]:
    found_pages: list[RobotPage] = []
    for robot_id in range(start_id + 1, end_id + 1):
        page = fetch_robot_page(robot_id, timeout=timeout)
        if page.exists:
            found_pages.append(page)

    return found_pages


def process_new_pages(
    new_pages: list[RobotPage], state: dict[str, Any], timeout: int
) -> None:
    for page in new_pages:
        notify(page, timeout=timeout)
        state["last_seen_id"] = page.robot_id
        save_state(state)


def parse_args(argv: list[str]) -> dict[str, Any]:
    args: dict[str, Any] = {"probe_id": None}
    if len(argv) == 3 and argv[1] == "--probe":
        args["probe_id"] = int(argv[2])
    elif len(argv) != 1:
        raise SystemExit("Usage: python watch_robo_one.py [--probe ROBOT_ID]")
    return args


def main(argv: list[str]) -> int:
    load_local_env()
    args = parse_args(argv)
    timeout = int(os.getenv("REQUEST_TIMEOUT", str(DEFAULT_TIMEOUT)))

    if args["probe_id"] is not None:
        page = fetch_robot_page(args["probe_id"], timeout=timeout)
        print(json.dumps(page.__dict__, ensure_ascii=False, indent=2))
        return 0 if page.exists else 1

    state = load_state()
    last_seen_id = int(os.getenv("ROBO_ONE_START_ID", state.get("last_seen_id", 1929)))
    require_notification = os.getenv("REQUIRE_NOTIFICATION", "").lower() in {
        "1",
        "true",
        "yes",
    }
    if require_notification and not notification_target_is_configured():
        raise RuntimeError(
            "REQUIRE_NOTIFICATION is enabled, but no notification webhook is configured"
        )

    latest_robot_id = fetch_latest_robot_id(timeout=timeout)
    new_pages = scan_for_new_pages(last_seen_id, latest_robot_id, timeout)
    if not new_pages:
        print(f"No new robot garage after #{last_seen_id}")
        return 0

    process_new_pages(new_pages, state, timeout=timeout)
    print(
        f"Detected {len(new_pages)} new robot garage page(s). "
        f"Updated last_seen_id to {state['last_seen_id']}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
