"""텔레그램 메시지 발송 모듈."""

import os

import httpx

TELEGRAM_API = "https://api.telegram.org/bot{token}"


def _api_url(method: str) -> str:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    return f"{TELEGRAM_API.format(token=token)}/{method}"


def send_message(chat_id: str, text: str, parse_mode: str = "HTML") -> dict:
    """텔레그램으로 텍스트 메시지 발송."""
    resp = httpx.post(
        _api_url("sendMessage"),
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def send_photo(chat_id: str, photo_url: str, caption: str = "") -> dict:
    """텔레그램으로 이미지 발송."""
    resp = httpx.post(
        _api_url("sendPhoto"),
        json={
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption[:1024],
            "parse_mode": "HTML",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def format_paper_message(paper: dict, interpretation: str) -> str:
    """논문 정보를 텔레그램 메시지 형식으로 포맷."""
    authors_str = ", ".join(paper["authors"][:3])
    if len(paper["authors"]) > 3:
        authors_str += " et al."

    doi_link = f'<a href="https://doi.org/{paper["doi"]}">{paper["doi"]}</a>' if paper["doi"] else "N/A"

    msg = (
        "📄 <b>오늘의 이식 연구</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        f"📌 <b>{paper['title']}</b>\n\n"
        f"📖 {paper['journal']}\n"
        f"📅 {paper['date']}\n"
        f"👥 {authors_str}\n"
        f"🔗 DOI: {doi_link}\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "📋 <b>Abstract</b>\n\n"
        f"{paper['abstract'][:2000]}\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "🔬 <b>AI 해석</b>\n\n"
        f"{interpretation}\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "💬 이 논문에 대해 질문하시면 답변해드립니다!"
    )

    # 텔레그램 메시지 길이 제한 (4096자)
    if len(msg) > 4096:
        # Abstract를 줄임
        max_abstract = 4096 - len(msg) + len(paper['abstract'][:2000]) - 100
        msg = (
            "📄 <b>오늘의 이식 연구</b>\n"
            "━━━━━━━━━━━━━━━━\n\n"
            f"📌 <b>{paper['title']}</b>\n\n"
            f"📖 {paper['journal']}\n"
            f"📅 {paper['date']}\n"
            f"👥 {authors_str}\n"
            f"🔗 DOI: {doi_link}\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "📋 <b>Abstract</b>\n\n"
            f"{paper['abstract'][:max(500, max_abstract)]}...\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "🔬 <b>AI 해석</b>\n\n"
            f"{interpretation}\n\n"
            "━━━━━━━━━━━━━━━━\n"
            "💬 이 논문에 대해 질문하시면 답변해드립니다!"
        )

    return msg


def send_daily_paper(paper: dict, interpretation: str) -> None:
    """오늘의 논문을 텔레그램으로 발송."""
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    # 메인 메시지 발송
    msg = format_paper_message(paper, interpretation)
    send_message(chat_id, msg)

    # Figure 이미지 발송 (있는 경우)
    figure_urls = paper.get("figure_urls", [])
    for i, url in enumerate(figure_urls[:2]):
        try:
            send_photo(chat_id, url, f"🖼️ Figure {i + 1}")
        except Exception:
            pass  # figure 전송 실패 시 무시
