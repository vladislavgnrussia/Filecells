from flask_wtf import FlaskForm
from wtforms import PasswordField, EmailField, StringField, SubmitField
from wtforms.validators import DataRequired, Length

class Registration(FlaskForm):
    name = StringField('Имя', validators=[DataRequired()])
    email = EmailField('E-mail', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(max=20, min=8)])
    password_again = PasswordField('Пароль', validators=[DataRequired(), Length(max=20, min=8)])


    submit = SubmitField('Зарегистрироваться')
