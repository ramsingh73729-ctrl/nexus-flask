from flask_wtf import CSRFProtect
from flask_wtf.form import FlaskForm
from wtforms import StringField, PasswordField, EmailField
from wtforms.validators import DataRequired, Email, Length
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
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
# Security configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(32).hex())
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = os.environ.get('WTF_CSRF_SECRET_KEY', os.urandom(32).hex())
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Initialize CSRF protection
csrf = CSRFProtect(app)
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
from forms import SignupForm, LoginForm, ForgotPasswordForm, ResetPasswordForm
from models import User, UserActivity
from datetime import timedelta
import secrets

# ... existing imports ...

@app.route('/signup', methods=['GET', 'POST'])
@limiter.limit("10 per minute")  # Prevent spam
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = SignupForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            # Check if user exists
            existing_user = User.query.filter(
                (User.username == form.username.data) | 
                (User.email == form.email.data)
            ).first()
            
            if existing_user:
                if request.is_json:
                    return jsonify({'error': 'Username or email already exists'}), 400
                flash('Username or email already exists', 'error')
                return render_template('index.html', form=form)
            
            # Create new user
            user = User(
                username=form.username.data,
                email=form.email.data
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            # Log activity
            activity = UserActivity(
                user_id=user.id,
                action_type='signup',
                xp_earned=50
            )
            user.add_xp(50)
            db.session.add(activity)
            db.session.commit()
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'redirect_url': url_for('login')
                })
            
            flash('Account created! Please login.', 'success')
            return redirect(url_for('login'))
        
        else:
            # Form validation failed
            errors = []
            for field, field_errors in form.errors.items():
                errors.extend(field_errors)
            
            if request.is_json:
                return jsonify({'error': errors[0] if errors else 'Validation failed'}), 400
            
            for error in errors:
                flash(error, 'error')
    
    if request.is_json:
        return jsonify({'error': 'Invalid request'}), 400
    
    return render_template('index.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            
            if user and user.check_password(form.password.data):
                login_user(user, remember=True)
                
                # Update login streak
                streak = user.check_login_streak()
                if streak > 1:
                    bonus_xp = streak * 10
                    user.add_xp(bonus_xp)
                    
                    # Log activity
                    activity = UserActivity(
                        user_id=user.id,
                        action_type='login_streak',
                        action_data={'streak': streak},
                        xp_earned=bonus_xp
                    )
                    db.session.add(activity)
                    db.session.commit()
                
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                if request.is_json:
                    return jsonify({
                        'success': True,
                        'redirect_url': url_for('index')
                    })
                
                flash(f'Welcome back, {user.username}! 🔥 Streak: {streak} days', 'success')
                return redirect(url_for('index'))
            else:
                if request.is_json:
                    return jsonify({'error': 'Invalid email or password'}), 400
                flash('Invalid email or password', 'error')
        else:
            errors = []
            for field, field_errors in form.errors.items():
                errors.extend(field_errors)
            
            if request.is_json:
                return jsonify({'error': errors[0] if errors else 'Validation failed'}), 400
            
            for error in errors:
                flash(error, 'error')
    
    if request.is_json:
        return jsonify({'error': 'Invalid request'}), 400
    
    return render_template('index.html', form=form)


@app.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = ForgotPasswordForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            
            if user:
                # Generate reset token
                token = secrets.token_urlsafe(32)
                
                # Store token in database (add reset_token field to User model)
                # For now, we'll use a simple approach
                # In production, store hashed token with expiration
                
                # Send email (configure Flask-Mail)
                # For now, just show success
                flash('If that email exists, a password reset link has been sent', 'info')
            
            return redirect(url_for('login'))
    
    return render_template('auth/forgot_password.html', form=form)


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def reset_password(token):
    # Verify token and allow password reset
    # Implement token verification logic here
    flash('Password reset functionality coming soon', 'info')
    return redirect(url_for('login'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))
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
