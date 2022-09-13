import sqlite3
import os

from flask import Flask, render_template, request, g, flash, abort, url_for, redirect
from FDataBase import FDataBase
from werkzeug.security import generate_password_hash, check_password_hash


# Конфигурации
DATABASE = '/tmp/flsite.db'  # путь к БД
DEBUG = True
SECRET_KEY = 'fjkwehruiouvsdf><piwewepof>pweir6234sffd'

app = Flask(__name__)
app.config.from_object(__name__)

# Полный путь к БД, бд будет находится в рабочем каталоге нашего приложения
# Почему root_path: во flask может быть несколько приложений и у каждого своя БД и корневой коталог
app.config.update(dict(DATABASE=os.path.join(app.root_path, 'flsite.db')))  # Переопределение пути к БД


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
def showPost(alias):
    title, post = dbase.getPost(alias)  # getPost берёт данные из базы данных
    if not title:
        abort(404)

    return render_template('post.html', menu=dbase.getMenu(), title=title, post=post)


@app.route('/login')
def login():
    return render_template('login.html', menu=dbase.getMenu(), title="Авторизация")


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        if len(request.form['name']) > 4 and len(request.form['email']) > 4 and \
             len(request.form['psw']) > 4 and request.form['psw'] == request.form['psw2']:
            hash = generate_password_hash(request.form['psw'])
            res = dbase.addUser(request.form['name'], request.form['email'], hash)
            if res:
                flash('Вы успешно зарегестрировались!', category='success')
                return redirect(url_for('login'))
            else:
                flash('Ошибка при регистрации!', category='error')
        else:
            flash('Не верно заполнены поля', category='error')

    return render_template('register.html', menu=dbase.getMenu(), title="Регистрация")


if __name__ == "__main__":
    app.run(debug=True)
