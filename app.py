# app.py
from flask import Flask, render_template, request, Response
from scraper import scrape_product
import sys, io

app = Flask(__name__)
app.debug = False

@app.route("/")
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

if __name__ == "__main__":
    app.run(debug=True)
