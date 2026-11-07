import httpx
import pytest

from src import pubmed

ARTICLE_XML = """
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <Journal>
          <JournalIssue>
            <PubDate><Year>2024</Year><Month>Jan</Month><Day>15</Day></PubDate>
          </JournalIssue>
          <Title>Example Journal</Title>
        </Journal>
        <ArticleTitle>Acute <i>bronchitis</i> in adults</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">Background text.</AbstractText>
          <AbstractText Label="RESULTS">Results text.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author><LastName>Smith</LastName><ForeName>Jane</ForeName></Author>
        </AuthorList>
        <PublicationTypeList>
          <PublicationType>Randomized Controlled Trial</PublicationType>
        </PublicationTypeList>
      </Article>
      <MeshHeadingList>
        <MeshHeading><DescriptorName>Bronchitis</DescriptorName></MeshHeading>
      </MeshHeadingList>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="doi">10.1000/example</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""


def test_parse_pubmed_xml_extracts_metadata():
    documents = pubmed.parse_pubmed_xml(ARTICLE_XML.encode())

    assert len(documents) == 1
    document = documents[0]
    assert document["id"] == "PMID:12345678"
    assert document["pmid"] == "12345678"
    assert document["title"] == "Acute bronchitis in adults"
    assert document["published"] == "2024-Jan-15"
    assert [section["heading"] for section in document["sections"]] == ["BACKGROUND", "RESULTS"]
    assert document["meta"]["journal"] == "Example Journal"
    assert document["meta"]["doi"] == "10.1000/example"
    assert document["meta"]["mesh"] == ["Bronchitis"]
    assert document["meta"]["publication_types"] == ["Randomized Controlled Trial"]
    assert document["meta"]["authors"] == ["Jane Smith"]


def test_parse_pubmed_xml_skips_articles_without_abstract():
    xml = """
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>1</PMID>
          <Article><ArticleTitle>No abstract</ArticleTitle></Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>
    """

    assert pubmed.parse_pubmed_xml(xml.encode()) == []


def test_search_and_fetch_with_mock_transport(monkeypatch):
    monkeypatch.setattr(pubmed, "_pause", lambda api_key: None)

    def handler(request):
        if request.url.path.endswith("/esearch.fcgi"):
            return httpx.Response(
                200,
                json={"esearchresult": {"count": "2", "idlist": ["1", "2"]}},
            )
        return httpx.Response(200, content=ARTICLE_XML.encode())

    client = httpx.Client(transport=httpx.MockTransport(handler))

    pmids = pubmed.search_pubmed(client, "bronchitis", limit=2)
    documents = list(pubmed.fetch_pubmed_documents(client, pmids, batch_size=2))

    assert pmids == ["1", "2"]
    assert len(documents) == 1
    assert documents[0]["pmid"] == "12345678"

    client.close()


def test_search_stops_at_limit(monkeypatch):
    monkeypatch.setattr(pubmed, "_pause", lambda api_key: None)
    requests = []

    def handler(request):
        requests.append(dict(request.url.params))
        return httpx.Response(
            200,
            json={"esearchresult": {"count": "3", "idlist": ["1", "2"]}},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    pmids = pubmed.search_pubmed(client, "query", limit=1)

    assert pmids == ["1"]
    assert requests[0]["retmax"] == "1"
    client.close()


def test_parse_pubmed_xml_requires_valid_xml():
    import xml.etree.ElementTree as ElementTree

    with pytest.raises(ElementTree.ParseError):
        pubmed.parse_pubmed_xml(b"<not-xml>")
