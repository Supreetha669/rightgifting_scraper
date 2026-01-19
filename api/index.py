from flask import Flask, render_template, request, Response
from scraper import scrape_product
import sys, io

app = Flask(__name__, template_folder="../templates")

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/run", methods=["POST"])
def run_scraper():
    url = request.form.get("url")

    def generate():
        buffer = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buffer
        try:
            scrape_product(url)
            return buffer.getvalue()
        except Exception as e:
            return str(e)
        finally:
            sys.stdout = old_stdout

    return Response(generate(), mimetype="text/plain")

# 🔥 THIS IS WHAT VERCEL NEEDS
def app_handler(environ, start_response):
    return app.wsgi_app(environ, start_response)
