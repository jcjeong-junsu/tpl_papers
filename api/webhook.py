"""Vercel Serverless Function - 텔레그램 Q&A 웹훅 핸들러."""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler

# Vercel에서 src 모듈을 찾을 수 있도록 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx

from src.fetch_paper import get_todays_paper
from src.interpret import answer_question, interpret_paper
from src.storage import get_current_paper, save_paper
from src.telegram_sender import send_daily_paper


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


def _handle_update(body: dict) -> None:
    """텔레그램 업데이트를 처리."""
    message = body.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if not text:
        return

    # /start 명령어
    if text == "/start":
        _send_telegram_message(
            chat_id,
            "👋 안녕하세요! 이식 연구 봇입니다.\n\n"
            "매일 아침 최신 이식 관련 논문을 보내드립니다.\n"
            "논문에 대한 질문을 자유롭게 보내주세요!\n\n"
            "📋 /paper - 현재 논문 정보 보기\n"
            "🆕 /new - 새 논문 바로 받기",
        )
        return

    # /new 명령어 - 새 논문 바로 받기
    if text == "/new":
        _send_telegram_message(chat_id, "🔍 새 논문을 검색하고 있습니다...")
        try:
            paper = get_todays_paper()
            if not paper:
                _send_telegram_message(chat_id, "최근 이식 관련 논문을 찾지 못했습니다.")
                return
            interpretation = interpret_paper(paper)
            save_paper(paper, interpretation)
            send_daily_paper(paper, interpretation)
        except Exception as e:
            _send_telegram_message(chat_id, f"오류가 발생했습니다: {str(e)[:200]}")
        return

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
        return

    # 일반 질문 - Q&A
    paper = get_current_paper()
    if not paper:
        _send_telegram_message(
            chat_id,
            "아직 저장된 논문이 없습니다. 내일 아침 첫 논문이 발송됩니다!",
        )
        return

    try:
        _send_telegram_message(chat_id, "🤔 답변을 생성하고 있습니다...")
        answer = answer_question(paper, text)
        _send_telegram_message(chat_id, answer)
    except Exception as e:
        _send_telegram_message(
            chat_id,
            f"죄송합니다, 답변 생성 중 오류가 발생했습니다: {str(e)[:200]}",
        )


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)
            _handle_update(data)
        except Exception:
            pass

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode())
