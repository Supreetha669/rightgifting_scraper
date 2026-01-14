from flask import Flask, render_template, request, Response
from scraper import scrape_product
import sys
import io



app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/run", methods=["POST"])
def run_scraper():
    url = request.form.get("url")

    def stream():
        old_stdout = sys.stdout
        sys.stdout = mystdout = io.StringIO()

        try:
            scrape_product(url)
        except Exception as e:
            print("ERROR:", e)

        sys.stdout = old_stdout
        yield mystdout.getvalue()

    return Response(stream(), mimetype="text/plain")


if __name__ == "__main__":
    app.run(debug=True)
