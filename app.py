import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

# --- DB 연결 함수 ---
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            nickname TEXT NOT NULL,
            role TEXT DEFAULT 'USER'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            writer_id TEXT NOT NULL,
            writer_nickname TEXT NOT NULL,
            category TEXT DEFAULT 'ETC',
            views INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# --- 라우팅 (페이지 연결) ---

@app.route('/')
def home():
    # 메인 페이지 (테이스트메이트.html 디자인)
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['userid'] # HTML name="userid"
        password = request.form['userpw'] # HTML name="userpw"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user'] = {'username': user['nickname'], 'id': user['username'], 'role': user['role']}
            return redirect(url_for('home'))
        else:
            return "<script>alert('아이디 또는 비밀번호가 틀립니다.'); history.back();</script>"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # HTML 폼의 name 속성과 맞춰야 합니다.
        username = request.form['userid']
        password = request.form['userpw']
        nickname = request.form['username'] # HTML에서는 '이름'을 닉네임으로 씁시다
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password, nickname) VALUES (?, ?, ?)", 
                           (username, password, nickname))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except:
            return "<script>alert('이미 존재하는 아이디입니다.'); history.back();</script>"
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/chatbot')
def chatbot():
    return render_template('aichat.html')

# 커뮤니티 메인 (카테고리 고르는 화면)
@app.route('/community')
def community():
    return render_template('community.html')

# 게시판 목록 보기 (SOLO, DATE, WORK, ETC 통합 처리!)
@app.route('/community/list/<category>')
def post_list(category):
    # 한글 제목 변환
    titles = {'SOLO': '🍱 혼밥 커뮤니티', 'DATE': '💑 데이트 커뮤니티', 'WORK': '🍻 회식 커뮤니티', 'ETC': '🌈 기타 커뮤니티'}
    page_title = titles.get(category, '커뮤니티')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts WHERE category = ? ORDER BY id DESC", (category,))
    posts = cursor.fetchall()
    conn.close()
    
    # board.html 이라는 하나의 파일로 모든 게시판을 보여줍니다.
    return render_template('board.html', posts=posts, category=category, page_title=page_title)

@app.route('/community/write', methods=['GET', 'POST'])
def write():
    if not session.get('user'):
        return "<script>alert('로그인이 필요합니다!'); location.href='/login';</script>"

    if request.method == 'POST':
        category = request.form['category']
        title = request.form['title']
        content = request.form['content']
        writer_id = session['user']['id']
        writer_nickname = session['user']['username']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO posts (title, content, writer_id, writer_nickname, category) VALUES (?, ?, ?, ?, ?)",
                       (title, content, writer_id, writer_nickname, category))
        conn.commit()
        conn.close()
        return redirect(url_for('post_list', category=category)) # 쓴 게시판으로 이동

    return render_template('write.html')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)