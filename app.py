from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# [중요] 세션 암호화 키 (팀원들과 공유하는 비밀번호 같은 것)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# ==========================================
# 1. 데이터베이스(DB) 초기화 및 설정
# ==========================================
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # 1. 회원 테이블 (기존 유지 + role)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,  -- 로그인 ID
            password TEXT NOT NULL,         -- 비밀번호
            nickname TEXT NOT NULL,         -- 화면 표시용 이름
            role TEXT DEFAULT 'USER'        -- 권한 (USER/ADMIN)
        )
    ''')
    
    # 2. 게시글 테이블 (대폭 업그레이드!)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,                 -- [NEW] 글 제목
            content TEXT NOT NULL,               -- 글 내용
            writer_id TEXT NOT NULL,             -- [NEW] 작성자 로그인 ID (나중에 수정/삭제 권한 확인용)
            writer_nickname TEXT NOT NULL,       -- [NEW] 작성자 닉네임 (화면에 바로 보여주기 위함)
            category TEXT DEFAULT 'free',        -- [NEW] 카테고리 (free:자유, review:후기, qna:질문)
            views INTEGER DEFAULT 0,             -- [NEW] 조회수
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- [NEW] 작성 시간 (자동 입력됨)
        )
    ''')

    # 3. 댓글 테이블 (팀원이 여유 되면 구현하라고 미리 만들어둠)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,            -- 어느 게시글에 달린 댓글인지 (posts.id 연결)
            writer_nickname TEXT NOT NULL,       -- 댓글 작성자 닉네임
            content TEXT NOT NULL,               -- 댓글 내용
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 작성 시간
            FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE -- 게시글 지워지면 댓글도 삭제
        )
    ''')

    conn.commit()
    conn.close()
# ==========================================
# 2. 메인 화면 & 인증(로그인/회원가입)
# ==========================================

# 메인 홈 화면
@app.route('/')
def home():
    user_info = session.get('user') # 로그인했는지 확인
    return render_template('index.html', user=user_info)

# 회원가입 기능
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        nickname = request.form['nickname']
        
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            # role은 기본값 'USER'로 저장
            cursor.execute("INSERT INTO users (username, password, nickname, role) VALUES (?, ?, ?, 'USER')", 
                           (username, password, nickname))
            conn.commit()
            conn.close()
            return redirect(url_for('login')) # 가입 성공 시 로그인 페이지로 이동
        except Exception as e:
            return f"회원가입 실패 (아이디 중복 등): {e}"

    return render_template('register.html')

# 로그인 기능
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row # 데이터를 딕셔너리처럼(이름으로) 꺼내기 위해 필수
        cursor = conn.cursor()
        
        # 아이디/비번 확인
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            # 로그인 성공! 세션에 정보 저장 (닉네임, 권한 등)
            session['user'] = {
                'username': user['nickname'],  # 화면에 보여줄 닉네임
                'id': user['username'],        # DB 찾을 때 쓸 아이디
                'role': user['role']           # 관리자 여부 (USER/ADMIN)
            }
            return redirect(url_for('home'))
        else:
            return "아이디 또는 비밀번호가 틀렸습니다."
    
    return render_template('login.html')

# 로그아웃 기능
@app.route('/logout')
def logout():
    session.pop('user', None) # 세션 삭제
    return redirect(url_for('home'))

# ==========================================
# 3. 관리자(Admin) 기능
# ==========================================

# 관리자 페이지 보기
@app.route('/admin')
def admin_page():
    # 관리자인지 체크 (보안)
    user_info = session.get('user')
    if not user_info or user_info['role'] != 'ADMIN':
        return "<script>alert('관리자만 접근 가능합니다!'); history.back();</script>"

    # 모든 회원 정보 가져오기
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()

    return render_template('admin.html', users=users)

# 회원 정보 수정 (관리자가 수정 버튼 눌렀을 때)
@app.route('/admin/update', methods=['POST'])
def admin_update_user():
    # 관리자 체크
    if session.get('user')['role'] != 'ADMIN':
        return "권한이 없습니다."

    target_id = request.form['id']          # 수정할 대상의 번호
    new_nickname = request.form['nickname'] # 변경할 닉네임
    new_role = request.form['role']         # 변경할 권한

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET nickname = ?, role = ? WHERE id = ?", (new_nickname, new_role, target_id))
    conn.commit()
    conn.close()

    return redirect(url_for('admin_page'))

# ==========================================
# 4. 기능 페이지 (챗봇, 커뮤니티)
# ==========================================

# 챗봇 화면
@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

# [API] 챗봇 대화 처리 (AI 연결 부분)
@app.route('/api/ask', methods=['POST'])
def ask_ai():
    user_input = request.json.get('message')
    
    # --- [TODO] 여기에 나중에 OpenAI 연결 코드를 넣으세요 ---
    # 지금은 테스트용 가짜 응답
    ai_response = f"AI: '{user_input}'에 어울리는 안주를 찾고 있어요! (아직 개발 중)"
    
    return jsonify({'response': ai_response})

# 커뮤니티 목록 보기
@app.route('/community')
def community():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # 최신글이 위에 오도록 정렬 (ORDER BY id DESC)
    cursor.execute("SELECT * FROM posts ORDER BY id DESC")
    posts = cursor.fetchall()
    conn.close()
    
    # 로그인한 사용자 정보도 같이 넘겨줌 (글쓰기 권한 확인용)
    return render_template('community.html', posts=posts, user=session.get('user'))

# 커뮤니티 글쓰기
@app.route('/community/write', methods=['POST'])
def write_post():
    # 로그인 안 한 사람이 주소창으로 억지로 들어오면 막기
    if 'user' not in session:
        return "로그인이 필요합니다!"

    username = session['user']['username'] # 로그인한 사람의 닉네임 자동 입력
    content = request.form['content']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO posts (username, content) VALUES (?, ?)", (username, content))
    conn.commit()
    conn.close()
    
    return redirect(url_for('community'))

# ==========================================
# 5. 서버 실행
# ==========================================
if __name__ == '__main__':
    init_db() # 서버 켤 때마다 DB/테이블 있는지 확인
    # host='0.0.0.0'을 넣어야 팀원들이 내 IP로 접속 가능
    app.run(host='192.168.0.239', port=5000, debug=True)