from flask import Flask, render_template, request, Response
from scraper import scrape_product
import sys
import io
import os # Add this

app = Flask(__name__)

# Essential for Vercel: Define the WSGI app
app.debug = False

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/run", methods=["POST"])
def run_scraper():
    url = request.form.get("url")

    def stream():
        # Using a safer way to capture output in serverless
        output = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = output

        try:
            scrape_product(url)
            yield output.getvalue()
        except Exception as e:
            yield f"ERROR: {str(e)}"
        finally:
            sys.stdout = old_stdout

    return Response(stream(), mimetype="text/plain")

# Vercel ignores this block, but keep it for local testing
if __name__ == "__main__":
    app.run()