"""매일 실행되는 메인 스크립트 - GitHub Actions에서 호출."""

import sys

from src.fetch_paper import get_todays_paper
from src.interpret import interpret_paper
from src.storage import save_paper
from src.telegram_sender import send_daily_paper


def main():
    print("🔍 이식 관련 최신 논문 검색 중...")
    paper = get_todays_paper()

    if paper is None:
        print("❌ 오늘 발표된 이식 관련 논문을 찾지 못했습니다.")
        sys.exit(0)

    print(f"📄 선택된 논문: {paper['title']}")
    print(f"   저널: {paper['journal']}")
    print(f"   PMID: {paper['pmid']}")

    print("🤖 Claude API로 논문 해석 중...")
    interpretation = interpret_paper(paper)

    print("💾 Redis에 논문 컨텍스트 저장 중...")
    save_paper(paper, interpretation)

    print("📨 텔레그램으로 발송 중...")
    send_daily_paper(paper, interpretation)

    print("✅ 완료!")


if __name__ == "__main__":
    main()
