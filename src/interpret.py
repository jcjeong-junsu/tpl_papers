"""Google Gemini API를 사용하여 논문을 해석하는 모듈."""

import json
import os

import httpx

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

SYSTEM_PROMPT = """당신은 장기이식(organ transplantation) 분야의 전문 의학 연구자입니다.
주어진 논문의 abstract를 분석하여 한국어로 알기 쉽게 해석해주세요.

다음 형식으로 답변해주세요:

🎯 연구 목적
(1-2문장)

🔬 연구 방법
(핵심 방법론 2-3문장)

📊 주요 결과
(가장 중요한 결과 2-3가지를 bullet point로)

💡 임상적 의의
(이 연구가 이식 분야에 미치는 영향 1-2문장)

⚠️ 한계점
(주요 한계점 1-2가지)"""


def _call_gemini(system: str, user_message: str) -> str:
    """Gemini API 호출."""
    api_key = os.environ["GEMINI_API_KEY"]

    resp = httpx.post(
        f"{GEMINI_API_URL}?key={api_key}",
        json={
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user_message}]}],
            "generationConfig": {"maxOutputTokens": 1500},
        },
        timeout=60,
    )
    resp.raise_for_status()

    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def interpret_paper(paper: dict) -> str:
    """Gemini API로 논문을 해석."""
    authors_str = ", ".join(paper["authors"][:5])
    if len(paper["authors"]) > 5:
        authors_str += " et al."

    user_message = f"""다음 이식 관련 논문을 해석해주세요.

제목: {paper['title']}
저널: {paper['journal']}
저자: {authors_str}
출판일: {paper['date']}

Abstract:
{paper['abstract']}"""

    return _call_gemini(SYSTEM_PROMPT, user_message)


def answer_question(paper_context: dict, question: str) -> str:
    """논문에 대한 질문에 답변."""
    system = f"""당신은 장기이식 분야의 전문 의학 연구자입니다.
사용자가 아래 논문에 대해 질문합니다. 논문 내용을 바탕으로 정확하고 알기 쉽게 한국어로 답변해주세요.
논문 정보가 부족한 부분은 일반적인 의학 지식으로 보충하되, 추론인 경우 명시해주세요.

논문 정보:
제목: {paper_context.get('title', 'N/A')}
저널: {paper_context.get('journal', 'N/A')}
Abstract: {paper_context.get('abstract', 'N/A')}
AI 해석: {paper_context.get('interpretation', 'N/A')}"""

    return _call_gemini(system, question)
