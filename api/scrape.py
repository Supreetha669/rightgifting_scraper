from scraper import scrape_product
import json

def handler(request):
    if request.method != "POST":
        return {
            "statusCode": 405,
            "body": json.dumps({"error": "POST only"})
        }

    body = request.json
    url = body.get("url")

    if not url:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "URL required"})
        }

    data = scrape_product(url)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(data)
    }
