from zoneinfo import available_timezones

from flask import Flask, render_template, request, redirect
from SECRETS import Config
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from data import db_session
from data.Table_user import User
from data.Table_cells import Cell
import datetime as dt
import os

"""
TODO:
1. Добавить валидацию e-mail с regular expressions
2. Строку поиска на страницу со своими файлами
3. Сообщение при отказе в загрузке слишком больших файлов
"""

app = Flask(__name__)
app.config.from_object(Config)
app.config['PERMANENT_SESSION_LIFETIME'] = dt.timedelta(
    days=60
)

manager = LoginManager()
manager.init_app(app)
PATH_TO_FILES = '/Users/vladgn/PycharmProjects/WebProject/files'


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


@app.route('/directories')
def directories():
    return render_template('directories.html')


@app.route('/add_files', methods=['GET', 'POST'])
@login_required
def add_files():
    if request.method == 'GET':
        sess = db_session.create_session()
        user = sess.query(User).get(current_user.id)
        user: User
        available_memory = round(user.available_memory, 4)

        if user.is_account_pro:
            used_memory = 10 - available_memory
        else:
            used_memory = 5 - available_memory

        used_memory = round(used_memory, 4)
        return render_template('add_files.html', used_memory=used_memory,
                               available_memory=available_memory, is_pro=user.is_account_pro, message='')
    else:
        files = request.files.getlist('files')
        title = request.form['title']
        summary_weight = 0  # bytes
        sess = db_session.create_session()
        available_memory = sess.query(User).get(current_user.id).available_memory

        check = sess.query(Cell).filter(Cell.user_id == current_user.id, Cell.cellname == title).first()
        if check:
            return render_template('add_files.html',
                                   message='Ячейка с таким названием уже существует!')

        try:
            os.mkdir(f'{PATH_TO_FILES}/{current_user.username}')
        except FileExistsError:
            pass
        try:
            os.mkdir(f'{PATH_TO_FILES}/{current_user.username}/{title}')
        except FileExistsError:
            pass

        for file in files:
            file.seek(0, os.SEEK_END)
            summary_weight += file.tell()

            if summary_weight <= available_memory * 2 ** 30 and file.filename != '':
                file.save(f'{PATH_TO_FILES}/{current_user.username}/{title}/{file.filename}')
            else:
                pass

        cell = Cell()
        cell.cellname = title
        cell.user_id = current_user.id
        cell.path = f'{PATH_TO_FILES}/{current_user.username}/{title}'
        cell.description = request.form.get('description')
        if request.form.get('is_private') is not None:
            cell.is_private = True
            cell.set_password(request.form.get('password'))
        else:
            cell.is_private = False
        cell.created_date = dt.datetime.now()
        cell.weight_of_directory = summary_weight / 2 ** 30

        user = sess.query(User).get(current_user.id)
        user.available_memory -= summary_weight / 2 ** 30

        sess.add(cell)
        sess.commit()

    return '1212'


@app.route('/view_files')
def view_files():
    return render_template('view_files.html')


if __name__ == '__main__':
    db_session.global_init('db/database.db')
    app.run(port=8080)
