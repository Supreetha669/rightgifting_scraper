import os
import csv
import json
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

# ================= CONFIG =================
CATEGORY_URL = "https://rightgifting.com/fashion/him/t-shirt.html"
HEADERS = {"User-Agent": "Mozilla/5.0"}

OUTPUT_ROOT = "output"
PRODUCT_TYPE = "t-shirt"
SKU_ROOT = os.path.join(OUTPUT_ROOT, PRODUCT_TYPE)

MAX_WORKERS = 6
csv_lock = Lock()

os.makedirs(SKU_ROOT, exist_ok=True)

# ================= HELPERS =================
def category_from_url(url):
    if "/him/" in url:
        return "Men"
    if "/her/" in url:
        return "Women"
    if "/kids/" in url:
        return "Kids"
    return "Other"

def clean(text):
    return " ".join(text.split()).strip()

# ================= IMAGE LABEL =================
def label_image(url, index):
    u = url.lower()

    if "front" in u or "ref-front" in u:
        return "front"
    if "back" in u:
        return "back"
    if "side" in u:
        return "side"
    if "chart" in u:
        return "size_chart"

    # fallback by order
    if index == 1:
        return "front"
    if index == 2:
        return "back"
    if index == 3:
        return "side"

    return f"alt_{index}"

# ================= IMAGE COLLECTOR (FIXED) =================
def collect_product_images(soup):
    urls = []

    # 🔥 PRIMARY — MAGENTO GALLERY JSON
    gallery = soup.select_one("div.fotorama-item[data-gallery]")
    if gallery:
        try:
            data = json.loads(gallery["data-gallery"])
            for item in data.get("data", []):
                img = item.get("img")
                if img and "/media/catalog/product/" in img:
                    if "chart" not in img.lower():
                        urls.append(img)
        except Exception:
            pass

    # FALLBACK — meta image
    if not urls:
        for meta in soup.select('meta[itemprop="image"]'):
            src = meta.get("content")
            if src:
                urls.append(src)

    return list(dict.fromkeys(urls))  # remove duplicates

# ================= CATEGORY SCRAPER =================
def extract_product_urls(category_url):
    print(f"🔍 Fetching category: {category_url}\n")
    urls = []

    res = requests.get(category_url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(res.text, "html.parser")

    for a in soup.select("a.product-item-link"):
        href = a.get("href")
        if href:
            href = href.replace(".html.html", ".html")
            if href not in urls:
                urls.append(href)

    print(f"✅ Found {len(urls)} products\n")
    return urls

# ================= PRODUCT SCRAPER =================
def scrape_product(product_url):
    try:
        res = requests.get(product_url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, "html.parser")

        product = soup.select_one('div[itemtype="http://schema.org/Product"]')
        if not product:
            return

        sku = product.select_one('meta[itemprop="sku"]')["content"]
        name = product.select_one('meta[itemprop="name"]')["content"]
        category = category_from_url(product_url)

        price_tag = soup.select_one("span.price")
        price = price_tag.text.strip() if price_tag else ""

        desc_tag = soup.select_one("div.product.attribute.overview div.value")
        description = clean(desc_tag.text) if desc_tag else ""

        # folders
        sku_folder = os.path.join(SKU_ROOT, sku)
        img_folder = os.path.join(sku_folder, "images")
        os.makedirs(img_folder, exist_ok=True)

        image_csv = os.path.join(sku_folder, "image_urls.csv")
        product_csv = os.path.join(sku_folder, "productdetails.csv")

        if os.path.exists(product_csv):
            print(f"⏭️  {sku} already scraped")
            return

        # sizes
        sizes = []
        size_label = soup.find("div", class_="swatch-attribute-label", string="Size")
        if size_label:
            for opt in size_label.find_next("div").find_all("div", class_="swatch-option"):
                sizes.append(opt.text.strip())

        # fabrics
        fabrics = []
        fabric_label = soup.find("div", class_="swatch-attribute-label", string="Fabric")
        if fabric_label:
            for opt in fabric_label.find_next("div").find_all("div", class_="swatch-option"):
                fabrics.append(opt.text.strip())

        # images
        image_urls = collect_product_images(soup)
        image_rows = []

        for i, img_url in enumerate(image_urls, 1):
            label = label_image(img_url, i)
            ext = os.path.splitext(img_url)[1] or ".jpg"
            filename = f"{label}{ext}"
            path = os.path.join(img_folder, filename)

            r = requests.get(img_url, headers=HEADERS, timeout=20)
            if r.status_code == 200 and len(r.content) > 2000:
                with open(path, "wb") as f:
                    f.write(r.content)
                image_rows.append([sku, label, img_url, filename])

        # image_urls.csv
        with open(image_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["sku", "label", "image_url", "filename"])
            writer.writerows(image_rows)

        # productdetails.csv
        with open(product_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "sku", "name", "category", "price",
                "description", "sizes", "fabrics", "product_url"
            ])
            writer.writerow([
                sku, name, category, price,
                description, ",".join(sizes),
                ",".join(fabrics), product_url
            ])

        print(f"✅ Scraped {sku} ({len(image_rows)} images)")

    except Exception as e:
        print(f"❌ Error {product_url}: {e}")

# ================= MAIN =================
if __name__ == "__main__":
    product_urls = extract_product_urls(CATEGORY_URL)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(scrape_product, product_urls)

    print("\n🎉 SCRAPING COMPLETED SUCCESSFULLY")
