from flask_wtf import Form
from flask_pagedown.fields import PageDownField
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import Required, Length, Email, Regexp, EqualTo
from wtforms import ValidationError

class PostForm(Form):
    title = StringField('Title', validators=[Required()])
    body = PageDownField("What's in your mind?", validators=[Required()])
    submit = SubmitField('Publish')