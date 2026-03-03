from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "store.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.config["DATABASE"] = str(DB_PATH)


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exception: Exception | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    with app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf8"))

    admin_exists = db.execute("SELECT id FROM users WHERE email = ?", ("admin@mobify.pt",)).fetchone()
    if not admin_exists:
        db.execute(
            """
            INSERT INTO users (name, email, password_hash, role)
            VALUES (?, ?, ?, ?)
            """,
            (
                "Admin",
                "admin@mobify.pt",
                generate_password_hash("admin123"),
                "admin",
            ),
        )

    if not db.execute("SELECT id FROM furniture LIMIT 1").fetchone():
        demo_products = [
            (
                "Sofá Nórdico KALA",
                "Sala",
                "Sofá modular em tecido reciclado com estrutura em madeira maciça.",
                899.90,
                12,
                "https://images.unsplash.com/photo-1555041469-a586c61ea9bc",
                "Largura 240cm x Profundidade 95cm x Altura 82cm",
                "bege,cinza",
            ),
            (
                "Mesa de Jantar LIN",
                "Jantar",
                "Mesa extensível para 8 pessoas com acabamento em carvalho.",
                499.00,
                8,
                "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85",
                "140-200cm x 90cm x 75cm",
                "carvalho,preto",
            ),
            (
                "Cama Plataforma VIK",
                "Quarto",
                "Cama com arrumação integrada e cabeceira almofadada.",
                649.50,
                5,
                "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85",
                "160cm x 200cm",
                "branco,areia",
            ),
        ]
        db.executemany(
            """
            INSERT INTO furniture
                (name, category, description, price, stock, image_url, dimensions, colors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            demo_products,
        )

    db.commit()


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Precisas de iniciar sessão para continuar.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Acesso reservado a administradores.", "danger")
            return redirect(url_for("index"))
        return view_func(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_now():
    return {"year": datetime.now().year}


@app.route("/")
def index():
    db = get_db()
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    query = "SELECT * FROM furniture WHERE 1=1"
    params: list[str] = []

    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        like_term = f"%{search}%"
        params.extend([like_term, like_term])

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY created_at DESC"

    products = db.execute(query, params).fetchall()
    categories = db.execute("SELECT DISTINCT category FROM furniture ORDER BY category").fetchall()

    return render_template(
        "index.html",
        products=products,
        categories=categories,
        selected_category=category,
        search=search,
    )


@app.route("/produto/<int:product_id>")
def product_detail(product_id: int):
    db = get_db()
    product = db.execute("SELECT * FROM furniture WHERE id = ?", (product_id,)).fetchone()
    if not product:
        flash("Produto não encontrado.", "danger")
        return redirect(url_for("index"))
    return render_template("product_detail.html", product=product)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 6:
            flash("Dados inválidos. Password deve ter pelo menos 6 caracteres.", "danger")
            return redirect(url_for("register"))

        db = get_db()
        existing_user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing_user:
            flash("Email já registado.", "warning")
            return redirect(url_for("register"))

        db.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (name, email, generate_password_hash(password), "user"),
        )
        db.commit()
        flash("Conta criada com sucesso! Agora faz login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Credenciais inválidas.", "danger")
            return redirect(url_for("login"))

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["role"] = user["role"]
        flash(f"Bem-vindo(a), {user['name']}!", "success")
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sessão terminada.", "info")
    return redirect(url_for("index"))


@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    db = get_db()
    products = db.execute("SELECT * FROM furniture ORDER BY id DESC").fetchall()
    users = db.execute("SELECT id, name, email, role, created_at FROM users ORDER BY id DESC").fetchall()
    return render_template("admin.html", products=products, users=users)


@app.route("/admin/product/new", methods=["POST"])
@login_required
@admin_required
def create_product():
    form = request.form
    db = get_db()
    db.execute(
        """
        INSERT INTO furniture (name, category, description, price, stock, image_url, dimensions, colors)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            form.get("name", "").strip(),
            form.get("category", "").strip(),
            form.get("description", "").strip(),
            float(form.get("price", "0") or 0),
            int(form.get("stock", "0") or 0),
            form.get("image_url", "").strip(),
            form.get("dimensions", "").strip(),
            form.get("colors", "").strip(),
        ),
    )
    db.commit()
    flash("Produto adicionado com sucesso.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/product/<int:product_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_product(product_id: int):
    db = get_db()
    db.execute("DELETE FROM furniture WHERE id = ?", (product_id,))
    db.commit()
    flash("Produto removido.", "info")
    return redirect(url_for("admin_dashboard"))


@app.cli.command("init-db")
def init_db_command():
    init_db()
    print("Base de dados inicializada.")


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
