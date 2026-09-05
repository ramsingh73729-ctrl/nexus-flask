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
from sqlalchemy import CheckConstraint, Index, UniqueConstraint, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

running_on_render = os.environ.get("RENDER", "").lower() in {
    "1",
    "true",
    "yes",
}
is_production = os.environ.get("FLASK_ENV") == "production"
configured_secret_key = os.environ.get("SECRET_KEY", "").strip()
if not configured_secret_key:
    if is_production or running_on_render:
        raise RuntimeError("SECRET_KEY must be configured in the environment.")
    configured_secret_key = secrets.token_urlsafe(32)
app.config["SECRET_KEY"] = configured_secret_key

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

    # Module 1 progression fields. They are added through the migration in
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
    game_favorites = db.relationship(
        "GameFavorite",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    game_reviews = db.relationship(
        "GameReview",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    recent_game_plays = db.relationship(
        "RecentGamePlay",
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


class GameFavorite(db.Model):
    __tablename__ = "game_favorites"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    game_slug = db.Column(db.String(80), nullable=False, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    user = db.relationship("User", back_populates="game_favorites")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "game_slug",
            name="uq_game_favorites_user_game",
        ),
        Index("ix_game_favorites_user_created", "user_id", "created_at"),
    )


class GameReview(db.Model):
    __tablename__ = "game_reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    game_slug = db.Column(db.String(80), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)
    body = db.Column(db.String(1000), nullable=False, default="", server_default="")
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = db.relationship("User", back_populates="game_reviews")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "game_slug",
            name="uq_game_reviews_user_game",
        ),
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="ck_game_reviews_rating_range",
        ),
        Index("ix_game_reviews_game_updated", "game_slug", "updated_at"),
    )


class RecentGamePlay(db.Model):
    __tablename__ = "recent_game_plays"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    game_slug = db.Column(db.String(80), nullable=False, index=True)
    played_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    play_count = db.Column(db.Integer, nullable=False, default=1, server_default="1")

    user = db.relationship("User", back_populates="recent_game_plays")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "game_slug",
            name="uq_recent_game_plays_user_game",
        ),
        Index("ix_recent_game_plays_user_played", "user_id", "played_at"),
    )


# `db.create_all()` is intentionally opt-in. Production schema changes must go
# through `flask db upgrade`; local throwaway development can opt in explicitly.
if (
    os.environ.get("NEXUS_AUTO_CREATE_DB", "").lower() in {"1", "true", "yes"}
    and not is_production
    and not running_on_render
):
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
TURNSTILE_SITE_KEY = (
    os.environ.get("TURNSTILE_SITE_KEY", "").strip()
)


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
    try:
        return db.session.get(User, user_id)
    except SQLAlchemyError:
        # A stale session must not turn the public landing page into a 500.
        # This can happen briefly when a deployment has not applied a schema
        # migration yet; clear only the invalid browser session and let the
        # user continue as a signed-out visitor.
        db.session.rollback()
        session.pop("user_id", None)
        app.logger.warning("Cleared an unreadable browser user session.")
        return None


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


RANK_TIERS = (
    (0, "Recruit"),
    (250, "Scout"),
    (750, "Vanguard"),
    (1_500, "Elite"),
    (3_000, "Arena Legend"),
    (6_000, "Nexus Master"),
)


def rank_for_xp(total_xp):
    safe_xp = max(0, int(total_xp))
    rank = RANK_TIERS[0][1]
    for threshold, title in RANK_TIERS:
        if safe_xp < threshold:
            break
        rank = title
    return rank


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
        "rank": rank_for_xp(user.total_xp),
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


# Module 2 keeps the original landing-page catalog intact and layers a small,
# server-owned discovery catalog on top of it. The catalog is intentionally
# static for now; player-owned data (favorites, reviews, and recent plays) is
# stored separately so this module does not require a risky content migration.
RADAR_GAME_META = {
    "neon-rift": {
        "genres": ["Roguelite", "Action"],
        "tags": ["gravity", "solo", "runs"],
        "platform": "PC / Cloud",
        "developer": "NEXUS Originals",
        "status": "Featured drop",
        "popularity": 24800,
        "release_order": 1,
        "playable": False,
    },
    "chroma-run": {
        "genres": ["Arcade", "Racing"],
        "tags": ["speed", "neon", "time trials"],
        "platform": "Browser / PC",
        "developer": "Luma Circuit",
        "status": "New season",
        "popularity": 18200,
        "release_order": 2,
        "playable": False,
    },
    "void-wraith": {
        "genres": ["Tactical", "Co-op"],
        "tags": ["stealth", "squad", "frontier"],
        "platform": "PC / Console",
        "developer": "Black Signal Lab",
        "status": "Squad up",
        "popularity": 31100,
        "release_order": 3,
        "playable": False,
    },
    "echo-ops": {
        "genres": ["Strategy", "PvP"],
        "tags": ["network", "tactics", "competitive"],
        "platform": "Browser / PC",
        "developer": "Echo Division",
        "status": "Community pick",
        "popularity": 12400,
        "release_order": 4,
        "playable": False,
    },
}

NEON_RUNNER_GAME = {
    "number": "05",
    "slug": "neon-runner",
    "title": "NEON RUNNER",
    "genre": "Arcade / Endless",
    "genres": ["Arcade", "Endless"],
    "tags": ["playable", "reflex", "score chase"],
    "eyebrow": "Playable now",
    "status": "Playable now",
    "players": "LIVE",
    "popularity": 0,
    "release_order": 5,
    "description": "Dodge the signal, survive the grid, and lock your best run onto the NEXUS board.",
    "art_class": "art-rift",
    "platform": "Browser",
    "developer": "NEXUS Arcade",
    "playable": True,
}


def _slug_for_title(title):
    return {
        "NEON RIFT": "neon-rift",
        "CHROMA RUN": "chroma-run",
        "VOID//WRAITH": "void-wraith",
        "ECHO OPS": "echo-ops",
    }.get(title)


def build_radar_catalog():
    catalog = []
    for game in GAMES:
        slug = _slug_for_title(game["title"])
        if not slug or slug not in RADAR_GAME_META:
            continue
        item = dict(game)
        item["slug"] = slug
        item.update(RADAR_GAME_META[slug])
        catalog.append(item)
    catalog.append(dict(NEON_RUNNER_GAME))
    return catalog


RADAR_GAMES = build_radar_catalog()
RADAR_SORTS = {"newest", "popular", "rated"}
RADAR_PAGE_SIZE = 6
RADAR_MAX_PAGE_SIZE = 12


def get_radar_game(slug):
    normalized_slug = str(slug or "").strip().lower()
    return next(
        (game for game in RADAR_GAMES if game["slug"] == normalized_slug),
        None,
    )


def parse_positive_int(value, default, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(parsed, maximum))


def game_review_stats(slugs=None):
    query = db.session.query(
        GameReview.game_slug,
        func.avg(GameReview.rating),
        func.count(GameReview.id),
    ).group_by(GameReview.game_slug)
    if slugs is not None:
        safe_slugs = [str(slug) for slug in slugs]
        if not safe_slugs:
            return {}
        query = query.filter(GameReview.game_slug.in_(safe_slugs))

    return {
        slug: {
            "rating": round(float(average), 1) if average is not None else None,
            "rating_count": int(count),
        }
        for slug, average, count in query.all()
    }


def favorite_slugs_for_user(user_id):
    return {
        row.game_slug
        for row in GameFavorite.query.with_entities(GameFavorite.game_slug)
        .filter_by(user_id=user_id)
        .all()
    }


def radar_game_payload(game, review_stats=None, favorite=False):
    stats = (review_stats or {}).get(game["slug"], {})
    return {
        "number": game["number"],
        "slug": game["slug"],
        "title": game["title"],
        "genre": game["genre"],
        "genres": list(game["genres"]),
        "tags": list(game["tags"]),
        "eyebrow": game["eyebrow"],
        "status": game["status"],
        "players": game["players"],
        "description": game["description"],
        "art_class": game["art_class"],
        "platform": game["platform"],
        "developer": game["developer"],
        "playable": bool(game["playable"]),
        "rating": stats.get("rating"),
        "rating_count": stats.get("rating_count", 0),
        "is_favorite": bool(favorite),
    }


def radar_listing(query_text="", genre="", sort="newest", page=1, per_page=RADAR_PAGE_SIZE, user_id=None):
    safe_query = str(query_text or "").strip()[:80]
    safe_genre = str(genre or "").strip()[:40]
    safe_sort = str(sort or "newest").strip().lower()
    if safe_sort not in RADAR_SORTS:
        safe_sort = "newest"

    filtered = []
    query_casefolded = safe_query.casefold()
    genre_casefolded = safe_genre.casefold()
    for game in RADAR_GAMES:
        searchable = " ".join(
            [game["title"], game["genre"], *game["genres"], *game["tags"]]
        ).casefold()
        if query_casefolded and query_casefolded not in searchable:
            continue
        if genre_casefolded and genre_casefolded not in {
            item.casefold() for item in game["genres"]
        }:
            continue
        filtered.append(game)

    review_stats = game_review_stats(game["slug"] for game in filtered)
    if safe_sort == "popular":
        filtered.sort(key=lambda game: game["popularity"], reverse=True)
    elif safe_sort == "rated":
        filtered.sort(
            key=lambda game: (
                review_stats.get(game["slug"], {}).get("rating") is not None,
                review_stats.get(game["slug"], {}).get("rating", -1),
                review_stats.get(game["slug"], {}).get("rating_count", 0),
                game["release_order"],
            ),
            reverse=True,
        )
    else:
        filtered.sort(key=lambda game: game["release_order"], reverse=True)

    total = len(filtered)
    total_pages = max(1, (total + per_page - 1) // per_page)
    safe_page = max(1, min(int(page), total_pages))
    start = (safe_page - 1) * per_page
    page_games = filtered[start : start + per_page]
    favorite_slugs = favorite_slugs_for_user(user_id) if user_id else set()
    return {
        "games": [
            radar_game_payload(
                game,
                review_stats,
                favorite=game["slug"] in favorite_slugs,
            )
            for game in page_games
        ],
        "pagination": {
            "page": safe_page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages if total else 0,
        },
        "query": safe_query,
        "genre": safe_genre,
        "sort": safe_sort,
    }


def review_payload(review):
    return {
        "id": review.id,
        "name": review.user.name if review.user else "NEXUS player",
        "rating": review.rating,
        "body": review.body,
        "created_at": review.updated_at.isoformat(),
    }


def recent_game_payload(row, review_stats=None):
    game = get_radar_game(row.game_slug)
    if not game:
        return None
    payload = radar_game_payload(game, review_stats)
    payload["played_at"] = row.played_at.isoformat()
    payload["play_count"] = row.play_count
    return payload


def radar_library_payload(user_id, favorite_limit=6, recent_limit=6):
    stats = game_review_stats()
    favorite_query = GameFavorite.query.filter_by(user_id=user_id)
    favorites = (
        favorite_query
        .order_by(GameFavorite.created_at.desc())
        .limit(favorite_limit)
        .all()
    )
    recent_rows = (
        RecentGamePlay.query
        .filter_by(user_id=user_id)
        .order_by(RecentGamePlay.played_at.desc())
        .limit(recent_limit)
        .all()
    )
    return {
        "favorite_count": favorite_query.count(),
        "favorites": [
            radar_game_payload(get_radar_game(row.game_slug), stats, favorite=True)
            for row in favorites
            if get_radar_game(row.game_slug)
        ],
        "recently_played": [
            payload
            for row in recent_rows
            if (payload := recent_game_payload(row, stats)) is not None
        ],
    }


def touch_recent_game(user_id, game_slug):
    if not get_radar_game(game_slug):
        return
    row = RecentGamePlay.query.filter_by(
        user_id=user_id,
        game_slug=game_slug,
    ).first()
    if row:
        row.played_at = utc_now()
        row.play_count = min(row.play_count + 1, 2_147_483_647)
        return
    db.session.add(
        RecentGamePlay(
            user_id=user_id,
            game_slug=game_slug,
            played_at=utc_now(),
        )
    )

CONTACTS = []
DOWNLOADS = 0


@app.get("/")
def home():
    return render_template(
        "index.html",
        games=GAMES,
        turnstile_site_key=TURNSTILE_SITE_KEY,
    )


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
    library = radar_library_payload(user.id)
    return render_template(
        "dashboard.html",
        user=user,
        activities=activities,
        leaderboard=leaderboard_payload(limit=5),
        reward_available=user.last_reward_claimed_date != today,
        rank=rank_for_xp(user.total_xp),
        favorite_count=library["favorite_count"],
        favorite_games=library["favorites"],
        recently_played=library["recently_played"],
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
    library = radar_library_payload(user.id)
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
        favorite_count=library["favorite_count"],
        favorites=library["favorites"],
        recently_played=library["recently_played"],
    )


@app.get("/api/leaderboard")
def leaderboard_api():
    game = request.args.get("game", "neon-runner").strip().lower()
    if game != "neon-runner":
        return jsonify(ok=False, message="Leaderboard is not available for this game."), 404
    return jsonify(ok=True, game=game, entries=leaderboard_payload(limit=10))


@app.get("/games")
def game_radar():
    user = current_user()
    listing = radar_listing(
        query_text=request.args.get("q", ""),
        genre=request.args.get("genre", ""),
        sort=request.args.get("sort", "newest"),
        page=parse_positive_int(request.args.get("page"), 1, 10_000),
        per_page=RADAR_PAGE_SIZE,
        user_id=user.id if user else None,
    )
    genres = sorted(
        {
            genre_name
            for game in RADAR_GAMES
            for genre_name in game["genres"]
        }
    )
    return render_template(
        "game_radar.html",
        games=listing["games"],
        pagination=listing["pagination"],
        query=listing["query"],
        selected_genre=listing["genre"],
        selected_sort=listing["sort"],
        genres=genres,
    )


@app.get("/games/<slug>")
def game_detail(slug):
    game = get_radar_game(slug)
    if not game:
        return render_template("game_not_found.html", slug=slug), 404

    user = current_user()
    stats = game_review_stats([game["slug"]])
    reviews = (
        GameReview.query
        .filter_by(game_slug=game["slug"])
        .order_by(GameReview.updated_at.desc())
        .limit(20)
        .all()
    )
    related = [
        radar_game_payload(other, game_review_stats([other["slug"]]))
        for other in RADAR_GAMES
        if other["slug"] != game["slug"]
        and set(other["genres"]).intersection(game["genres"])
    ][:3]
    user_review = None
    is_favorite = False
    if user:
        user_review = GameReview.query.filter_by(
            user_id=user.id,
            game_slug=game["slug"],
        ).first()
        is_favorite = GameFavorite.query.filter_by(
            user_id=user.id,
            game_slug=game["slug"],
        ).first() is not None

    return render_template(
        "game_detail.html",
        game=radar_game_payload(game, stats, favorite=is_favorite),
        reviews=reviews,
        related_games=related,
        user_review=user_review,
        is_favorite=is_favorite,
    )


@app.get("/api/radar/games")
def radar_games_api():
    user = current_user()
    listing = radar_listing(
        query_text=request.args.get("q", ""),
        genre=request.args.get("genre", ""),
        sort=request.args.get("sort", "newest"),
        page=parse_positive_int(request.args.get("page"), 1, 10_000),
        per_page=parse_positive_int(
            request.args.get("per_page"),
            RADAR_PAGE_SIZE,
            RADAR_MAX_PAGE_SIZE,
        ),
        user_id=user.id if user else None,
    )
    return jsonify(ok=True, **listing)


@app.get("/api/games/<slug>")
def game_detail_api(slug):
    game = get_radar_game(slug)
    if not game:
        return jsonify(ok=False, message="Game signal not found."), 404

    user = current_user()
    stats = game_review_stats([game["slug"]])
    reviews = (
        GameReview.query
        .filter_by(game_slug=game["slug"])
        .order_by(GameReview.updated_at.desc())
        .limit(20)
        .all()
    )
    favorite = bool(
        user
        and GameFavorite.query.filter_by(
            user_id=user.id,
            game_slug=game["slug"],
        ).first()
    )
    return jsonify(
        ok=True,
        game=radar_game_payload(game, stats, favorite=favorite),
        reviews=[review_payload(review) for review in reviews],
    )


@app.get("/api/library")
@login_required
def library_api():
    user = current_user()
    return jsonify(ok=True, **radar_library_payload(user.id))


@app.route("/api/games/<slug>/favorite", methods=["POST", "DELETE"])
@login_required
@browser_csrf_protected
def game_favorite_api(slug):
    game = get_radar_game(slug)
    if not game:
        return jsonify(ok=False, message="Game signal not found."), 404

    user = current_user()
    favorite = GameFavorite.query.filter_by(
        user_id=user.id,
        game_slug=game["slug"],
    ).first()

    if request.method == "DELETE":
        if favorite:
            db.session.delete(favorite)
            try:
                db.session.commit()
            except SQLAlchemyError as error:
                db.session.rollback()
                app.logger.error(
                    "Favorite removal failed: %s",
                    error.__class__.__name__,
                )
                return jsonify(
                    ok=False,
                    message="Your vault could not be updated right now.",
                ), 503
        return jsonify(
            ok=True,
            favorite=False,
            message="Removed from your vault.",
        )

    if favorite:
        return jsonify(
            ok=True,
            favorite=True,
            message="Already in your vault.",
        )

    db.session.add(GameFavorite(user_id=user.id, game_slug=game["slug"]))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(
            ok=True,
            favorite=True,
            message="Already in your vault.",
        )
    except SQLAlchemyError as error:
        db.session.rollback()
        app.logger.error(
            "Favorite save failed: %s",
            error.__class__.__name__,
        )
        return jsonify(
            ok=False,
            message="Your vault could not be updated right now.",
        ), 503

    return jsonify(
        ok=True,
        favorite=True,
        message="Saved to your NEXUS vault.",
    ), 201


@app.route("/api/games/<slug>/review", methods=["POST", "PUT", "DELETE"])
@login_required
@browser_csrf_protected
def game_review_api(slug):
    game = get_radar_game(slug)
    if not game:
        return jsonify(ok=False, message="Game signal not found."), 404

    user = current_user()
    review = GameReview.query.filter_by(
        user_id=user.id,
        game_slug=game["slug"],
    ).first()

    if request.method == "DELETE":
        if review:
            db.session.delete(review)
            try:
                db.session.commit()
            except SQLAlchemyError as error:
                db.session.rollback()
                app.logger.error(
                    "Review removal failed: %s",
                    error.__class__.__name__,
                )
                return jsonify(
                    ok=False,
                    message="Your review could not be removed right now.",
                ), 503
        return jsonify(ok=True, review=None, message="Review removed.")

    data = request.get_json(silent=True) or {}
    raw_rating = data.get("rating")
    if isinstance(raw_rating, bool) or raw_rating is None:
        return jsonify(ok=False, message="Choose a rating from 1 to 5."), 400
    if isinstance(raw_rating, float) and not raw_rating.is_integer():
        return jsonify(ok=False, message="Choose a rating from 1 to 5."), 400
    try:
        rating = int(raw_rating)
    except (TypeError, ValueError):
        return jsonify(ok=False, message="Choose a rating from 1 to 5."), 400
    if rating < 1 or rating > 5:
        return jsonify(ok=False, message="Choose a rating from 1 to 5."), 400

    raw_body = data.get("body", "")
    if raw_body is None:
        raw_body = ""
    if not isinstance(raw_body, str):
        return jsonify(ok=False, message="Review text is invalid."), 400
    body = raw_body.strip()
    if len(body) > 1000:
        return jsonify(ok=False, message="Review must be 1,000 characters or less."), 400

    created = review is None
    if review is None:
        review = GameReview(
            user_id=user.id,
            game_slug=game["slug"],
            rating=rating,
            body=body,
        )
        db.session.add(review)
    else:
        review.rating = rating
        review.body = body
        review.updated_at = utc_now()

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(
            ok=False,
            message="Your review changed at the same time. Please try again.",
        ), 409
    except SQLAlchemyError as error:
        db.session.rollback()
        app.logger.error(
            "Review save failed: %s",
            error.__class__.__name__,
        )
        return jsonify(
            ok=False,
            message="Your review could not be saved right now.",
        ), 503

    stats = game_review_stats([game["slug"]])
    return jsonify(
        ok=True,
        review=review_payload(review),
        rating=stats.get(game["slug"], {}).get("rating"),
        rating_count=stats.get(game["slug"], {}).get("rating_count", 0),
        message="Your signal is live on this game page.",
    ), (201 if created else 200)



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

    if len(name) > 120 or len(email) > 255:
        return jsonify(ok=False, message="Name or email is too long."), 400

    if "@" not in email:
        return jsonify(ok=False, message="Enter a valid email."), 400

    if password != confirm_password:
        return jsonify(ok=False, message="Passwords do not match."), 400

    if len(password) < 8:
        return jsonify(ok=False, message="Password must be at least 8 characters."), 400

    if len(password) > 128:
        return jsonify(ok=False, message="Password is too long."), 400

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

    if not isinstance(verification, dict):
        app.logger.warning("Turnstile Siteverify returned an unexpected payload")
        return jsonify(ok=False, message=TURNSTILE_UNAVAILABLE_MESSAGE), 502

    if not verification.get("success"):
        error_codes = verification.get("error-codes") or []
        safe_codes = ", ".join(str(code) for code in error_codes[:5])
        app.logger.info(
            "Turnstile rejected signup token: %s",
            safe_codes or "unknown",
        )
        return jsonify(
            ok=False,
            message=TURNSTILE_FAILURE_MESSAGE,
            turnstile_reset=True,
        ), 400

    if User.query.filter_by(email=email).first():
        return jsonify(
            ok=False,
            message="Account already exists.",
            turnstile_reset=True,
        ), 409

    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password)
    )

    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(
            ok=False,
            message="Account already exists.",
            turnstile_reset=True,
        ), 409
    except SQLAlchemyError as error:
        db.session.rollback()
        app.logger.error(
            "Signup database write failed: %s",
            error.__class__.__name__,
        )
        return jsonify(
            ok=False,
            message="Account could not be created right now. Please try again.",
            turnstile_reset=True,
        ), 503

    return jsonify(
        ok=True,
        message="Account created successfully.",
        turnstile_reset=True,
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
    # Serialize claims on databases that support row-level locks. The unique
    # activity key below remains the idempotency backstop for SQLite and races
    # that reach the database at the same time.
    user = (
        db.session.query(User)
        .filter_by(id=user.id)
        .with_for_update()
        .first()
    )
    if user is None:
        session.pop("user_id", None)
        return jsonify(ok=False, message="Please log in to continue."), 401
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
        if user is None:
            return jsonify(ok=False, message="Please log in to continue."), 401
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
    try:
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        app.logger.error(
            "Play session creation failed: %s",
            error.__class__.__name__,
        )
        return jsonify(
            ok=False,
            message="A secure run could not be started right now. Please try again.",
        ), 503

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

    if not isinstance(raw_score, (int, float, str)):
        return jsonify(ok=False, message="This score is invalid."), 400

    if isinstance(raw_score, float) and not raw_score.is_integer():
        return jsonify(ok=False, message="This score is invalid."), 400

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
        .with_for_update()
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
        try:
            db.session.commit()
        except SQLAlchemyError as error:
            db.session.rollback()
            app.logger.error(
                "Expired play session update failed: %s",
                error.__class__.__name__,
            )
            return jsonify(
                ok=False,
                message="This run could not be checked right now. Please try again.",
            ), 503
        return jsonify(
            ok=False,
            message="This run expired. Start a new run to try again."
        ), 400

    elapsed_seconds = max(
        0,
        (now - aware_utc(play_session.started_at)).total_seconds(),
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
    touch_recent_game(user.id, "neon-runner")
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(
            ok=False,
            message="This run has already been submitted.",
        ), 409
    except SQLAlchemyError as error:
        db.session.rollback()
        app.logger.error(
            "Score database write failed: %s",
            error.__class__.__name__,
        )
        return jsonify(
            ok=False,
            message="This score could not be saved right now. Please try again.",
        ), 503

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
