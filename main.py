import os
import sys
import csv
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

#UI_CATEGORY

CATEGORY = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

CATEGORY_MAP = {
    "men": "/him/",
    "women": "/her/",
    "kids": "/kids/"
}


# ================= CONFIG =================
SITEMAP_URL = "https://rightgifting.com/sitemap.xml"
HEADERS = {"User-Agent": "Mozilla/5.0"}
SKU_ROOT = "sku"
MASTER_CSV = "master_variants.csv"
MAX_WORKERS = 6

os.makedirs(SKU_ROOT, exist_ok=True)
csv_lock = Lock()

# ================= MASTER CSV INIT =================
if not os.path.exists(MASTER_CSV):
    with open(MASTER_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "sku",
            "category",
            "size",
            "fabric",
            "base_price",
            "product_name",
            "product_url"

        ])


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


def download_image(url, folder, idx):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            path = os.path.join(folder, f"image_{idx}.jpg")
            with open(path, "wb") as f:
                f.write(r.content)
            return path
    except:
        pass
    return ""


# ================= SCRAPER =================
def scrape_product(product_url):
    try:
        res = requests.get(product_url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, "html.parser")

        product = soup.select_one('div[itemtype="http://schema.org/Product"]')
        if not product:
            return

        sku = product.select_one('meta[itemprop="sku"]')["content"]
        sku_folder = os.path.join(SKU_ROOT, sku)
        os.makedirs(sku_folder, exist_ok=True)

        product_csv = os.path.join(sku_folder, "productdetails.csv")

        # Resume only if real data exists
        if os.path.exists(product_csv) and os.path.getsize(product_csv) > 50:
            print(f" {sku}")
            return

        # -------- BASIC DETAILS --------
        name = product.select_one('meta[itemprop="name"]')["content"]
        category = category_from_url(product_url)

        price_tag = soup.select_one("span.price")
        price = price_tag.text.strip() if price_tag else ""

        desc_tag = soup.select_one(
            "div.product.attribute.overview div.value"
        )
        description = clean(desc_tag.text) if desc_tag else ""

        # -------- SI
        # ZES --------
        sizes = []
        size_label = soup.find("div", class_="swatch-attribute-label", string="Size")
        if size_label:
            container = size_label.find_next("div", class_="swatch-option-container")
            if container:
                for opt in container.find_all("div", class_="swatch-option"):
                    sizes.append(opt.text.strip())

        # -------- FABRICS --------
        fabrics = []
        fabric_label = soup.find("div", class_="swatch-attribute-label", string="Fabric")
        if fabric_label:
            container = fabric_label.find_next("div", class_="swatch-option-container")
            if container:
                for opt in container.find_all("div", class_="swatch-option"):
                    fabrics.append(opt.text.strip())

        # -------- IMAGES --------
        image_urls = []
        for img in soup.select(".fotorama__stage__frame img"):
            src = img.get("src")
            if src and src not in image_urls:
                image_urls.append(src)

        for i, img_url in enumerate(image_urls, 1):
            download_image(img_url, sku_folder, i)

        # -------- productdetails.csv --------
        with open(product_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "sku",
                "product_name",
                "category",
                "price",
                "description",
                "sizes",
                "fabrics",
                "image_url",
                "product_url"
            ])
            writer.writerow([
                sku,
                name,
                category,
                price,
                description,
                ",".join(sizes),
                ",".join(fabrics),
                product_url
            ])

        # -------- variants.csv (PER SKU) --------
        variant_csv = os.path.join(sku_folder, "variants.csv")
        with open(variant_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "sku",
                "category",
                "size",
                "fabric",
                "base_price"
            ])
            for size in sizes:
                for fabric in fabrics:
                    writer.writerow([
                        sku,
                        category,
                        size,
                        fabric,
                        price
                    ])

        # -------- MASTER CSV (ALL SKUs) --------
        with csv_lock:
            with open(MASTER_CSV, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for size in sizes:
                    for fabric in fabrics:
                        writer.writerow([
                            sku,
                            category,
                            size,
                            fabric,
                            price,
                            name,
                            product_url
                        ])

        print(f"✅ Scraped {sku}")

    except Exception as e:
        print(f"❌ Error {product_url}: {e}")


# ================= MAIN =================
print("🔍 Fetching product sitemap...")
sitemap = requests.get(SITEMAP_URL, headers=HEADERS)
soup = BeautifulSoup(sitemap.text, "xml")

product_urls = [
    loc.text.strip()
    for loc in soup.find_all("loc")
    if "t-shirtrg" in loc.text.lower()
]

print(f"Found {len(product_urls)} T-Shirt products\n")

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    executor.map(scrape_product, product_urls)

print("\n🎉 SCRAPING COMPLETED SUCCESSFULLY")
