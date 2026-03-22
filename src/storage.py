"""Upstash Redis를 사용한 논문 컨텍스트 저장/조회 모듈."""

import json
import os

from upstash_redis import Redis


def _get_redis() -> Redis:
    return Redis(
        url=os.environ["UPSTASH_REDIS_URL"],
        token=os.environ["UPSTASH_REDIS_TOKEN"],
    )


def save_paper(paper: dict, interpretation: str) -> None:
    """오늘의 논문과 해석을 Redis에 저장."""
    redis = _get_redis()

    data = {
        "pmid": paper["pmid"],
        "title": paper["title"],
        "abstract": paper["abstract"],
        "journal": paper["journal"],
        "date": paper["date"],
        "authors": paper["authors"][:10],
        "doi": paper["doi"],
        "pmc_id": paper.get("pmc_id", ""),
        "figure_urls": paper.get("figure_urls", []),
        "interpretation": interpretation,
    }

    # 현재 논문으로 저장 (Q&A용)
    redis.set("current_paper", json.dumps(data, ensure_ascii=False))
    # 7일 후 만료
    redis.expire("current_paper", 7 * 24 * 60 * 60)

    # PMID로도 저장 (히스토리)
    redis.set(f"paper:{paper['pmid']}", json.dumps(data, ensure_ascii=False))
    redis.expire(f"paper:{paper['pmid']}", 7 * 24 * 60 * 60)


def get_current_paper() -> dict | None:
    """현재 저장된 논문 컨텍스트를 가져옴."""
    redis = _get_redis()
    data = redis.get("current_paper")
    if data is None:
        return None
    if isinstance(data, str):
        return json.loads(data)
    return data
