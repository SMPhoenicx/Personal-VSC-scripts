import json
import requests
from bs4 import BeautifulSoup
import boto3
from datetime import datetime

CATEGORY_URLS = {
    "news": "https://www.sjsreview.com/category/news/",
    "sports": "https://www.sjsreview.com/category/sports/",
    "culture": "https://www.sjsreview.com/category/culture/",
    "opinions": "https://www.sjsreview.com/category/opinions/",
    "mavericks": "https://www.sjsreview.com/category/mavericks/"
}

def scrape_articles(section, url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    article_blocks = soup.select("#contentleft .profile-rendered.catlist-panel.catlist_sidebar")
    articles = []

    for post in article_blocks:
        title_tag = post.select_one("h2 a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        link = title_tag["href"]

        author_tag = post.select_one(".catlist-writer")
        author = author_tag.get_text(strip=True).replace(",", "") if author_tag else ""

        date_tag = post.select_one(".catlist-date .time-wrapper")
        date = date_tag.get_text(strip=True) if date_tag else ""

        description_tag = post.select_one(".catlist-teaser p")
        description = description_tag.get_text(strip=True) if description_tag else ""

        image_tag = post.select_one(".catlist-panel-media img")
        image_url = image_tag["src"] if image_tag else ""

        articles.append({
            "title": title,
            "author": author,
            "date": date,
            "description": description,
            "link": link,
            "image_url": image_url,
            "section": section
        })

    return articles

def lambda_handler(event, context):
    all_articles = []
    seen_links = set()

    for section, url in CATEGORY_URLS.items():
        section_articles = scrape_articles(section, url)
        for article in section_articles:
            if article["link"] not in seen_links:
                all_articles.append(article)
                seen_links.add(article["link"])

    result = {
        "lastUpdated": datetime.utcnow().isoformat() + "Z",
        "articles": all_articles
    }

    # Upload to S3
    s3 = boto3.client("s3")
    bucket_name = "sjsreview-articles-json"  # <--- your bucket name
    key = "articles.json"
    s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(result, indent=2),
        ContentType="application/json"
    )

    return {
        "statusCode": 200,
        "body": json.dumps(f"{len(all_articles)} articles uploaded to {bucket_name}/{key}")
    }
