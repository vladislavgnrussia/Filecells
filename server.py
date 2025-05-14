from flask import Flask, render_template, request, redirect, abort, session, send_file
from zips.SECRETS import Config
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, AnonymousUserMixin
from data import db_session
from data.Table_user import User
from data.Table_cells import Cell
from data.Table_codes_for_pro import Codes
import datetime as dt
import os
import shutil

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
PATH_TO_ZIPS = '/Users/vladgn/PycharmProjects/WebProject/zips'
ADMIN_ID = 7


@manager.user_loader
def load_user(user_id) -> User:
    sess = db_session.create_session()
    user = sess.query(User).get(user_id)
    sess.close()
    return user


@app.route('/signin', methods=['GET', 'POST'])
def sign_in():
    if request.method == 'GET':
        return render_template('signin.html', message='')
    else:
        sess = db_session.create_session()
        user = sess.query(User).filter(User.email == request.form['email']).first()
        user: User
        sess.close()
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

        sess.close()
        return redirect('/')


@app.route('/', methods=['GET', 'POST'])
def main_page():
    if request.method == 'GET':
        return render_template('base.html')
    else:
        if request.form.get('author').strip() != '':
            author = request.form.get('author')
        else:
            author = 'none'

        if request.form.get('cellname').strip() != '':
            cellname = request.form.get('cellname')
        else:
            cellname = 'none'
        return redirect(f'/directories/author={author}/cellname={cellname}')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.route('/directories/author=<string:author>/cellname=<string:cellname>', methods=['GET', 'POST'])
def directories(author: str, cellname: str):
    if request.method == 'GET':
        sess = db_session.create_session()
        dirs = []
        if author == 'none' and cellname == 'none':
            ...
            return redirect('/')
        if author == 'none':
            dirs = sess.query(Cell).filter(Cell.cellname.like(f'%{cellname}%'))
        elif cellname == 'none':
            users = sess.query(User).filter(User.username.like(f'%{author}%'))
            users_id = [user.id for user in users[:5]]
            dirs = sess.query(Cell).filter(Cell.user_id.in_(users_id))
        else:
            users = sess.query(User).filter(User.username.like(f'%{author}%'))
            users_id = [user.id for user in users[:5]]
            dirs = sess.query(Cell).filter(Cell.user_id.in_(users_id), Cell.cellname.like(f'%{cellname}%'))

        authors = {}
        for cell in dirs:
            user = sess.query(User).get(cell.user_id)
            authors[cell.user_id] = user.username
        cellname = '' if cellname == 'none' else cellname
        author = '' if author == 'none' else author

        if isinstance(current_user, AnonymousUserMixin):
            sess.close()
            return render_template('directories.html', directories=dirs, authors=authors,
                                   query_author=author, query_cellname=cellname)

        user = sess.query(User).get(current_user.id)
        user: User
        user.available_memory = get_user_available_memory(user)
        available_memory = round(user.available_memory, 4)

        if user.is_account_pro:
            used_memory = 10 - available_memory
        else:
            used_memory = 5 - available_memory

        used_memory = round(used_memory, 4)

        sess.commit()
        sess.close()
        return render_template('directories.html', directories=dirs, authors=authors, query_author=author,
                               query_cellname=cellname, is_pro=current_user.is_account_pro, used_memory=used_memory,
                               available_memory=available_memory)
    else:
        if request.form.get('search') == 'True':
            if request.form.get('author').strip() != '':
                author = request.form.get('author')
            else:
                author = 'none'

            if request.form.get('cellname').strip() != '':
                cellname = request.form.get('cellname')
            else:
                cellname = 'none'
            return redirect(f'/directories/author={author}/cellname={cellname}')
        elif (dir_id := request.form.get('delete')) is not None:
            delete_directory(dir_id, current_user.id)
            return redirect(request.path)

        elif (dir_id := request.form.get('edit')) is not None:
            return redirect(f'../../edit_directory/{dir_id}')

        else:  # download

            clear_zips()
            dir_id = request.form.get('download')
            sess = db_session.create_session()
            cell = sess.query(Cell).get(dir_id)
            cell: Cell

            if cell.is_private and current_user.id != cell.user_id:
                password = session.get(f'cell_id:{cell.id}')
                if password is None or not cell.check_password(password):
                    return redirect(f'../../password/{cell.id}')

            shutil.make_archive(f'../zips/{cell.cellname}', 'zip', cell.path)

            return send_file(f'../zips/{cell.cellname}.zip', as_attachment=True)


@app.route('/create_cell', methods=['GET', 'POST'])
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

        sess.close()
        return render_template('add_files.html', used_memory=used_memory,
                               available_memory=available_memory, is_pro=user.is_account_pro, message='')
    else:
        if request.form.get('search') == 'True':
            if request.form.get('author').strip() != '':
                author = request.form.get('author')
            else:
                author = 'none'

            if request.form.get('cellname').strip() != '':
                cellname = request.form.get('cellname')
            else:
                cellname = 'none'
            return redirect(f'/directories/author={author}/cellname={cellname}')

        files = request.files.getlist('files')
        title = request.form['title']
        summary_weight = 0  # bytes
        sess = db_session.create_session()
        available_memory = sess.query(User).get(current_user.id).available_memory

        check = sess.query(Cell).filter(Cell.user_id == current_user.id, Cell.cellname == title).first()
        if check:
            sess.close()
            return render_template('add_files.html',
                                   message='Ячейка с таким названием уже существует!')

        try:
            os.mkdir(f'{PATH_TO_FILES}/{current_user.email}')
        except FileExistsError:
            pass
        try:
            os.mkdir(f'{PATH_TO_FILES}/{current_user.email}/{title}')
        except FileExistsError:
            pass

        for file in files:
            file.seek(0, os.SEEK_END)
            summary_weight += file.tell()

            if summary_weight <= available_memory * 2 ** 30 and file.filename != '':
                file.save(f'{PATH_TO_FILES}/{current_user.email}/{title}/{file.filename}')
            else:
                pass

        cell = Cell()
        cell.cellname = title
        cell.user_id = current_user.id
        cell.path = f'{PATH_TO_FILES}/{current_user.email}/{title}'
        cell.description = request.form.get('description')
        if request.form.get('is_private') is not None:
            cell.is_private = True
            cell.set_password(request.form.get('password'))
        else:
            cell.is_private = False
        cell.created_date = dt.datetime.now()
        cell.weight_of_directory = summary_weight / 2 ** 30

        user = sess.query(User).get(current_user.id)
        user.available_memory = get_user_available_memory(user)

        sess.add(cell)
        sess.commit()

        return redirect(f'../edit_directory/{cell.id}')


@login_required
@app.route('/edit_directory/<int:dir_id>', methods=['GET', 'POST'])
def edit_files(dir_id):
    sess = db_session.create_session()
    cell = sess.query(Cell).get(dir_id)
    cell: Cell
    if cell.user_id != current_user.id:
        abort(403)
    user = sess.query(User).get(current_user.id)
    user: User
    dir_path = cell.path
    if request.method == 'GET':

        is_private = cell.is_private
        title = cell.cellname
        description = cell.description

        files = os.listdir(dir_path)
        available_memory = round(user.available_memory, 4)
        if user.is_account_pro:
            used_memory = 10 - available_memory
        else:
            used_memory = 5 - available_memory

        used_memory = round(used_memory, 4)

        sess.close()
        return render_template('add_files.html', used_memory=used_memory,
                               available_memory=available_memory, is_pro=user.is_account_pro, message='', files=files,
                               is_private=is_private, title_dir=title, description=description)
    else:
        if request.form.get('search') == 'True':
            if request.form.get('author').strip() != '':
                author = request.form.get('author')
            else:
                author = 'none'

            if request.form.get('cellname').strip() != '':
                cellname = request.form.get('cellname')
            else:
                cellname = 'none'
            return redirect(f'/directories/author={author}/cellname={cellname}')

        keys = list(request.form.keys())
        message = ''

        for key in keys:
            if key[:4] == 'del_':
                os.remove(f'{dir_path}/{key[4:]}')

        files = request.files.getlist('files')
        summary_weight = sum([os.path.getsize(f'{dir_path}/{file}') for file in os.listdir(dir_path)])

        available_memory = user.available_memory
        title = request.form.get('title')

        os.rename(dir_path, f'{PATH_TO_FILES}/{current_user.email}/{title}')
        for file in files:
            file.seek(0, os.SEEK_END)
            summary_weight += file.tell()
            file.seek(0, 0)

            if summary_weight <= available_memory * 2 ** 30 and file.filename != '':
                file.save(f'{PATH_TO_FILES}/{current_user.email}/{title}/{file.filename}')
            else:
                message = 'Вся доступная память использована!'

        cell.weight_of_directory = summary_weight / 2 ** 30
        cell.cellname = title
        cell.description = request.form.get('description')

        if request.form.get('is_private') is not None:
            cell.is_private = True
            if request.form.get('password'):
                cell.set_password(request.form.get('password'))
        else:
            cell.is_private = False
            cell.hashed_password = ''

        cell.path = f'{PATH_TO_FILES}/{current_user.email}/{title}'

        user.available_memory = get_user_available_memory(user)
        sess.commit()
        sess.close()

        return redirect(f'/edit_directory/{dir_id}')


@app.route('/view_files/<int:cell_id>', methods=['GET', 'POST'])
def view_files(cell_id: int):
    if request.method == 'GET':
        sess = db_session.create_session()
        cell = sess.query(Cell).get(cell_id)
        cell: Cell

        if cell.is_private and current_user.id != cell.user_id:
            password = session.get(f'cell_id:{cell_id}')
            if password is None or not cell.check_password(password):
                return redirect(f'../password/{cell_id}')

        path = cell.path
        dir_title = cell.cellname

        files = os.listdir(path)
        if isinstance(current_user, AnonymousUserMixin):
            sess.close()
            return render_template('view_files.html',
                                   message='', files=files, dir_title=dir_title)

        user = sess.query(User).get(current_user.id)
        user: User
        user.available_memory = get_user_available_memory(user)
        available_memory = round(user.available_memory, 4)

        if user.is_account_pro:
            used_memory = 10 - available_memory
        else:
            used_memory = 5 - available_memory

        used_memory = round(used_memory, 4)

        is_pro = user.is_account_pro
        sess.commit()
        sess.close()
        return render_template('view_files.html', used_memory=used_memory,
                               available_memory=available_memory, is_pro=is_pro,
                               message='', files=files, dir_title=dir_title)
    else:
        if request.form.get('search') == 'True':
            if request.form.get('author').strip() != '':
                author = request.form.get('author')
            else:
                author = 'none'

            if request.form.get('cellname').strip() != '':
                cellname = request.form.get('cellname')
            else:
                cellname = 'none'
            return redirect(f'/directories/author={author}/cellname={cellname}')
        else:
            filename = request.form.get('download')
            sess = db_session.create_session()
            cell = sess.query(Cell).get(cell_id)
            cell: Cell
            return send_file(f'{cell.path}/{filename}', as_attachment=True)


@app.route('/password/<int:cell_id>', methods=['GET', 'POST'])
@login_required
def password_for_private_cell(cell_id):
    sess = db_session.create_session()
    cell = sess.query(Cell).get(cell_id)
    cell: Cell
    sess.close()
    password = session.get(f'cell_id:{cell.id}')
    if cell.check_password(password):
        return redirect(f'../view_files/{cell_id}')
    if current_user.id == cell.user_id:
        return redirect(f'../view_files/{cell_id}')
    if request.method == 'GET':
        return render_template('password.html', cellname=cell.cellname, message='')
    else:
        password = request.form.get('password')

        if password is None or not cell.check_password(password):
            return render_template('password.html', cellname=cell.cellname, message='Пароль не введен или неверный!')
        session[f'cell_id:{cell_id}'] = password
        return redirect(f'../view_files/{cell_id}')


@app.route('/create_code', methods=['GET', 'POST'])
def add_code_for_pro():
    if current_user.id != ADMIN_ID:
        abort(403)

    if request.method == 'GET':
        return render_template('create_code.html', message='')
    else:
        code_value = request.form.get('code')
        usings = request.form.get('usings')
        sess = db_session.create_session()
        if sess.query(Codes).filter(Codes.code == code_value).first():
            return render_template('create_code.html', message='Такой код уже создан!')
        code = Codes()
        code.code = code_value
        code.remain_using = abs(int(usings))
        sess.add(code)
        sess.commit()
        sess.close()
        return redirect(request.path)


@app.route('/enter_code', methods=['GET', 'POST'])
@login_required
def enter_code():
    if request.method == 'GET':
        return render_template('enter_code.html', message='')
    else:
        code_value = request.form.get('code')
        sess = db_session.create_session()
        code = sess.query(Codes).filter(Codes.code == code_value).first()
        code: Codes

        if code is None:
            sess.close()
            return render_template('enter_code.html', message='Код неверен!')
        elif code.remain_using == 0:
            sess.close()
            return render_template('enter_code.html', message='Код уже был использован!')

        user = sess.query(User).get(current_user.id)
        user: User
        user.is_account_pro = True
        code.remain_using -= 1

        sess.commit()
        sess.close()
        return redirect('/')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'GET':
        name = current_user.username
        email = current_user.email
        available_memory = round(current_user.available_memory, 4)
        return render_template('profile.html', username=name, email=email, memory=available_memory)
    else:
        form = request.form
        if form.get('my-cells') == 'True':
            return redirect(f'/directories/author={current_user.username}/cellname=none')
        elif form.get('get-pro') == 'True':
            return redirect('/enter_code')
        elif form.get('edit-profile') == 'True':
            return redirect('/change_username')
        else:
            return redirect('/logout')


@app.route('/change_username', methods=['GET', 'POST'])
@login_required
def change_username():
    if request.method == 'GET':
        return render_template('change_username.html', message='')
    else:
        new_username = request.form.get('new_username')
        sess = db_session.create_session()
        if sess.query(User).filter(User.username == new_username).first():
            sess.close()
            return render_template('change_username.html', message='Пользователь с таким именем уже существует!')
        user = sess.query(User).get(current_user.id)
        user: User
        user.username = new_username
        sess.commit()
        sess.close()
        return redirect('/profile')

def get_user_available_memory(user: User) -> float:
    start = 10 if user.is_account_pro else 5

    path_to_user = f'{PATH_TO_FILES}/{user.email}'
    if os.path.exists(path_to_user):
        for cell in os.listdir(path_to_user):
            for file in os.listdir(f'{path_to_user}/{cell}'):
                start -= os.path.getsize(f'{path_to_user}/{cell}/{file}') / 2 ** 30

    return start


def delete_directory(dir_id, user_id) -> None:
    sess = db_session.create_session()
    cell = sess.query(Cell).get(dir_id)
    cell: Cell
    sess.delete(cell)
    shutil.rmtree(cell.path)

    user = sess.query(User).get(user_id)
    user: User
    user.available_memory = get_user_available_memory(user)

    sess.commit()
    sess.close()


def clear_zips() -> None:
    for file in os.listdir(PATH_TO_ZIPS):
        os.remove(f'{PATH_TO_ZIPS}/{file}')

if __name__ == '__main__':
    db_session.global_init('db/database.db')

    sess = db_session.create_session()
    for cell in sess.query(Cell).all():
        sess.delete(cell)
    sess.commit()

    app.run(port=8080)
