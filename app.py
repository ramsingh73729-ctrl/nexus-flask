import requests
import os
from datetime import datetime, timezone

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session
)

from flask_sqlalchemy import SQLAlchemy

from authlib.integrations.flask_client import OAuth

from werkzeug.security import generate_password_hash, check_password_hash

from flask import Flask, render_template, request, jsonify

from flask import Flask, jsonify, render_template, request


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "dev-secret-change-this"
)

database_url = os.environ.get("DATABASE_URL", "sqlite:///nexus.db")

if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql+psycopg://",
        1
    )
    
    
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
oauth = OAuth(app)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash = db.Column(db.String(255), nullable=True)
    google_id = db.Column(
        db.String(255),
        unique=True,
        nullable=True
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )


with app.app_context():
    db.create_all()
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url=(
        "https://accounts.google.com/.well-known/openid-configuration"
    ),
    
    client_kwargs={
        "scope": "openid profile email"
    }
)

GAMES = [
    {
        "number": "01",
        "title": "NEON RIFT",
        "genre": "Roguelite / Action",
        "eyebrow": "Featured drop",
        "players": "24.8K",
        "description": "Bend gravity. Break the loop. A kinetic run through a city that refuses to stay still.",
        "art_class": "art-rift",
    },
    {
        "number": "02",
        "title": "CHROMA RUN",
        "genre": "Arcade / Racing",
        "eyebrow": "New season",
        "players": "18.2K",
        "description": "Every turn changes the track. Hit the light, outrun the static, and own the skyline.",
        "art_class": "art-chroma",
    },
    {
        "number": "03",
        "title": "VOID//WRAITH",
        "genre": "Tactical / Co-op",
        "eyebrow": "Squad up",
        "players": "31.1K",
        "description": "Silence is your strongest weapon. Coordinate the perfect breach across a collapsing frontier.",
        "art_class": "art-void",
    },
    {
        "number": "04",
        "title": "ECHO OPS",
        "genre": "Strategy / PvP",
        "eyebrow": "Community pick",
        "players": "12.4K",
        "description": "Outthink the signal. Build your network, read the room, and rewrite the battlefield.",
        "art_class": "art-echo",
    },
]

CONTACTS = []
DOWNLOADS = 0


@app.get("/")
def home():
    return render_template("index.html", games=GAMES)


@app.get("/health")
def health():
    return jsonify(status="ok", service="nexus-gaming-flask")


@app.get("/api/games")
def games():
   return jsonify(games=GAMES)



@app.post("/api/contact")
def contact():
    payload = request.get_json(silent=True) or request.form.to_dict()
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip()
    message = str(payload.get("message", "")).strip()

    if not name or not email or not message:
        return jsonify(error="Please complete all fields."), 400

    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        return jsonify(error="Please enter a valid email address."), 400

    CONTACTS.append(
        {
            "name": name[:120],
            "email": email[:180],
            "message": message[:4000],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return jsonify(status="ok", message="Signal received. Welcome to the network.")
@app.route("/api/signup", methods=["POST"])
@app.route("/api/register", methods=["POST"])
def api_signup():
    data = request.get_json(silent=True) or {}
    
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    confirm_password = str(data.get("confirm_password") or "")
    turnstile_token = str(data.get("turnstile_token") or "").strip()

    if not name or not email or not password or not confirm_password:
        return jsonify(ok=False, message="All fields are required."), 400

    if "@" not in email:
        return jsonify(ok=False, message="Enter a valid email."), 400

    if password != confirm_password:
        return jsonify(ok=False, message="Passwords do not match."), 400

    if len(password) < 8:
        return jsonify(ok=False, message="Password must be at least 8 characters."), 400

    secret = os.environ.get("TURNSTILE_SECRET_KEY", "").strip()

    if not secret or not turnstile_token:
        return jsonify(ok=False, message="Please complete the security check."), 400

    try:
        response = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": secret, "response": turnstile_token},
            timeout=10
        )
        verification = response.json()
    except (requests.RequestException, ValueError):
        return jsonify(ok=False, message="Security check unavailable."), 502

    if not verification.get("success"):
        return jsonify(ok=False, message="Security check failed."), 400

    if User.query.filter_by(email=email).first():
        return jsonify(ok=False, message="Account already exists."), 409

    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password)
    )

    db.session.add(user)
    db.session.commit()

    return jsonify(
        ok=True,
        message="Account created successfully."
    ), 201
def api_signup():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({
            "ok": False,
            "message": "Name, email, and password are required."
        }), 400

    if len(password) < 8:
        return jsonify({
            "ok": False,
            "message": "Password must be at least 8 characters."
        }), 400

    if User.query.filter_by(email=email).first():
        return jsonify({
            "ok": False,
            "message": "Account already exists."
        }), 409

    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password)
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "ok": True,
        "message": "Account created successfully."
    }), 201
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = User.query.filter_by(email=email).first()

    if not user or not user.password_hash:
        return jsonify({
            "ok": False,
            "message": "Account not found."
        }), 401

    if not check_password_hash(user.password_hash, password):
        return jsonify({
            "ok": False,
            "message": "Invalid email or password."
        }), 401

    session["user_id"] = user.id

    return jsonify({
        "ok": True,
        "message": f"Welcome back, {user.name}!"
    })
@app.route("/auth/google")
def google_login():
    redirect_uri = "https://nexus-flask.onrender.com/auth/google/callback"
    return oauth.google.authorize_redirect(redirect_uri)


@app.route("/auth/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()
    user_info = token["userinfo"]

    email = user_info["email"].strip().lower()
    google_id = user_info["sub"]
    name = user_info.get("name") or email.split("@")[0]

    user = User.query.filter_by(email=email).first()

    if user is None:
        user = User(
            name=name,
            email=email,
            google_id=google_id
        )
        db.session.add(user)
    else:
        user.google_id = user.google_id or google_id

    db.session.commit()
    session["user_id"] = user.id

    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = os.environ.get('WTF_CSRF_SECRET_KEY', os.urandom(32).hex())
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(32).hex())

csrf = CSRFProtect(app)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
@app.route('/profile/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    recent_activity = UserActivity.query.filter_by(user_id=user.id)\
        .order_by(UserActivity.timestamp.desc()).limit(10).all()
    return render_template('profile.html', user=user, activity=recent_activity)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        username = request.form.get('username')
        bio = request.form.get('bio')
        
        # Validate
        if len(username) < 3:
            flash('Username must be at least 3 characters', 'error')
        else:
            current_user.username = username
            current_user.bio = bio
            db.session.commit()
            flash('Profile updated!', 'success')
            return redirect(url_for('profile', username=current_user.username))
    
    return render_template('edit_profile.html')

@app.route('/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save file logic here
    filename = f"avatar_{current_user.id}_{secrets.token_hex(8)}.jpg"
    file.save(os.path.join('static/uploads/avatars', filename))
    
    current_user.avatar = filename
    db.session.commit()
    
    return jsonify({'success': True, 'avatar': filename})
