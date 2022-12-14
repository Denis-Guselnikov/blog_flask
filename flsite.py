import sqlite3
import os

from flask import Flask, render_template, request, g, flash, abort, url_for, redirect, make_response
from FDataBase import FDataBase
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from UserLogin import UserLogin
from forms import LoginForm, RegisterForm
from admin.admin import admin


# Конфигурации
DATABASE = '/tmp/flsite.db'  # путь к БД
DEBUG = True
SECRET_KEY = 'fjkwehruiouvsdf><piwewepof>pweir6234sffd'
MAX_CONTENT_LENGTH = 1024 * 1024

app = Flask(__name__)
app.config.from_object(__name__)

# Полный путь к БД, бд будет находится в рабочем каталоге нашего приложения
# Почему root_path: во flask может быть несколько приложений и у каждого своя БД и корневой коталог
app.config.update(dict(DATABASE=os.path.join(app.root_path, 'flsite.db')))  # Переопределение пути к БД

app.register_blueprint(admin, url_prefix='/admin')

login_manager = LoginManager(app)  # Через login_manager будем управлять процессом авторизации
login_manager.login_view = 'login'  # перекинуть незарегестрированного пользователя на login
login_manager.login_message = 'Авторизируйтесь для доступа к закрытым страницам'
login_manager.login_message_category = 'success'


@login_manager.user_loader
def load_user(user_id):
    print("load_user")
    return UserLogin().fromDB(user_id, dbase)


# Функция для установления соединения с БД
def connect_db():
    conn = sqlite3.connect(app.config['DATABASE'])  # Метод connect принимает путь где находится БД
    conn.row_factory = sqlite3.Row  # Это для того что-бы записи в БД были представленны не ввиде
    return conn
    # картежа а ввиде славаря


# Вспомогательная функция для создания таблиц в БД
def create_db():
    db = connect_db()  # вызываем функцию
    with app.open_resource('sq_db.sql', mode='r') as f:  # менеджер контекста для прочтения файла sq_db.sql
        db.cursor().executescript(f.read())  # обращаемся к классу cursor и выполняем метод для запуска скриптов из
    db.commit()  # файла sq_db.sql
    db.close()  # .commit() запись всех изменений в БД


# Соединение с БД
def get_db():
    if not hasattr(g, 'link_db'):  # g-Глобальная переменная в которую записывают любую пользовательскую инфу.
        g.link_db = connect_db()  # Проверяем существует в g свойство link_db
    return g.link_db

dbase = None
# Установление соединения с БД перед выполнением запроса
@app.before_request
def before_request():
    global dbase
    db = get_db()
    dbase = FDataBase(db)


# Закрываем соединение с БД если оно было установленно
@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'link_db'):
        g.link_db.close()


@app.route('/')
def index():
    return render_template('index.html', menu=dbase.getMenu(), posts=dbase.getPostsAnonce())
    # Метод .getMenu возвращает коллекцию из словарей .getPostsAnonce


@app.route('/add_post', methods=['POST', 'GET'])
def addPost():
    if request.method == "POST":
        if len(request.form['name']) > 4 and len(request.form['post']) > 10:
            res = dbase.addPost(request.form['name'], request.form['post'], request.form['url'])
            if not res:
                flash('Ошибка добавления статьи', category='error')
            else:
                flash('Статья добавлена успешно', category='success')
        else:
            flash('Ошибка добавления статьи', category='error')

    return render_template('add_post.html', menu=dbase.getMenu(), title="Добавление статьи")


@app.route('/post/<alias>')
@login_required
def showPost(alias):
    title, post = dbase.getPost(alias)  # getPost берёт данные из базы данных
    if not title:
        abort(404)

    return render_template('post.html', menu=dbase.getMenu(), title=title, post=post)


@app.route("/login", methods=["POST", "GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    form = LoginForm()
    if form.validate_on_submit():
        user = dbase.getUserByEmail(form.email.data)
        if user and check_password_hash(user['psw'], form.psw.data):
            userlogin = UserLogin().create(user)
            rm = form.remember.data
            login_user(userlogin, remember=rm)
            return redirect(request.args.get('next') or url_for('profile'))

        flash("Неверная пара логин/пароль", category='error')

    return render_template('login.html', menu=dbase.getMenu(), title="Авторизация", form=form)


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hash = generate_password_hash(request.form['psw'])
        res = dbase.addUser(form.name.data, form.email.data, hash)
        if res:
            flash("Вы успешно зарегистрированы", "success")
            return redirect(url_for('login'))
        else:
            flash("Ошибка при добавлении в БД", "error")

    return render_template("register.html", menu=dbase.getMenu(), title="Регистрация", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта", category='success')
    return redirect(url_for('login'))


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', menu=dbase.getMenu(), title="Профиль")


@app.route('/userava')
@login_required
def userava():
    img = current_user.getAvatar(app)  # current_user текущий пользователь
    if not img:
        return ""

    h = make_response(img)                  # make_response создание объекта запроса
    h.headers['Content-Type'] = 'image/png'
    return h


@app.route('/upload', methods=["POST", "GET"])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files['file']  # берётся поле file из объекта request которое сходится с загрузкой в profile
        if file and current_user.verifyExt(file.filename):   # verifyExt метод отвечающий за расширение файла png
            try:
                img = file.read()
                res = dbase.updateUserAvatar(img, current_user.get_id())
                if not res:
                    flash("Ошибка обновления аватара", "error")
                flash("Аватар обновлен", "success")
            except FileNotFoundError as e:
                flash("Ошибка чтения файла", "error")
        else:
            flash("Ошибка обновления аватара", "error")

    return redirect(url_for('profile'))


if __name__ == "__main__":
    app.run(debug=True)
