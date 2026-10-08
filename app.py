from flask import Flask, request, redirect, url_for, render_template_string, session
from pathlib import Path
from datetime import date, timedelta
import json
import uuid

app = Flask(__name__)
app.secret_key = "change-this-demo-secret-key"
DATA_DIR = Path(__file__).resolve().parent
INVENTORY_FILE = DATA_DIR / "inventory.json"
ORDERS_FILE = DATA_DIR / "orders.json"

DEFAULT_PRODUCTS = [
    {"id": 1, "name": "Fresh Apples", "category": "Fruits", "price": 120.0, "stock": 25, "emoji": "🍎"},
    {"id": 2, "name": "Bananas", "category": "Fruits", "price": 50.0, "stock": 40, "emoji": "🍌"},
    {"id": 3, "name": "Tomatoes", "category": "Vegetables", "price": 35.0, "stock": 30, "emoji": "🍅"},
    {"id": 4, "name": "Carrots", "category": "Vegetables", "price": 45.0, "stock": 20, "emoji": "🥕"},
    {"id": 5, "name": "Milk", "category": "Dairy", "price": 32.0, "stock": 35, "emoji": "🥛"},
    {"id": 6, "name": "Bread", "category": "Bakery", "price": 45.0, "stock": 18, "emoji": "🍞"},
    {"id": 7, "name": "Rice (1 kg)", "category": "Staples", "price": 70.0, "stock": 50, "emoji": "🍚"},
    {"id": 8, "name": "Orange Juice", "category": "Beverages", "price": 85.0, "stock": 15, "emoji": "🧃"},
]

PAGE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>FreshBasket Grocery Delivery</title><style>
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;background:#f5f7f3;color:#263326}header{background:#176b3a;color:white;padding:18px 5%;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}header a{color:white;text-decoration:none;margin-left:14px;font-weight:bold}.brand{font-size:23px;font-weight:bold}main{max-width:1100px;margin:26px auto;padding:0 16px}.hero{background:#e2f4df;padding:26px;border-radius:16px;margin-bottom:22px}h1{margin-top:0}.filters{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}input,select,textarea,button{font:inherit;padding:10px;border:1px solid #cbd5c9;border-radius:8px}input,select,textarea{background:white}button,.btn{background:#176b3a;color:white;border:0;cursor:pointer;text-decoration:none;display:inline-block;padding:10px 14px;border-radius:8px}button:hover,.btn:hover{background:#10532c}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px}.card{background:white;padding:18px;border-radius:14px;box-shadow:0 2px 10px #0000000c}.emoji{font-size:40px}.price{font-size:20px;font-weight:bold;color:#176b3a}.muted{color:#657265}.row{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}table{width:100%;border-collapse:collapse;background:white;margin:16px 0}th,td{text-align:left;padding:12px;border-bottom:1px solid #e3e8e1}.panel{background:white;padding:20px;border-radius:14px;overflow-x:auto}.field{display:block;width:100%;margin:7px 0 14px}.notice{background:#fff4d6;padding:12px;border-radius:8px;margin:12px 0}footer{text-align:center;padding:24px;color:#657265}
</style></head><body><header><div class="brand">🧺 FreshBasket</div><nav><a href="{{ url_for('home') }}">Shop</a><a href="{{ url_for('cart') }}">Cart ({{ cart_count }})</a><a href="{{ url_for('orders') }}">Orders</a><a href="{{ url_for('inventory') }}">Inventory</a></nav></header><main>{% if message %}<div class="notice">{{ message }}</div>{% endif %}{{ content|safe }}</main><footer>FreshBasket · Grocery delivery demo app</footer></body></html>'''

HOME = r'''<section class="hero"><h1>Fresh groceries, delivered to you 🥬</h1><p>Choose your essentials, check stock, and schedule a delivery.</p></section><form class="filters" method="get"><input name="q" placeholder="Search groceries..." value="{{ q }}"><select name="category"><option value="">All categories</option>{% for c in categories %}<option value="{{ c }}" {% if c == selected %}selected{% endif %}>{{ c }}</option>{% endfor %}</select><button type="submit">Search</button><a class="btn" href="{{ url_for('home') }}">Clear</a></form><div class="grid">{% for p in products %}<article class="card"><div class="emoji">{{ p.emoji }}</div><h3>{{ p.name }}</h3><p class="muted">{{ p.category }} · Stock: {{ p.stock }}</p><p class="price">₹{{ '%.2f'|format(p.price) }}</p>{% if p.stock > 0 %}<form method="post" action="{{ url_for('add_to_cart', product_id=p.id) }}"><label>Quantity <input type="number" name="quantity" value="1" min="1" max="{{ p.stock }}" style="width:80px"></label> <button type="submit">Add to cart</button></form>{% else %}<p>Out of stock</p>{% endif %}</article>{% else %}<p>No products match your search.</p>{% endfor %}</div>'''
CART = r'''<h1>Your shopping cart</h1>{% if items %}<div class="panel"><table><tr><th>Product</th><th>Price</th><th>Quantity</th><th>Subtotal</th><th>Update</th></tr>{% for item in items %}<tr><td>{{ item.name }}</td><td>₹{{ '%.2f'|format(item.price) }}</td><td>{{ item.quantity }}</td><td>₹{{ '%.2f'|format(item.subtotal) }}</td><td><form method="post" action="{{ url_for('update_cart') }}"><input type="hidden" name="product_id" value="{{ item.id }}"><input type="number" name="quantity" min="0" max="{{ item.stock }}" value="{{ item.quantity }}" style="width:75px"> <button>Save</button></form></td></tr>{% endfor %}</table><div class="row"><h2>Total: ₹{{ '%.2f'|format(total) }}</h2><a class="btn" href="{{ url_for('checkout') }}">Proceed to checkout</a></div><p class="muted">Set quantity to 0 and save to remove an item.</p></div>{% else %}<div class="panel"><p>Your cart is empty.</p><a class="btn" href="{{ url_for('home') }}">Continue shopping</a></div>{% endif %}'''
CHECKOUT = r'''<h1>Delivery details</h1><div class="panel">{% if errors %}<div class="notice">{% for e in errors %}<div>{{ e }}</div>{% endfor %}</div>{% endif %}<form method="post"><label>Full name<input class="field" name="name" value="{{ form.get('name','') }}" required></label><label>10-digit phone number<input class="field" name="phone" inputmode="numeric" value="{{ form.get('phone','') }}" required></label><label>Delivery address<textarea class="field" name="address" rows="3" required>{{ form.get('address','') }}</textarea></label><label>Delivery date<input class="field" type="date" name="delivery_date" min="{{ min_date }}" value="{{ form.get('delivery_date', min_date) }}" required></label><label>Delivery slot<select class="field" name="slot" required>{% for s in slots %}<option value="{{ s }}" {% if form.get('slot') == s %}selected{% endif %}>{{ s }}</option>{% endfor %}</select></label><h3>Order total: ₹{{ '%.2f'|format(total) }}</h3><button type="submit">Place order</button></form></div>'''
ORDER = r'''<h1>Order placed successfully! 🎉</h1><div class="panel"><p><b>Order ID:</b> {{ order.id }}</p><p><b>Name:</b> {{ order.name }}</p><p><b>Delivery:</b> {{ order.delivery_date }} · {{ order.slot }}</p><p><b>Address:</b> {{ order.address }}</p><table><tr><th>Item</th><th>Quantity</th><th>Subtotal</th></tr>{% for item in order.items %}<tr><td>{{ item.name }}</td><td>{{ item.quantity }}</td><td>₹{{ '%.2f'|format(item.subtotal) }}</td></tr>{% endfor %}</table><h2>Total: ₹{{ '%.2f'|format(order.total) }}</h2><a class="btn" href="{{ url_for('home') }}">Shop more</a></div>'''
ORDERS = r'''<h1>Recent orders</h1><div class="panel">{% if orders %}<table><tr><th>Order ID</th><th>Customer</th><th>Delivery</th><th>Total</th><th>Status</th></tr>{% for o in orders %}<tr><td><a href="{{ url_for('order_detail', order_id=o.id) }}">{{ o.id }}</a></td><td>{{ o.name }}</td><td>{{ o.delivery_date }} · {{ o.slot }}</td><td>₹{{ '%.2f'|format(o.total) }}</td><td>{{ o.status }}</td></tr>{% endfor %}</table>{% else %}<p>No orders have been placed yet.</p>{% endif %}</div>'''
INVENTORY = r'''<h1>Live inventory</h1><div class="panel"><p class="muted">Stock changes automatically when an order is placed.</p><table><tr><th>Product</th><th>Category</th><th>Price</th><th>Stock</th></tr>{% for p in products %}<tr><td>{{ p.emoji }} {{ p.name }}</td><td>{{ p.category }}</td><td>₹{{ '%.2f'|format(p.price) }}</td><td>{{ p.stock }}</td></tr>{% endfor %}</table></div>'''

def read_json(path, fallback):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback

def write_json(path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_products():
    if not INVENTORY_FILE.exists():
        write_json(INVENTORY_FILE, DEFAULT_PRODUCTS)
    return read_json(INVENTORY_FILE, DEFAULT_PRODUCTS)

def save_products(products):
    write_json(INVENTORY_FILE, products)

def get_orders():
    return read_json(ORDERS_FILE, [])

def render_page(template, message="", **kwargs):
    cart_count = sum(int(q) for q in session.get("cart", {}).values())
    content = render_template_string(template, **kwargs)
    return render_template_string(PAGE, content=content, cart_count=cart_count, message=message)

def cart_items():
    products, cart = get_products(), session.get("cart", {})
    items = []
    for key, quantity in cart.items():
        p = next((p for p in products if p["id"] == int(key)), None)
        if p and int(quantity) > 0:
            item = dict(p)
            item["quantity"] = int(quantity)
            item["subtotal"] = item["price"] * item["quantity"]
            items.append(item)
    return items

@app.route("/")
def home():
    products = get_products()
    q = request.args.get("q", "").strip().lower()
    selected = request.args.get("category", "")
    categories = sorted({p["category"] for p in products})
    filtered = [p for p in products if (not q or q in p["name"].lower() or q in p["category"].lower()) and (not selected or p["category"] == selected)]
    return render_page(HOME, products=filtered, categories=categories, q=request.args.get("q", ""), selected=selected)

@app.post("/add/<int:product_id>")
def add_to_cart(product_id):
    products = get_products()
    p = next((p for p in products if p["id"] == product_id), None)
    try:
        quantity = int(request.form.get("quantity", "1"))
    except ValueError:
        quantity = 0
    if not p or quantity < 1:
        return redirect(url_for("home"))
    cart = session.get("cart", {})
    current = int(cart.get(str(product_id), 0))
    if current + quantity > p["stock"]:
        return redirect(url_for("home"))
    cart[str(product_id)] = current + quantity
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/cart")
def cart():
    items = cart_items()
    return render_page(CART, items=items, total=sum(i["subtotal"] for i in items))

@app.post("/cart/update")
def update_cart():
    pid = request.form.get("product_id", "")
    try:
        quantity = int(request.form.get("quantity", "0"))
    except ValueError:
        quantity = -1
    p = next((p for p in get_products() if str(p["id"]) == pid), None)
    if p and 0 <= quantity <= p["stock"]:
        cart = session.get("cart", {})
        if quantity == 0:
            cart.pop(pid, None)
        else:
            cart[pid] = quantity
        session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items = cart_items()
    if not items:
        return redirect(url_for("cart"))
    total = sum(i["subtotal"] for i in items)
    slots = ["9:00 AM - 12:00 PM", "12:00 PM - 3:00 PM", "3:00 PM - 6:00 PM", "6:00 PM - 9:00 PM"]
    min_date = (date.today() + timedelta(days=1)).isoformat()
    form = request.form if request.method == "POST" else {}
    errors = []
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        delivery_date = request.form.get("delivery_date", "")
        slot = request.form.get("slot", "")
        if not name: errors.append("Please enter your name.")
        if not (phone.isdigit() and len(phone) == 10): errors.append("Phone number must contain exactly 10 digits.")
        if not address: errors.append("Please enter your delivery address.")
        if not delivery_date or delivery_date < min_date: errors.append("Choose a delivery date starting tomorrow.")
        if slot not in slots: errors.append("Choose a valid delivery slot.")
        products = get_products()
        for item in items:
            p = next((p for p in products if p["id"] == item["id"]), None)
            if not p or item["quantity"] > p["stock"]:
                errors.append(f"Not enough stock for {item['name']}. Please update your cart.")
        if not errors:
            order = {"id": uuid.uuid4().hex[:8].upper(), "name": name, "phone": phone, "address": address,
                     "delivery_date": delivery_date, "slot": slot,
                     "items": [{"id": i["id"], "name": i["name"], "quantity": i["quantity"], "price": i["price"], "subtotal": i["subtotal"]} for i in items],
                     "total": total, "status": "Confirmed"}
            for item in items:
                p = next(p for p in products if p["id"] == item["id"])
                p["stock"] -= item["quantity"]
            save_products(products)
            orders = get_orders()
            orders.insert(0, order)
            write_json(ORDERS_FILE, orders)
            session["cart"] = {}
            return redirect(url_for("order_detail", order_id=order["id"]))
    return render_page(CHECKOUT, total=total, form=form, errors=errors, slots=slots, min_date=min_date)

@app.route("/order/<order_id>")
def order_detail(order_id):
    order = next((o for o in get_orders() if o["id"] == order_id), None)
    if not order:
        return "Order not found", 404
    return render_page(ORDER, order=order)

@app.route("/orders")
def orders():
    return render_page(ORDERS, orders=get_orders())

@app.route("/inventory")
def inventory():
    return render_page(INVENTORY, products=get_products())

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
