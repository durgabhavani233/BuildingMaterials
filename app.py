from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate   # ✅ Added
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import random
import string


app = Flask(__name__)
app.secret_key = "dev-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ✅ Enable migrations
migrate = Migrate(app, db)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    product_name = db.Column(db.String(120), nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    product_name = db.Column(db.String(120), nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    shipping_address = db.Column(db.Text, nullable=False)
    shipping_charges = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    order_status = db.Column(db.String(50), default="Pending")
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    delivery_date = db.Column(db.DateTime, nullable=True)
    tracking_id = db.Column(db.String(20, ), unique=True, nullable=False)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    review_date = db.Column(db.DateTime, default=datetime.utcnow)


# Simple product catalog (demo data)
PRODUCT_CATALOG = {
    "concrete": {
        "name": "Concrete",
        "image": "https://media.istockphoto.com/id/692096736/photo/concrete-pouring-during-commercial-concreting-floors-of-building.jpg?s=612x612&w=0&k=20&c=LuGlrtanYNsJNatAYczwcEC5QCpJjsGhSFUcora3MfE=",
        "description": "Durable ready-mix concrete for strong foundations.",
        "specs": ["M20 to M40 grades", "Fast-setting options", "Bulk delivery available"],
        "price": 500.0
    },
    "bricks": {
        "name": "Bricks",
        "image": "https://t3.ftcdn.net/jpg/05/61/69/58/360_F_561695885_nsjqnCQs0O9vkg78kPY0Pj2r3j5tBwXa.jpg",
        "description": "High-quality red clay bricks for walls and structures.",
        "specs": ["Standard and modular sizes", "Low water absorption", "High compressive strength"],
        "price": 8.0
    },
    "steel": {
        "name": "Steel",
        "image": "https://www.shutterstock.com/image-photo/prepare-products-delivery-customers-deformed-260nw-2462110609.jpg",
        "description": "Strong TMT steel bars for long-lasting construction.",
        "specs": ["Fe500/Fe550 grades", "Corrosion resistant", "Various diameters"],
        "price": 75.0
    },
    "wood": {
        "name": "Wood",
        "image": "https://4.imimg.com/data4/WN/KO/MY-3909841/wooden-logs.jpg",
        "description": "Premium timber and plywood for interiors and roofing.",
        "specs": ["Seasoned timber", "Marine-grade plywood", "Custom cuts available"],
        "price": 120.0
    },
    "cement": {
        "name": "Cement",
        "image": "https://5.imimg.com/data5/LU/KD/MY-53176023/ultratech-cement.jpg",
        "description": "OPC and PPC cement for all types of construction needs.",
        "specs": ["OPC 43/53 grade", "PPC", "Fresh stock"],
        "price": 380.0
    },
    "tiles": {
        "name": "Tiles",
        "image": "https://www.shutterstock.com/image-photo/colored-samples-ceramic-tiles-kitchen-600nw-2117695976.jpg",
        "description": "Beautiful floor and wall tiles for modern designs.",
        "specs": ["Glossy/matte finishes", "Anti-skid options", "Multiple sizes"],
        "price": 55.0
    },
    "sand": {
        "name": "Sand",
        "image": "https://cementshop.in/wp-content/uploads/2021/06/sand2.jpg",
        "description": "High-grade river sand and M-sand for construction.",
        "specs": ["River sand", "M-sand", "Clean and graded"],
        "price": 35.0
    },
    "aggregate": {
        "name": "Aggregate",
        "image": "https://5.imimg.com/data5/SELLER/Default/2022/2/JA/TV/UJ/14684209/10-mm-construction-aggerate-500x500.jpg",
        "description": "Crushed stone and gravel aggregates for concrete mixes.",
        "specs": ["10mm/20mm/40mm", "Dust-free", "Bulk supply"],
        "price": 28.0
    },
    "glass": {
        "name": "Glass",
        "image": "https://t3.ftcdn.net/jpg/02/74/92/66/360_F_274926617_3PkKeuunfe0Ch4KIo8ANcOdJB1zjaxYU.jpg",
        "description": "Clear and toughened glass for windows and facades.",
        "specs": ["Toughened/laminated", "Custom sizes", "High clarity"],
        "price": 250.0
    },
    "marble": {
        "name": "Marble",
        "image": "https://rynestone.in/cdn/shop/articles/Featured_Image_BLogb_1.png?v=1643613468",
        "description": "Premium marble for flooring and countertops.",
        "specs": ["Multiple colors", "Polished/honed", "Imported and local"],
        "price": 900.0
    },
    "gypsum": {
        "name": "Gypsum",
        "image": "https://www.croplife.com/wp-content/uploads/2020/12/Gypsum-Source-of-Calcium-and-Sulfur.jpg",
        "description": "Gypsum boards for ceilings and partitions.",
        "specs": ["Standard and moisture-resistant", "Lightweight", "Smooth finish"],
        "price": 320.0
    },
}


def login_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped_view


def generate_tracking_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/products") 
@login_required
def products():
    return render_template("product.html")


@app.route("/products/<item>")
@login_required
def product_detail(item: str):
    key = item.lower()
    product = PRODUCT_CATALOG.get(key)
    if not product:
        return redirect(url_for("products"))
    return render_template("product_detail.html", product=product)


@app.route("/add_to_cart", methods=["POST"])
@login_required
def add_to_cart():
    product_name = request.form.get("product_name")
    quantity_raw = request.form.get("quantity")
    try:
        quantity = int(quantity_raw)
    except (TypeError, ValueError):
        return redirect(url_for("products"))
    
    selected = None
    for key, data in PRODUCT_CATALOG.items():
        if data["name"].lower() == (product_name or "").lower():
            selected = data
            break
    if not selected:
        return redirect(url_for("products"))
    
    existing = Cart.query.filter_by(
        username=session.get("user_id"),
        product_name=selected["name"]
    ).first()
    
    if existing:
        existing.quantity += quantity
    else:
        cart_item = Cart(
            username=session.get("user_id"),
            product_name=selected["name"],
            unit_price=selected["price"],
            quantity=quantity
        )
        db.session.add(cart_item)
    
    db.session.commit()
    return redirect(url_for("view_cart"))


@app.route("/cart")
@login_required
def view_cart():
    cart_items = Cart.query.filter_by(username=session.get("user_id")).all()
    total = sum(item.unit_price * item.quantity for item in cart_items)
    return render_template("cart.html", cart_items=cart_items, total=total)


@app.route("/remove_from_cart/<int:item_id>")
@login_required
def remove_from_cart(item_id):
    item = Cart.query.get_or_404(item_id)
    if item.username == session.get("user_id"):
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for("view_cart"))


@app.route("/checkout")
@login_required
def checkout():
    cart_items = Cart.query.filter_by(username=session.get("user_id")).all()
    if not cart_items:
        return redirect(url_for("view_cart"))
    
    subtotal = sum(item.unit_price * item.quantity for item in cart_items)
    shipping_charges = 150.0 if subtotal < 1000 else 0.0
    total = subtotal + shipping_charges
    
    return render_template("checkout.html", 
                         cart_items=cart_items, 
                         subtotal=subtotal, 
                         shipping_charges=shipping_charges, 
                         total=total)


@app.route("/place_order", methods=["POST"])
@login_required
def place_order():
    cart_items = Cart.query.filter_by(username=session.get("user_id")).all()
    if not cart_items:
        return redirect(url_for("view_cart"))
    
    shipping_address = request.form.get("shipping_address")
    payment_method = request.form.get("payment_method")
    
    if not shipping_address or not payment_method:
        return redirect(url_for("checkout"))
    
    subtotal = sum(item.unit_price * item.quantity for item in cart_items)
    shipping_charges = 150.0 if subtotal < 1000 else 0.0
    total = subtotal + shipping_charges
    tracking_id = generate_tracking_id()
    
    # ✅ Create order for each cart item
    for item in cart_items:
        order = Order(
            username=session.get("user_id"),
            product_name=item.product_name,
            unit_price=item.unit_price,
            quantity=item.quantity,
            subtotal=item.unit_price * item.quantity,
            shipping_address=shipping_address,
            shipping_charges=shipping_charges,  
            total_amount=(item.unit_price * item.quantity) + shipping_charges,  # ✅ Fixed
            payment_method=payment_method,
            tracking_id=tracking_id
        )
        db.session.add(order)
    
    # Clear cart
    for item in cart_items:
        db.session.delete(item)
    
    db.session.commit()
    
    return redirect(url_for("order_confirmation", tracking_id=tracking_id))


@app.route("/order_confirmation/<tracking_id>")
@login_required
def order_confirmation(tracking_id):
    orders = Order.query.filter_by(tracking_id=tracking_id).all()
    if not orders or orders[0].username != session.get("user_id"):
        return redirect(url_for("products"))
    
    return render_template("order_confirm.html", orders=orders, tracking_id=tracking_id)


@app.route("/track_order/<tracking_id>")
@login_required
def track_order(tracking_id):
    orders = Order.query.filter_by(tracking_id=tracking_id).all()
    if not orders or orders[0].username != session.get("user_id"):
        return redirect(url_for("products"))
    
    return render_template("track_order.html", orders=orders, tracking_id=tracking_id)


@app.route("/my_orders")
@login_required
def my_orders():
    orders = Order.query.filter_by(username=session.get("user_id")).order_by(Order.order_date.desc()).all()
    return render_template("my_orders.html", orders=orders)


@app.route("/update_order_status/<int:order_id>")
@login_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    if order.username == session.get("user_id"):
        if order.order_status == "Pending":
            order.order_status = "Processing"
        elif order.order_status == "Processing":
            order.order_status = "Shipped"
        elif order.order_status == "Shipped":
            order.order_status = "Delivered"
            order.delivery_date = datetime.utcnow()
        db.session.commit()
    return redirect(url_for("track_order", tracking_id=order.tracking_id))


@app.route("/review_order/<int:order_id>", methods=["GET", "POST"])
@login_required
def review_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.username != session.get("user_id"):
        return redirect(url_for("products"))
    
    if request.method == "POST":
        rating = request.form.get("rating")
        comment = request.form.get("comment")
        
        if rating:
            existing_review = Review.query.filter_by(order_id=order_id).first()
            if existing_review:
                existing_review.rating = int(rating)
                existing_review.comment = comment
            else:
                review = Review(
                    order_id=order_id,
                    username=session.get("user_id"),
                    rating=int(rating),
                    comment=comment
                )
                db.session.add(review)
            db.session.commit()
            return redirect(url_for("my_orders"))
    
    existing_review = Review.query.filter_by(order_id=order_id).first()
    return render_template("review_order.html", order=order, existing_review=existing_review)


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username and password:
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session["user_id"] = user.username
                return redirect(url_for("products"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            return render_template("register.html", error="Username and password required")
        existing = User.query.filter_by(username=username).first()
        if existing:
            return render_template("register.html", error="User already exists")
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.username
        return redirect(url_for("products"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    # Make sure 'site.db' is deleted before running this script!
    with app.app_context():
        db.create_all()
    app.run(debug=True)
