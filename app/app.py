#!/usr/bin/python3
from logging.config import dictConfig

import psycopg
from flask import flash
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask import Response
from psycopg.rows import namedtuple_row
from psycopg_pool import ConnectionPool
from math import ceil


# postgres://{user}:{password}@{hostname}:{port}/{database-name}
DATABASE_URL = "postgres://db:db@postgres/db"

pool = ConnectionPool(conninfo=DATABASE_URL)
# the pool starts connecting immediately.

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s:%(lineno)s - %(funcName)20s(): %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["wsgi"]},
    }
)

app = Flask(__name__)
log = app.logger
app.secret_key = "teste"


@app.route("/", methods=("GET",))
def index():
    return render_template("base.html")


@app.route("/products", methods=("GET",))
def products_index():
    DEFAULT_AMMOUNT = 10

    if request.args.get("p") is None:
        return redirect(url_for("products_index", p=1))

    p = eval(request.args.get("p"))

    if p < 1:
        return redirect(url_for("products_index", p=1))

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            try:
                count = cur.execute(
                    """
                    SELECT COUNT(*) FROM product;
                    """
                ).fetchone()[0]

                if count == 0:
                    return render_template(
                        "products/index.html", products=[], p=1, last_p=1
                    )

                if DEFAULT_AMMOUNT * (p - 1) >= count:
                    return redirect(
                        url_for("products_index", p=ceil(count / DEFAULT_AMMOUNT))
                    )

                products = cur.execute(
                    """
                        SELECT * FROM product LIMIT %(limit)s OFFSET %(page)s;
                    """,
                    {"page": DEFAULT_AMMOUNT * (p - 1), "limit": DEFAULT_AMMOUNT},
                ).fetchall()
            except:
                flash(
                    "There was an error adding the product. Please try again later.",
                    "error",
                )
                return redirect(url_for("products_index"))

    return render_template(
        "products/index.html",
        products=products,
        p=p,
        last_p=ceil(count / DEFAULT_AMMOUNT),
    )


@app.route("/products/new", methods=("GET", "POST"))
def products_new():
    if request.method == "GET":
        return render_template("products/new.html")

    if request.method == "POST":
        # These conditions are enforced in the client side
        if (
            len(request.form["description"]) == 0
            or len(request.form["name"]) == 0
            or len(request.form["name"]) > 200
            or len(request.form["sku"]) == 0
            or len(request.form["sku"]) > 25
            or len(request.form["ean"]) > 13
            or not request.form["price"].replace(".", "", 1).isnumeric()
        ):
            flash(
                "There was an error adding the product. Please try again later.",
                "error",
            )
            return redirect(url_for("products_index"))

        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                try:
                    if len(request.form["ean"]) == 0:
                        cur.execute(
                            """
                                INSERT INTO product VALUES(%(sku)s, %(name)s, %(description)s, %(price)s);
                            """,
                            request.form,
                        )
                    else:
                        cur.execute(
                            """
                                INSERT INTO product VALUES(%(sku)s, %(name)s, %(description)s, %(price)s, %(ean)s);
                            """,
                            request.form,
                        )
                except psycopg.errors.UniqueViolation:
                    flash("A product with the same SKU already exists.", "warn")
                except:
                    flash(
                        "There was an error adding the product. Please try again later.",
                        "error",
                    )

                return redirect(url_for("products_index"))


@app.route("/products/<sku>", methods=("GET", "POST"))
def products_edit(sku):
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            try:
                product = cur.execute(
                    """
                            SELECT * FROM product WHERE sku = %s
                        """,
                    (sku,),
                ).fetchone()

                if product is None:
                    flash("Product unavaillable.", "warn")
                    return redirect(url_for("products_index"))
            except:
                flash(
                    "There was an error adding the product. Please try again later.",
                    "error",
                )
                return redirect(url_for("products_index"))

    if request.method == "GET":
        return render_template("products/edit.html", product=product)

    if request.method == "POST":
        if (
            len(request.form["description"]) == 0
            or not request.form["price"].replace(".", "", 1).isnumeric()
        ):
            flash(
                "There was an error editing the product. Please try again later.",
                "error",
            )
            return redirect(url_for("products_index"))

        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                try:
                    cur.execute(
                        """
                        UPDATE product SET description = %(description)s, price = %(price)s WHERE sku = %(sku)s;
                        """,
                        {
                            "description": request.form["description"],
                            "price": request.form["price"],
                            "sku": sku,
                        },
                    )
                except:
                    flash(
                        "There was an error editing the product. Please try again later.",
                        "error",
                    )
        return redirect(url_for("products_index"))


@app.route("/products/delete/<sku>", methods=("GET", "POST"))
def products_delete(sku):
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            try:
                product = cur.execute(
                    """
                        SELECT * FROM product WHERE sku = %s;
                    """,
                    (sku,),
                ).fetchone()

                if product is None:
                    flash("Product unavaillable.", "warn")
                    return redirect(url_for("products_index"))

                orders = cur.execute(
                    """
                        SELECT DISTINCT
                            order_no,
                            date,
                            cust_no,
                            c.name
                        FROM 
                            contains
                        NATURAL JOIN
                            orders
                        INNER JOIN
                            customer c
                        USING (cust_no)
                        WHERE 
                            sku = %s;
                    """,
                    (sku,),
                ).fetchall()

                suppliers = cur.execute(
                    """
                        SELECT DISTINCT tin, address, name FROM supplier WHERE sku = %s;
                    """,
                    (sku,),
                ).fetchall()

                deliveries = cur.execute(
                    """
                        SELECT
                            tin,
                            d.address
                        FROM
                            delivery d
                        INNER JOIN 
                            supplier USING (TIN)
                        WHERE
                            sku = %s; 
                    """,
                    (sku,),
                ).fetchall()
            except:
                flash(
                    "There was an error adding the product. Please try again later.",
                    "error",
                )
                return redirect(url_for("products_index"))

    if request.method == "GET":
        return render_template(
            "products/delete.html",
            product=product,
            orders=orders,
            suppliers=suppliers,
            deliveries=deliveries,
        )

    if request.method == "POST":
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                try:
                    cur.execute(
                        """
                            DELETE FROM contains WHERE sku = %s;
                        """,
                        (sku,),
                    )

                    for supplier in suppliers:
                        cur.execute(
                            """
                                DELETE FROM delivery WHERE tin = %s;
                            """,
                            (supplier[0],),
                        )

                    cur.execute(
                        """
                            DELETE FROM supplier WHERE sku = %s;
                        """,
                        (sku,),
                    )

                    cur.execute(
                        """
                            DELETE FROM product WHERE sku = %s;
                        """,
                        (sku,),
                    )
                except:
                    flash(
                        "There was an error adding the product. Please try again later.",
                        "error",
                    )
                    return redirect(url_for("products_index"))

        flash(f"Product {sku} deleted successfully.", "info")
        return redirect(url_for("products_index"))


@app.route("/suppliers", methods=("GET",))
def suppliers_index():
    DEFAULT_AMMOUNT = 10

    if request.args.get("p") is None:
        return redirect(url_for("suppliers_index", p=1))

    p = eval(request.args.get("p"))

    if p < 1:
        return redirect(url_for("suppliers_index", p=1))

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            try:
                count = cur.execute(
                    """
                    SELECT COUNT(*) FROM supplier;
                    """
                ).fetchone()[0]

                if count == 0:
                    return render_template(
                        "suppliers/index.html", suppliers=[], p=1, last_p=1
                    )

                if DEFAULT_AMMOUNT * (p - 1) >= count:
                    return redirect(
                        url_for("suppliers_index", p=ceil(count / DEFAULT_AMMOUNT))
                    )

                suppliers = cur.execute(
                    """
                        SELECT * FROM supplier LIMIT %(limit)s OFFSET %(page)s;
                    """,
                    {"page": DEFAULT_AMMOUNT * (p - 1), "limit": DEFAULT_AMMOUNT},
                ).fetchall()
            except:
                flash(
                    "There was an error getting the suppliers. Please try again later.",
                    "error",
                )
                return redirect(url_for("suppliers_index"))

    return render_template(
        "suppliers/index.html",
        suppliers=suppliers,
        p=p,
        last_p=ceil(count / DEFAULT_AMMOUNT),
    )


@app.route("/suppliers/new", methods=("GET", "POST"))
def suppliers_new():
    if request.method == "GET":
        return render_template("suppliers/new.html")

    if request.method == "POST":
        # These conditions are enforced in the client side
        if (
            len(request.form["tin"]) == 0
            or len(request.form["tin"]) > 20
            or len(request.form["name"]) > 200
            or len(request.form["address"]) > 255
            or len(request.form["sku"]) == 0
            or len(request.form["sku"]) > 255
            # Verify date
        ):
            flash(
                "There was an error adding the supplier. Please try again later.",
                "error",
            )
            return redirect(url_for("suppliers_index"))

        info = {
            "tin": request.form["tin"],
            "name": None,
            "address": None,
            "sku": request.form["sku"],
            "date": None,
        }

        if len(request.form["name"]) != 0:
            info["name"] = request.form["name"]

        if len(request.form["address"]) != 0:
            info["address"] = request.form["address"]

        if len(request.form["date"]) != 0:
            info["date"] = request.form["date"]

        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                try:
                    cur.execute(
                        """
                                INSERT INTO supplier VALUES(%(tin)s,%(name)s ,%(address)s , %(sku)s, %(date)s);
                            """,
                        info,
                    )
                except psycopg.errors.UniqueViolation:
                    flash("A supplier with the same TIN already exists.", "warn")
                except:
                    flash(
                        "There was an error adding the supplier. Please try again later.",
                        "error",
                    )
            return redirect(url_for("suppliers_index"))


@app.route("/suppliers/delete/<tin>", methods=("GET", "POST"))
def suppliers_delete(tin):
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            try:
                supplier = cur.execute(
                    """
                        SELECT * FROM supplier WHERE tin = %s;
                    """,
                    (tin,),
                ).fetchone()

                if supplier is None:
                    flash("Supplier unavaillable.", "warn")
                    return redirect(url_for("suppliers_index"))

                deliveries = cur.execute(
                    """
                        SELECT
                            tin,
                            d.address
                        FROM
                            delivery d
                        INNER JOIN 
                            supplier USING (TIN)
                        WHERE
                            tin = %s; 
                    """,
                    (tin,),
                ).fetchall()
            except:
                flash(
                    "There was an error deleting the supplier. Please try again later.",
                    "error",
                )
                return redirect(url_for("suppliers_index"))

    if request.method == "GET":
        return render_template(
            "suppliers/delete.html",
            supplier=supplier,
            deliveries=deliveries,
        )

    if request.method == "POST":
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                try:
                    cur.execute(
                        """
                            DELETE FROM delivery WHERE tin = %s;
                        """,
                        (tin,),
                    )

                    cur.execute(
                        """
                            DELETE FROM supplier WHERE tin = %s;
                        """,
                        (tin,),
                    )

                except:
                    flash(
                        "There was an error deleting the supplier. Please try again later.",
                        "error",
                    )
                    return redirect(url_for("suppliers_index"))

        flash(f"Supplier {tin} deleted successfully.", "info")
        return redirect(url_for("suppliers_index"))


@app.route("/customers", methods=("GET",))
def customers_index():
    DEFAULT_AMMOUNT = 10

    if request.args.get("p") is None:
        return redirect(url_for("customers_index", p=1))

    p = eval(request.args.get("p"))

    if p < 1:
        return redirect(url_for("customers_index", p=1))

    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            try:
                count = cur.execute(
                    """
                    SELECT COUNT(*) FROM customer;
                    """
                ).fetchone()[0]

                if count == 0:
                    return render_template(
                        "customers/index.html", customers=[], p=1, last_p=1
                    )

                if DEFAULT_AMMOUNT * (p - 1) >= count:
                    return redirect(
                        url_for("customers_index", p=ceil(count / DEFAULT_AMMOUNT))
                    )

                customers = cur.execute(
                    """
                        SELECT * FROM customer LIMIT %(limit)s OFFSET %(page)s;
                    """,
                    {"page": DEFAULT_AMMOUNT * (p - 1), "limit": DEFAULT_AMMOUNT},
                ).fetchall()
            except:
                flash(
                    "There was an error getting the customers. Please try again later.",
                    "error",
                )
                return redirect(url_for("customers_index"))

    return render_template(
        "customers/index.html",
        customers=customers,
        p=p,
        last_p=ceil(count / DEFAULT_AMMOUNT),
    )


@app.route("/customers/new", methods=("GET", "POST"))
def customers_new():
    if request.method == "GET":
        return render_template("customers/new.html")

    if request.method == "POST":
        # These conditions are enforced in the client side
        if (
            not request.form["cust_no"].isnumeric()
            or len(request.form["name"]) == 0
            or len(request.form["name"]) > 80
            or len(request.form["email"]) == 0
            or len(request.form["email"]) > 254
            or len(request.form["phone"]) > 15
            or len(request.form["address"]) > 255
        ):
            flash(
                "There was an error adding the product. Please try again later.",
                "error",
            )
            return redirect(url_for("products_index"))

        info = {
            "cust_no": request.form["cust_no"],
            "name": request.form["name"],
            "email": request.form["email"],
            "phone": None,
            "address": None,
        }

        if len(request.form["phone"]) != 0:
            info["phone"] = request.form["phone"]

        if len(request.form["address"]) != 0:
            info["address"] = request.form["address"]

        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                try:
                    cur.execute(
                        """
                            INSERT INTO customer VALUES(%(cust_no)s, %(name)s, %(email)s, %(phone)s, %(address)s);
                        """,
                        info,
                    )
                except psycopg.errors.UniqueViolation:
                    flash("A customer with the same number already exists.", "warn")
                except:
                    flash(
                        "There was an error adding the product. Please try again later.",
                        "error",
                    )

                return redirect(url_for("customers_index"))


@app.route("/customers/delete/<cust_no>", methods=("GET", "POST"))
def customers_delete(cust_no):
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            try:
                customer = cur.execute(
                    """
                        SELECT * FROM customer WHERE cust_no = %s;
                    """,
                    (cust_no,),
                ).fetchone()

                if customer is None:
                    flash("Customer unavaillable.", "warn")
                    return redirect(url_for("customers_index"))

                orders = cur.execute(
                    """
                        SELECT DISTINCT
                            order_no,
                            date
                        FROM 
                            customer
                        NATURAL JOIN
                            orders
                        WHERE 
                            cust_no = %s;
                    """,
                    (cust_no,),
                ).fetchall()
            except:
                flash(
                    "There was an error deleting the customer. Please try again later.",
                    "error",
                )
                return redirect(url_for("customers_index"))

    if request.method == "GET":
        return render_template(
            "customers/delete.html", customer=customer, orders=orders
        )

    if request.method == "POST":
        with pool.connection() as conn:
            with conn.cursor(row_factory=namedtuple_row) as cur:
                try:
                    for order in orders:
                        cur.execute(
                            """
                                DELETE FROM contains WHERE order_no = %s;
                            """,
                            (order[0],),
                        )

                        cur.execute(
                            """
                                DELETE FROM process WHERE order_no = %s;
                            """,
                            (order[0],),
                        )

                    cur.execute(
                        """
                            DELETE FROM pay WHERE cust_no = %s;
                        """,
                        (cust_no,),
                    )

                    cur.execute(
                        """
                            DELETE FROM orders WHERE cust_no = %s;
                        """,
                        (cust_no,),
                    )

                    cur.execute(
                        """
                            DELETE FROM customer WHERE cust_no = %s;
                        """,
                        (cust_no,),
                    )
                except:
                    flash(
                        "There was an error deleting the customer. Please try again later.",
                        "error",
                    )
                    return redirect(url_for("customers_index"))

        flash(f"Customer {cust_no} deleted successfully.", "info")
        return redirect(url_for("customers_index"))


if __name__ == "__main__":
    app.run()
