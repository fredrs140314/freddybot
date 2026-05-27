import pandas as pd
import re
from urllib.parse import urljoin, urlparse
from collections import Counter
from rapidfuzz import fuzz
import scrapy
from scrapy.crawler import CrawlerProcess


class AnchorSpider(scrapy.Spider):
    name = "anchor_spider"

    custom_settings = {
        "LOG_ENABLED": False,
        "DOWNLOAD_TIMEOUT": 10,
    }

    def __init__(self, start_url, max_pages, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.start_urls = [start_url]
        self.allowed_domain = urlparse(start_url).netloc
        self.max_pages = max_pages

        self.visited_pages = set()
        self.link_data = []

    def parse(self, response):

        if len(self.visited_pages) >= self.max_pages:
            return

        current_url = response.url

        if current_url in self.visited_pages:
            return

        self.visited_pages.add(current_url)

        links = response.css("a")

        for link in links:
            anchor_text = " ".join(link.css("::text").getall()).strip()
            href = link.attrib.get("href")

            if not href:
                continue

            destination_url = urljoin(current_url, href)

            self.link_data.append({
                "source_url": current_url,
                "anchor_text": anchor_text,
                "destination_url": destination_url
            })

        # Follow internal links only
        for href in response.css("a::attr(href)").getall():

            next_url = urljoin(current_url, href)
            parsed = urlparse(next_url)

            if parsed.netloc == self.allowed_domain:
                yield scrapy.Request(next_url, callback=self.parse)


def normalize_text(text):

    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def match_keyword(anchor_text, keywords):

    anchor_normalized = normalize_text(anchor_text)

    matched = []

    for keyword in keywords:

        keyword_normalized = normalize_text(keyword)

        if keyword_normalized in anchor_normalized:
            matched.append(keyword)
            continue

        similarity = fuzz.partial_ratio(
            keyword_normalized,
            anchor_normalized
        )

        if similarity >= 85:
            matched.append(keyword)

    return matched


def run_audit(uploaded_file, start_url, max_pages):

    keyword_df = pd.read_excel(uploaded_file)

    keywords = keyword_df.iloc[:, 0].dropna().astype(str).tolist()

    process = CrawlerProcess()

    spider = AnchorSpider

    process.crawl(
        spider,
        start_url=start_url,
        max_pages=max_pages
    )

    crawler = next(iter(process.crawlers))

    process.start()

    link_data = crawler.spider.link_data

    links_df = pd.DataFrame(link_data)

    if links_df.empty:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            {
                "total_links": 0,
                "optimized_links": 0,
                "unoptimized_links": 0,
                "unique_keywords_found": 0,
            }
        )

    matched_keywords_column = []
    optimized_column = []

    keyword_counter = Counter()

    for _, row in links_df.iterrows():

        matches = match_keyword(row["anchor_text"], keywords)

        matched_keywords_column.append(", ".join(matches))

        is_optimized = len(matches) > 0

        optimized_column.append(is_optimized)

        for keyword in matches:
            keyword_counter[keyword] += 1

    links_df["matched_keywords"] = matched_keywords_column
    links_df["optimized"] = optimized_column

    keyword_summary_df = pd.DataFrame(
        keyword_counter.items(),
        columns=["keyword", "mentions"]
    ).sort_values(by="mentions", ascending=False)

    total_links = len(links_df)
    optimized_links = links_df["optimized"].sum()
    unoptimized_links = total_links - optimized_links
    unique_keywords_found = len(keyword_counter)

    summary = {
        "total_links": total_links,
        "optimized_links": int(optimized_links),
        "unoptimized_links": int(unoptimized_links),
        "unique_keywords_found": unique_keywords_found,
    }

    return keyword_summary_df, links_df, summary
