from google.appengine.ext import db

class User(db.Model):
    user = db.StringProperty(required=True)
    password = db.StringProperty(required=True)
    email = db.StringProperty()

    @classmethod
    def register(cls, user, password, email=None):
        return User(user=user,
                    password=make_pw_hash(user, password),
                    email=email)

    @classmethod
    def login(cls, user, pw):
        u = cls.by_name(user)
        if u and valid_pw(user, pw, u.password):
            return u

    @classmethod
    def by_name(cls, user):
        u = User.all().filter('user =', user).get()
        return u


class Posts(db.Model):
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    modified = db.DateTimeProperty(auto_now=True)
    author = db.StringProperty()

    def render(self, user):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p=self, user=user)