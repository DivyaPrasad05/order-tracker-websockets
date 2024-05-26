# from flask import Flask, render_template, request, session, redirect, url_for, sessions
# from flask_socketio import join_room, leave_room, send, SocketIO
# import random

# app = Flask(__name__)
# app.config["SECRET_KEY"] = "shopify"  # note: see if you can secure this more
# socketio = SocketIO(app)

# trackingService = {}  # store info about the order inside here
# trackingNumberLength = 8


# def generateTrackingNumber(length):
#     if length <= 0:
#         raise ValueError("Number of digits must be greater than 0")

#     lowerBound = 10 ** (length - 1)  # 10^(d - 1)
#     upperBound = (10**length) - 1  # (10^d) -1

#     foundUniqueID = False  # easier readability
#     while not foundUniqueID:
#         trackingID = random.randint(lowerBound, upperBound)  # inclusive of both ends
#         if trackingID not in trackingService:
#             foundUniqueID = True
#     return trackingID


# @app.route(
#     "/", methods=["POST", "GET"]
# )  # setting up a route which is essentially the home page (decorator syntax)
# def loginSeller():
#     session.clear()
#     if request.method == "POST":  # research how this get method works -> basically using a python dictionary
#         displayName = request.form.get("displayName")
#         trackingNumber = request.form.get("trackingNumber")
#         orderUpdates = request.form.get(
#             "orderUpdates", False
#         )  # will return false bc it is a button rather than its typically ''
#         newTracker = request.form.get("newTracker", False)

#         if not displayName:
#             return render_template(
#                 "seller.html",
#                 error="Please enter a display name",
#                 displayName=displayName,
#                 trackingNumber=trackingNumber,
#             )  # we need to pass in the variables so that when the post request is send, it refreshes the page and whatever the user typed in is lost

#         if orderUpdates != False and not trackingNumber:
#             return render_template(
#                 "seller.html",
#                 error="Please enter a tracking number",
#                 displayName=displayName,
#                 trackingNumber=trackingNumber,
#             )

#         order = trackingNumber
#         if newTracker != False:  # creating a new tracking order (seller)
#             order = generateTrackingNumber(trackingNumberLength)
#             trackingService[order] = {"members": 0, "updates": []}
#         elif trackingNumber not in trackingService:  # join a tracking order but it does not exist
#             return render_template(
#                 "seller.html",
#                 error="Order does not exist",
#                 displayName=displayName,
#                 trackingNumber=trackingNumber,
#             )

#         # Note: I will be changing this for a more advanced way of user authentication
#         session["order"] = order
#         session["displayName"] = displayName
#         return redirect(url_for("order"))

#     return render_template("seller.html")  # returns the html page


# @app.route("/order")
# def order():
#     order = session.get("order")
#     if order is None or session.get("displayName") is None or order not in trackingService:
#         return redirect(url_for("loginSeller"))

#     return render_template("order.html", code=order, messages=trackingService[order]["messages"])

# @socketio.on("message")
# def message(data):
#     order = session.get("order")
#     if order not in trackingService:
#         return
#     content = {
#         "displayName": session.get("displayName"),
#         "message": data["data"]
#     }
#     send(content, to=order)
#     trackingService[order]["messages"].append(content)
#     print(f"{session.get('name')} said: {data['data']}")


# @socketio.on("connect")
# def connect(auth):
#     order = session.get("order")
#     print(f" Order: {order}")
#     displayName = session.get("displayName")
#     if not order or not displayName:  # error handeling
#         return
#     if order not in trackingService:
#         leave_room(order)
#         return
#     join_room(order)
#     send({"displayName": displayName, "messages": "is now online"}, to=order)
#     trackingService[order]["members"] += 1
#     print(f"{displayName} has joined to see order updates {order}")
#     print(f"order: {order}")
#     for key, value in trackingService.items():
#         print(f"(Key) {key}: (val) {value}")


# @socketio.on("disconnect")
# def disconnect():
#     order = session.get("order")
#     displayName = session.get("displayName")
#     leave_room(order)

#     if order in trackingService:
#         trackingService[order]["members"] -= 1
#         if trackingService[order]["members"] <= 0:  # might wanna handle this differently
#             del trackingService[order]
#     send({"displayName": displayName, "messages": "is now offline"}, to=order)
#     print(f"{displayName} has left {order}")


# if __name__ == "__main__":
#     socketio.run(app, debug=True)

from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

app = Flask(__name__)
app.config["SECRET_KEY"] = "shopify"
socketio = SocketIO(app)

rooms = {}


def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break

    return code


@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template(
                "home.html", error="Please enter a name.", code=code, name=name
            )

        if join != False and not code:
            return render_template(
                "home.html", error="Please enter a order code.", code=code, name=name
            )

        order = code
        if create != False:
            order = generate_unique_code(4)
            rooms[order] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template(
                "home.html", error="Room does not exist.", code=code, name=name
            )

        session["order"] = order
        session["name"] = name
        return redirect(url_for("order"))

    return render_template("home.html")


@app.route("/order")
def order():
    order = session.get("order")
    if order is None or session.get("name") is None or order not in rooms:
        return redirect(url_for("home"))

    return render_template("order.html", code=order, messages=rooms[order]["messages"])


@socketio.on("message")
def message(data):
    order = session.get("order")
    if order not in rooms:
        return

    content = {"name": session.get("name"), "message": data["data"]}
    send(content, to=order)
    rooms[order]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")


@socketio.on("connect")
def connect(auth):
    order = session.get("order")
    name = session.get("name")
    if not order or not name:
        return
    if order not in rooms:
        leave_room(order)
        return

    join_room(order)
    send({"name": name, "message": "has entered the order"}, to=order)
    rooms[order]["members"] += 1
    print(f"{name} joined order {order}")


@socketio.on("disconnect")
def disconnect():
    order = session.get("order")
    name = session.get("name")
    leave_room(order)

    if order in rooms:
        rooms[order]["members"] -= 1
        if rooms[order]["members"] <= 0:
            del rooms[order]

    send({"name": name, "message": "has left the order"}, to=order)
    print(f"{name} has left the order {order}")


if __name__ == "__main__":
    socketio.run(app, debug=True)
