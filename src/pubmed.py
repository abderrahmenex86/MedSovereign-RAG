"""PubMed E-utilities client and XML parsing (stdlib XML + httpx)."""

from __future__ import annotations

import time
import xml.etree.ElementTree as ElementTree

import httpx

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL_NAME = "medsovereign-rag"

DEFAULT_QUERY = (
    "(guideline[Publication Type] OR systematic review[Publication Type] "
    "OR meta-analysis[Publication Type] OR randomized controlled trial[Publication Type]) "
    "AND hasabstract[text] "
    'AND ("2015/01/01"[Date - Publication] : "2026/12/31"[Date - Publication])'
)


def _text(element):
    if element is None:
        return ""
    if isinstance(element, str):
        return " ".join(element.split())
    return " ".join("".join(element.itertext()).split())


def _publication_date(article):
    pub_date = article.find("Journal/JournalIssue/PubDate")
    if pub_date is None:
        return ""

    year = _text(pub_date.find("Year"))
    if not year:
        return _text(pub_date.find("MedlineDate"))

    parts = [year]
    month = _text(pub_date.find("Month"))
    day = _text(pub_date.find("Day"))
    if month:
        parts.append(month)
    if day:
        parts.append(day)
    return "-".join(parts)


def parse_pubmed_article(article):
    citation = article.find("MedlineCitation")
    if citation is None:
        return None

    pmid = _text(citation.find("PMID"))
    article_element = citation.find("Article")
    if not pmid or article_element is None:
        return None

    title = _text(article_element.find("ArticleTitle")) or "Untitled"
    sections = []

    for abstract_node in article_element.findall("Abstract/AbstractText"):
        label = _text(abstract_node.get("Label"))
        text = _text(abstract_node)
        if text:
            sections.append({"heading": label, "text": text})

    if not sections:
        text = _text(article_element.find("Abstract"))
        if text:
            sections.append({"heading": "", "text": text})

    if not sections:
        return None

    journal = _text(article_element.find("Journal/Title"))
    publication_types = [
        _text(node)
        for node in article_element.findall("PublicationTypeList/PublicationType")
        if _text(node)
    ]
    mesh_terms = [
        _text(node)
        for node in citation.findall("MeshHeadingList/MeshHeading/DescriptorName")
        if _text(node)
    ]
    authors = []
    for author in article_element.findall("AuthorList/Author"):
        last_name = _text(author.find("LastName"))
        fore_name = _text(author.find("ForeName"))
        if last_name:
            authors.append(f"{fore_name} {last_name}".strip())

    doi = ""
    for article_id in article.findall("PubmedData/ArticleIdList/ArticleId"):
        if article_id.get("IdType") == "doi":
            doi = _text(article_id)

    return {
        "id": f"PMID:{pmid}",
        "source": "pubmed",
        "title": title,
        "text": "\n\n".join(section["text"] for section in sections),
        "sections": sections,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "published": _publication_date(article_element),
        "license": "PubMed abstract; publisher terms apply",
        "pmid": pmid,
        "meta": {
            "journal": journal,
            "publication_types": publication_types,
            "mesh": mesh_terms,
            "doi": doi,
            "authors": authors[:20],
        },
    }


def parse_pubmed_xml(xml_bytes):
    root = ElementTree.fromstring(xml_bytes)
    documents = []

    for article in root.findall(".//PubmedArticle"):
        document = parse_pubmed_article(article)
        if document:
            documents.append(document)

    return documents


def _pause(api_key):
    time.sleep(0.11 if api_key else 0.34)


def make_client():
    return httpx.Client(
        timeout=httpx.Timeout(connect=20.0, read=120.0, write=30.0, pool=20.0),
        transport=httpx.HTTPTransport(retries=3),
        headers={"User-Agent": f"{TOOL_NAME}/1.0"},
    )


def _request(client, endpoint, params, attempts=5):
    last_error = None

    for attempt in range(attempts):
        response = client.get(f"{EUTILS_BASE}/{endpoint}", params=params)

        if response.status_code == 429 or 500 <= response.status_code < 600:
            last_error = httpx.HTTPStatusError(
                f"PubMed returned {response.status_code}",
                request=response.request,
                response=response,
            )
            time.sleep(2**attempt)
            continue

        response.raise_for_status()
        return response

    raise last_error or RuntimeError("PubMed request failed")


def _get_json(client, endpoint, params, attempts=8):
    """Retry intermittent HTML/error bodies returned with a 200 status."""
    last_response = None

    for attempt in range(attempts):
        response = _request(client, endpoint, params)
        try:
            return response.json()
        except ValueError:
            last_response = response
            print(
                f"[WARN] PubMed returned non-JSON content "
                f"({response.status_code}, {response.headers.get('content-type')}): "
                f"{response.text[:180]!r}",
                flush=True,
            )
            time.sleep(min(2**attempt, 30))

    content_type = last_response.headers.get("content-type") if last_response else "unknown"
    raise RuntimeError(
        f"PubMed returned non-JSON content ({content_type}); retry the fetch with --resume"
    )


def search_pubmed(
    client,
    query,
    limit,
    api_key=None,
    email=None,
    sort="relevance",
    page_size=10_000,
):
    common = {"db": "pubmed", "term": query, "retmode": "json", "sort": sort, "tool": TOOL_NAME}
    if email:
        common["email"] = email
    if api_key:
        common["api_key"] = api_key

    pmids: list[str] = []
    seen = set()
    retstart = 0

    _pause(api_key)

    while len(pmids) < limit:
        params = {**common, "retmax": min(page_size, limit - len(pmids)), "retstart": retstart}
        payload = _get_json(client, "esearch.fcgi", params).get("esearchresult", {})
        page = payload.get("idlist", [])

        if not page:
            break

        for pmid in page:
            if pmid not in seen:
                seen.add(pmid)
                pmids.append(pmid)

        total = int(payload.get("count", "0"))
        retstart += len(page)
        if retstart >= total:
            break

        _pause(api_key)

    return pmids[:limit]


def fetch_pubmed_documents(
    client,
    pmids,
    api_key=None,
    email=None,
    batch_size=200,
):
    common = {"db": "pubmed", "retmode": "xml", "tool": TOOL_NAME}
    if email:
        common["email"] = email
    if api_key:
        common["api_key"] = api_key

    for start in range(0, len(pmids), batch_size):
        batch = pmids[start : start + batch_size]
        params = {**common, "id": ",".join(batch)}
        response = _request(client, "efetch.fcgi", params)
        yield from parse_pubmed_xml(response.content)

        _pause(api_key)
