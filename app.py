from flask import Flask, render_template, request, redirect, url_for, session
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import string
import os

app = Flask(__name__)
app.secret_key = "BuildingMaterial"

# ✅ MongoDB Atlas connection (use environment variable in Render)
app.config["MONGO_URI"] = os.getenv(
    "MONGO_URI",
    "mongodb+srv://pdurgabhavani233_db_user:pdurgabhavani233_db_user@cluster0.kusp0to.mongodb.net/buildingmaterials?retryWrites=true&w=majority&appName=Cluster0"
)

mongo = PyMongo(app)

# Collections
users_col = mongo.db.users
cart_col = mongo.db.cart
orders_col = mongo.db.orders
reviews_col = mongo.db.reviews

# Product catalog (static)
PRODUCT_CATALOG = {
    "cement": {
        "name": "Cement",
        "price": 380.0,
        "description": "OPC and PPC cement for all types of construction needs."
    },
    "bricks": {
        "name": "Bricks",
        "price": 8.0,
        "description": "High-quality red clay bricks for walls and structures."
    },
    "steel": {
        "name": "Steel",
        "price": 75.0,
        "description": "Strong TMT steel bars for long-lasting construction."
    }
}

# Login required decorator
def login_required(view_func):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper

# Tracking ID generator
def generate_tracking_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

# Routes
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/products")
@login_required
def products():
    return render_template("product.html", products=PRODUCT_CATALOG)

@app.route("/products/<item>")
@login_required
def product_detail(item):
    product = PRODUCT_CATALOG.get(item.lower())
    if not product:
        return redirect(url_for("products"))
    return render_template("product_detail.html", product=product)

@app.route("/add_to_cart", methods=["POST"])
@login_required
def add_to_cart():
    product_name = request.form.get("product_name")
    quantity = int(request.form.get("quantity", 1))

    product = None
    for key, data in PRODUCT_CATALOG.items():
        if data["name"].lower() == product_name.lower():
            product = data
            break
    if not product:
        return redirect(url_for("products"))

    existing = cart_col.find_one({"username": session["user_id"], "product_name": product["name"]})
    if existing:
        cart_col.update_one(
            {"_id": existing["_id"]},
            {"$inc": {"quantity": quantity}}
        )
    else:
        cart_col.insert_one({
            "username": session["user_id"],
            "product_name": product["name"],
            "unit_price": product["price"],
            "quantity": quantity,
            "added_at": datetime.utcnow()
        })

    return redirect(url_for("view_cart"))

@app.route("/cart")
@login_required
def view_cart():
    cart_items = list(cart_col.find({"username": session["user_id"]}))
    total = sum(item["unit_price"] * item["quantity"] for item in cart_items)
    return render_template("cart.html", cart_items=cart_items, total=total)

@app.route("/remove_from_cart/<item_id>")
@login_required
def remove_from_cart(item_id):
    from bson import ObjectId
    cart_col.delete_one({"_id": ObjectId(item_id), "username": session["user_id"]})
    return redirect(url_for("view_cart"))

@app.route("/checkout")
@login_required
def checkout():
    cart_items = list(cart_col.find({"username": session["user_id"]}))
    if not cart_items:
        return redirect(url_for("view_cart"))

    subtotal = sum(item["unit_price"] * item["quantity"] for item in cart_items)
    shipping_charges = 150.0 if subtotal < 1000 else 0.0
    total = subtotal + shipping_charges
    return render_template("checkout.html", cart_items=cart_items,
                           subtotal=subtotal, shipping_charges=shipping_charges, total=total)

@app.route("/place_order", methods=["POST"])
@login_required
def place_order():
    cart_items = list(cart_col.find({"username": session["user_id"]}))
    if not cart_items:
        return redirect(url_for("view_cart"))

    shipping_address = request.form.get("shipping_address")
    payment_method = request.form.get("payment_method")
    tracking_id = generate_tracking_id()

    for item in cart_items:
        subtotal = item["unit_price"] * item["quantity"]
        shipping_charges = 150.0 if subtotal < 1000 else 0.0
        total = subtotal + shipping_charges

        orders_col.insert_one({
            "username": session["user_id"],
            "product_name": item["product_name"],
            "unit_price": item["unit_price"],
            "quantity": item["quantity"],
            "subtotal": subtotal,
            "shipping_address": shipping_address,
            "shipping_charges": shipping_charges,
            "total_amount": total,
            "payment_method": payment_method,
            "order_status": "Pending",
            "order_date": datetime.utcnow(),
            "delivery_date": None,
            "tracking_id": tracking_id
        })

    cart_col.delete_many({"username": session["user_id"]})

    return redirect(url_for("order_confirmation", tracking_id=tracking_id))

@app.route("/order_confirmation/<tracking_id>")
@login_required
def order_confirmation(tracking_id):
    orders = list(orders_col.find({"tracking_id": tracking_id, "username": session["user_id"]}))
    if not orders:
        return redirect(url_for("products"))
    return render_template("order_confirm.html", orders=orders, tracking_id=tracking_id)

@app.route("/track_order/<tracking_id>")
@login_required
def track_order(tracking_id):
    orders = list(orders_col.find({"tracking_id": tracking_id, "username": session["user_id"]}))
    if not orders:
        return redirect(url_for("products"))
    return render_template("track_order.html", orders=orders, tracking_id=tracking_id)

@app.route("/my_orders")
@login_required
def my_orders():
    orders = list(orders_col.find({"username": session["user_id"]}).sort("order_date", -1))
    return render_template("my_orders.html", orders=orders)

@app.route("/review_order/<order_id>", methods=["GET", "POST"])
@login_required
def review_order(order_id):
    from bson import ObjectId
    order = orders_col.find_one({"_id": ObjectId(order_id), "username": session["user_id"]})
    if not order:
        return redirect(url_for("products"))

    if request.method == "POST":
        rating = int(request.form.get("rating", 0))
        comment = request.form.get("comment", "")
        existing_review = reviews_col.find_one({"order_id": order_id})
        if existing_review:
            reviews_col.update_one(
                {"_id": existing_review["_id"]},
                {"$set": {"rating": rating, "comment": comment, "review_date": datetime.utcnow()}}
            )
        else:
            reviews_col.insert_one({
                "order_id": order_id,
                "username": session["user_id"],
                "rating": rating,
                "comment": comment,
                "review_date": datetime.utcnow()
            })
        return redirect(url_for("my_orders"))

    existing_review = reviews_col.find_one({"order_id": order_id})
    return render_template("review_order.html", order=order, existing_review=existing_review)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = users_col.find_one({"username": username})
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["username"]
            return redirect(url_for("products"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if users_col.find_one({"username": username}):
            return render_template("register.html", error="User already exists")

        users_col.insert_one({
            "username": username,
            "password_hash": generate_password_hash(password)
        })
        session["user_id"] = username
        return redirect(url_for("products"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)