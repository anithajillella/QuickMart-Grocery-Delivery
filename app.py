import os
import time

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    render_template_string,
    request,
    session,
)

from werkzeug.security import check_password_hash, generate_password_hash

from database import create_database, get_db_connection


# =========================================
# FLASK APP
# =========================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "QUICKMART_SECRET_KEY",
    "quickmart-secret-key-2026",
)


# =========================================
# DATABASE
# =========================================

create_database()


# =========================================
# HELPERS
# =========================================

def is_customer_logged_in():
    return "user_id" in session


def is_admin_logged_in():
    return "admin_id" in session


def get_cart_from_request(data):
    cart = data.get("cart", []) if isinstance(data, dict) else []
    if not isinstance(cart, list) or not cart:
        return None
    return cart


def generate_order_number():
    return "QM" + str(int(time.time() * 1000))


def rebuild_cart_from_database(cart):
    """Use database product prices, not browser-supplied prices."""
    connection = get_db_connection()

    try:
        cleaned_cart = []
        subtotal = 0.0

        for item in cart:
            try:
                product_id = int(item.get("id"))
                quantity = int(item.get("quantity", 0))
            except (TypeError, ValueError):
                raise ValueError("Invalid product information")

            if quantity <= 0:
                raise ValueError("Invalid product quantity")

            product = connection.execute(
                """
                SELECT id, name, price, emoji
                FROM products
                WHERE id = ?
                """,
                (product_id,),
            ).fetchone()

            if product is None:
                raise ValueError(
                    f"Product with ID {product_id} was not found"
                )

            price = float(product["price"])
            subtotal += price * quantity

            cleaned_cart.append(
                {
                    "id": product["id"],
                    "name": product["name"],
                    "price": price,
                    "emoji": product["emoji"] or "",
                    "quantity": quantity,
                }
            )

        delivery_fee = 20.0
        total_amount = subtotal + delivery_fee

        return cleaned_cart, subtotal, delivery_fee, total_amount

    finally:
        connection.close()


def validate_delivery_fields(data):
    fields = {
        "Customer name": str(data.get("customer_name", "")).strip(),
        "Mobile number": str(data.get("mobile", "")).strip(),
        "House number": str(data.get("house", "")).strip(),
        "Street": str(data.get("street", "")).strip(),
        "City": str(data.get("city", "")).strip(),
        "Pincode": str(data.get("pincode", "")).strip(),
    }

    for field_name, value in fields.items():
        if not value:
            return None, field_name + " is required"

    return fields, None


# =========================================
# CUSTOMER PAGES
# =========================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/products")
def products_page():
    return render_template("products.html")


@app.route("/cart")
def cart_page():
    return render_template("cart.html")


@app.route("/checkout")
def checkout_page():
    if not is_customer_logged_in():
        return render_template("login.html")
    return render_template("checkout.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/my-orders")
def my_orders_page():
    if not is_customer_logged_in():
        return render_template("login.html")
    return render_template("my_orders.html")


@app.route("/order-tracking/<order_number>")
def order_tracking_page(order_number):
    if not is_customer_logged_in():
        return render_template("login.html")

    return render_template(
        "order_tracking.html",
        order_number=order_number,
    )


@app.route("/order-success")
def order_success():
    order_number = request.args.get("order", "")
    return render_template(
        "order_success.html",
        order_number=order_number,
    )


# =========================================
# CUSTOMER AUTH API
# =========================================

@app.route("/api/login", methods=["POST"])
def login_user():
    data = request.get_json(silent=True)

    if not data:
        return jsonify(
            {
                "success": False,
                "message": "No login data received",
            }
        ), 400

    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email:
        return jsonify(
            {"success": False, "message": "Email is required"}
        ), 400

    if not password:
        return jsonify(
            {"success": False, "message": "Password is required"}
        ), 400

    connection = get_db_connection()

    try:
        user = connection.execute(
            """
            SELECT id, name, email, password
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()
    finally:
        connection.close()

    if user is None or not check_password_hash(user["password"], password):
        return jsonify(
            {
                "success": False,
                "message": "Invalid email or password",
            }
        ), 401

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]

    return jsonify(
        {
            "success": True,
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
            },
        }
    )


@app.route("/api/register", methods=["POST"])
def register_user():
    data = request.get_json(silent=True)

    if not data:
        return jsonify(
            {
                "success": False,
                "message": "No registration data received",
            }
        ), 400

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not name:
        return jsonify(
            {"success": False, "message": "Name is required"}
        ), 400

    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return jsonify(
            {
                "success": False,
                "message": "Please enter a valid email address",
            }
        ), 400

    if len(password) < 6:
        return jsonify(
            {
                "success": False,
                "message": "Password must be at least 6 characters",
            }
        ), 400

    connection = get_db_connection()

    try:
        existing_user = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if existing_user:
            return jsonify(
                {
                    "success": False,
                    "message": "Email is already registered",
                }
            ), 400

        connection.execute(
            """
            INSERT INTO users (name, email, password)
            VALUES (?, ?, ?)
            """,
            (
                name,
                email,
                generate_password_hash(password),
            ),
        )
        connection.commit()

        return jsonify(
            {
                "success": True,
                "message": "Registration successful",
            }
        )

    except Exception as error:
        connection.rollback()
        print("Registration error:", repr(error))
        return jsonify(
            {
                "success": False,
                "message": "Registration failed",
            }
        ), 500

    finally:
        connection.close()


@app.route("/api/logout", methods=["POST"])
def logout_user():
    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("user_email", None)

    return jsonify(
        {"success": True, "message": "Logout successful"}
    )


@app.route("/api/current-user")
def current_user():
    if not is_customer_logged_in():
        return jsonify({"logged_in": False})

    return jsonify(
        {
            "logged_in": True,
            "user": {
                "id": session["user_id"],
                "name": session["user_name"],
                "email": session["user_email"],
            },
        }
    )


# =========================================
# ADMIN AUTH
# =========================================

@app.route("/admin/login")
def admin_login_page():
    return render_template("admin_login.html")


@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True)

    if not data:
        return jsonify(
            {
                "success": False,
                "message": "No admin login data received",
            }
        ), 400

    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email:
        return jsonify(
            {"success": False, "message": "Admin email is required"}
        ), 400

    if not password:
        return jsonify(
            {"success": False, "message": "Admin password is required"}
        ), 400

    connection = get_db_connection()

    try:
        admin = connection.execute(
            """
            SELECT id, name, email, password
            FROM admins
            WHERE email = ?
            """,
            (email,),
        ).fetchone()
    finally:
        connection.close()

    if admin is None or not check_password_hash(admin["password"], password):
        return jsonify(
            {
                "success": False,
                "message": "Invalid admin email or password",
            }
        ), 401

    session["admin_id"] = admin["id"]
    session["admin_name"] = admin["name"]
    session["admin_email"] = admin["email"]

    return jsonify(
        {
            "success": True,
            "message": "Admin login successful",
            "admin": {
                "id": admin["id"],
                "name": admin["name"],
                "email": admin["email"],
            },
        }
    )


@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_id", None)
    session.pop("admin_name", None)
    session.pop("admin_email", None)

    return jsonify(
        {"success": True, "message": "Admin logout successful"}
    )


@app.route("/api/admin/current")
def current_admin():
    if not is_admin_logged_in():
        return jsonify({"logged_in": False})

    return jsonify(
        {
            "logged_in": True,
            "admin": {
                "id": session["admin_id"],
                "name": session["admin_name"],
                "email": session["admin_email"],
            },
        }
    )


# =========================================
# ADMIN DASHBOARD
# =========================================

ADMIN_DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuickMart - Admin Dashboard</title>
    <style>
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f5f7fb;
            color: #222;
        }
        .header {
            background: #111827;
            color: white;
            padding: 18px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
        }
        .header h1 { margin: 0; font-size: 24px; }
        .header-right { display: flex; align-items: center; gap: 12px; }
        button {
            border: none;
            padding: 10px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
        }
        button:disabled { opacity: 0.6; cursor: not-allowed; }
        .logout-btn { background: #dc2626; color: white; }
        .add-btn, .save-btn { background: #16a34a; color: white; }
        .edit-btn { background: #2563eb; color: white; margin-right: 5px; }
        .delete-btn { background: #dc2626; color: white; }
        .cancel-btn { background: #6b7280; color: white; }
        .refresh-btn { background: #374151; color: white; margin-left: 8px; }
        .update-order-btn { background: #7c3aed; color: white; margin-top: 8px; }
        .container { max-width: 1250px; margin: 30px auto; padding: 0 20px; }
        .welcome, .section, .form-box, .card {
            background: white;
            border-radius: 10px;
            padding: 22px;
            box-shadow: 0 2px 10px rgba(0,0,0,.06);
        }
        .welcome, .section { margin-bottom: 25px; }
        .welcome h2, .section h2 { margin-top: 0; }
        .stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 18px;
            margin-bottom: 25px;
        }
        .card-title { color: #6b7280; font-size: 14px; margin-bottom: 10px; }
        .card-value { font-size: 30px; font-weight: bold; }
        .section-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 15px;
        }
        .form-box { display: none; margin-bottom: 20px; border: 1px solid #e5e7eb; }
        .form-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        .form-group { display: flex; flex-direction: column; gap: 6px; }
        .form-group label { font-weight: bold; font-size: 14px; }
        .form-group input {
            padding: 11px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 15px;
        }
        .form-actions { margin-top: 18px; }
        table { width: 100%; border-collapse: collapse; min-width: 900px; }
        th, td {
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
            text-align: left;
            vertical-align: top;
        }
        th { background: #f9fafb; }
        .empty { padding: 25px 0; color: #6b7280; text-align: center; }
        .message { margin-top: 12px; padding: 10px; border-radius: 6px; display: none; }
        .message.success { display: block; background: #dcfce7; color: #166534; }
        .message.error { display: block; background: #fee2e2; color: #991b1b; }
        .status { font-weight: bold; }
        .status-select {
            padding: 9px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            min-width: 170px;
        }
        .order-details { font-size: 13px; color: #6b7280; line-height: 1.5; margin-top: 5px; }
        .payment-paid { color: #166534; font-weight: bold; }
        .payment-pending { color: #92400e; font-weight: bold; }
        @media (max-width: 850px) {
            .stats { grid-template-columns: repeat(2, 1fr); }
            .form-grid { grid-template-columns: 1fr; }
        }
        @media (max-width: 500px) {
            .stats { grid-template-columns: 1fr; }
            .header { padding: 16px; }
            .container { padding: 0 12px; }
        }
    </style>
</head>
<body>
<header class="header">
    <h1>🛒 QuickMart Admin Dashboard</h1>
    <div class="header-right">
        <span>Welcome, {{ admin_name }}</span>
        <button class="logout-btn" onclick="logoutAdmin()">Logout</button>
    </div>
</header>

<main class="container">
    <section class="welcome">
        <h2>📊 Dashboard Overview</h2>
        <p>Manage QuickMart products, orders, customers and payments.</p>
    </section>

    <section class="stats">
        <div class="card">
            <div class="card-title">Total Products</div>
            <div class="card-value" id="totalProducts">0</div>
        </div>
        <div class="card">
            <div class="card-title">Total Orders</div>
            <div class="card-value" id="totalOrders">0</div>
        </div>
        <div class="card">
            <div class="card-title">Total Customers</div>
            <div class="card-value" id="totalUsers">0</div>
        </div>
        <div class="card">
            <div class="card-title">Order Value</div>
            <div class="card-value" id="totalSales">₹0.00</div>
        </div>
    </section>

    <section class="section">
        <div class="section-top">
            <h2>🛒 Manage Products</h2>
            <div>
                <button class="add-btn" onclick="showAddProductForm()">➕ Add Product</button>
                <button class="refresh-btn" onclick="loadAdminProducts()">🔄 Refresh</button>
            </div>
        </div>

        <div class="form-box" id="productForm">
            <h3 id="formTitle">Add Product</h3>
            <input type="hidden" id="productId">
            <div class="form-grid">
                <div class="form-group">
                    <label>Product Name</label>
                    <input type="text" id="productName" placeholder="Example: Mango">
                </div>
                <div class="form-group">
                    <label>Category</label>
                    <input type="text" id="productCategory" placeholder="Example: Fruits">
                </div>
                <div class="form-group">
                    <label>Price</label>
                    <input type="number" id="productPrice" min="0.01" step="0.01" placeholder="Example: 100">
                </div>
                <div class="form-group">
                    <label>Emoji</label>
                    <input type="text" id="productEmoji" placeholder="Example: 🥭">
                </div>
            </div>
            <div class="form-actions">
                <button class="save-btn" onclick="saveProduct()">💾 Save Product</button>
                <button class="cancel-btn" onclick="cancelProductForm()">Cancel</button>
            </div>
        </div>

        <div class="message" id="productMessage"></div>
        <div id="productsContainer"><p class="empty">Loading products...</p></div>
    </section>

    <section class="section">
        <div class="section-top">
            <h2>📦 Manage Orders</h2>
            <button class="refresh-btn" onclick="loadAdminOrders()">🔄 Refresh Orders</button>
        </div>
        <div class="message" id="orderMessage"></div>
        <div id="adminOrdersContainer"><p class="empty">Loading orders...</p></div>
    </section>

    <section class="section">
        <h2>📦 Recent Orders</h2>
        <div id="ordersContainer"><p class="empty">Loading orders...</p></div>
    </section>
</main>

<script>
let adminProducts = [];

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

async function loadDashboard() {
    try {
        const response = await fetch("/api/admin/dashboard");
        const result = await response.json();

        if (response.status === 401) {
            window.location.href = "/admin/login";
            return;
        }

        if (!response.ok || !result.success) {
            throw new Error(result.message || "Unable to load dashboard");
        }

        document.getElementById("totalProducts").textContent = result.stats.total_products;
        document.getElementById("totalOrders").textContent = result.stats.total_orders;
        document.getElementById("totalUsers").textContent = result.stats.total_users;
        document.getElementById("totalSales").textContent = "₹" + Number(result.stats.total_sales).toFixed(2);

        const orders = result.recent_orders || [];
        const container = document.getElementById("ordersContainer");

        if (orders.length === 0) {
            container.innerHTML = '<p class="empty">No orders available yet.</p>';
            return;
        }

        let table = `
            <table>
                <thead>
                    <tr>
                        <th>Order</th>
                        <th>Customer</th>
                        <th>Total</th>
                        <th>Payment</th>
                        <th>Payment Status</th>
                        <th>Order Status</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
        `;

        orders.forEach(function(order) {
            const paymentStatus = order.payment_status || "Pending";
            const paymentClass = paymentStatus === "Paid" ? "payment-paid" : "payment-pending";
            table += `
                <tr>
                    <td>${escapeHtml(order.order_number)}</td>
                    <td>${escapeHtml(order.customer_name)}</td>
                    <td>₹${Number(order.total_amount).toFixed(2)}</td>
                    <td>${escapeHtml(order.payment_method)}</td>
                    <td class="${paymentClass}">${escapeHtml(paymentStatus)}</td>
                    <td class="status">${escapeHtml(order.status)}</td>
                    <td>${escapeHtml(order.created_at)}</td>
                </tr>
            `;
        });

        table += `</tbody></table>`;
        container.innerHTML = table;

    } catch (error) {
        console.error("Dashboard Error:", error);
        document.getElementById("ordersContainer").innerHTML =
            '<p class="empty">' + escapeHtml(error.message || "Unable to load dashboard data.") + '</p>';
    }
}

async function loadAdminProducts() {
    const container = document.getElementById("productsContainer");
    container.innerHTML = '<p class="empty">Loading products...</p>';

    try {
        const response = await fetch("/api/admin/products");
        const result = await response.json();

        if (response.status === 401) {
            window.location.href = "/admin/login";
            return;
        }

        if (!response.ok || !result.success) {
            throw new Error(result.message || "Unable to load products");
        }

        adminProducts = result.products || [];

        if (adminProducts.length === 0) {
            container.innerHTML = '<p class="empty">No products available.</p>';
            return;
        }

        let table = `
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Product</th>
                        <th>Category</th>
                        <th>Price</th>
                        <th>Emoji</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
        `;

        adminProducts.forEach(function(product) {
            table += `
                <tr>
                    <td>${product.id}</td>
                    <td>${escapeHtml(product.name)}</td>
                    <td>${escapeHtml(product.category)}</td>
                    <td>₹${Number(product.price).toFixed(2)}</td>
                    <td>${escapeHtml(product.emoji || "")}</td>
                    <td>
                        <button class="edit-btn" onclick="editProduct(${product.id})">Edit</button>
                        <button class="delete-btn" onclick="deleteProduct(${product.id})">Delete</button>
                    </td>
                </tr>
            `;
        });

        table += `</tbody></table>`;
        container.innerHTML = table;

    } catch (error) {
        console.error("Products Error:", error);
        container.innerHTML =
            '<p class="empty">' + escapeHtml(error.message || "Unable to load products.") + '</p>';
    }
}

function showAddProductForm() {
    document.getElementById("productForm").style.display = "block";
    document.getElementById("formTitle").textContent = "Add Product";
    document.getElementById("productId").value = "";
    document.getElementById("productName").value = "";
    document.getElementById("productCategory").value = "";
    document.getElementById("productPrice").value = "";
    document.getElementById("productEmoji").value = "";
    clearProductMessage();
    document.getElementById("productName").focus();
}

function editProduct(productId) {
    const product = adminProducts.find(function(item) {
        return item.id === productId;
    });

    if (!product) {
        alert("Product information not found.");
        return;
    }

    document.getElementById("productForm").style.display = "block";
    document.getElementById("formTitle").textContent = "Edit Product";
    document.getElementById("productId").value = product.id;
    document.getElementById("productName").value = product.name;
    document.getElementById("productCategory").value = product.category;
    document.getElementById("productPrice").value = product.price;
    document.getElementById("productEmoji").value = product.emoji || "";
    clearProductMessage();
    document.getElementById("productName").focus();
}

async function saveProduct() {
    const id = document.getElementById("productId").value.trim();

    const product = {
        name: document.getElementById("productName").value.trim(),
        category: document.getElementById("productCategory").value.trim(),
        price: document.getElementById("productPrice").value,
        emoji: document.getElementById("productEmoji").value.trim(),
    };

    if (!product.name) {
        showProductMessage("Product name is required.", "error");
        return;
    }
    if (!product.category) {
        showProductMessage("Category is required.", "error");
        return;
    }
    if (product.price === "" || Number(product.price) <= 0) {
        showProductMessage("Price must be greater than 0.", "error");
        return;
    }

    const url = id ? "/api/admin/products/" + id : "/api/admin/products";
    const method = id ? "PUT" : "POST";

    try {
        const response = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(product),
        });

        const result = await response.json();

        if (response.status === 401) {
            window.location.href = "/admin/login";
            return;
        }

        if (!response.ok || !result.success) {
            showProductMessage(result.message || "Unable to save product.", "error");
            return;
        }

        cancelProductForm();
        await loadAdminProducts();
        await loadDashboard();
        showProductMessage(result.message, "success");

    } catch (error) {
        console.error("Save Product Error:", error);
        showProductMessage(error.message || "Unable to save product.", "error");
    }
}

async function deleteProduct(productId) {
    const product = adminProducts.find(function(item) {
        return item.id === productId;
    });

    const productName = product ? product.name : "this product";

    if (!confirm("Are you sure you want to delete " + productName + "?")) {
        return;
    }

    try {
        const response = await fetch("/api/admin/products/" + productId, {
            method: "DELETE",
        });

        const result = await response.json();

        if (response.status === 401) {
            window.location.href = "/admin/login";
            return;
        }

        if (!response.ok || !result.success) {
            showProductMessage(result.message || "Unable to delete product.", "error");
            return;
        }

        await loadAdminProducts();
        await loadDashboard();
        showProductMessage(result.message, "success");

    } catch (error) {
        console.error("Delete Product Error:", error);
        showProductMessage(error.message || "Unable to delete product.", "error");
    }
}

function cancelProductForm() {
    document.getElementById("productForm").style.display = "none";
    document.getElementById("productId").value = "";
    document.getElementById("productName").value = "";
    document.getElementById("productCategory").value = "";
    document.getElementById("productPrice").value = "";
    document.getElementById("productEmoji").value = "";
    clearProductMessage();
}

function showProductMessage(message, type) {
    const element = document.getElementById("productMessage");
    element.textContent = message;
    element.className = "message " + type;
}

function clearProductMessage() {
    const element = document.getElementById("productMessage");
    element.textContent = "";
    element.className = "message";
}

async function loadAdminOrders() {
    const container = document.getElementById("adminOrdersContainer");
    container.innerHTML = '<p class="empty">Loading orders...</p>';

    try {
        const response = await fetch("/api/admin/orders");
        const result = await response.json();

        if (response.status === 401) {
            window.location.href = "/admin/login";
            return;
        }

        if (!response.ok || !result.success) {
            throw new Error(result.message || "Unable to load orders");
        }

        const orders = result.orders || [];

        if (orders.length === 0) {
            container.innerHTML = '<p class="empty">No customer orders available yet.</p>';
            return;
        }

        let table = `
            <table>
                <thead>
                    <tr>
                        <th>Order</th>
                        <th>Customer</th>
                        <th>Contact</th>
                        <th>Total</th>
                        <th>Payment</th>
                        <th>Payment Status</th>
                        <th>Order Status</th>
                        <th>Update</th>
                        <th>Date</th>
                    </tr>
                </thead>
                <tbody>
        `;

        orders.forEach(function(order) {
            const paymentStatus = order.payment_status || "Pending";
            const paymentClass = paymentStatus === "Paid" ? "payment-paid" : "payment-pending";

            table += `
                <tr>
                    <td><strong>${escapeHtml(order.order_number)}</strong></td>
                    <td>
                        ${escapeHtml(order.customer_name)}
                        <div class="order-details">
                            ${escapeHtml(order.house)},
                            ${escapeHtml(order.street)},
                            ${escapeHtml(order.city)} -
                            ${escapeHtml(order.pincode)}
                        </div>
                    </td>
                    <td>${escapeHtml(order.mobile)}</td>
                    <td>₹${Number(order.total_amount).toFixed(2)}</td>
                    <td>${escapeHtml(order.payment_method)}</td>
                    <td class="${paymentClass}">${escapeHtml(paymentStatus)}</td>
                    <td class="status">${escapeHtml(order.status)}</td>
                    <td>
                        <select class="status-select" id="orderStatus-${order.id}">
                            ${buildStatusOptions(order.status)}
                        </select>
                        <br>
                        <button class="update-order-btn" onclick="updateOrderStatus(${order.id})">Update</button>
                    </td>
                    <td>${escapeHtml(order.created_at)}</td>
                </tr>
            `;
        });

        table += `</tbody></table>`;
        container.innerHTML = table;

    } catch (error) {
        console.error("Admin Orders Error:", error);
        container.innerHTML =
            '<p class="empty">' + escapeHtml(error.message || "Unable to load admin orders.") + '</p>';
    }
}

function buildStatusOptions(currentStatus) {
    const statuses = [
        "Order Placed",
        "Confirmed",
        "Preparing",
        "Out for Delivery",
        "Delivered",
    ];

    return statuses.map(function(status) {
        const selected = status === currentStatus ? "selected" : "";
        return `<option value="${escapeHtml(status)}" ${selected}>${escapeHtml(status)}</option>`;
    }).join("");
}

async function updateOrderStatus(orderId) {
    const select = document.getElementById("orderStatus-" + orderId);

    if (!select) {
        showOrderMessage("Order status control not found.", "error");
        return;
    }

    try {
        const response = await fetch("/api/admin/orders/" + orderId, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: select.value }),
        });

        const result = await response.json();

        if (response.status === 401) {
            window.location.href = "/admin/login";
            return;
        }

        if (!response.ok || !result.success) {
            showOrderMessage(result.message || "Unable to update order status.", "error");
            return;
        }

        showOrderMessage(
            "Order " + result.order_number + " updated to " + result.status + ".",
            "success"
        );

        await loadAdminOrders();
        await loadDashboard();

    } catch (error) {
        console.error("Update Order Status Error:", error);
        showOrderMessage(error.message || "Unable to update order status.", "error");
    }
}

function showOrderMessage(message, type) {
    const element = document.getElementById("orderMessage");
    element.textContent = message;
    element.className = "message " + type;
}

async function logoutAdmin() {
    try {
        const response = await fetch("/api/admin/logout", { method: "POST" });
        const result = await response.json();

        if (result.success) {
            window.location.href = "/admin/login";
            return;
        }

        alert(result.message || "Logout failed.");

    } catch (error) {
        console.error("Admin Logout Error:", error);
        alert("Unable to logout.");
    }
}

document.addEventListener("DOMContentLoaded", function() {
    loadDashboard();
    loadAdminProducts();
    loadAdminOrders();
});
</script>
</body>
</html>
"""


@app.route("/admin/dashboard")
def admin_dashboard():
    if not is_admin_logged_in():
        return redirect("/admin/login")

    return render_template_string(
        ADMIN_DASHBOARD_HTML,
        admin_name=session.get("admin_name", "Admin"),
    )


@app.route("/admin/logout")
def admin_logout_page():
    session.pop("admin_id", None)
    session.pop("admin_name", None)
    session.pop("admin_email", None)
    return redirect("/admin/login")


# =========================================
# ADMIN DASHBOARD API
# =========================================

@app.route("/api/admin/dashboard")
def admin_dashboard_data():
    if not is_admin_logged_in():
        return jsonify(
            {
                "success": False,
                "message": "Admin login required",
            }
        ), 401

    connection = get_db_connection()

    try:
        total_products = connection.execute(
            "SELECT COUNT(*) AS count FROM products"
        ).fetchone()["count"]

        total_orders = connection.execute(
            "SELECT COUNT(*) AS count FROM orders"
        ).fetchone()["count"]

        total_users = connection.execute(
            "SELECT COUNT(*) AS count FROM users"
        ).fetchone()["count"]

        total_sales = connection.execute(
            """
            SELECT COALESCE(SUM(total_amount), 0) AS total
            FROM orders
            """
        ).fetchone()["total"]

        recent_orders = connection.execute(
            """
            SELECT
                id,
                order_number,
                customer_name,
                total_amount,
                payment_method,
                payment_status,
                status,
                created_at
            FROM orders
            ORDER BY id DESC
            LIMIT 10
            """
        ).fetchall()

        return jsonify(
            {
                "success": True,
                "stats": {
                    "total_products": total_products,
                    "total_orders": total_orders,
                    "total_users": total_users,
                    "total_sales": float(total_sales or 0),
                },
                "recent_orders": [dict(order) for order in recent_orders],
            }
        )

    except Exception as error:
        print("Admin dashboard error:", repr(error))
        return jsonify(
            {
                "success": False,
                "message": "Unable to load admin dashboard",
            }
        ), 500

    finally:
        connection.close()


# =========================================
# ADMIN PRODUCT MANAGEMENT
# =========================================

@app.route("/api/admin/products")
def admin_get_products():
    if not is_admin_logged_in():
        return jsonify(
            {"success": False, "message": "Admin login required"}
        ), 401

    connection = get_db_connection()

    try:
        products = connection.execute(
            """
            SELECT id, name, category, price, emoji
            FROM products
            ORDER BY id
            """
        ).fetchall()

        return jsonify(
            {
                "success": True,
                "products": [dict(product) for product in products],
            }
        )

    except Exception as error:
        print("Admin get products error:", repr(error))
        return jsonify(
            {"success": False, "message": "Unable to load products"}
        ), 500

    finally:
        connection.close()


@app.route("/api/admin/products", methods=["POST"])
def admin_add_product():
    if not is_admin_logged_in():
        return jsonify(
            {"success": False, "message": "Admin login required"}
        ), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify(
            {"success": False, "message": "No product data received"}
        ), 400

    name = str(data.get("name", "")).strip()
    category = str(data.get("category", "")).strip()
    emoji = str(data.get("emoji", "")).strip()

    try:
        price = float(data.get("price", 0))
    except (TypeError, ValueError):
        return jsonify(
            {"success": False, "message": "Invalid price"}
        ), 400

    if not name:
        return jsonify(
            {"success": False, "message": "Product name is required"}
        ), 400

    if not category:
        return jsonify(
            {"success": False, "message": "Category is required"}
        ), 400

    if price <= 0:
        return jsonify(
            {"success": False, "message": "Price must be greater than 0"}
        ), 400

    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO products (name, category, price, emoji)
            VALUES (?, ?, ?, ?)
            """,
            (name, category, price, emoji),
        )
        connection.commit()

        return jsonify(
            {
                "success": True,
                "message": "Product added successfully",
                "product_id": cursor.lastrowid,
            }
        ), 201

    except Exception as error:
        connection.rollback()
        print("Admin add product error:", repr(error))
        return jsonify(
            {"success": False, "message": "Could not add product"}
        ), 500

    finally:
        connection.close()


@app.route("/api/admin/products/<int:product_id>", methods=["PUT"])
def admin_update_product(product_id):
    if not is_admin_logged_in():
        return jsonify(
            {"success": False, "message": "Admin login required"}
        ), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify(
            {"success": False, "message": "No product data received"}
        ), 400

    name = str(data.get("name", "")).strip()
    category = str(data.get("category", "")).strip()
    emoji = str(data.get("emoji", "")).strip()

    try:
        price = float(data.get("price", 0))
    except (TypeError, ValueError):
        return jsonify(
            {"success": False, "message": "Invalid price"}
        ), 400

    if not name:
        return jsonify(
            {"success": False, "message": "Product name is required"}
        ), 400

    if not category:
        return jsonify(
            {"success": False, "message": "Category is required"}
        ), 400

    if price <= 0:
        return jsonify(
            {"success": False, "message": "Price must be greater than 0"}
        ), 400

    connection = get_db_connection()

    try:
        existing_product = connection.execute(
            "SELECT id FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()

        if existing_product is None:
            return jsonify(
                {"success": False, "message": "Product not found"}
            ), 404

        connection.execute(
            """
            UPDATE products
            SET name = ?, category = ?, price = ?, emoji = ?
            WHERE id = ?
            """,
            (name, category, price, emoji, product_id),
        )
        connection.commit()

        return jsonify(
            {"success": True, "message": "Product updated successfully"}
        )

    except Exception as error:
        connection.rollback()
        print("Admin update product error:", repr(error))
        return jsonify(
            {"success": False, "message": "Could not update product"}
        ), 500

    finally:
        connection.close()


@app.route("/api/admin/products/<int:product_id>", methods=["DELETE"])
def admin_delete_product(product_id):
    if not is_admin_logged_in():
        return jsonify(
            {"success": False, "message": "Admin login required"}
        ), 401

    connection = get_db_connection()

    try:
        existing_product = connection.execute(
            "SELECT id FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()

        if existing_product is None:
            return jsonify(
                {"success": False, "message": "Product not found"}
            ), 404

        connection.execute(
            "DELETE FROM products WHERE id = ?",
            (product_id,),
        )
        connection.commit()

        return jsonify(
            {"success": True, "message": "Product deleted successfully"}
        )

    except Exception as error:
        connection.rollback()
        print("Admin delete product error:", repr(error))
        return jsonify(
            {"success": False, "message": "Could not delete product"}
        ), 500

    finally:
        connection.close()


# =========================================
# ADMIN ORDER MANAGEMENT
# =========================================

@app.route("/api/admin/orders")
def admin_get_orders():
    if not is_admin_logged_in():
        return jsonify(
            {"success": False, "message": "Admin login required"}
        ), 401

    connection = get_db_connection()

    try:
        orders = connection.execute(
            """
            SELECT
                id,
                order_number,
                customer_name,
                mobile,
                house,
                street,
                city,
                pincode,
                payment_method,
                payment_status,
                payment_id,
                razorpay_order_id,
                total_amount,
                status,
                created_at
            FROM orders
            ORDER BY id DESC
            """
        ).fetchall()

        return jsonify(
            {
                "success": True,
                "orders": [dict(order) for order in orders],
            }
        )

    except Exception as error:
        print("Admin get orders error:", repr(error))
        return jsonify(
            {"success": False, "message": "Unable to load orders"}
        ), 500

    finally:
        connection.close()


@app.route("/api/admin/orders/<int:order_id>", methods=["PUT"])
def admin_update_order(order_id):
    if not is_admin_logged_in():
        return jsonify(
            {"success": False, "message": "Admin login required"}
        ), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify(
            {"success": False, "message": "No order data received"}
        ), 400

    status = str(data.get("status", "")).strip()
    allowed_statuses = [
        "Order Placed",
        "Confirmed",
        "Preparing",
        "Out for Delivery",
        "Delivered",
    ]

    if status not in allowed_statuses:
        return jsonify(
            {"success": False, "message": "Invalid order status"}
        ), 400

    connection = get_db_connection()

    try:
        existing_order = connection.execute(
            "SELECT id, order_number FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()

        if existing_order is None:
            return jsonify(
                {"success": False, "message": "Order not found"}
            ), 404

        connection.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status, order_id),
        )
        connection.commit()

        return jsonify(
            {
                "success": True,
                "message": "Order status updated successfully",
                "order_id": order_id,
                "order_number": existing_order["order_number"],
                "status": status,
            }
        )

    except Exception as error:
        connection.rollback()
        print("Admin update order error:", repr(error))
        return jsonify(
            {
                "success": False,
                "message": "Could not update order status",
            }
        ), 500

    finally:
        connection.close()


# =========================================
# CUSTOMER PRODUCT APIs
# =========================================

@app.route("/api/products")
def get_products():
    connection = get_db_connection()
    try:
        products = connection.execute(
            "SELECT * FROM products ORDER BY id"
        ).fetchall()
        return jsonify([dict(product) for product in products])
    finally:
        connection.close()


@app.route("/api/products/search")
def search_products():
    search = request.args.get("q", "").strip()
    connection = get_db_connection()
    try:
        products = connection.execute(
            """
            SELECT * FROM products
            WHERE name LIKE ?
            ORDER BY id
            """,
            (f"%{search}%",),
        ).fetchall()
        return jsonify([dict(product) for product in products])
    finally:
        connection.close()


@app.route("/api/products/category/<category>")
def products_by_category(category):
    connection = get_db_connection()
    try:
        products = connection.execute(
            """
            SELECT * FROM products
            WHERE category = ?
            ORDER BY id
            """,
            (category,),
        ).fetchall()
        return jsonify([dict(product) for product in products])
    finally:
        connection.close()


@app.route("/api/products/<int:product_id>")
def get_product(product_id):
    connection = get_db_connection()
    try:
        product = connection.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
    finally:
        connection.close()

    if product is None:
        return jsonify(
            {"success": False, "message": "Product not found"}
        ), 404

    return jsonify(dict(product))


# =========================================
# COD ORDER API
# =========================================

@app.route("/api/orders", methods=["POST"])
def create_order():
    if not is_customer_logged_in():
        return jsonify(
            {
                "success": False,
                "message": "Please login before placing an order",
            }
        ), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify(
            {"success": False, "message": "No order data received"}
        ), 400

    fields, error_message = validate_delivery_fields(data)
    if error_message:
        return jsonify(
            {"success": False, "message": error_message}
        ), 400

    payment_method = str(data.get("payment_method", "")).strip()
    if payment_method == "COD":
        payment_method = "Cash on Delivery"

    if payment_method != "Cash on Delivery":
        return jsonify(
            {
                "success": False,
                "message": "Online payments must use the online payment option.",
            }
        ), 400

    cart = get_cart_from_request(data)
    if cart is None:
        return jsonify(
            {"success": False, "message": "Cart is empty"}
        ), 400

    try:
        cleaned_cart, subtotal, delivery_fee, total_amount = rebuild_cart_from_database(cart)
    except ValueError as error:
        return jsonify(
            {"success": False, "message": str(error)}
        ), 400

    order_number = generate_order_number()
    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO orders (
                user_id,
                order_number,
                customer_name,
                mobile,
                house,
                street,
                city,
                pincode,
                payment_method,
                payment_status,
                total_amount,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                order_number,
                fields["Customer name"],
                fields["Mobile number"],
                fields["House number"],
                fields["Street"],
                fields["City"],
                fields["Pincode"],
                "Cash on Delivery",
                "Pending",
                total_amount,
                "Order Placed",
            ),
        )

        order_id = cursor.lastrowid

        for item in cleaned_cart:
            connection.execute(
                """
                INSERT INTO order_items (
                    order_id,
                    product_id,
                    product_name,
                    price,
                    quantity
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    item["id"],
                    item["name"],
                    item["price"],
                    item["quantity"],
                ),
            )

        connection.commit()

        return jsonify(
            {
                "success": True,
                "message": "Order placed successfully",
                "order_id": order_id,
                "order_number": order_number,
                "subtotal": subtotal,
                "delivery_fee": delivery_fee,
                "total_amount": total_amount,
                "payment_method": "Cash on Delivery",
                "payment_status": "Pending",
            }
        )

    except Exception as error:
        connection.rollback()
        print("COD order error:", repr(error))
        return jsonify(
            {"success": False, "message": "Could not save order"}
        ), 500

    finally:
        connection.close()


# =========================================
# DEMO ONLINE PAYMENT
# =========================================

@app.route("/api/payment/demo", methods=["POST"])
def demo_online_payment():
    """Create a fully local demo-paid order without an external gateway."""
    if not is_customer_logged_in():
        return jsonify(
            {
                "success": False,
                "message": "Please login before making payment",
            }
        ), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify(
            {"success": False, "message": "No payment data received"}
        ), 400

    fields, error_message = validate_delivery_fields(data)
    if error_message:
        return jsonify(
            {"success": False, "message": error_message}
        ), 400

    cart = get_cart_from_request(data)
    if cart is None:
        return jsonify(
            {"success": False, "message": "Cart is empty"}
        ), 400

    try:
        cleaned_cart, subtotal, delivery_fee, total_amount = rebuild_cart_from_database(cart)
    except ValueError as error:
        return jsonify(
            {"success": False, "message": str(error)}
        ), 400

    order_number = generate_order_number()
    demo_payment_id = "DEMO" + str(int(time.time() * 1000))

    connection = get_db_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO orders (
                user_id,
                order_number,
                customer_name,
                mobile,
                house,
                street,
                city,
                pincode,
                payment_method,
                payment_status,
                payment_id,
                total_amount,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                order_number,
                fields["Customer name"],
                fields["Mobile number"],
                fields["House number"],
                fields["Street"],
                fields["City"],
                fields["Pincode"],
                "Demo Online Payment",
                "Paid",
                demo_payment_id,
                total_amount,
                "Order Placed",
            ),
        )

        order_id = cursor.lastrowid

        for item in cleaned_cart:
            connection.execute(
                """
                INSERT INTO order_items (
                    order_id,
                    product_id,
                    product_name,
                    price,
                    quantity
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    item["id"],
                    item["name"],
                    item["price"],
                    item["quantity"],
                ),
            )

        connection.commit()

        return jsonify(
            {
                "success": True,
                "message": "Demo payment successful",
                "order_id": order_id,
                "order_number": order_number,
                "subtotal": subtotal,
                "delivery_fee": delivery_fee,
                "total_amount": total_amount,
                "payment_method": "Demo Online Payment",
                "payment_status": "Paid",
                "payment_id": demo_payment_id,
            }
        )

    except Exception as error:
        connection.rollback()
        print("Demo payment order error:", repr(error))
        return jsonify(
            {
                "success": False,
                "message": "Could not save demo payment order",
            }
        ), 500

    finally:
        connection.close()


# =========================================
# CUSTOMER ORDERS
# =========================================

@app.route("/api/my-orders")
def get_my_orders():
    if not is_customer_logged_in():
        return jsonify(
            {"success": False, "message": "Please login first"}
        ), 401

    connection = get_db_connection()

    try:
        orders = connection.execute(
            """
            SELECT
                id,
                order_number,
                customer_name,
                mobile,
                house,
                street,
                city,
                pincode,
                payment_method,
                payment_status,
                payment_id,
                razorpay_order_id,
                total_amount,
                status,
                created_at
            FROM orders
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (session["user_id"],),
        ).fetchall()

        return jsonify(
            {
                "success": True,
                "orders": [dict(order) for order in orders],
            }
        )

    finally:
        connection.close()


@app.route("/api/orders/<order_number>")
def get_order_details(order_number):
    if not is_customer_logged_in():
        return jsonify(
            {"success": False, "message": "Please login first"}
        ), 401

    connection = get_db_connection()

    try:
        order = connection.execute(
            """
            SELECT
                id,
                order_number,
                customer_name,
                mobile,
                house,
                street,
                city,
                pincode,
                payment_method,
                payment_status,
                payment_id,
                razorpay_order_id,
                total_amount,
                status,
                created_at
            FROM orders
            WHERE order_number = ?
              AND user_id = ?
            """,
            (order_number, session["user_id"]),
        ).fetchone()

    finally:
        connection.close()

    if order is None:
        return jsonify(
            {"success": False, "message": "Order not found"}
        ), 404

    return jsonify(
        {"success": True, "order": dict(order)}
    )


# =========================================
# HEALTH CHECK
# =========================================

@app.route("/api/health")
def health_check():
    return jsonify(
        {
            "status": "success",
            "message": "QuickMart API is running",
        }
    )


# =========================================
# ERROR HANDLERS
# =========================================

@app.errorhandler(404)
def page_not_found(error):
    return jsonify(
        {"success": False, "message": "Page not found"}
    ), 404


@app.errorhandler(500)
def internal_server_error(error):
    print("Internal server error:", repr(error))
    return jsonify(
        {"success": False, "message": "Internal server error"}
    ), 500


# =========================================
# START SERVER
# =========================================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000,
    )
