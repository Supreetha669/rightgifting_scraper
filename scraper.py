import os
import csv
import requests
from bs4 import BeautifulSoup
import json
from io import BytesIO
import cloudinary.uploader
import cloudinary_config


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
# Inside scraper.py
OUTPUT_DIR = "sku"



# Main folder as requested
def extract_category_from_url(url):
    parts = url.lower().split("/")

    gender = "unknown"
    product_type = "unknown"
    main_category = "fashion"

    # ---------- PERSONAL PRODUCTS ----------
    if "personal-products" in parts:
        main_category = "personal-products"
        idx = parts.index("personal-products")
        product_type = parts[idx + 1] if idx + 1 < len(parts) else "unknown"

    # ---------- FASHION ----------
    else:
        if "him" in parts:
            gender = "him"
        elif "her" in parts:
            gender = "her"
        elif "babies" in parts or "kids" in parts:
            gender = "babies-kids"
        elif "plus-size" in parts:              # ✅ FIXED
            gender = "plus-size"

        PRODUCT_TYPES = [
            "t-shirt",
            "tshirt",
            "hoodies",
            "legging",
            "couple-tshirt",
            "apron"
            # Babies & Kids (your list)
            "bib",
            "baby-blanket",
            "stroller-blanket",
            "romper",
            "fabric-book",
            "height-chart",
            "drawstring-bag",
            "pencil-pouch",
            "pillow - book"
            "pillow-cum-book",
            "bookmark",
            "book - mark",
            "meal-mat",
            "apron - full",
            "cape-kids"
        ]

        for p in parts:
            if p in PRODUCT_TYPES:
                product_type = p
                break

    return main_category, gender, product_type


def clean(text):
    return " ".join(text.split()).strip() if text else ""


def scrape_product(url):
    print(f"\n--- Scraping Product ---\nURL: {url}")

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"ERROR: Status {r.status_code}")
            return

        soup = BeautifulSoup(r.text, "html.parser")
        main_category, gender, product_type = extract_category_from_url(url)

        # 1. Extract SKU & Name (Using safer selectors)
        sku_tag = soup.select_one('div[itemprop="sku"]') or soup.select_one('.product.attribute.sku .value')
        sku = sku_tag.text.strip() if sku_tag else url.split('/')[-1].split('.')[0].upper()

        name_tag = soup.select_one('h1.page-title') or soup.select_one('span[itemprop="name"]')
        name = name_tag.text.strip() if name_tag else "Product Name Not Found"

        price_tag = soup.select_one("span.price")
        price = clean(price_tag.text) if price_tag else ""

        desc_tag = soup.select_one("#description") or soup.select_one(".product.attribute.description")
        description = clean(desc_tag.text) if desc_tag else ""

        # ---------- Folders: sku / [SKU_ID] / images ----------
        sku_dir = os.path.join(
            OUTPUT_DIR,
            main_category,
            gender,
            product_type,
            sku
        )

        img_dir = os.path.join(sku_dir, "images")
        os.makedirs(img_dir, exist_ok=True)

        # ---------- Sizes & Fabrics ----------
        sizes = [opt.text.strip() for opt in soup.select(".swatch-attribute.size .swatch-option")]
        fabrics = [opt.text.strip() for opt in soup.select(".swatch-attribute.fabric .swatch-option")]

        # ---------- Image Extraction (Magento JSON Gallery) ----------
        image_urls = []

        # Magento stores the full gallery in a specific script tag
        script_tags = soup.find_all('script', type='text/x-magento-init')
        for script in script_tags:
            if 'mage/gallery/gallery' in script.text:
                try:
                    data = json.loads(script.text)
                    # Drill down into the gallery data
                    gallery_placeholder = data.get('[data-gallery-role=gallery-placeholder]', {})
                    gallery_config = gallery_placeholder.get('mage/gallery/gallery', {})
                    gallery_data = gallery_config.get('data', [])

                    for item in gallery_data:
                        src = item.get('full')  # 'full' is the high-res original image
                        if src and "size_chart" not in src.lower():
                            image_urls.append(src)
                except Exception as e:
                    continue

        # Remove duplicates
        image_urls = list(dict.fromkeys(image_urls))
        print(f"Found {len(image_urls)} high-res images")

        # ---------- Download Images ----------
        for i, img_url in enumerate(image_urls, 1):
            try:
                img_res = requests.get(img_url, headers=HEADERS, timeout=20)
                if img_res.status_code == 200:
                    filename = f"{sku}_image_{i}.jpg"
                    with open(os.path.join(img_dir, filename), "wb") as f:
                        f.write(img_res.content)
                    print(f"   ✓ Saved {filename}")
            except:
                continue



        # ---------- Save CSVs ----------
        # 1. productdetails.csv
        with open(os.path.join(sku_dir, "productdetails.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["sku", "name", "price", "description", "url"])
            writer.writerow([sku, name, price, description, url])

        # 2. variants.csv
        with open(os.path.join(sku_dir, "variants.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["sku", "size", "fabric", "price"])
            if sizes or fabrics:
                # Ensure we have at least one of each to loop, even if one list is empty
                loop_sizes = sizes if sizes else ["N/A"]
                loop_fabrics = fabrics if fabrics else ["N/A"]
                for s in loop_sizes:
                    for fab in loop_fabrics:
                        writer.writerow([sku, s, fab, price])
            else:
                writer.writerow([sku, "N/A", "N/A", price])

        print(f"SUCCESS: Data saved in folder: {sku_dir}")

    except Exception as e:
        print(f"CRITICAL ERROR on {url}: {e}")

