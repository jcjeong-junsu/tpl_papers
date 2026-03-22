"""PubMed/PMC에서 이식 관련 최신 논문을 검색하고 가져오는 모듈."""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import httpx

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PMC_OA_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"

# 주요 이식 관련 저널 (높은 IF 순)
TOP_JOURNALS = [
    "N Engl J Med", "Lancet", "JAMA", "BMJ", "Nature", "Science",
    "Am J Transplant", "Transplantation", "J Heart Lung Transplant",
    "Liver Transpl", "Kidney Int", "Ann Surg", "JAMA Surg",
    "Nat Med", "Lancet Gastroenterol Hepatol",
]

SEARCH_QUERY = (
    '("organ transplantation"[MeSH Terms] OR "kidney transplantation"[MeSH Terms] '
    'OR "liver transplantation"[MeSH Terms] OR "heart transplantation"[MeSH Terms] '
    'OR "lung transplantation"[MeSH Terms] OR "hematopoietic stem cell transplantation"[MeSH Terms] '
    'OR "graft rejection"[MeSH Terms] OR "immunosuppression therapy"[MeSH Terms])'
)


def search_recent_papers(days: int = 7, max_results: int = 20) -> list[str]:
    """최근 N일 이내의 이식 관련 논문 PMID 목록을 반환."""
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
    date_to = datetime.now().strftime("%Y/%m/%d")

    params = {
        "db": "pubmed",
        "term": SEARCH_QUERY,
        "retmax": max_results,
        "sort": "relevance",
        "datetype": "pdat",
        "mindate": date_from,
        "maxdate": date_to,
        "retmode": "xml",
    }

    resp = httpx.get(PUBMED_SEARCH_URL, params=params, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    return [id_elem.text for id_elem in root.findall(".//Id") if id_elem.text]


def fetch_paper_details(pmids: list[str]) -> list[dict]:
    """PMID 목록으로 논문 상세 정보를 가져옴."""
    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }

    resp = httpx.get(PUBMED_FETCH_URL, params=params, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    papers = []

    for article in root.findall(".//PubmedArticle"):
        medline = article.find(".//MedlineCitation")
        if medline is None:
            continue

        pmid = medline.findtext(".//PMID", "")
        art = medline.find(".//Article")
        if art is None:
            continue

        title = art.findtext(".//ArticleTitle", "")
        abstract_parts = art.findall(".//Abstract/AbstractText")
        abstract = "\n".join(
            (f"{p.get('Label', '')}: " if p.get("Label") else "") + (p.text or "")
            for p in abstract_parts
        )

        journal = art.findtext(".//Journal/Title", "")
        journal_abbrev = art.findtext(".//Journal/ISOAbbreviation", "")

        # 날짜
        pub_date = art.find(".//Journal/JournalIssue/PubDate")
        date_str = ""
        if pub_date is not None:
            year = pub_date.findtext("Year", "")
            month = pub_date.findtext("Month", "")
            day = pub_date.findtext("Day", "")
            date_str = f"{year} {month} {day}".strip()

        # 저자
        authors = []
        for author in art.findall(".//AuthorList/Author"):
            last = author.findtext("LastName", "")
            first = author.findtext("ForeName", "")
            if last:
                authors.append(f"{last} {first}".strip())

        # DOI
        doi = ""
        for id_elem in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
            if id_elem.get("IdType") == "doi":
                doi = id_elem.text or ""
                break

        # PMC ID
        pmc_id = ""
        for id_elem in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
            if id_elem.get("IdType") == "pmc":
                pmc_id = id_elem.text or ""
                break

        papers.append({
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "journal": journal,
            "journal_abbrev": journal_abbrev,
            "date": date_str,
            "authors": authors,
            "doi": doi,
            "pmc_id": pmc_id,
        })

    return papers


def get_figure_urls(pmc_id: str) -> list[str]:
    """PMC 오픈액세스 논문에서 figure 이미지 URL을 추출."""
    if not pmc_id:
        return []

    try:
        url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/"
        resp = httpx.get(url, timeout=30, follow_redirects=True)
        resp.raise_for_status()

        figure_urls = []
        # PMC HTML에서 figure 이미지 추출
        import re
        # PMC figure 이미지 패턴
        patterns = [
            rf'src="(/pmc/articles/{pmc_id}/bin/[^"]+\.jpg)"',
            rf'src="(/pmc/articles/{pmc_id}/figure/[^"]+)"',
            rf'data-src="(https://[^"]*pmc[^"]*\.jpg)"',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, resp.text)
            for match in matches:
                if match.startswith("/"):
                    figure_urls.append(f"https://www.ncbi.nlm.nih.gov{match}")
                else:
                    figure_urls.append(match)

        # 중복 제거, 최대 3개
        seen = set()
        unique = []
        for u in figure_urls:
            if u not in seen:
                seen.add(u)
                unique.append(u)
        return unique[:3]
    except Exception:
        return []


def select_best_paper(papers: list[dict]) -> dict | None:
    """주요 저널 우선, abstract가 있는 논문을 선택."""
    if not papers:
        return None

    # abstract가 있는 논문만
    with_abstract = [p for p in papers if p["abstract"].strip()]
    if not with_abstract:
        return papers[0]

    # 주요 저널 우선
    for paper in with_abstract:
        for top_j in TOP_JOURNALS:
            if top_j.lower() in paper["journal"].lower() or top_j.lower() in paper["journal_abbrev"].lower():
                return paper

    return with_abstract[0]


def get_todays_paper() -> dict | None:
    """오늘의 이식 연구 논문을 가져옴."""
    pmids = search_recent_papers(days=7, max_results=30)
    if not pmids:
        # 범위를 넓혀서 재시도
        pmids = search_recent_papers(days=14, max_results=30)

    if not pmids:
        return None

    papers = fetch_paper_details(pmids)
    paper = select_best_paper(papers)

    if paper and paper["pmc_id"]:
        paper["figure_urls"] = get_figure_urls(paper["pmc_id"])
    elif paper:
        paper["figure_urls"] = []

    return paper
