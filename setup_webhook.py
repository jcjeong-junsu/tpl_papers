"""텔레그램 웹훅 설정 스크립트 - Vercel 배포 후 1회 실행."""

import os
import sys

import httpx


def set_webhook(vercel_url: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN 환경변수를 설정해주세요.")
        sys.exit(1)

    webhook_url = f"{vercel_url}/api/webhook"
    resp = httpx.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json={"url": webhook_url},
        timeout=30,
    )
    result = resp.json()

    if result.get("ok"):
        print(f"✅ 웹훅이 설정되었습니다: {webhook_url}")
    else:
        print(f"❌ 웹훅 설정 실패: {result}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python setup_webhook.py <VERCEL_URL>")
        print("예시: python setup_webhook.py https://tpl-papers.vercel.app")
        sys.exit(1)

    set_webhook(sys.argv[1])
