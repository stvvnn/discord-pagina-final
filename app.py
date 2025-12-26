from flask import Flask, render_template, request, redirect, session
from pymongo import MongoClient
from flask_socketio import SocketIO, emit
import hashlib
import socket

app = Flask(__name__)
app.secret_key = "clave_super_secreta_xd"
socketio = SocketIO(app, cors_allowed_origins="*")

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
            return redirect("/chat")

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

# CHAT GENERAL
@app.route("/chat")
def chat():
    if "user" not in session:
        return redirect("/")

    msgs = messages.find().sort("_id")
    return render_template("chat.html", user=session["user"], messages=msgs)

# BORRAR HISTORIAL
@app.route("/clear", methods=["POST"])
def clear_chat():
    if "user" not in session:
        return redirect("/")

    messages.delete_many({})
    return redirect("/chat")

# SOCKET.IO
@socketio.on("chat_message")
def handle_chat_message(data):
    print(f"MENSAJE DE {data['user']}: {data['msg']}")

    # Creamos el diccionario para la base de datos
    msg_to_save = {
        "user": data["user"],
        "msg": data["msg"]
    }

    # Al insertar, Mongo le meterá el _id a 'msg_to_save'
    messages.insert_one(msg_to_save)

    # AQUÍ ESTÁ EL TRUCO
    # Enviamos un diccionario NUEVO que no tenga el _id de Mongo
    # o convertimos el que ya tenemos a algo seguro.
    msg_to_emit = {
        "user": data["user"],
        "msg": data["msg"]
    }

    # Ahora sí, el emit no va a fallar
    emit("chat_message", msg_to_emit, broadcast=True)

if __name__ == "__main__":
    hostname = socket.gethostname()
    ip_actual = socket.gethostbyname(hostname)
    socketio.run(app, host=ip_actual, port=3000, debug=True)
