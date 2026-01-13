import os
import csv
import requests
from bs4 import BeautifulSoup
import json


HEADERS = {"User-Agent": "Mozilla/5.0"}
OUTPUT_DIR = "output"


def clean(text):
    return " ".join(text.split()).strip()


def scrape_product(url):
    print(f"\nScraping URL:\n{url}\n")

    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        print("ERROR: Page not reachable")
        return

    soup = BeautifulSoup(r.text, "html.parser")

    product = soup.select_one('div[itemtype="http://schema.org/Product"]')
    if not product:
        print("ERROR: Not a valid product page")
        return

    sku = product.select_one('meta[itemprop="sku"]')["content"]
    name = product.select_one('meta[itemprop="name"]')["content"]

    price_tag = soup.select_one("span.price")
    price = clean(price_tag.text) if price_tag else ""

    desc_tag = soup.select_one("div.product.attribute.overview div.value")
    description = clean(desc_tag.text) if desc_tag else ""

    # ---------- folders ----------
    sku_dir = os.path.join(OUTPUT_DIR, sku)
    img_dir = os.path.join(sku_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    # ---------- sizes ----------
    sizes = []
    size_label = soup.find("div", class_="swatch-attribute-label", string="Size")
    if size_label:
        for opt in size_label.find_next("div").find_all("div", class_="swatch-option"):
            sizes.append(opt.text.strip())

    # ---------- fabrics ----------
    fabrics = []
    fabric_label = soup.find("div", class_="swatch-attribute-label", string="Fabric")
    if fabric_label:
        for opt in fabric_label.find_next("div").find_all("div", class_="swatch-option"):
            fabrics.append(opt.text.strip())

    # ---------- images ----------


    def collect_product_images(soup):

        image_urls = []

        # 1️⃣ Schema.org image (good but often only ONE)
        for meta in soup.select('meta[itemprop="image"]'):
            src = meta.get("content")
            if src and "/media/catalog/product/" in src:
                image_urls.append(src)

        # 2️⃣ Fotorama frames rendered in HTML (scrollable frames)
        for frame in soup.select("div.fotorama__stage__frame[href]"):
            src = frame.get("href")
            if not src:
                continue

            if "size_chart" in src or "chart" in src:
                continue

            if "/media/catalog/product/" in src:
                image_urls.append(src)

        # 3️⃣ 🔥 JS-loaded images (data-gallery) — THIS WAS MISSING
        gallery = soup.select_one("div.fotorama-item[data-gallery]")
        if gallery:
            try:
                data = json.loads(gallery["data-gallery"])
                for item in data.get("data", []):
                    src = item.get("img")
                    if src and "/media/catalog/product/" in src:
                        if "size_chart" not in src and "chart" not in src:
                            image_urls.append(src)
            except Exception:
                pass

        # 4️⃣ Remove duplicates (VERY IMPORTANT)
        image_urls = list(dict.fromkeys(image_urls))
        return image_urls

    image_urls = collect_product_images(soup)

    print(f"Found {len(image_urls)} catalog images")

    for i, img_url in enumerate(image_urls, 1):
        filename = f"image_{i}.jpg"
        path = os.path.join(img_dir, filename)

        r = requests.get(img_url, headers=HEADERS, timeout=20)
        if r.status_code == 200 and len(r.content) > 2000:
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"Saved {filename}")

    # ---------- productdetails.csv ----------
    with open(os.path.join(sku_dir, "productdetails.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "name", "price", "description", "url"])
        writer.writerow([sku, name, price, description, url])

    # ---------- variants.csv ----------
    with open(os.path.join(sku_dir, "variants.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "size", "fabric", "price"])
        if sizes and fabrics:
            for s in sizes:
                for fab in fabrics:
                    writer.writerow([sku, s, fab, price])
        else:
            writer.writerow([sku, "", "", price])

    print(f"SUCCESS: Scraped {sku}")
