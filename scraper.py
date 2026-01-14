import os
import csv
import json
import requests
import cloudscraper
from bs4 import BeautifulSoup

# --- 1. GLOBAL CONFIGURATION (Fixes 'Unresolved reference HEADERS') ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Vercel writeable directory
OUTPUT_DIR = "/tmp/sku"


# --- 2. HELPER FUNCTIONS (Fixes 'Unresolved reference clean') ---
def clean(text):
    return " ".join(text.split()).strip() if text else ""


# --- 3. MAIN SCRAPER FUNCTION ---
def scrape_product(url):
    yield f"--- Scraping Product ---\nURL: {url}\n"

    try:
        # Using cloudscraper to bypass the 403 Forbidden error on Vercel
        scraper = cloudscraper.create_scraper()
        r = scraper.get(url, headers=HEADERS, timeout=30)

        if r.status_code != 200:
            yield f"ERROR: Status {r.status_code}. Site might be blocking the request.\n"
            return

        soup = BeautifulSoup(r.text, "html.parser")

        # Extract SKU & Name
        sku_tag = soup.select_one('div[itemprop="sku"]') or soup.select_one('.product.attribute.sku .value')
        sku = sku_tag.text.strip() if sku_tag else url.split('/')[-1].split('.')[0].upper()
        sku = "".join(c for c in sku if c.isalnum())  # Clean for folder paths

        name_tag = soup.select_one('h1.page-title') or soup.select_one('span[itemprop="name"]')
        name = name_tag.text.strip() if name_tag else "Product Name Not Found"

        # Price and Description using the helper function
        price_tag = soup.select_one("span.price")
        price = clean(price_tag.text) if price_tag else ""

        desc_tag = soup.select_one("#description") or soup.select_one(".product.attribute.description")
        description = clean(desc_tag.text) if desc_tag else ""

        # Setup Folders in /tmp (Required for Vercel)
        sku_dir = os.path.join(OUTPUT_DIR, sku)
        img_dir = os.path.join(sku_dir, "images")
        os.makedirs(img_dir, exist_ok=True)

        yield f"✅ Success! Accessed {sku}. Downloading images...\n"

        # Image Extraction (Magento Gallery logic)
        image_urls = []
        script_tags = soup.find_all('script', type='text/x-magento-init')
        for script in script_tags:
            if 'mage/gallery/gallery' in script.text:
                try:
                    data = json.loads(script.text)
                    gallery_config = data.get('[data-gallery-role=gallery-placeholder]', {}).get('mage/gallery/gallery',
                                                                                                 {})
                    gallery_data = gallery_config.get('data', [])
                    for item in gallery_data:
                        src = item.get('full')
                        if src and "size_chart" not in src.lower():
                            image_urls.append(src)
                except:
                    continue

        image_urls = list(dict.fromkeys(image_urls))

        # Download Images
        for i, img_url in enumerate(image_urls, 1):
            try:
                img_res = scraper.get(img_url, headers=HEADERS, timeout=20)
                if img_res.status_code == 200:
                    filename = f"{sku}_image_{i}.jpg"
                    with open(os.path.join(img_dir, filename), "wb") as f:
                        f.write(img_res.content)
                    yield f"   ✓ Saved {filename}\n"
            except:
                continue

        # Save CSV Data
        with open(os.path.join(sku_dir, "productdetails.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["sku", "name", "price", "description", "url"])
            writer.writerow([sku, name, price, description, url])

        yield f"SUCCESS: Files saved in {sku_dir}\n"

    except Exception as e:
        yield f"CRITICAL ERROR: {str(e)}\n"