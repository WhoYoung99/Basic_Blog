#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os, string, re, random
import webapp2
import jinja2
import hashlib
import hmac

from google.appengine.ext import db
from blog_class import User, Posts

template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                                autoescape = True, auto_reload=True)

secret = "Some secret string here..."

def make_secure_val(val):
    """
    Take one value, return a string with original val
    and one salted hash value, seperated by |
    """
    return "%s|%s" % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
    """
    Verify the integrity of secured value
    generated by make_secure_val function.
    Return original value if pass test.
    """
    val = secure_val.split('|')[0]
    return val and secure_val == make_secure_val(val)

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

class BlogHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))
        self.set_secure_cookie('user_name', str(user.user))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')
        self.response.headers.add_header('Set-Cookie', 'user_name=; Path=/')


USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)

class Signup(BlogHandler):
    def get(self):
        self.render("signup-form.html")

    def post(self):
        have_error = False
        self.username = self.request.get("user")
        self.password = self.request.get("password")
        self.verify = self.request.get("verify")
        self.email = self.request.get("email")

        params = dict(username=self.username,
                      email=self.email)

        if not valid_username:
            have_error = True
            params["error_username"] = "This wasn't a valid username."

        if not valid_password(self.password):
            params['error_password'] = "That wasn't a valid password."
            have_error = True

        elif self.password != self.verify:
            params['error_verify'] = "Your password didn't match."
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "That wasn't a valid email."
            have_error = True

        if have_error:
            self.render("signup-form.html", **params)
        else:
            self.done()

    def done(self):
            raise NotImplementedError

class Welcome(BlogHandler):
    def get(self):
        username = self.request.get('username')
        if valid_username(username):
            self.render('welcome.html', username=username)
        else:
            self.redirect('/signup')

def make_salt(length=5):
    return ''.join(random.sample(string.ascii_letters, length))

def make_pw_hash(name, pw, salt=None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return "%s,%s" % (salt, h)

def valid_pw(name, pw, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(name, pw, salt)

# class User(db.Model):
#     user = db.StringProperty(required=True)
#     password = db.StringProperty(required=True)
#     email = db.StringProperty()

#     @classmethod
#     def register(cls, user, password, email=None):
#         return User(user=user,
#                     password=make_pw_hash(user, password),
#                     email=email)

#     @classmethod
#     def login(cls, user, pw):
#         u = cls.by_name(user)
#         if u and valid_pw(user, pw, u.password):
#             return u

#     @classmethod
#     def by_name(cls, user):
#         u = User.all().filter('user =', user).get()
#         return u

# class Posts(db.Model):
#     subject = db.StringProperty(required=True)
#     content = db.TextProperty(required=True)
#     created = db.DateTimeProperty(auto_now_add=True)
#     modified = db.DateTimeProperty(auto_now=True)
#     author = db.StringProperty()

#     def render(self, user):
#         self._render_text = self.content.replace('\n', '<br>')
#         return render_str("post.html", p=self, user=user)

class Register(Signup):
    def done(self):
        u = User.by_name(self.username)
        if u:
            error = "User already exists."
            self.render('signup-form.html', error_username=error)
        else:
            u = User.register(self.username, self.password, self.email)
            u.put()
            self.login(u)
            self.redirect('/welcome?username=%s' % self.username)

class Login(BlogHandler):
    def get(self):
        # user = self.request.cookies.get('user_name').split('|')[0]
        if self.read_secure_cookie('user_name'):
            self.render('login.html', user=user)
        else:
            msg = "Not a valid user."
            self.render('login.html', error=msg)

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/blog')
        else:
            msg = 'Invalid login'
            self.render('login.html', error = msg)

class Logout(BlogHandler):
    def get(self):
        self.logout()
        self.redirect('/blog')

class Newpost(BlogHandler):
    def get(self):
        user = self.request.cookies.get('user_name').split('|')[0]
        if user and self.read_secure_cookie('user_name'):
            self.render("new-post.html", user=user)
        else:
            msg="Please login to write a new post."
            self.render("new-post.html", error_post=msg)

    def post(self):
        subject = self.request.get("subject")
        content = self.request.get("content")
        author = self.request.cookies.get("user_name").split('|')[0]

        if subject and content:
            post = Posts(subject=subject, content=content, author=author)
            post.put()
            self.redirect("/blog/%s" % str(post.key().id()))
        else:
            error = "Required both subject and content!"
            self.render("new-post.html", error_post=error, subject=subject, content=content)

class PostPage(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Posts', int(post_id))
        post = db.get(key)

        user = self.request.cookies.get('user_name').split('|')[0]
        self.render("permalink.html", post=post, user=user)

class EditPage(BlogHandler):
    def get(self, post_id):
        user = self.read_secure_cookie('user_name')
        key = db.Key.from_path('Posts', int(post_id))
        post = db.get(key)
        if user and self.request.cookies.get('user_name').split('|')[0] == post.author:
            subject = post.subject
            content = post.content
            self.render("editpost.html", subject=subject, content=content, post_id=post_id)
        else:
            msg="Only the author can edit this post."
            self.render("editpost.html", error_post=msg)

    def post(self, post_id):
        key = db.Key.from_path('Posts', int(post_id))
        post = db.get(key)
        edit_content = self.request.get("content")
        if (not post.subject.startswith("[Edit]")) and post.content != edit_content:
            post.subject = ''.join(["[Edit] ", post.subject])
        post.content = edit_content
        post.put()
        self.redirect("/blog/%s" % str(post.key().id()))

class DeletePage(BlogHandler):
    def get(self, post_id):
        self.render("delete.html")

    def post(self, post_id):
        key = db.Key.from_path('Posts', int(post_id))
        delete = db.get(key).delete()
        self.redirect("/blog")

class Main(Login):
    def get(self):
        # posts = Posts.all().order("-created")
        posts = db.GqlQuery("SELECT * FROM Posts ORDER BY created DESC LIMIT 100")
        user = self.request.cookies.get('user_name').split('|')[0]
        if self.read_secure_cookie('user_name'):
            self.render("blog.html", posts=posts, user=user)
        else:
            self.logout()
            self.render("blog.html", posts=posts)


app = webapp2.WSGIApplication([('/', Main),
                               ('/blog', Main),
                               ('/blog/newpost', Newpost),
                               ('/blog/edit/([0-9]+)', EditPage),
                               ('/blog/delete/([0-9]+)', DeletePage),
                               ('/blog/([0-9]+)', PostPage),
                               ('/signup', Register),
                               ('/login', Login),
                               ('/logout', Logout),
                               ('/welcome', Welcome)],
                                debug=True)