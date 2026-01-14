from flask import Flask, render_template, request, Response, stream_with_context
from scraper import scrape_product

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/run", methods=["POST"])
def run_scraper():
    url = request.form.get("url")
    if not url:
        return "Please provide a URL", 400

    # stream_with_context allows Vercel to keep the connection open while scraping
    return Response(stream_with_context(scrape_product(url)), mimetype="text/plain")


if __name__ == "__main__":
    app.run(debug=True)