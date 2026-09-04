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
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate token and send email
            token = user.generate_reset_token()
            # Send email with reset link
            flash('Password reset link sent to your email', 'success')
        else:
            flash('If that email exists, a reset link has been sent', 'info')
        
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Verify token and allow password reset
    pass
@app.route('/games')
def games_index():
    # Get filters
    genre = request.args.get('genre')
    search = request.args.get('search')
    sort = request.args.get('sort', 'newest')
    
    query = Game.query
    
    if genre:
        query = query.filter_by(genre=genre)
    
    if search:
        query = query.filter(Game.title.ilike(f'%{search}%'))
    
    if sort == 'popular':
        query = query.order_by(Game.plays_count.desc())
    elif sort == 'rating':
        query = query.order_by(Game.rating_avg.desc())
    else:
        query = query.order_by(Game.created_at.desc())
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    games = query.paginate(page=page, per_page=20, error_out=False)
    
    # Get all genres for filter dropdown
    genres = db.session.query(Game.genre).distinct().all()
    
    return render_template('games.html', games=games, genres=genres, 
                         current_genre=genre, current_search=search)

@app.route('/game/<slug>')
def game_detail(slug):
    game = Game.query.filter_by(slug=slug).first_or_404()
    
    # Increment play count
    game.plays_count += 1
    db.session.commit()
    
    # Get reviews
    reviews = Review.query.filter_by(game_id=game.id)\
        .order_by(Review.created_at.desc()).limit(5).all()
    
    # Get similar games
    similar = Game.query.filter_by(genre=game.genre)\
        .filter(Game.id != game.id).limit(6).all()
    
    return render_template('game_detail.html', game=game, 
                         reviews=reviews, similar=similar)

@app.route('/api/game/<int:game_id>/favorite', methods=['POST'])
@login_required
def toggle_favorite(game_id):
    favorite = FavoriteGame.query.filter_by(
        user_id=current_user.id, 
        game_id=game_id
    ).first()
    
    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({'favorited': False})
    else:
        favorite = FavoriteGame(user_id=current_user.id, game_id=game_id)
        db.session.add(favorite)
        db.session.commit()
        return jsonify({'favorited': True})

@app.route('/api/game/<int:game_id>/review', methods=['POST'])
@login_required
def add_review(game_id):
    data = request.get_json()
    
    # Check if already reviewed
    existing = Review.query.filter_by(
        user_id=current_user.id,
        game_id=game_id
    ).first()
    
    if existing:
        return jsonify({'error': 'Already reviewed'}), 400
    
    review = Review(
        user_id=current_user.id,
        game_id=game_id,
        rating=data['rating'],
        title=data.get('title', ''),
        content=data.get('content', '')
    )
    
    db.session.add(review)
    
    # Update game rating
    game = Game.query.get(game_id)
    all_reviews = Review.query.filter_by(game_id=game_id).all()
    game.rating_avg = sum(r.rating for r in all_reviews) / len(all_reviews)
    game.rating_count = len(all_reviews)
    
    db.session.commit()
    
    return jsonify({'success': True})
@app.route('/community')
def community():
    page = request.args.get('page', 1, type=int)
    posts = CommunityPost.query.order_by(
        CommunityPost.is_pinned.desc(),
        CommunityPost.created_at.desc()
    ).paginate(page=page, per_page=15)
    
    return render_template('community.html', posts=posts)

@app.route('/community/post/<int:post_id>')
def view_post(post_id):
    post = CommunityPost.query.get_or_404(post_id)
    post.views_count += 1
    db.session.commit()
    
    comments = Comment.query.filter_by(post_id=post_id, parent_id=None)\
        .order_by(Comment.created_at.desc()).all()
    
    return render_template('post_detail.html', post=post, comments=comments)

@app.route('/api/community/post', methods=['POST'])
@login_required
def create_post():
    data = request.get_json()
    
    post = CommunityPost(
        user_id=current_user.id,
        title=data['title'],
        content=data['content'],
        tags=data.get('tags', [])
    )
    
    db.session.add(post)
    db.session.commit()
    
    return jsonify({'success': True, 'post_id': post.id})

@app.route('/api/post/<int:post_id>/like', methods=['POST'])
@login_required
def toggle_like(post_id):
    like = PostLike.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()
    
    post = CommunityPost.query.get(post_id)
    
    if like:
        db.session.delete(like)
        post.likes_count -= 1
        db.session.commit()
        return jsonify({'liked': False, 'count': post.likes_count})
    else:
        like = PostLike(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
        post.likes_count += 1
        db.session.commit()
        
        # Create notification for post author
        if post.user_id != current_user.id:
            notify = Notification(
                user_id=post.user_id,
                type='like',
                actor_id=current_user.id,
                post_id=post_id
            )
            db.session.add(notify)
        
        db.session.commit()
        return jsonify({'liked': True, 'count': post.likes_count})

@app.route('/api/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    data = request.get_json()
    
    comment = Comment(
        post_id=post_id,
        user_id=current_user.id,
        content=data['content'],
        parent_id=data.get('parent_id')  # For replies
    )
    
    db.session.add(comment)
    
    post = CommunityPost.query.get(post_id)
    post.comments_count += 1
    db.session.commit()
    
    return jsonify({'success': True, 'comment_id': comment.id})

@app.route('/api/post/<int:post_id>/report', methods=['POST'])
@login_required
def report_post(post_id):
    data = request.get_json()
    
    # Check if already reported
    existing = PostReport.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()
    
    if existing:
        return jsonify({'error': 'Already reported'}), 400
    
    report = PostReport(
        user_id=current_user.id,
        post_id=post_id,
        reason=data.get('reason', '')
    )
    
    db.session.add(report)
    
    post = CommunityPost.query.get(post_id)
    post.report_count += 1
    if post.report_count >= 5:
        post.is_reported = True
    
    db.session.commit()
    
    return jsonify({'success': True})
@app.route('/events')
def events_index():
    upcoming = Event.query.filter(
        Event.status == 'upcoming',
        Event.start_date > datetime.utcnow()
    ).order_by(Event.start_date).limit(10).all()
    
    active = Event.query.filter(
        Event.status == 'active'
    ).order_by(Event.start_date.desc()).all()
    
    return render_template('events.html', upcoming=upcoming, active=active)

@app.route('/event/<slug>')
def event_detail(slug):
    event = Event.query.filter_by(slug=slug).first_or_404()
    
    # Get leaderboard
    leaderboard = LeaderboardEntry.query.filter_by(event_id=event.id)\
        .order_by(LeaderboardEntry.score.desc()).limit(50).all()
    
    # Check if user is participating
    is_participating = False
    if current_user.is_authenticated:
        is_participating = EventParticipant.query.filter_by(
            event_id=event.id,
            user_id=current_user.id
        ).first() is not None
    
    return render_template('event_detail.html', event=event, 
                         leaderboard=leaderboard, is_participating=is_participating)

@app.route('/api/event/<int:event_id>/register', methods=['POST'])
@login_required
def register_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Check if already registered
    existing = EventParticipant.query.filter_by(
        event_id=event_id,
        user_id=current_user.id
    ).first()
    
    if existing:
        return jsonify({'error': 'Already registered'}), 400
    
    # Check if event is full
    if event.max_participants and event.current_participants >= event.max_participants:
        return jsonify({'error': 'Event is full'}), 400
    
    # Check registration deadline
    if event.registration_deadline and datetime.utcnow() > event.registration_deadline:
        return jsonify({'error': 'Registration closed'}), 400
    
    participant = EventParticipant(
        event_id=event_id,
        user_id=current_user.id
    )
    
    db.session.add(participant)
    event.current_participants += 1
    db.session.commit()
    
    # Create notification
    notify = Notification(
        user_id=current_user.id,
        type='event_registered',
        event_id=event_id
    )
    db.session.add(notify)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/event/<int:event_id>/leaderboard/update', methods=['POST'])
@login_required
def update_leaderboard(event_id):
    data = request.get_json()
    score = data.get('score', 0)
    
    entry = LeaderboardEntry.query.filter_by(
        event_id=event_id,
        user_id=current_user.id
    ).first()
    
    if not entry:
        # Auto-register if not registered
        entry = LeaderboardEntry(
            event_id=event_id,
            user_id=current_user.id,
            score=score
        )
        db.session.add(entry)
    else:
        entry.score = max(entry.score, score)  # Keep highest score
    
    # Update rank
    all_entries = LeaderboardEntry.query.filter_by(event_id=event_id)\
        .order_by(LeaderboardEntry.score.desc()).all()
    
    for i, e in enumerate(all_entries, 1):
        e.rank = i
    
    db.session.commit()
    
    return jsonify({'success': True, 'rank': entry.rank, 'score': entry.score})
@app.route('/notifications')
@login_required
def notifications():
    unread = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(20).all()
    
    all_notifs = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).paginate(page=1, per_page=50)
    
    return render_template('notifications.html', unread=unread, all=all_notifs)

@app.route('/api/notification/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    notif = Notification.query.filter_by(
        id=notif_id,
        user_id=current_user.id
    ).first_or_404()
    
    notif.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/notifications/read-all', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()
    
    return jsonify({'success': True})

# Helper function to create notifications
def create_notification(user_id, type, message, actor_id=None, **kwargs):
    notif = Notification(
        user_id=user_id,
        type=type,
        message=message,
        actor_id=actor_id,
        **kwargs
    )
    db.session.add(notif)
    db.session.commit()
    return notif
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@admin_required
def admin_dashboard():
    # Stats
    total_users = User.query.count()
    total_games = Game.query.count()
    total_posts = CommunityPost.query.count()
    total_events = Event.query.count()
    
    # Recent activity
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    reported_posts = CommunityPost.query.filter_by(is_reported=True).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_games=total_games,
                         total_posts=total_posts,
                         total_events=total_events,
                         recent_users=recent_users,
                         reported_posts=reported_posts)

@app.route('/admin/users')
@admin_required
def admin_users():
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/users.html', users=users)

@app.route('/admin/user/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f'{user.username} is now {"admin" if user.is_admin else "user"}', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/games')
@admin_required
def admin_games():
    games = Game.query.order_by(Game.created_at.desc()).all()
    return render_template('admin/games.html', games=games)

@app.route('/admin/reports')
@admin_required
def admin_reports():
    reports = PostReport.query.order_by(PostReport.created_at.desc()).all()
    return render_template('admin/reports.html', reports=reports)

@app.route('/admin/post/<int:post_id>/delete', methods=['POST'])
@admin_required
def admin_delete_post(post_id):
    post = CommunityPost.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted', 'success')
    return redirect(url_for('admin_reports'))
