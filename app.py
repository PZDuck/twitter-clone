import os

from flask import Flask, render_template, request, flash, redirect, session, g, url_for, abort
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm, UserEditForm
from models import db, connect_db, User, Message
from decorators import login_required

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = (os.environ.get('DATABASE_URL', "postgresql://postgres:password@localhost:5432/warbler")) # Setup the databse URI in .env file or insert manually
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False

# app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True

connect_db(app)

##############################################################################
# User signup/login/logout

@app.before_request
def add_user_to_g():
    """If logged in, add curr user to Flask global"""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])
    else:
        g.user = None


def do_login(user):
    """Log in user"""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user"""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]

# User routes

@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup"""

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)
        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login"""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user"""

    if session.get(CURR_USER_KEY):
        do_logout()
        flash("You've successfully logged out.", "success")
    
    else:
        flash("You are not logged in.", "danger")
    
    return redirect(url_for("login"))


##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile"""

    user = User.query.get_or_404(user_id)

    messages = (Message.query.filter(Message.user_id == user_id).order_by(Message.timestamp.desc()).limit(100).all())

    return render_template('users/show.html', user=user, messages=messages)


@app.route('/users/<int:user_id>/following')
@login_required
def show_following(user_id):
    """Show list of people this user is following"""

    user = User.query.get_or_404(user_id)

    return render_template('users/following.html', user=user)


@app.route('/users/<int:user_id>/followers')
@login_required
def users_followers(user_id):
    """Show list of followers of this user"""

    user = User.query.get_or_404(user_id)

    return render_template('users/followers.html', user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
@login_required
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user"""

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)

    db.session.commit()

    return redirect(request.referrer)


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
@login_required
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user"""

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)

    db.session.commit()

    return redirect(request.referrer)


@app.route('/users/profile', methods=["GET", "POST"])
@login_required
def profile():
    """Update profile for current user"""
    
    user = g.user

    form = UserEditForm(obj=user)

    # REVIEW THIS CODE; FIND A WAY TO OPTIMIZE
    if form.validate_on_submit():
        if User.authenticate(user.username, form.password.data):
            if form.new_password.data:
                if form.new_password.data != form.new_password_confirm.data:
                    flash("Passwords do not match.", "danger")
                    return render_template('users/edit.html', form=form, user_id=user.id)
                else:
                    if not User.change_password(user.username, form.password.data, form.new_password.data):
                        flash("New password should be different from the old one.", "danger")
                        return render_template('users/edit.html', form=form, user_id=user.id)

            user.username = form.username.data
            user.email = form.email.data
            user.image_url = form.image_url.data or "/static/image/default-pic.png"
            user.header_image_url = form.header_image_url.data or "/static/image/warbler-hero.jpg"
            user.bio = form.bio.data
            user.location = form.location.data

            db.session.commit()

            return redirect(f"/users/{user.id}")
        
        flash("Wrong password.", "danger")
    
    return render_template('users/edit.html', form=form, user_id=user.id)


@app.route('/users/delete', methods=["POST"])
@login_required
def delete_user():
    """Delete user"""

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect(url_for("signup"))


@app.route('/users/<int:user_id>/likes')
@login_required
def show_likes(user_id):
    """Display all posts that the current user liked"""
    
    user = User.query.get_or_404(user_id)
    return render_template('users/likes.html', user=user, likes=user.likes)


@app.route('/users/add_like/<int:message_id>', methods=['POST'])
@login_required
def add_like(message_id):
    """Add message to the list of liked messages"""
    
    liked = Message.query.get_or_404(message_id)

    if liked.user_id == g.user.id:
        return abort(403)
    
    if liked in g.user.likes:
        g.user.likes = [like for like in g.user.likes if like != liked]
    else:
        g.user.likes.append(liked)
    
    db.session.commit()

    return redirect(request.referrer)

##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
@login_required
def messages_add():
    """Add a message"""

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message"""

    msg = Message.query.get_or_404(message_id)
    return render_template('messages/show.html', message=msg)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
@login_required
def messages_destroy(message_id):
    """Delete a message"""

    msg = Message.query.get(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    if g.user:
        following = [f.id for f in g.user.following]
        messages = Message.query.filter(Message.user_id.in_(following)).order_by(Message.timestamp.desc()).limit(100).all()
        likes = [msg.id for msg in g.user.likes]

        return render_template('home.html', messages=messages, likes=likes)

    else:
        return render_template('home-anon.html')

@app.errorhandler(404)
def not_found(error):

    return render_template('404.html'), 404


##############################################################################
# Turn off all caching in Flask
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(req):
    """Add non-caching headers on every request"""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'

    return req
