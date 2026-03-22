"""Vercel Serverless Function - 텔레그램 Q&A 웹훅 핸들러."""

import json
import os
import sys

# Vercel에서 src 모듈을 찾을 수 있도록 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx

from src.interpret import answer_question
from src.storage import get_current_paper


def _send_telegram_message(chat_id: int, text: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        },
        timeout=30,
    )


def handler(request):
    """Vercel serverless function handler."""
    # GET 요청 - 헬스체크
    if request.method == "GET":
        return json.dumps({"status": "ok"})

    # POST 요청 - 텔레그램 웹훅
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, AttributeError):
        return json.dumps({"error": "invalid request"}), 400

    message = body.get("message")
    if not message:
        return json.dumps({"ok": True})

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if not text:
        return json.dumps({"ok": True})

    # /start 명령어
    if text == "/start":
        _send_telegram_message(
            chat_id,
            "👋 안녕하세요! 이식 연구 봇입니다.\n\n"
            "매일 아침 최신 이식 관련 논문을 보내드립니다.\n"
            "논문에 대한 질문을 자유롭게 보내주세요!\n\n"
            "📋 /paper - 현재 논문 정보 보기",
        )
        return json.dumps({"ok": True})

    # /paper 명령어 - 현재 논문 요약
    if text == "/paper":
        paper = get_current_paper()
        if paper:
            _send_telegram_message(
                chat_id,
                f"📄 <b>현재 논문</b>\n\n"
                f"📌 {paper['title']}\n"
                f"📖 {paper['journal']} | {paper['date']}\n"
                f"🔗 PMID: {paper['pmid']}",
            )
        else:
            _send_telegram_message(chat_id, "아직 저장된 논문이 없습니다.")
        return json.dumps({"ok": True})

    # 일반 질문 - Q&A
    paper = get_current_paper()
    if not paper:
        _send_telegram_message(
            chat_id,
            "아직 저장된 논문이 없습니다. 내일 아침 첫 논문이 발송됩니다!",
        )
        return json.dumps({"ok": True})

    try:
        _send_telegram_message(chat_id, "🤔 답변을 생성하고 있습니다...")
        answer = answer_question(paper, text)
        _send_telegram_message(chat_id, answer)
    except Exception as e:
        _send_telegram_message(chat_id, f"죄송합니다, 답변 생성 중 오류가 발생했습니다: {str(e)[:200]}")

    return json.dumps({"ok": True})
