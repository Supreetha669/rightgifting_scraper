import os
import csv
import requests
from bs4 import BeautifulSoup
import json

# Enhanced headers to mimic a real browser and bypass 403 Forbidden
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://rightgifting.com/",
    "Connection": "keep-alive"
}

# VERCEL REQUIREMENT: Only the /tmp directory is writeable
OUTPUT_DIR = "/tmp/sku"


def clean(text):
    return " ".join(text.split()).strip() if text else ""


def scrape_product(url):
    yield f"--- Scraping Product ---\nURL: {url}\n"

    try:
        session = requests.Session()
        r = session.get(url, headers=HEADERS, timeout=30)

        if r.status_code != 200:
            yield f"ERROR: Status {r.status_code}. Site might be blocking Vercel.\n"
            return

        soup = BeautifulSoup(r.text, "html.parser")

        # Extract SKU & Name
        sku_tag = soup.select_one('div[itemprop="sku"]') or soup.select_one('.product.attribute.sku .value')
        sku = sku_tag.text.strip() if sku_tag else url.split('/')[-1].split('.')[0].upper()
        sku = "".join(c for c in sku if c.isalnum())  # Clean for file system

        name_tag = soup.select_one('h1.page-title') or soup.select_one('span[itemprop="name"]')
        name = name_tag.text.strip() if name_tag else "Product Name Not Found"

        price_tag = soup.select_one("span.price")
        price = clean(price_tag.text) if price_tag else ""

        desc_tag = soup.select_one("#description") or soup.select_one(".product.attribute.description")
        description = clean(desc_tag.text) if desc_tag else ""

        # Setup Folders in /tmp
        sku_dir = os.path.join(OUTPUT_DIR, sku)
        img_dir = os.path.join(sku_dir, "images")
        os.makedirs(img_dir, exist_ok=True)

        # Image Extraction (Magento Gallery)
        image_urls = []
        script_tags = soup.find_all('script', type='text/x-magento-init')
        for script in script_tags:
            if 'mage/gallery/gallery' in script.text:
                try:
                    data = json.loads(script.text)
                    gallery_data = data.get('[data-gallery-role=gallery-placeholder]', {}).get('mage/gallery/gallery',
                                                                                               {}).get('data', [])
                    for item in gallery_data:
                        src = item.get('full')
                        if src and "size_chart" not in src.lower():
                            image_urls.append(src)
                except:
                    continue

        image_urls = list(dict.fromkeys(image_urls))
        yield f"Found {len(image_urls)} images. Downloading...\n"

        for i, img_url in enumerate(image_urls, 1):
            try:
                img_res = session.get(img_url, headers=HEADERS, timeout=20)
                if img_res.status_code == 200:
                    filename = f"{sku}_image_{i}.jpg"
                    with open(os.path.join(img_dir, filename), "wb") as f:
                        f.write(img_res.content)
                    yield f"   ✓ Saved {filename}\n"
            except:
                continue

        # Save CSVs
        with open(os.path.join(sku_dir, "productdetails.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["sku", "name", "price", "description", "url"])
            writer.writerow([sku, name, price, description, url])

        # Variants
        sizes = [opt.text.strip() for opt in soup.select(".swatch-attribute.size .swatch-option")]
        fabrics = [opt.text.strip() for opt in soup.select(".swatch-attribute.fabric .swatch-option")]

        with open(os.path.join(sku_dir, "variants.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["sku", "size", "fabric", "price"])
            loop_sizes = sizes if sizes else ["N/A"]
            loop_fabrics = fabrics if fabrics else ["N/A"]
            for s in loop_sizes:
                for fab in loop_fabrics:
                    writer.writerow([sku, s, fab, price])

        yield f"SUCCESS: Scraped and saved to /tmp/{sku}\n"

    except Exception as e:
        yield f"CRITICAL ERROR: {str(e)}\n"