from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from models import User

class SignupForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=80, message='Username must be 3-80 characters')
    ])
    email = EmailField('Email', validators=[
        DataRequired(),
        Email(message='Enter a valid email'),
        Length(max=120)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, max=128, message='Password must be 8-128 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

class ForgotPasswordForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, max=128)
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])

class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=80)
    ])
    bio = TextAreaField('Bio', validators=[
        Optional(),
        Length(max=500, message='Bio must be under 500 characters')
    ])

class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    message = TextAreaField('Message', validators=[DataRequired(), Length(max=2000)])
