import sqlite3

from werkzeug.security import generate_password_hash


DATABASE = "quickmart.db"


# =========================================
# DATABASE CONNECTION
# =========================================

def get_db_connection():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    # Enable foreign keys
    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


# =========================================
# CREATE DATABASE
# =========================================

def create_database():

    connection = get_db_connection()
    cursor = connection.cursor()


    # =========================================
    # USERS TABLE
    # =========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL

        )
    """)


    # =========================================
    # ADMINS TABLE
    # =========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL

        )
    """)


    # =========================================
    # PRODUCTS TABLE
    # =========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            category TEXT NOT NULL,

            price REAL NOT NULL,

            emoji TEXT

        )
    """)


    # =========================================
    # ORDERS TABLE
    # =========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            order_number TEXT UNIQUE NOT NULL,

            customer_name TEXT NOT NULL,

            mobile TEXT NOT NULL,

            house TEXT NOT NULL,

            street TEXT NOT NULL,

            city TEXT NOT NULL,

            pincode TEXT NOT NULL,

            payment_method TEXT NOT NULL,

            payment_status TEXT NOT NULL DEFAULT 'Pending',

            payment_id TEXT,

            razorpay_order_id TEXT,

            total_amount REAL NOT NULL,

            status TEXT NOT NULL DEFAULT 'Order Placed',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)

        )
    """)


    # =========================================
    # CHECK EXISTING ORDERS COLUMNS
    # =========================================

    columns = cursor.execute(
        "PRAGMA table_info(orders)"
    ).fetchall()

    column_names = [
        column["name"]
        for column in columns
    ]


    # =========================================
    # ADD user_id TO OLD DATABASE
    # =========================================

    if "user_id" not in column_names:

        cursor.execute("""
            ALTER TABLE orders
            ADD COLUMN user_id INTEGER
        """)


    # =========================================
    # ADD payment_status TO OLD DATABASE
    # =========================================

    if "payment_status" not in column_names:

        cursor.execute("""
            ALTER TABLE orders
            ADD COLUMN payment_status TEXT
            NOT NULL DEFAULT 'Pending'
        """)


    # =========================================
    # ADD payment_id TO OLD DATABASE
    # =========================================

    if "payment_id" not in column_names:

        cursor.execute("""
            ALTER TABLE orders
            ADD COLUMN payment_id TEXT
        """)


    # =========================================
    # ADD razorpay_order_id TO OLD DATABASE
    # =========================================

    if "razorpay_order_id" not in column_names:

        cursor.execute("""
            ALTER TABLE orders
            ADD COLUMN razorpay_order_id TEXT
        """)


    # =========================================
    # FIX OLD ORDERS PAYMENT STATUS
    # =========================================

    cursor.execute("""
        UPDATE orders
        SET payment_status = 'Pending'
        WHERE payment_status IS NULL
           OR payment_status = ''
    """)


    # =========================================
    # ORDER ITEMS TABLE
    # =========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            order_id INTEGER NOT NULL,

            product_id INTEGER NOT NULL,

            product_name TEXT NOT NULL,

            price REAL NOT NULL,

            quantity INTEGER NOT NULL,

            FOREIGN KEY (order_id)
                REFERENCES orders(id)

        )
    """)


    # =========================================
    # CREATE DEFAULT ADMIN ACCOUNT
    # =========================================

    admin_count = cursor.execute(
        "SELECT COUNT(*) FROM admins"
    ).fetchone()[0]


    if admin_count == 0:

        admin_password = generate_password_hash(
            "Admin@123"
        )

        cursor.execute(
            """
            INSERT INTO admins
            (name, email, password)
            VALUES (?, ?, ?)
            """,
            (
                "QuickMart Admin",
                "admin@quickmart.com",
                admin_password
            )
        )


    # =========================================
    # CHECK PRODUCTS
    # =========================================

    product_count = cursor.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]


    # =========================================
    # INSERT DEFAULT PRODUCTS
    # =========================================

    if product_count == 0:

        products = [

            ("Fresh Apples", "Fruits", 120, "🍎"),
            ("Bananas", "Fruits", 50, "🍌"),
            ("Oranges", "Fruits", 80, "🍊"),
            ("Grapes", "Fruits", 100, "🍇"),

            ("Tomatoes", "Vegetables", 40, "🍅"),
            ("Potatoes", "Vegetables", 35, "🥔"),
            ("Carrots", "Vegetables", 45, "🥕"),
            ("Broccoli", "Vegetables", 70, "🥦"),

            ("Milk", "Dairy", 60, "🥛"),
            ("Cheese", "Dairy", 150, "🧀"),
            ("Butter", "Dairy", 120, "🧈"),
            ("Curd", "Dairy", 40, "🥣"),

            ("Biscuits", "Snacks", 30, "🍪"),
            ("Potato Chips", "Snacks", 40, "🍟"),
            ("Chocolate", "Snacks", 50, "🍫"),
            ("Cookies", "Snacks", 60, "🍪"),

            ("Orange Juice", "Beverages", 90, "🧃"),
            ("Soft Drink", "Beverages", 50, "🥤"),
            ("Green Tea", "Beverages", 100, "🍵"),
            ("Mineral Water", "Beverages", 20, "💧"),

            ("Dish Wash", "Household", 90, "🧴"),
            ("Floor Cleaner", "Household", 120, "🧹"),
            ("Laundry Detergent", "Household", 180, "🧺"),
            ("Tissue Paper", "Household", 70, "🧻")

        ]

        cursor.executemany(
            """
            INSERT INTO products
            (name, category, price, emoji)
            VALUES (?, ?, ?, ?)
            """,
            products
        )


    # =========================================
    # SAVE DATABASE
    # =========================================

    connection.commit()

    connection.close()


# =========================================
# RUN DATABASE
# =========================================

if __name__ == "__main__":

    create_database()

    print(
        "Database created successfully!"
    )