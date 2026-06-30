import os
import json
import smtplib
import base64
import re
from functools import wraps
from datetime import datetime
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from sqlalchemy import inspect, text
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IS_VERCEL = bool(os.environ.get("VERCEL"))
UPLOAD_FOLDER = os.path.join("/tmp", "am_gems_uploads") if IS_VERCEL else os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
SHOP_CATEGORIES = [
    "Precious/Semi-Precious Gemstones",
    "Rashi Gemstones",
    "Bracelets",
    "Rings",
    "Pendants",
    "Other Jewellery",
]

app = Flask(__name__, template_folder="templates", static_folder="static")
if os.environ.get("RENDER") or IS_VERCEL:
    db_path = os.environ.get("AM_GEMS_DB_PATH", "/tmp/am_gems.db")
else:
    db_path = os.environ.get("AM_GEMS_DB_PATH", os.path.join(BASE_DIR, "am_gems.db"))
app.config["SECRET_KEY"] = os.environ.get("AM_GEMS_SECRET_KEY", "am-gems-secret-2026")
database_url = os.environ.get("AM_GEMS_DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": int(os.environ.get("AM_GEMS_DB_POOL_RECYCLE", "300")),
}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["UPLOAD_ADMIN_CODE"] = os.environ.get("AM_GEMS_UPLOAD_CODE", "amgems2026")
app.config["SITE_URL"] = (
    os.environ.get("AM_GEMS_SITE_URL")
    or os.environ.get("RENDER_EXTERNAL_URL")
    or (f"https://{os.environ.get('VERCEL_URL')}" if os.environ.get("VERCEL_URL") else None)
    or "http://127.0.0.1:5050"
)
app.config["UPI_ID"] = os.environ.get("AM_GEMS_UPI_ID", "8310614641@axl")
app.config["PAYMENT_NUMBER"] = os.environ.get("AM_GEMS_PAYMENT_NUMBER", "8310614641")
app.config["WHATSAPP_NUMBER"] = os.environ.get("AM_GEMS_WHATSAPP_NUMBER", "+918310614641")
app.config["MAIL_SERVER"] = os.environ.get("AM_GEMS_MAIL_SERVER", "")
app.config["MAIL_PORT"] = int(os.environ.get("AM_GEMS_MAIL_PORT", "587"))
app.config["MAIL_USERNAME"] = os.environ.get("AM_GEMS_MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"] = os.environ.get("AM_GEMS_MAIL_PASSWORD", "")
app.config["MAIL_FROM"] = os.environ.get("AM_GEMS_MAIL_FROM", "")
app.config["ADMIN_EMAIL"] = os.environ.get("AM_GEMS_ADMIN_EMAIL", "")
app.config["RAZORPAY_KEY_ID"] = os.environ.get("AM_GEMS_RAZORPAY_KEY_ID", "")
app.config["RAZORPAY_KEY_SECRET"] = os.environ.get("AM_GEMS_RAZORPAY_KEY_SECRET", "")
app.config["PHONEPE_CHECKOUT_URL"] = os.environ.get("AM_GEMS_PHONEPE_CHECKOUT_URL", "")


db = SQLAlchemy(app)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)
    image_data = db.Column(db.Text, nullable=True)
    image_mime = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Inquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Testimonial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(80), nullable=False)
    quote = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=5)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(30), nullable=False)
    address = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="initiated")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    product = db.relationship("Product", backref=db.backref("orders", lazy=True))


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def image_data_uri(product: Product) -> str:
    if product.image_data and product.image_mime:
        return f"data:{product.image_mime};base64,{product.image_data}"
    if product.image_filename:
        return url_for("static", filename="uploads/" + product.image_filename)
    return ""


def format_inr(value) -> str:
    amount = Decimal(value)
    return f"{amount:,.2f}"


def build_whatsapp_link(message: str) -> str:
    safe_message = quote(message)
    whatsapp_digits = re.sub(r"\D", "", app.config["WHATSAPP_NUMBER"])
    return f"https://wa.me/{whatsapp_digits}?text={safe_message}"


def send_email_notification(subject: str, body: str, recipient: str) -> bool:
    mail_server = app.config["MAIL_SERVER"]
    mail_username = app.config["MAIL_USERNAME"]
    mail_password = app.config["MAIL_PASSWORD"]
    mail_from = app.config["MAIL_FROM"] or mail_username

    if not (mail_server and mail_username and mail_password and mail_from and recipient):
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = recipient
    msg.set_content(body)

    with smtplib.SMTP(mail_server, app.config["MAIL_PORT"]) as server:
        server.starttls()
        server.login(mail_username, mail_password)
        server.send_message(msg)
    return True


def create_razorpay_payment_link(product: Product, order: Order):
    key_id = app.config["RAZORPAY_KEY_ID"]
    key_secret = app.config["RAZORPAY_KEY_SECRET"]
    if not key_id or not key_secret:
        return None, "Razorpay is not configured."

    basic_auth = base64.b64encode(f"{key_id}:{key_secret}".encode("utf-8")).decode("utf-8")
    callback_url = url_for("payment_status", _external=True)
    payload = {
        "amount": int(Decimal(product.price) * 100),
        "currency": "INR",
        "description": f"{product.name} - A.M Gems and Jewellery",
        "customer": {
            "name": order.customer_name,
            "email": order.customer_email,
            "contact": order.customer_phone,
        },
        "notify": {"sms": True, "email": True},
        "reminder_enable": True,
        "callback_url": callback_url,
        "callback_method": "get",
    }

    req = Request(
        "https://api.razorpay.com/v1/payment_links",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {basic_auth}",
        },
    )

    try:
        with urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
            short_url = data.get("short_url")
            if short_url:
                return short_url, None
            return None, "Razorpay response did not include a payment URL."
    except HTTPError as exc:
        return None, f"Razorpay request failed: HTTP {exc.code}."
    except URLError:
        return None, "Razorpay service is currently unreachable."


def admin_login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_authenticated"):
            flash("Please log in as admin to access this page.", "error")
            return redirect(url_for("admin_login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapped_view


@app.context_processor
def inject_global_data():
    whatsapp_digits = re.sub(r"\D", "", app.config["WHATSAPP_NUMBER"])
    order_count = Order.query.count()
    latest_order = Order.query.order_by(Order.created_at.desc()).first()
    return {
        "site_name": "A.M Gems and Jewellery",
        "site_url": app.config["SITE_URL"],
        "upi_id": app.config["UPI_ID"],
        "payment_number": app.config["PAYMENT_NUMBER"],
        "whatsapp_number": app.config["WHATSAPP_NUMBER"],
        "whatsapp_number_digits": whatsapp_digits,
        "whatsapp_link": build_whatsapp_link("Hello A.M Gems and Jewellery, I want to enquire about your jewellery collection."),
        "razorpay_enabled": bool(app.config["RAZORPAY_KEY_ID"] and app.config["RAZORPAY_KEY_SECRET"]),
        "phonepe_checkout_url": app.config["PHONEPE_CHECKOUT_URL"],
        "admin_logged_in": bool(session.get("admin_authenticated")),
        "admin_order_count": order_count,
        "latest_order": latest_order,
        "shop_categories": SHOP_CATEGORIES,
        "year": datetime.utcnow().year,
        "image_data_uri": image_data_uri,
    }


@app.template_filter("inr")
def inr_filter(value):
    return format_inr(value)


@app.route("/")
def home():
    featured_products = Product.query.order_by(Product.created_at.desc()).limit(6).all()
    featured_testimonials = Testimonial.query.order_by(Testimonial.created_at.desc()).limit(3).all()
    return render_template(
        "home.html",
        title="Luxury Gemstone Jewellery",
        meta_description="A.M Gems and Jewellery offers premium gemstone bracelets, rings, and fine jewellery with secure enquiries and direct GPay / PhonePe checkout.",
        products=featured_products,
        testimonials=featured_testimonials,
    )


@app.route("/shop")
def shop():
    category = request.args.get("category", "All")
    search_query = request.args.get("q", "").strip()
    query = Product.query
    if category in SHOP_CATEGORIES:
        query = query.filter(Product.category == category)

    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            (Product.name.ilike(search_term))
            | (Product.category.ilike(search_term))
            | (Product.description.ilike(search_term))
        )

    products = query.order_by(Product.created_at.desc()).all()
    return render_template(
        "shop.html",
        title="Shop Gemstone Jewellery",
        meta_description="Shop handcrafted gemstone bracelets, rings, and jewellery from A.M Gems and Jewellery.",
        products=products,
        categories=SHOP_CATEGORIES,
        selected_category=category,
        search_query=search_query,
    )


@app.route("/order/<int:product_id>", methods=["GET", "POST"])
def order_checkout(product_id: int):
    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        customer_email = request.form.get("customer_email", "").strip()
        customer_phone = request.form.get("customer_phone", "").strip()
        house_number = request.form.get("house_number", "").strip()
        street = request.form.get("street", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        pincode = request.form.get("pincode", "").strip()
        landmark = request.form.get("landmark", "").strip()
        payment_method = request.form.get("payment_method", "gpay").strip()

        if not customer_name or not customer_email or not customer_phone or not house_number or not street or not city or not state or not pincode:
            flash("Please fill in all checkout details.", "error")
            return redirect(url_for("order_checkout", product_id=product_id))

        address_parts = [
            f"House/Flat: {house_number}",
            f"Street/Area: {street}",
            f"City: {city}",
            f"State: {state}",
            f"Pincode: {pincode}",
        ]
        if landmark:
            address_parts.append(f"Landmark: {landmark}")
        address = ", ".join(address_parts)

        order = Order(
            product_id=product.id,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            address=address,
            amount=Decimal(product.price),
            payment_method=payment_method,
            status="initiated",
        )
        db.session.add(order)
        db.session.commit()

        mail_subject = f"Order Initiated - {product.name}"
        customer_mail_body = (
            f"Dear {customer_name},\n\n"
            f"Thank you for choosing A.M Gems and Jewellery.\n"
            f"Order ID: {order.id}\n"
            f"Product: {product.name}\n"
            f"Amount: INR {format_inr(order.amount)}\n"
            f"Payment Method: {payment_method.upper()}\n\n"
            "Please complete your payment and contact us on WhatsApp for any support."
        )
        admin_mail_body = (
            f"New order initiated.\n\n"
            f"Order ID: {order.id}\n"
            f"Customer: {customer_name}\n"
            f"Email: {customer_email}\n"
            f"Phone: {customer_phone}\n"
            f"Address: {address}\n"
            f"Product: {product.name}\n"
            f"Amount: INR {format_inr(order.amount)}\n"
            f"Method: {payment_method.upper()}"
        )

        try:
            send_email_notification(mail_subject, customer_mail_body, customer_email)
            send_email_notification(mail_subject, admin_mail_body, app.config["ADMIN_EMAIL"])
        except Exception:
            flash("Order saved. Email notification is not configured yet.", "error")

        if payment_method == "razorpay":
            return redirect(url_for("pay_razorpay", product_id=product.id, order_id=order.id))

        return redirect(url_for("pay", product_id=product.id, order_id=order.id))

    return render_template(
        "order_checkout.html",
        title=f"Checkout - {product.name}",
        meta_description="Complete your checkout details for secure jewellery purchase.",
        product=product,
    )


@app.route("/about")
def about():
    return render_template(
        "about.html",
        title="About A.M Gems and Jewellery",
        meta_description="Learn about A.M Gems and Jewellery, our gemstone sourcing philosophy, craftsmanship, and customer-first service.",
    )


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            flash("Please fill in name, email, and your enquiry message.", "error")
            return redirect(url_for("contact"))

        inquiry = Inquiry(name=name, email=email, phone=phone, message=message)
        db.session.add(inquiry)
        db.session.commit()
        admin_subject = "New Enquiry - A.M Gems and Jewellery"
        admin_body = (
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Phone: {phone}\n"
            f"Message:\n{message}\n"
        )
        customer_subject = "We received your enquiry - A.M Gems and Jewellery"
        customer_body = (
            f"Hello {name},\n\n"
            "Thank you for contacting A.M Gems and Jewellery. Our team will reach out shortly.\n"
            "You can also connect instantly on WhatsApp for faster assistance."
        )
        try:
            send_email_notification(admin_subject, admin_body, app.config["ADMIN_EMAIL"])
            send_email_notification(customer_subject, customer_body, email)
        except Exception:
            flash("Enquiry saved. Email notification is not configured yet.", "error")
        flash("Thank you. Your enquiry has been sent to A.M Gems and Jewellery.", "success")
        return redirect(url_for("contact"))

    return render_template(
        "contact.html",
        title="Contact A.M Gems and Jewellery",
        meta_description="Contact A.M Gems and Jewellery for gemstone jewellery consultations, custom orders, and purchase enquiries.",
    )


@app.route("/testimonials")
def testimonials():
    all_testimonials = Testimonial.query.order_by(Testimonial.created_at.desc()).all()
    return render_template(
        "testimonials.html",
        title="Customer Testimonials",
        meta_description="Read verified customer testimonials for gemstone bracelets, rings, and jewellery from A.M Gems and Jewellery.",
        testimonials=all_testimonials,
    )


@app.route("/admin/upload", methods=["GET", "POST"])
@admin_login_required
def admin_upload():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        price_raw = request.form.get("price", "").strip()
        image = request.files.get("image")

        if not name or not category or not description or not price_raw:
            flash("Please fill in all product fields.", "error")
            return redirect(url_for("admin_upload"))

        try:
            price = Decimal(price_raw)
            if price <= 0:
                raise InvalidOperation
        except InvalidOperation:
            flash("Price must be a valid positive amount.", "error")
            return redirect(url_for("admin_upload"))

        filename = None
        image_data = None
        image_mime = None
        if image and image.filename:
            if not allowed_file(image.filename):
                flash("Only PNG, JPG, JPEG, and WEBP images are allowed.", "error")
                return redirect(url_for("admin_upload"))

            safe_name = secure_filename(image.filename)
            filename = f"{int(datetime.utcnow().timestamp())}_{safe_name}"
            image_bytes = image.read()
            image_data = base64.b64encode(image_bytes).decode("utf-8")
            image_mime = image.mimetype or "image/jpeg"

        product = Product(
            name=name,
            category=category,
            description=description,
            price=price,
            image_filename=filename,
            image_data=image_data,
            image_mime=image_mime,
        )
        db.session.add(product)
        db.session.commit()

        flash("Product uploaded successfully.", "success")
        return redirect(url_for("shop"))

    return render_template(
        "admin_upload.html",
        title="Upload Product",
        meta_description="Secure product upload panel for A.M Gems and Jewellery inventory management.",
        categories=SHOP_CATEGORIES,
    )


@app.route("/admin/products")
@admin_login_required
def admin_products():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template(
        "admin_products.html",
        title="Manage Products",
        meta_description="Edit or delete products from A.M Gems and Jewellery inventory.",
        products=products,
        categories=SHOP_CATEGORIES,
    )


@app.route("/admin/orders")
@admin_login_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template(
        "admin_orders.html",
        title="Orders",
        meta_description="View customer orders, addresses, and payment status for A.M Gems and Jewellery.",
        orders=orders,
    )


@app.route("/admin/product/<int:product_id>/update", methods=["POST"])
@admin_login_required
def admin_product_update(product_id: int):
    product = Product.query.get_or_404(product_id)
    product.name = request.form.get("name", product.name).strip()
    product.category = request.form.get("category", product.category).strip()
    product.description = request.form.get("description", product.description).strip()
    price_raw = request.form.get("price", "").strip()
    image = request.files.get("image")

    try:
        price = Decimal(price_raw)
        if price <= 0:
            raise InvalidOperation
        product.price = price
    except InvalidOperation:
        flash("Invalid price for update.", "error")
        return redirect(url_for("admin_products"))

    if image and image.filename:
        if not allowed_file(image.filename):
            flash("Only PNG, JPG, JPEG, and WEBP images are allowed.", "error")
            return redirect(url_for("admin_products"))

        safe_name = secure_filename(image.filename)
        filename = f"{int(datetime.utcnow().timestamp())}_{safe_name}"
        image_bytes = image.read()
        product.image_data = base64.b64encode(image_bytes).decode("utf-8")
        product.image_mime = image.mimetype or "image/jpeg"
        product.image_filename = filename

    db.session.commit()
    flash("Product updated successfully.", "success")
    return redirect(url_for("admin_products"))


@app.route("/admin/product/<int:product_id>/delete", methods=["POST"])
@admin_login_required
def admin_product_delete(product_id: int):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted.", "success")
    return redirect(url_for("admin_products"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        admin_code = request.form.get("admin_code", "")
        next_url = request.form.get("next", "").strip()

        if admin_code == app.config["UPLOAD_ADMIN_CODE"]:
            session["admin_authenticated"] = True
            flash("Admin login successful.", "success")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("admin_products"))

        flash("Invalid admin credentials.", "error")
        return redirect(url_for("admin_login", next=next_url))

    if session.get("admin_authenticated"):
        return redirect(url_for("admin_products"))

    next_url = request.args.get("next", "")
    return render_template(
        "admin_login.html",
        title="Admin Login",
        meta_description="Admin session login for A.M Gems and Jewellery inventory panel.",
        next_url=next_url,
    )


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_authenticated", None)
    flash("Admin logged out.", "success")
    return redirect(url_for("admin_login"))


@app.route("/pay/<int:product_id>")
def pay(product_id: int):
    product = Product.query.get_or_404(product_id)
    order_id = request.args.get("order_id", "")
    amount = f"{Decimal(product.price):.2f}"
    transaction_note = quote(f"{product.name} - A.M Gems and Jewellery")
    payee_name = quote("A.M Gems and Jewellery")
    upi_id = app.config["UPI_ID"]
    upi_url = (
        f"upi://pay?pa={upi_id}&pn={payee_name}&tn={transaction_note}&am={amount}&cu=INR"
    )
    whatsapp_payment_help = build_whatsapp_link(
        f"Hi A.M Gems and Jewellery, I need payment help for {product.name}."
    )

    phonepe_redirect = ""
    if app.config["PHONEPE_CHECKOUT_URL"]:
        phonepe_redirect = app.config["PHONEPE_CHECKOUT_URL"]
        query = urlencode({"amount": amount, "product": product.name})
        connector = "&" if "?" in phonepe_redirect else "?"
        phonepe_redirect = f"{phonepe_redirect}{connector}{query}"

    return render_template(
        "payment.html",
        title=f"Pay for {product.name}",
        meta_description="Direct GPay / PhonePe payment page for A.M Gems and Jewellery orders.",
        product=product,
        upi_url=upi_url,
        order_id=order_id,
        phonepe_redirect=phonepe_redirect,
        whatsapp_payment_help=whatsapp_payment_help,
    )


@app.route("/pay/razorpay/<int:product_id>")
def pay_razorpay(product_id: int):
    product = Product.query.get_or_404(product_id)
    order_id = request.args.get("order_id", type=int)
    if not order_id:
        flash("Please complete checkout details first.", "error")
        return redirect(url_for("order_checkout", product_id=product.id))

    order = Order.query.get_or_404(order_id)
    razorpay_url, error = create_razorpay_payment_link(product, order)
    if error:
        flash(error, "error")
        return redirect(url_for("pay", product_id=product.id, order_id=order.id))

    return redirect(razorpay_url)


@app.route("/payment-status")
def payment_status():
    order_id = request.args.get("order_id", type=int)
    payment_id = request.args.get("razorpay_payment_id", "")

    if order_id:
        order = Order.query.get(order_id)
        if order:
            order.status = "paid" if payment_id else "pending"
            db.session.commit()

    if payment_id:
        flash("Payment completed successfully.", "success")
    else:
        flash("Payment status received. Please contact us if assistance is needed.", "success")
    return redirect(url_for("shop"))


@app.route("/robots.txt")
def robots():
    return send_from_directory(app.static_folder, "robots.txt")


@app.route("/sitemap.xml")
def sitemap():
    pages = [
        url_for("home", _external=True),
        url_for("shop", _external=True),
        url_for("about", _external=True),
        url_for("contact", _external=True),
        url_for("testimonials", _external=True),
    ]
    return render_template("sitemap.xml", pages=pages), 200, {"Content-Type": "application/xml"}


def seed_defaults():
    if Testimonial.query.count() == 0:
        default_testimonials = [
            Testimonial(
                name="Priya Nair",
                city="Bangalore",
                quote="The ruby bracelet is stunning and arrived beautifully packaged. The quality feels premium.",
                rating=5,
            ),
            Testimonial(
                name="Rohan Mehta",
                city="Indiranagar",
                quote="Excellent ring collection and very responsive support team for sizing guidance.",
                rating=5,
            ),
            Testimonial(
                name="Ananya Rao",
                city="Jayanagar",
                quote="Authentic gemstone finish and elegant craftsmanship. Highly recommended.",
                rating=5,
            ),
        ]
        db.session.add_all(default_testimonials)
        db.session.commit()


def ensure_product_image_columns():
    inspector = inspect(db.engine)
    if not inspector.has_table("product"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("product")}
    statements = []
    if "image_data" not in existing_columns:
        statements.append("ALTER TABLE product ADD COLUMN image_data TEXT")
    if "image_mime" not in existing_columns:
        statements.append("ALTER TABLE product ADD COLUMN image_mime VARCHAR(80)")

    for statement in statements:
        db.session.execute(text(statement))
    if statements:
        db.session.commit()


with app.app_context():
    try:
        db.create_all()
        ensure_product_image_columns()
        seed_defaults()
    except Exception:
        app.logger.exception("Database initialization failed during startup.")


if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5050")),
    )
