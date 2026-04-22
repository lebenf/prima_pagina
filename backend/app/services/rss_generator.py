from datetime import datetime, timezone
from xml.dom.minidom import parseString
from xml.etree.ElementTree import Element, SubElement, tostring

from app.models.article import Article
from app.models.digest import Digest
from app.models.virtual_feed import VirtualFeed

ATOM_NS = "http://www.w3.org/2005/Atom"


async def generate_atom_feed(
    virtual_feed: VirtualFeed,
    articles: list[Article],
    digest: Digest | None,
    base_url: str,
) -> str:
    """Generate a valid Atom 1.0 feed as a UTF-8 XML string."""
    root = Element("feed")
    root.set("xmlns", ATOM_NS)

    # Feed metadata
    SubElement(root, "id").text = (
        f"{base_url}api/v1/virtual-feeds/{virtual_feed.id}/rss"
    )
    SubElement(root, "title").text = virtual_feed.name
    if virtual_feed.description:
        SubElement(root, "subtitle").text = virtual_feed.description

    rss_href = (
        f"{base_url}api/v1/virtual-feeds/{virtual_feed.id}/rss"
        f"?token={virtual_feed.rss_token}"
    )
    SubElement(root, "link", href=rss_href, rel="self", type="application/atom+xml")
    SubElement(root, "link", href=base_url.rstrip("/"), rel="alternate", type="text/html")

    if articles:
        latest = max(
            articles,
            key=lambda a: a.published_at or a.fetched_at or datetime.min,
        )
        updated_dt = latest.published_at or latest.fetched_at or datetime.utcnow()
    else:
        updated_dt = datetime.utcnow()
    SubElement(root, "updated").text = _to_atom_date(updated_dt)

    gen = SubElement(root, "generator", uri="https://github.com/prima-pagina", version="0.1")
    gen.text = "Prima Pagina"

    # Digest as first entry when include_digest=True
    if digest and virtual_feed.include_digest:
        _add_digest_entry(root, digest, virtual_feed, base_url)

    for article in articles:
        _add_article_entry(root, article)

    raw = tostring(root, encoding="unicode", xml_declaration=False)
    dom = parseString(f'<?xml version="1.0" encoding="UTF-8"?>{raw}')
    return dom.toprettyxml(indent="  ", encoding=None)


def _add_article_entry(parent: Element, article: Article) -> None:
    entry = SubElement(parent, "entry")

    SubElement(entry, "id").text = article.guid or str(article.id)
    SubElement(entry, "title").text = article.title or "(untitled)"

    if article.url:
        SubElement(entry, "link", href=article.url, rel="alternate")

    if article.published_at:
        SubElement(entry, "published").text = _to_atom_date(article.published_at)
    if article.fetched_at:
        SubElement(entry, "updated").text = _to_atom_date(article.fetched_at)

    if article.author:
        author_el = SubElement(entry, "author")
        SubElement(author_el, "name").text = article.author

    feed = getattr(article, "feed", None)
    if feed:
        source = SubElement(entry, "source")
        SubElement(source, "title").text = feed.title or ""
        if feed.site_url:
            SubElement(source, "link", href=feed.site_url)

    if article.content_excerpt:
        SubElement(entry, "summary", type="html").text = article.content_excerpt
    if article.content_fulltext:
        SubElement(entry, "content", type="html").text = article.content_fulltext

    for tag in (article.tags or []):
        SubElement(entry, "category", term=str(tag))


def _add_digest_entry(
    parent: Element,
    digest: Digest,
    virtual_feed: VirtualFeed,
    base_url: str,
) -> None:
    entry = SubElement(parent, "entry")
    SubElement(entry, "id").text = f"urn:prima-pagina:digest:{digest.id}"
    SubElement(entry, "title").text = digest.title or "Rassegna Stampa"
    SubElement(
        entry, "link",
        href=f"{base_url}api/v1/digests/{digest.id}",
        rel="alternate",
    )
    ts = _to_atom_date(digest.created_at)
    SubElement(entry, "updated").text = ts
    SubElement(entry, "published").text = ts
    author_el = SubElement(entry, "author")
    SubElement(author_el, "name").text = "Prima Pagina"
    if digest.content_html:
        SubElement(entry, "content", type="html").text = digest.content_html
    SubElement(entry, "category", term="digest")


def _to_atom_date(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
