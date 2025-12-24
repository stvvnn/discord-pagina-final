from flask import Flask, render_template, request, redirect, session
from pymongo import MongoClient
from flask_socketio import SocketIO, emit
import hashlib

app = Flask(__name__)
app.secret_key = "clave_super_secreta_xd"
socketio = SocketIO(app)

# MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client.discord_app
users = db.users
messages = db.messages

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

# LOGIN
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = hash_pass(request.form["password"])

        user = users.find_one({
            "username": username,
            "password": password
        })

        if user:
            session["user"] = username
            return redirect("/dashboard")

    return render_template("login.html")

# REGISTER
@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    password = hash_pass(request.form["password"])

    if not users.find_one({"username": username}):
        users.insert_one({
            "username": username,
            "password": password
        })

    return redirect("/")

# DASHBOARD
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template("dashboard.html", user=session["user"])

# CHAT POR CANAL
@app.route("/chat/<channel>")
def chat(channel):
    if "user" not in session:
        return redirect("/")

    msgs = messages.find({"channel": channel}).sort("_id")
    return render_template(
        "chat.html",
        user=session["user"],
        messages=msgs,
        channel=channel
    )

# BORRAR HISTORIAL DEL CANAL
@app.route("/clear/<channel>", methods=["POST"])
def clear_channel(channel):
    if "user" not in session:
        return redirect("/")

    messages.delete_many({"channel": channel})
    return redirect(f"/chat/{channel}")

# SOCKET.IO → MENSAJES
@socketio.on("chat_message")
def handle_chat_message(data):
    if "user" not in session:
        return

    msg_data = {
        "user": data["user"],
        "msg": data["msg"],
        "channel": data["channel"]
    }

    messages.insert_one(msg_data)

    emit("chat_message", msg_data, broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=3000, debug=True)
