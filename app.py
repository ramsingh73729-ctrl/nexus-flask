import os
import hashlib
import secrets
import requests
from datetime import datetime, timedelta, timezone
from functools import wraps

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
from flask_migrate import Migrate

from authlib.integrations.flask_client import OAuth

from flask_wtf.csrf import generate_csrf, validate_csrf
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms.validators import ValidationError
from sqlalchemy.exc import IntegrityError


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
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
if os.environ.get("FLASK_ENV") == "production":
    app.config["SESSION_COOKIE_SECURE"] = True

db = SQLAlchemy(app)
migrate = Migrate(app, db)
oauth = OAuth(app)


class User(db.Model):
    __tablename__ = "user"

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

    # Phase 2 progression fields. They are added through the migration in
    # migrations/versions; defaults keep new players at a safe baseline.
    avatar_url = db.Column(db.String(500), nullable=True)
    total_xp = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    level = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    current_login_streak = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    last_activity_date = db.Column(db.Date, nullable=True)
    last_reward_claimed_date = db.Column(db.Date, nullable=True)

    activities = db.relationship(
        "UserActivity",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    play_sessions = db.relationship(
        "PlaySession",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )


class UserActivity(db.Model):
    __tablename__ = "user_activities"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type = db.Column(db.String(60), nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)
    xp_earned = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    idempotency_key = db.Column(db.String(160), nullable=True, unique=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    user = db.relationship("User", back_populates="activities")


class PlaySession(db.Model):
    __tablename__ = "play_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    game_slug = db.Column(db.String(80), nullable=False, index=True)
    session_token_hash = db.Column(db.String(64), nullable=False, unique=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    ended_at = db.Column(db.DateTime(timezone=True), nullable=True)
    score = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    status = db.Column(db.String(20), nullable=False, default="active", server_default="active")
    xp_awarded = db.Column(db.Integer, nullable=False, default=0, server_default="0")

    user = db.relationship("User", back_populates="play_sessions")


# `db.create_all()` is intentionally opt-in. Production schema changes must go
# through `flask db upgrade`; local throwaway development can opt in explicitly.
if os.environ.get("NEXUS_AUTO_CREATE_DB", "").lower() in {"1", "true", "yes"}:
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


TURNSTILE_FAILURE_MESSAGE = (
    "Security check failed or expired. Please complete it again."
)
TURNSTILE_UNAVAILABLE_MESSAGE = (
    "Security check is temporarily unavailable. Please try again."
)
CSRF_FAILURE_MESSAGE = "Your session expired. Refresh the page and try again."


@app.context_processor
def inject_csrf_token():
    """Make a CSRF token available to the browser forms without global API checks."""
    return {"csrf_token": generate_csrf}


def browser_csrf_protected(view):
    """Protect browser requests while keeping cookie-less JSON clients compatible."""

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        session_cookie_name = app.config.get("SESSION_COOKIE_NAME", "session")
        csrf_header = (
            request.headers.get("X-CSRFToken")
            or request.headers.get("X-CSRF-Token")
        )

        # Browser forms rendered by this app carry a session cookie and send the
        # token in a header. Cookie-less API clients keep the existing API shape.
        if request.cookies.get(session_cookie_name) or csrf_header:
            try:
                validate_csrf(csrf_header or request.form.get("csrf_token"))
            except ValidationError:
                return jsonify(ok=False, message=CSRF_FAILURE_MESSAGE), 400

        return view(*args, **kwargs)

    return wrapped_view


def utc_now():
    return datetime.now(timezone.utc)


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user = current_user()
        if user is None:
            if request.path.startswith("/api/"):
                return jsonify(ok=False, message="Please log in to continue."), 401
            return redirect(url_for("home", auth="required"))
        return view(*args, **kwargs)

    return wrapped_view


@app.context_processor
def inject_current_user():
    return {"current_user": current_user()}


def level_for_xp(total_xp):
    return (max(0, int(total_xp)) // 100) + 1


def update_login_streak(user):
    today = utc_now().date()
    if user.last_activity_date == today:
        return

    yesterday = today - timedelta(days=1)
    if user.last_activity_date == yesterday:
        user.current_login_streak = max(1, user.current_login_streak) + 1
    else:
        user.current_login_streak = 1
    user.last_activity_date = today


def user_payload(user):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "total_xp": user.total_xp,
        "level": user.level,
        "current_login_streak": user.current_login_streak,
    }


def leaderboard_payload(limit=10):
    rows = (
        db.session.query(PlaySession, User.name)
        .join(User, PlaySession.user_id == User.id)
        .filter(
            PlaySession.game_slug == "neon-runner",
            PlaySession.status == "completed",
        )
        .order_by(PlaySession.score.desc(), PlaySession.ended_at.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "rank": index,
            "name": name,
            "score": play_session.score,
            "played_at": (
                play_session.ended_at.isoformat()
                if play_session.ended_at else None
            ),
        }
        for index, (play_session, name) in enumerate(rows, start=1)
    ]


def hash_play_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def aware_utc(value):
    """Normalize database datetimes for SQLite and PostgreSQL comparisons."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)

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


@app.get("/dashboard")
@login_required
def dashboard():
    user = current_user()
    activities = (
        UserActivity.query
        .filter_by(user_id=user.id)
        .order_by(UserActivity.created_at.desc())
        .limit(6)
        .all()
    )
    today = utc_now().date()
    return render_template(
        "dashboard.html",
        user=user,
        activities=activities,
        leaderboard=leaderboard_payload(limit=5),
        reward_available=user.last_reward_claimed_date != today,
    )


@app.get("/play/neon-runner")
@login_required
def neon_runner():
    return render_template("neon_runner.html")


@app.get("/health")
def health():
    return jsonify(status="ok", service="nexus-gaming-flask")


@app.get("/api/games")
def games():
    return jsonify(games=GAMES)


@app.get("/api/dashboard")
@login_required
def dashboard_api():
    user = current_user()
    activities = (
        UserActivity.query
        .filter_by(user_id=user.id)
        .order_by(UserActivity.created_at.desc())
        .limit(8)
        .all()
    )
    return jsonify(
        ok=True,
        user=user_payload(user),
        activities=[
            {
                "action_type": item.action_type,
                "description": item.description,
                "xp_earned": item.xp_earned,
                "created_at": item.created_at.isoformat(),
            }
            for item in activities
        ],
        leaderboard=leaderboard_payload(limit=5),
        reward_available=user.last_reward_claimed_date != utc_now().date(),
    )


@app.get("/api/leaderboard")
def leaderboard_api():
    game = request.args.get("game", "neon-runner").strip().lower()
    if game != "neon-runner":
        return jsonify(ok=False, message="Leaderboard is not available for this game."), 404
    return jsonify(ok=True, game=game, entries=leaderboard_payload(limit=10))



@app.post("/api/contact")
@browser_csrf_protected
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


@app.post("/api/download")
@browser_csrf_protected
def download():
    global DOWNLOADS
    DOWNLOADS += 1
    return jsonify(
        status="ok",
        message="NEXUS portal queued. Connect your launcher to continue.",
    ), 202


@app.route("/api/signup", methods=["POST"])
@app.route("/api/register", methods=["POST"])
@browser_csrf_protected
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

    if not turnstile_token:
        return jsonify(ok=False, message=TURNSTILE_FAILURE_MESSAGE), 400

    if not secret:
        app.logger.error("Turnstile secret is not configured")
        return jsonify(ok=False, message=TURNSTILE_UNAVAILABLE_MESSAGE), 503

    try:
        response = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": secret, "response": turnstile_token},
            timeout=8
        )
        response.raise_for_status()
        verification = response.json()
    except requests.Timeout:
        app.logger.warning("Turnstile Siteverify request timed out")
        return jsonify(ok=False, message=TURNSTILE_UNAVAILABLE_MESSAGE), 502
    except requests.RequestException as error:
        app.logger.warning(
            "Turnstile Siteverify request failed: %s",
            error.__class__.__name__,
        )
        return jsonify(ok=False, message=TURNSTILE_UNAVAILABLE_MESSAGE), 502
    except ValueError:
        app.logger.warning("Turnstile Siteverify returned invalid JSON")
        return jsonify(ok=False, message=TURNSTILE_UNAVAILABLE_MESSAGE), 502

    if not verification.get("success"):
        error_codes = verification.get("error-codes") or []
        safe_codes = ", ".join(str(code) for code in error_codes[:5])
        app.logger.info(
            "Turnstile rejected signup token: %s",
            safe_codes or "unknown",
        )
        return jsonify(ok=False, message=TURNSTILE_FAILURE_MESSAGE), 400

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


@app.route("/api/login", methods=["POST"])
@browser_csrf_protected
def api_login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

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
    update_login_streak(user)
    db.session.commit()

    return jsonify({
        "ok": True,
        "message": f"Welcome back, {user.name}!"
    })


@app.post("/api/daily-reward")
@login_required
@browser_csrf_protected
def daily_reward():
    user = current_user()
    today = utc_now().date()

    if user.last_reward_claimed_date == today:
        return jsonify(
            ok=True,
            claimed=False,
            message="Daily reward already claimed. Come back tomorrow.",
            user=user_payload(user),
        )

    reward_xp = 25
    activity_key = f"daily-reward:{user.id}:{today.isoformat()}"
    user.total_xp += reward_xp
    user.level = level_for_xp(user.total_xp)
    user.last_reward_claimed_date = today
    db.session.add(
        UserActivity(
            user_id=user.id,
            action_type="daily_reward",
            description="Daily reward claimed",
            xp_earned=reward_xp,
            idempotency_key=activity_key,
        )
    )

    try:
        db.session.commit()
    except IntegrityError:
        # A second request arriving at the same time is treated as an already
        # claimed reward rather than awarding XP twice.
        db.session.rollback()
        user = current_user()
        return jsonify(
            ok=True,
            claimed=False,
            message="Daily reward already claimed. Come back tomorrow.",
            user=user_payload(user),
        )

    return jsonify(
        ok=True,
        claimed=True,
        message="Daily reward claimed: +25 XP.",
        user=user_payload(user),
    )


@app.post("/api/play/neon-runner/start")
@login_required
@browser_csrf_protected
def start_neon_runner():
    user = current_user()
    now = utc_now()
    expires_at = now + timedelta(minutes=3)
    token = secrets.token_urlsafe(32)
    play_session = PlaySession(
        user_id=user.id,
        game_slug="neon-runner",
        session_token_hash=hash_play_token(token),
        started_at=now,
        expires_at=expires_at,
    )
    db.session.add(play_session)
    db.session.commit()

    return jsonify(
        ok=True,
        game="neon-runner",
        session_token=token,
        expires_at=expires_at.isoformat(),
    ), 201


@app.post("/api/play/neon-runner/score")
@login_required
@browser_csrf_protected
def submit_neon_runner_score():
    user = current_user()
    data = request.get_json(silent=True) or {}
    token = str(data.get("session_token") or "").strip()
    raw_score = data.get("score")

    if not token or isinstance(raw_score, bool):
        return jsonify(ok=False, message="This game session is invalid."), 400

    try:
        submitted_score = int(raw_score)
    except (TypeError, ValueError):
        return jsonify(ok=False, message="This score is invalid."), 400

    if submitted_score < 0 or submitted_score > 1_000_000:
        return jsonify(ok=False, message="This score could not be verified."), 400

    play_session = (
        PlaySession.query
        .filter_by(
            user_id=user.id,
            game_slug="neon-runner",
            session_token_hash=hash_play_token(token),
        )
        .first()
    )
    if play_session is None:
        return jsonify(ok=False, message="This game session is invalid."), 404

    if play_session.status != "active":
        return jsonify(
            ok=False,
            message="This run has already been submitted."
        ), 409

    now = utc_now()
    if now > aware_utc(play_session.expires_at):
        play_session.status = "expired"
        play_session.ended_at = now
        db.session.commit()
        return jsonify(
            ok=False,
            message="This run expired. Start a new run to try again."
        ), 400

    elapsed_seconds = max(
        0,
        (aware_utc(play_session.expires_at) - aware_utc(play_session.started_at)).total_seconds()
        - (aware_utc(play_session.expires_at) - now).total_seconds(),
    )
    max_plausible_score = max(200, int(elapsed_seconds * 180) + 200)
    if submitted_score > max_plausible_score:
        return jsonify(ok=False, message="This score could not be verified."), 400

    accepted_score = min(submitted_score, max_plausible_score)
    xp_awarded = min(50, accepted_score // 25)
    play_session.score = accepted_score
    play_session.status = "completed"
    play_session.ended_at = now
    play_session.xp_awarded = xp_awarded
    user.total_xp += xp_awarded
    user.level = level_for_xp(user.total_xp)
    db.session.add(
        UserActivity(
            user_id=user.id,
            action_type="played_game",
            description=f"Neon Runner run complete — {accepted_score} points",
            xp_earned=xp_awarded,
            idempotency_key=f"play-session:{play_session.id}",
        )
    )
    db.session.commit()

    return jsonify(
        ok=True,
        score=accepted_score,
        xp_awarded=xp_awarded,
        user=user_payload(user),
        message="Run secured on the NEXUS board.",
    )
@app.route("/auth/google")
def google_login():
    redirect_uri = url_for("google_callback", _external=True)
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

    update_login_streak(user)
    db.session.commit()
    session["user_id"] = user.id

    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
