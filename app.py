from flask import Flask, render_template, request, redirect, session
from flask_socketio import SocketIO, emit, join_room
from pymongo import MongoClient
import socket

app = Flask(__name__)
app.secret_key = "supersecretkey"

socketio = SocketIO(app, manage_session=True)

# ---- Mongo ----
client = MongoClient("mongodb://localhost:27017/")
db = client["discord_app"]
users = db["users"]
messages = db["messages"]

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return "Faltan datos"

        if users.find_one({"username": username}):
            return "El usuario ya existe"

        users.insert_one({
            "username": username,
            "password": password
        })

        # return
        return redirect("/")

    return render_template("register.html")

# ---- Chats ----
chats = ["general"]

# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        if username:
            session["user"] = username
            return redirect("/chat/general")
    return render_template("login.html")

# ---------- CHAT ----------
@app.route("/chat/<chat_name>")
def chat(chat_name):
    if "user" not in session:
        return redirect("/")

    if chat_name not in chats:
        return redirect("/chat/general")

    chat_messages = messages.find({"chat": chat_name})

    return render_template(
        "chat.html",
        user=session["user"],
        chat=chat_name,
        chats=chats,
        messages=chat_messages
    )

# ---------- CREAR CHAT ----------
@app.route("/create_chat", methods=["POST"])
def create_chat():
    if "user" not in session:
        return redirect("/")

    chat_name = request.form.get("chat_name")

    if chat_name and chat_name not in chats:
        chats.append(chat_name)

    return redirect(f"/chat/{chat_name}")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- SOCKET ----------
@socketio.on("join")
def on_join(data):
    join_room(data["chat"])

@socketio.on("chat_message")
def handle_message(data):
    if "user" not in session:
        return

    msg_to_save = {
        "user": session["user"],
        "msg": data["msg"],
        "chat": data["chat"]
    }

    messages.insert_one(msg_to_save)

    emit(
        "chat_message",
        {
            "user": session["user"],
            "msg": data["msg"]
        },
        room=data["chat"]
    )

@app.route("/clear/<chat_name>", methods=["POST"])
def clear_chat(chat_name):
    if "user" not in session:
        return redirect("/")

    messages.delete_many({"chat": chat_name})
    return redirect(f"/chat/{chat_name}")


# ---------- MAIN ----------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=3000, debug=True)
