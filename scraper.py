import requests
import json
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def clean(text):
    return " ".join(text.split()).strip() if text else ""

def scrape_product(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        return {"success": False, "error": "Failed to fetch"}

    soup = BeautifulSoup(r.text, "html.parser")

    sku_tag = soup.select_one('div[itemprop="sku"]') or soup.select_one('.product.attribute.sku .value')
    sku = sku_tag.text.strip() if sku_tag else "UNKNOWN"

    name = clean((soup.select_one("h1.page-title") or {}).get_text())
    price = clean((soup.select_one("span.price") or {}).get_text())
    desc = clean((soup.select_one("#description") or {}).get_text())

    sizes = [s.text.strip() for s in soup.select(".swatch-attribute.size .swatch-option")]
    fabrics = [f.text.strip() for f in soup.select(".swatch-attribute.fabric .swatch-option")]

    images = []
    for script in soup.find_all("script", type="text/x-magento-init"):
        if "mage/gallery/gallery" in script.text:
            try:
                data = json.loads(script.text)
                gallery = (
                    data.get('[data-gallery-role=gallery-placeholder]', {})
                    .get('mage/gallery/gallery', {})
                    .get('data', [])
                )
                for img in gallery:
                    if img.get("full"):
                        images.append(img["full"])
            except:
                pass

    return {
        "success": True,
        "sku": sku,
        "name": name,
        "price": price,
        "description": desc,
        "sizes": sizes,
        "fabrics": fabrics,
        "images": list(dict.fromkeys(images))
    }
