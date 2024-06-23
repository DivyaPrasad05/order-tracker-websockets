from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
from flask_sqlalchemy import SQLAlchemy
import random
from datetime import timedelta
import string
from string import ascii_uppercase

# Setup:

app = Flask(__name__)
# Sets session timeout to 30 minutes
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
app.config["SECRET_KEY"] = "shopify"
socketio = SocketIO(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
db = SQLAlchemy(app)

trackingService = {}
trackingNumberLength = 8


# Models:


class Seller(db.Model):
    __tablename__ = "seller"
    id = db.Column(db.Integer, nullable=False, primary_key=True)
    email = db.Column(db.String(20), unique=True, nullable=True)
    password = db.Column(db.String(20), unique=False, nullable=True)


with app.app_context():
    db.create_all()


# Generates unique order code:


def generateOrderCode(length):
    while True:
        code = "".join(random.choices(string.ascii_uppercase, k=length))
        if code not in trackingService:
            return code


@app.route("/")
def home():
    return render_template("landing.html")


# For debugging:


@app.route("/view_database")
def view_database():
    sellers = Seller.query.all()
    return render_template("view_database.html", sellers=sellers)


@app.route("/signup")
def signup():
    return render_template("sellerSignup.html")


# User Authentication:


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = Seller.query.filter_by(email=email).first()
        if user and user.password == password:
            session["email"] = email
            return redirect(url_for("seller"))
        else:
            error_message = (
                "Login failed, incorrect email or password, please try again."
            )
            return render_template("sellerLogin.html", error_message=error_message)
    return render_template("sellerLogin.html")


@app.route("/signup", methods=["POST"])
def sellerProfile():
    email = request.form.get("email")
    password = request.form.get("password")

    if email != "" and password != "":
        p = Seller(email=email, password=password)
        db.session.add(p)
        db.session.commit()
        return redirect("/login")
    else:
        return redirect("/")


# Seller dashboard:


@app.route("/seller", methods=["POST", "GET"])
def seller():
    if "email" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template(
                "seller.html", error="Please enter a name.", code=code, name=name
            )

        if join != False and not code:
            return render_template(
                "seller.html", error="Please enter a order code.", code=code, name=name
            )

        order = code
        if create != False:
            order = generateOrderCode(trackingNumberLength)
            trackingService[order] = {"members": 0, "messages": []}
        elif code not in trackingService:
            return render_template(
                "seller.html", error="Order does not exist.", code=code, name=name
            )

        session["order"] = order
        session["name"] = name
        return redirect(url_for("order"))

    return render_template("seller.html")


# For buyers


@app.route("/buyerLogin", methods=["POST", "GET"])
def buyer():
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)

        if not name:
            return render_template(
                "buyerDashboard.html",
                error="Please enter a name.",
                code=code,
                name=name,
            )

        if join != False and not code:
            return render_template(
                "buyerDashboard.html",
                error="Please enter a order code.",
                code=code,
                name=name,
            )

        order = code
        if code not in trackingService:
            return render_template(
                "buyerDashboard.html",
                error="Order does not exist.",
                code=code,
                name=name,
            )

        session["order"] = order
        session["name"] = name
        return redirect(url_for("order"))

    return render_template("buyerDashboard.html")


# Websockets


@app.route("/order")
def order():
    order = session.get("order")
    if order is None or session.get("name") is None or order not in trackingService:
        return redirect(url_for("seller"))

    return render_template(
        "order.html", code=order, messages=trackingService[order]["messages"]
    )


@socketio.on("message")
def message(data):
    order = session.get("order")
    if order not in trackingService:
        return

    content = {"name": session.get("name"), "message": data["data"]}
    send(content, to=order)
    trackingService[order]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")


# Websockets connectivity


@socketio.on("connect")
def connect(auth):
    order = session.get("order")
    name = session.get("name")
    if not order or not name:
        return
    if order not in trackingService:
        leave_room(order)
        return

    join_room(order)
    send({"name": name, "message": "has entered the conversation"}, to=order)
    trackingService[order]["members"] += 1
    print(f"{name} joined order {order}")


@socketio.on("disconnect")
def disconnect():
    order = session.get("order")
    name = session.get("name")
    leave_room(order)

    if order in trackingService:
        trackingService[order]["members"] -= 1
        if trackingService[order]["members"] <= 0:
            del trackingService[order]

    send({"name": name, "message": "has left the conversation"}, to=order)


if __name__ == "__main__":
    socketio.run(app, debug=True)
