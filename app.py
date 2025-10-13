#!/usr/bin/env python3

import os
from datetime import datetime, timezone

from flask import Flask, render_template, request, redirect, url_for
import pymongo
from bson.objectid import ObjectId
from dotenv import load_dotenv, dotenv_values


load_dotenv()  # load environment variables from .env
db = None
db_connected = False


def create_app():
    # Create and configure Flask app
    app = Flask(__name__)
    app.config.from_mapping(dotenv_values())

    uri = os.getenv("MONGO_URI")
    dbname = os.getenv("MONGO_DBNAME")
    if uri and dbname:
        try:
            cxn = pymongo.MongoClient(uri, serverSelectionTimeoutMS=2000)
            db = cxn[dbname]
            cxn.admin.command("ping")
            db_connected = True
            print(" * Connected to MongoDB")
        except Exception as e:
            print(" * MongoDB not ready yet:", e)
            db_connected = False

    @app.before_request
    def check_db_connection():
        if not db_connected:
            return render_template("offline.html"), 503

    @app.route("/")
    def home():
        # list 10 recent items
        items = []
        if db is not None:
            cursor = (
                db["items"]
                .find({}, {"title": 1, "status": 1, "location": 1, "created_at": 1})
                .sort("created_at", -1)
                .limit(10)
            )
            items = list(cursor)
        return render_template("index.html", items=items)

    @app.route("/report", methods=["GET", "POST"])
    def report():
        if request.method == "POST":
            # Retrieve form data
            title = request.form.get("title", "").strip()
            status = request.form.get("status", "lost").strip().lower()
            location = request.form.get("location", "").strip()
            description = request.form.get("description", "").strip()
            contact_name = request.form.get("contact_name", "").strip()
            contact_email = request.form.get("contact_email", "").strip()
            image_url = request.form.get("image_url", "").strip()

            # Validate required fields
            if not title or not location or not contact_email:
                return render_template(
                    "report.html",
                    error="Title, location, and contact email are required.",
                )

            # Insert the report into the database
            item = {
                "title": title,
                "status": status,
                "location": location,
                "description": description,
                "contact_name": contact_name,
                "contact_email": contact_email,
                "image_url": image_url,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            db["items"].insert_one(item)

            return redirect(url_for("home"))

        return render_template("report.html")

    @app.route("/item/<post_id>")
    def detail(post_id):
        try:
            doc = db["items"].find_one({"_id": ObjectId(post_id)})
        except Exception:
            doc = None

        if not doc:
            return render_template("error.html", error="Item not found"), 404

        back_url = request.referrer or url_for("home")
        return render_template("detail.html", item=doc, back_url=back_url)

    @app.route("/search")
    def search():
        q = (request.args.get("q") or "").strip()
        status = (request.args.get("status") or "").strip().lower()

        criteria = {}
        if q:
            # case-insensitive
            rx = {"$regex": q, "$options": "i"}
            criteria["$or"] = [
                {"title": rx},
                {"description": rx},
                {"location": rx},
            ]
        if status:
            criteria["status"] = status

        projection = {
            "title": 1,
            "status": 1,
            "location": 1,
            "created_at": 1,
            "description": 1,
        }

        # sort by created_at descending order
        cursor = (
            db["items"]
            .find(criteria, projection)
            .sort([("created_at", -1), ("_id", -1)])
            .limit(25)
        )

        items = list(cursor)
        # string ids for links
        for it in items:
            it["sid"] = str(it["_id"])

        return render_template("search.html", items=items, q=q, status=status)

    @app.errorhandler(Exception)
    def handle_error(e):
        return render_template("error.html", error=f"{e.__class__.__name__}: {e}"), 500

    return app


app = create_app()

if __name__ == "__main__":
    flask_port = os.getenv("FLASK_PORT", "5000")
    flask_env = os.getenv("FLASK_ENV")
    print(f"FLASK_ENV: {flask_env}, FLASK_PORT: {flask_port}")
    app.run(port=flask_port)
