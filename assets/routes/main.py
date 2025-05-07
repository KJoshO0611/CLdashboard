from flask import Blueprint, render_template
from flask_login import current_user

main = Blueprint('main', __name__)

@main.route('/')
def home():
    """Landing page"""
    return render_template('home.html', title='Home')

@main.route('/about')
def about():
    """About page"""
    return render_template('about.html', title='About')

@main.route('/features')
def features():
    """Features page"""
    return render_template('features.html', title='Features')

@main.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html', title='Contact') 