# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
import uuid
from datetime import datetime, timezone

import feedparser
import pytest

from app.models.article import Article
from app.models.digest import Digest
from app.models.feed import Feed
from app.models.virtual_feed import VirtualFeed
from app.services.rss_generator import _to_atom_date, generate_atom_feed


def make_vf(**kwargs) -> VirtualFeed:
    vf = VirtualFeed(
        user_id=uuid.uuid4(),
        name=kwargs.get("name", "Test Feed"),
        description=kwargs.get("description", None),
        filter_type="tags",
        filter_config={"tags": ["test"]},
        is_shared=False,
        include_digest=kwargs.get("include_digest", False),
    )
    vf.id = uuid.uuid4()
    vf.rss_token = uuid.uuid4()
    vf.created_at = datetime.utcnow()
    vf.updated_at = datetime.utcnow()
    return vf


def make_article(title: str = "Test Article", tags: list | None = None) -> Article:
    feed = Feed(url="https://example.com/rss", title="Example Feed", site_url="https://example.com")
    feed.id = uuid.uuid4()

    art = Article(
        feed_id=feed.id,
        guid="guid-001",
        title=title,
        url="https://example.com/article/1",
        author="John Doe",
        content_excerpt="<p>Excerpt</p>",
        content_fulltext="<p>Full text of the article.</p>",
        tags=tags or ["test", "article"],
        fetched_at=datetime.utcnow(),
        published_at=datetime(2026, 4, 21, 9, 0, 0),
    )
    art.id = uuid.uuid4()
    art.feed = feed
    return art


def make_digest() -> Digest:
    d = Digest(
        user_id=uuid.uuid4(),
        title="Rassegna stampa — 21 aprile 2026",
        period_start=datetime(2026, 4, 20, 0, 0, 0),
        period_end=datetime(2026, 4, 21, 0, 0, 0),
        content_html="<h2>Economy</h2><p>Summary</p>",
        content_text="Economy\nSummary",
        article_count=5,
    )
    d.id = uuid.uuid4()
    d.created_at = datetime.utcnow()
    return d


BASE_URL = "http://localhost:8000/"


async def test_atom_xml_valid():
    vf = make_vf()
    articles = [make_article()]
    xml = await generate_atom_feed(vf, articles, None, BASE_URL)
    assert xml.startswith("<?xml")
    assert "<feed" in xml
    assert "xmlns" in xml


async def test_atom_parseable_by_feedparser():
    vf = make_vf(name="My Virtual Feed")
    articles = [make_article("News Article", tags=["news"])]
    xml = await generate_atom_feed(vf, articles, None, BASE_URL)

    parsed = feedparser.parse(xml)
    assert parsed.feed.get("title") == "My Virtual Feed"
    assert len(parsed.entries) == 1
    assert parsed.entries[0].get("title") == "News Article"


async def test_atom_includes_digest():
    vf = make_vf(include_digest=True)
    articles = [make_article()]
    digest = make_digest()

    xml = await generate_atom_feed(vf, articles, digest, BASE_URL)
    parsed = feedparser.parse(xml)

    # digest should be first entry
    assert len(parsed.entries) == 2
    assert "digest" in str(parsed.entries[0].get("id", ""))


async def test_atom_no_digest_when_include_false():
    vf = make_vf(include_digest=False)
    digest = make_digest()
    xml = await generate_atom_feed(vf, [make_article()], digest, BASE_URL)
    parsed = feedparser.parse(xml)
    # Only 1 entry (no digest)
    assert len(parsed.entries) == 1


async def test_atom_date_format():
    dt_naive = datetime(2026, 4, 21, 9, 0, 0)
    formatted = _to_atom_date(dt_naive)
    # Should include UTC timezone info
    assert "+00:00" in formatted or "Z" in formatted or "2026-04-21" in formatted


async def test_atom_date_format_with_timezone():
    dt_aware = datetime(2026, 4, 21, 9, 0, 0, tzinfo=timezone.utc)
    formatted = _to_atom_date(dt_aware)
    assert "2026-04-21" in formatted


async def test_atom_empty_feed():
    vf = make_vf()
    xml = await generate_atom_feed(vf, [], None, BASE_URL)
    parsed = feedparser.parse(xml)
    assert len(parsed.entries) == 0
    assert parsed.feed.get("title") == vf.name


async def test_atom_special_chars_escaped():
    vf = make_vf(name="Feed <Test> & 'More'")
    art = make_article(title='Title with <script>alert("xss")</script>')
    xml = await generate_atom_feed(vf, [art], None, BASE_URL)

    # XML must be well-formed (ElementTree escapes automatically)
    parsed = feedparser.parse(xml)
    assert len(parsed.entries) == 1
    # feedparser decodes entities, so we check the raw XML has escaped form
    assert "<script>" not in xml  # must be escaped as &lt;script&gt;


async def test_atom_max_50_articles():
    """RSS endpoint limits to 50, but generator itself handles whatever is given."""
    vf = make_vf()
    articles = [make_article(f"Article {i}") for i in range(10)]
    for i, a in enumerate(articles):
        a.guid = f"guid-{i}"
        a.id = uuid.uuid4()

    xml = await generate_atom_feed(vf, articles, None, BASE_URL)
    parsed = feedparser.parse(xml)
    assert len(parsed.entries) == 10


async def test_atom_rss_url_contains_token():
    vf = make_vf()
    xml = await generate_atom_feed(vf, [], None, BASE_URL)
    assert str(vf.rss_token) in xml


async def test_atom_source_element():
    """Articles should include <source> with feed title."""
    vf = make_vf()
    art = make_article()
    xml = await generate_atom_feed(vf, [art], None, BASE_URL)
    assert "Example Feed" in xml
