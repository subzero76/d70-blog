from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from functools import wraps
from flask import abort
from flask_gravatar import Gravatar
import os
from dotenv import dotenv_values

'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)

config = dotenv_values(".env")
app.config['SECRET_KEY'] = config["FLASH_KEY"]


ckeditor = CKEditor(app)
Bootstrap5(app)

# TODO: Configure Flask-Login


# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy()
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(app,
                    size=40,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)
# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="parent_post")

# Create a User table for all your registered users
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="commentor")

class Comment(UserMixin, db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(250), nullable=False)
    commentor_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    commentor = relationship("User", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")


with app.app_context():
    db.create_all()

def admin_only(f):
    @wraps(f)
    def check_admin_login(*args, **kwargs):
        if current_user.id == 1:
            return f(*args, **kwargs)
        else:
            return abort(403)
    return check_admin_login

# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        print("In POST")
        new_user = db.session.execute(db.select(User).where(User.email == request.form['email'])).scalar()
        if new_user:
            print("Already a user")
            flash("You've already registered.  Please login with this email")
            return redirect(url_for('login'))
        else:
            print("Creating new user")
            hashed_pwd = generate_password_hash(request.form['password'], method='pbkdf2:sha256', salt_length=8)
            print(f"Email = {request.form['email']}")
            print(f"Name = {request.form['name']}")
            user_to_add = User(
                email = request.form['email'],
                password = hashed_pwd,
                name= request.form['name']
            )
            with app.app_context():
                db.session.add(user_to_add)
                db.session.commit()
            #return render_template('secrets.html', name=request.form['name'])
            return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        loginuser = db.session.execute(db.select(User).where(User.email == request.form['email'])).scalar()
        if not loginuser:
            print("no such user exist")
            flash("The email does not exist.  Please try again.")
            return render_template("login.html", form=form)
        else:
            if check_password_hash(loginuser.password, request.form['password']):
                login_user(loginuser)
                return redirect(url_for('get_all_posts'))
            else:
                print("Wrong password")
                flash("The password is incorrect.  Please try again")
                return render_template("login.html", form=form)

    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = []
    posts = result.scalars().all()
    print(posts)
    return render_template("index.html", all_posts = posts)



# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=['POST', 'GET'])
def show_post(post_id):
    form = CommentForm()
    print("Correct .... ")
    if form.validate_on_submit():
        print("In validate on submit")
        if current_user.is_authenticated:
            print("Authenticated ....")
            print(f"comments - {request.form['comments']}")
            comment_to_add = Comment(
                text=request.form['comments'],
                post_id = post_id,
                commentor_id = current_user.id

            )
            with app.app_context():
                db.session.add(comment_to_add)
                db.session.commit()
            return redirect(url_for('show_post', post_id=post_id))
        else:
            flash("You need to login or register to comment")
            return redirect(url_for('login'))

    requested_post = db.get_or_404(BlogPost, post_id)
    related_comments = db.session.execute(db.select(Comment).where(Comment.post_id == post_id)).scalars().all()
    return render_template("post.html", post=requested_post, form=form, comments= related_comments)


# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=False, port=5002)
