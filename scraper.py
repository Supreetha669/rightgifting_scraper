# scraper.py
import os
import csv
import requests
from bs4 import BeautifulSoup
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://rightgifting.com/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}


OUTPUT_DIR = "/tmp/sku"  # Vercel-safe

def clean(text):
    return " ".join(text.split()).strip() if text else ""

def scrape_product(url):
    print(f"\n--- Scraping Product ---\nURL: {url}")

    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        print(f"ERROR: Status {r.status_code}")
        return

    soup = BeautifulSoup(r.text, "html.parser")

    sku_tag = soup.select_one('div[itemprop="sku"]') or soup.select_one('.product.attribute.sku .value')
    sku = sku_tag.text.strip() if sku_tag else "UNKNOWN_SKU"

    name_tag = soup.select_one('h1.page-title')
    name = name_tag.text.strip() if name_tag else "Product Name Not Found"

    price_tag = soup.select_one("span.price")
    price = clean(price_tag.text)

    desc_tag = soup.select_one("#description")
    description = clean(desc_tag.text)

    sku_dir = os.path.join(OUTPUT_DIR, sku)
    img_dir = os.path.join(sku_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    sizes = [o.text.strip() for o in soup.select(".swatch-attribute.size .swatch-option")]
    fabrics = [o.text.strip() for o in soup.select(".swatch-attribute.fabric .swatch-option")]

    image_urls = []
    scripts = soup.find_all("script", type="text/x-magento-init")

    for script in scripts:
        if "mage/gallery/gallery" in script.text:
            data = json.loads(script.text)
            gallery = data.get('[data-gallery-role=gallery-placeholder]', {})
            images = gallery.get('mage/gallery/gallery', {}).get("data", [])
            for img in images:
                src = img.get("full")
                if src:
                    image_urls.append(src)

    image_urls = list(dict.fromkeys(image_urls))
    print(f"Images found: {len(image_urls)}")

    for i, img_url in enumerate(image_urls, 1):
        img = requests.get(img_url, headers=HEADERS)
        with open(os.path.join(img_dir, f"{sku}_{i}.jpg"), "wb") as f:
            f.write(img.content)

    with open(os.path.join(sku_dir, "productdetails.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "name", "price", "description", "url"])
        writer.writerow([sku, name, price, description, url])

    with open(os.path.join(sku_dir, "variants.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "size", "fabric", "price"])
        for s in sizes or ["N/A"]:
            for fab in fabrics or ["N/A"]:
                writer.writerow([sku, s, fab, price])

    print(f"SUCCESS → Saved in {sku_dir}")
