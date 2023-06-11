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
            count = cur.execute(
                """
                SELECT COUNT(*) FROM product;
                """
            ).fetchone()[0]

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
            flash("There was an error adding the product. Please try again later.")
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
                    flash("A product with the same SKU already exists.")
                except:
                    flash(
                        "There was an error adding the product. Please try again later."
                    )

                return redirect(url_for("products_index"))


@app.route("/products/<sku>", methods=("GET", "POST"))
def products_edit(sku):
    with pool.connection() as conn:
        with conn.cursor(row_factory=namedtuple_row) as cur:
            product = cur.execute(
                """
                        SELECT * FROM product WHERE sku = %s
                    """,
                (sku,),
            ).fetchone()

            if product is None:
                flash("Product unavaillable.")
                return redirect(url_for("products_index"))

    if request.method == "GET":
        return render_template("products/edit.html", product=product)

    if request.method == "POST":
        if (
            len(request.form["description"]) == 0
            or not request.form["price"].replace(".", "", 1).isnumeric()
        ):
            flash("There was an error editing the product. Please try again later.")
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
                        "There was an error editing the product. Please try again later."
                    )

        return redirect(url_for("products_index"))


@app.route("/products/delete/<sku>")
def products_delete(sku):
    pass


if __name__ == "__main__":
    app.run()
