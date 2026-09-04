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
