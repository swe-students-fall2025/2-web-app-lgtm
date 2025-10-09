#!/usr/bin/env python3

import os
from flask import Flask, render_template, request
import pymongo
from bson.objectid import ObjectId
from dotenv import load_dotenv, dotenv_values

load_dotenv()  # load environment variables from .env


def create_app():
    #Create and configure Flask app
    app = Flask(__name__)
    app.config.from_mapping(dotenv_values())

    uri = os.getenv("MONGO_URI")
    dbname = os.getenv("MONGO_DBNAME")
    if uri and dbname:
        try:
            cxn = pymongo.MongoClient(uri, serverSelectionTimeoutMS=2000)
            db = cxn[dbname]
            cxn.admin.command("ping")
            print(" * Connected to MongoDB")
        except Exception as e:
            print(" * MongoDB not ready yet:", e)

    @app.route("/")
    def home():
        # TODO: list up to 10 recent items with title/status/location and link to details.
        return render_template("index.html")

    @app.route("/report", methods=["GET", "POST"])
    def report():
        if request.method == "POST":
            # TODO: read form, validate, insert into DB, redirect to home
            pass
        # TODO: render simple report form (title, status, location, description, contact, optional image URL)
        return render_template("report.html")

    @app.route("/item/<post_id>")
    def detail(post_id):
        # TODO: load item by ObjectId(post_id) and render all fields from the report and show message if not found.
        return render_template("detail.html", post_id=post_id)

    @app.route("/search")
    def search():
        # TODO: search title/description/location (case-insensitive) render results.
        return render_template("search.html")

    @app.errorhandler(Exception)
    def handle_error(e):
        # TODO: keep this simple for debugging during dev
        return render_template("error.html", error=e)

    return app


app = create_app()

if __name__ == "__main__":
    FLASK_PORT = os.getenv("FLASK_PORT", "5000")
    FLASK_ENV = os.getenv("FLASK_ENV")
    print(f"FLASK_ENV: {FLASK_ENV}, FLASK_PORT: {FLASK_PORT}")
    app.run(port=FLASK_PORT)
