# ============================================================================
# lsuite/auth/forms.py
# ============================================================================
"""
Authentication Forms
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from lsuite.models import User


class LoginForm(FlaskForm):
    """Login form"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegisterForm(FlaskForm):
    """Registration form"""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=80)
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters')
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Username already taken. Please choose another.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data.lower()).first()
        if user is not None:
            raise ValidationError('Email already registered. Please use another.')


class ProfileForm(FlaskForm):
    """Profile update form"""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=80)
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    submit = SubmitField('Update Profile')
    
    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.original_username = None
        self.original_email = None
    
    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user is not None:
                raise ValidationError('Username already taken.')
    
    def validate_email(self, email):
        if email.data.lower() != self.original_email:
            user = User.query.filter_by(email=email.data.lower()).first()
            if user is not None:
                raise ValidationError('Email already registered.')


class ChangePasswordForm(FlaskForm):
    """Change password form"""
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters')
    ])
    new_password2 = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Change Password')
