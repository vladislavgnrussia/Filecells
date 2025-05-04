from flask import Flask, render_template, request, redirect
from SECRETS import Config
from flask_login import LoginManager, login_user, login_required, logout_user
from data import db_session
from data.Table_user import User
from data.Table_cells import Cell
from forms.Register_form import Registration
import datetime as dt

app = Flask(__name__)
app.config.from_object(Config)
app.config['PERMANENT_SESSION_LIFETIME'] = dt.timedelta(
    days=60
)

manager = LoginManager()
manager.init_app(app)


@manager.user_loader
def load_user(user_id):
    sess = db_session.create_session()
    user = sess.query(User).get(user_id)
    return user


@app.route('/signin', methods=['GET', 'POST'])
def sign_in():
    if request.method == 'GET':
        return render_template('signin.html', message='')
    else:
        sess = db_session.create_session()
        user = sess.query(User).filter(User.email == request.form['email']).first()
        user: User
        if not all([request.form['password'], request.form['email']]):
            return render_template('signin.html', message='Все поля обязательны!')
        if user is None:
            return render_template('signin.html', message='Пользователь с такой почтой не существует!')
        if not user.check_password(request.form['password']):
            return render_template('signin.html', message='Неверный пароль!')

        if 'remember_me' in request.form.keys():
            login_user(user, remember=True)
        else:
            login_user(user, remember=False)

        return redirect('/')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html', message='')
    else:
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_again = request.form['passwordAgain']
        if not all([username, email, password, password_again]):
            return render_template('register.html', message='Все поля обязательны!')
        elif password != password_again:
            return render_template('register.html', message='Пароли не совпадают!')
        elif len(password) < 8:
            return render_template('register.html', message='Длина пароля менее 8 символов!')
        elif len(password) > 20:
            return render_template('register.html', message='Длина пароля более 20 символов!')

        sess = db_session.create_session()
        check_email = sess.query(User).filter(User.email == email).first()
        if check_email is not None:
            return render_template('register.html', message='Пользователь с таким email уже существует!')

        check_username = sess.query(User).filter(User.username == username).first()
        if check_username is not None:
            render_template('register.html', message='Пользователь с таким именем уже существует!')

        user = User()
        user.username = username
        user.email = email
        user.crated_date = dt.datetime.now()
        user.set_password(password)
        sess.add(user)
        sess.commit()

        if 'remember_me' in request.form.keys():
            login_user(user, remember=True)
        else:
            login_user(user, remember=False)

        return redirect('/')


@app.route('/', methods=['GET', 'POST'])
def main_page():
    return render_template('base.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


if __name__ == '__main__':
    db_session.global_init('db/database.db')
    app.run(port=8080)
