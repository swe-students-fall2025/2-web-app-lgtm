#!/usr/bin/env python3

import os
from flask import Flask, render_template, request, redirect, url_for
import pymongo
from bson.objectid import ObjectId
from dotenv import load_dotenv, dotenv_values
from datetime import datetime, timezone

load_dotenv()  # load environment variables from .env
db = None


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
            app.mongo = db
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
        # TODO: load item by ObjectId(post_id) and render all fields from the report and show message if not found.
        return render_template("detail.html", post_id=post_id)

    @app.route("/search")
    def search():
        q = (request.args.get("q") or "").strip()
        status = (request.args.get("status") or "").strip().lower()

        # criteria (implicit AND between keys)
        criteria = {}
        if q:
            rx = {"$regex": q, "$options": "i"}  # case-insensitive
            criteria["$or"] = [
                {"title": rx},
                {"description": rx},
                {"location": rx},
            ]
        if status:
            criteria["status"] = status

        # projection + sort + limit
        projection = {"title": 1, "status": 1, "location": 1, "date_event": 1, "description": 1}
        cursor = app.mongo["items"].find(criteria, projection).sort("_id", -1).limit(25)
        items = list(cursor)
        
        for it in items:
            it["sid"] = str(it["_id"])
            
        return render_template("search.html", items=items, q=q, status=status)

    @app.errorhandler(Exception)
    def handle_error(e):
        # TODO: keep this simple for debugging during dev
        return render_template("error.html", error=e)

    return app


app = create_app()

if __name__ == "__main__":
    flask_port = os.getenv("FLASK_PORT", "5000")
    flask_env = os.getenv("FLASK_ENV")
    print(f"FLASK_ENV: {flask_env}, FLASK_PORT: {flask_port}")
    app.run(port=flask_port)
