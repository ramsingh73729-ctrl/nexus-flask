from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import secrets

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Profile fields
    avatar = db.Column(db.String(256), default='default_avatar.png')
    bio = db.Column(db.Text, default='')
    level = db.Column(db.Integer, default=1)
    xp = db.Column(db.Integer, default=0)
    is_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Stats
    games_played = db.Column(db.Integer, default=0)
    total_score = db.Column(db.Integer, default=0)
    achievements_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    favorite_games = db.relationship('FavoriteGame', backref='user', lazy='dynamic')
    reviews = db.relationship('Review', backref='user', lazy='dynamic')
    posts = db.relationship('CommunityPost', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_reset_token(self):
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def verify_reset_token(token, expiration=3600):
        # Implement token verification
        pass

class UserActivity(db.Model):
    """Track user actions for activity feed"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action_type = db.Column(db.String(50))  # 'played_game', 'posted', 'commented', etc.
    action_data = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    description = db.Column(db.Text)
    thumbnail = db.Column(db.String(256))
    game_url = db.Column(db.String(500))
    
    # Metadata
    genre = db.Column(db.String(50), index=True)
    tags = db.Column(db.JSON, default=[])
    developer = db.Column(db.String(100))
    release_date = db.Column(db.DateTime)
    
    # Stats
    plays_count = db.Column(db.Integer, default=0)
    rating_avg = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    
    # SEO
    featured = db.Column(db.Boolean, default=False)
    trending = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    reviews = db.relationship('Review', backref='game', lazy='dynamic')
    favorites = db.relationship('FavoriteGame', backref='game', lazy='dynamic')

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    rating = db.Column(db.Integer)  # 1-5
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    helpful_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'game_id', name='unique_user_game_review'),)

class FavoriteGame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'game_id', name='unique_user_game_favorite'),)
class CommunityPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(256))
    tags = db.Column(db.JSON, default=[])
    
    # Stats
    likes_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    views_count = db.Column(db.Integer, default=0)
    
    # Moderation
    is_reported = db.Column(db.Boolean, default=False)
    report_count = db.Column(db.Integer, default=0)
    is_pinned = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    comments = db.relationship('Comment', backref='post', lazy='dynamic', 
                              cascade='all, delete-orphan')
    likes = db.relationship('PostLike', backref='post', lazy='dynamic')
    reports = db.relationship('PostReport', backref='post', lazy='dynamic')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('community_post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'))  # For replies
    
    content = db.Column(db.Text, nullable=False)
    likes_count = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Self-referential relationship for replies
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]))
    user = db.relationship('User', foreign_keys=[user_id])

class PostLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('community_post.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_post_like'),)

class PostReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('community_post.id'), nullable=False)
    reason = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    slug = db.Column(db.String(300), unique=True, nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(256))
    
    # Event type
    event_type = db.Column(db.String(50))  # 'tournament', 'challenge', 'giveaway'
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
    
    # Timing
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    registration_deadline = db.Column(db.DateTime)
    
    # Tournament settings
    max_participants = db.Column(db.Integer)
    current_participants = db.Column(db.Integer, default=0)
    prize_pool = db.Column(db.String(200))
    entry_fee = db.Column(db.Integer, default=0)
    
    # Status
    status = db.Column(db.String(20), default='upcoming')  # upcoming, active, completed
    is_featured = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    participants = db.relationship('EventParticipant', backref='event', lazy='dynamic')
    leaderboard = db.relationship('LeaderboardEntry', backref='event', lazy='dynamic')

class EventParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    score = db.Column(db.Integer, default=0)
    rank = db.Column(db.Integer)
    
    user = db.relationship('User', backref='event_participations')
    
    __table_args__ = (db.UniqueConstraint('event_id', 'user_id', name='unique_event_participant'),)

class LeaderboardEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    score = db.Column(db.Integer, default=0)
    rank = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User')
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Type: 'like', 'comment', 'follow', 'event', 'system'
    type = db.Column(db.String(50), nullable=False)
    
    # Actor (who triggered it)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    actor = db.relationship('User', foreign_keys=[actor_id])
    
    # Related content
    post_id = db.Column(db.Integer, db.ForeignKey('community_post.id'))
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    
    # Content
    message = db.Column(db.String(500))
    is_read = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
