#!/usr/bin/env python3

import os
from datetime import datetime, timezone
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    current_user,
    login_required,
)
from werkzeug.security import generate_password_hash, check_password_hash

from flask import Flask, render_template, request, redirect, url_for, session
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
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

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

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    class User(UserMixin):
        def __init__(self, doc):
            self.id = str(doc["_id"])
            self.email = doc.get("email", "")
            self.name = doc.get("name", "")

    @login_manager.user_loader
    def load_user(user_id):
        try:
            doc = db["users"].find_one({"_id": ObjectId(user_id)})
            return User(doc) if doc else None
        except Exception:
            return None

    @app.route("/")
    def home():
        # list 10 recent items
        session["back_url"] = url_for("home")
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

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            name = (request.form.get("name") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            password = request.form.get("password") or ""
            if not name or not email or not password:
                return render_template("signup.html", error="All fields are required.")
            if db["users"].find_one({"email": email}):
                return render_template("signup.html", error="Email already registered.")
            doc = {
                "name": name,
                "email": email,
                "password_hash": generate_password_hash(password),
                "created_at": datetime.utcnow(),
            }
            res = db["users"].insert_one(doc)
            user = User({**doc, "_id": res.inserted_id})
            login_user(user)
            return redirect(url_for("home"))
        return render_template("signup.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            password = request.form.get("password") or ""
            doc = db["users"].find_one({"email": email})
            if not doc or not check_password_hash(
                doc.get("password_hash", ""), password
            ):
                return render_template("login.html", error="Invalid email or password.")
            login_user(User(doc))
            return redirect(url_for("home"))
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("home"))

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

            # assign owner to the item
            owner_id = current_user.get_id() if current_user.is_authenticated else None
            owner_email = (
                current_user.email if current_user.is_authenticated else contact_email
            )
            item.update({"owner_id": owner_id, "owner_email": owner_email})

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

        back_url = session.get("back_url", url_for("home"))
        return render_template("detail.html", item=doc, back_url=back_url)

    @app.route("/search")
    def search():
        q = (request.args.get("q") or "").strip()
        status = (request.args.get("status") or "").strip().lower()

        # remember this exact search page for the Back link
        session["back_url"] = url_for("search", q=q, status=status)

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

    @app.route("/item/<post_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit(post_id):
        # load the item
        try:
            doc = db["items"].find_one({"_id": ObjectId(post_id)})
        except Exception:
            doc = None
        if not doc:
            return render_template("error.html", error="Item not found"), 404

        # only the owner can edit
        owner_id = str(doc.get("owner_id")) if doc.get("owner_id") is not None else None
        if current_user.get_id() != owner_id:
            return render_template("error.html", error="Not allowed"), 403

        if request.method == "POST":
            title = (request.form.get("title") or "").strip()
            status = (request.form.get("status") or "").strip().lower()
            location = (request.form.get("location") or "").strip()
            description = (request.form.get("description") or "").strip()
            contact_name = (request.form.get("contact_name") or "").strip()
            contact_email = (request.form.get("contact_email") or "").strip()
            image_url = (request.form.get("image_url") or "").strip()

            if not title or not location or not contact_email:
                return render_template(
                    "edit.html",
                    item=doc,
                    error="Title, location, and contact email are required.",
                    cancel_url=url_for("detail", post_id=post_id),
                )

            # allow lost/found/resolved on edit
            if status not in ("lost", "found", "resolved"):
                status = doc.get("status", "lost")

            update = {
                "title": title,
                "status": status,
                "location": location,
                "description": description,
                "contact_name": contact_name,
                "contact_email": contact_email,
                "image_url": image_url,
                "updated_at": datetime.now(timezone.utc),
            }

            db["items"].update_one({"_id": doc["_id"]}, {"$set": update})
            return redirect(url_for("detail", post_id=post_id))

        # GET → prefilled form
        return render_template(
            "edit.html",
            item=doc,
            cancel_url=url_for("detail", post_id=post_id),
        )

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