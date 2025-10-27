import requests
from bs4 import BeautifulSoup
import json

URL = "https://www.sjsreview.com/category/mavericks/"
response = requests.get(URL)
soup = BeautifulSoup(response.content, "html.parser")

# Select only articles inside the main content area
article_blocks = soup.select("#contentleft .profile-rendered.catlist-panel.catlist_sidebar")

articles = []

for post in article_blocks:
    title_tag = post.select_one("h2 a")
    title = title_tag.get_text(strip=True)
    link = title_tag["href"]

    author_tag = post.select_one(".catlist-writer")
    author = author_tag.get_text(strip=True).replace(",", "")

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
        "image_url": image_url
    })

# Save the articles to a JSON file
with open("articles.json", "w") as f:
    json.dump(articles, f, indent=4)
