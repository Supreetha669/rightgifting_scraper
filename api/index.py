from flask import Flask, render_template, request, Response
from scraper import scrape_product
import sys, io, os

app = Flask(__name__, template_folder="../templates")
app.debug = False

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/run", methods=["POST"])
def run_scraper():
    url = request.form.get("url")

    def stream():
        buffer = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buffer
        try:
            scrape_product(url)
            yield buffer.getvalue()
        except Exception as e:
            yield str(e)
        finally:
            sys.stdout = old_stdout

    return Response(stream(), mimetype="text/plain")

# Vercel needs this
def handler(request, context):
    return app(request, context)
