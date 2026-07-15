#
# cMusic.br
# Feito pelo Gabe Clevin K
# 
from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
import sqlite3
import os
import base64
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
SECRET_KEY = 'key123'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db():
    conn = sqlite3.connect('cmusicbr.sqlite')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS musicas (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,           -- Nome que aparece no app
            filename TEXT NOT NULL,        -- Nome real do arquivo
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    
    if not conn.execute("SELECT 1 FROM users WHERE username = 'admin'").fetchone():
        hashed = generate_password_hash('123456')
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', hashed))
        conn.commit()
    conn.close()

def validate_token(token):
    if not token:
        return False
    try:
        decoded = base64.b64decode(token).decode()
        return SECRET_KEY in decoded
    except:
        return False


@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if len(username) < 3 or len(password) < 4:
        return jsonify({'success': False, 'message': 'Usuário ou senha muito curtos'}), 400
    
    conn = get_db()
    try:
        hashed = generate_password_hash(password)
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
        conn.commit()
        return jsonify({'success': True, 'message': 'Usuário cadastrado com sucesso!'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Usuário já existe'}), 400
    finally:
        conn.close()


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password'], password):
        token = base64.b64encode(f"{datetime.datetime.now().timestamp()}|{user['id']}|{SECRET_KEY}".encode()).decode()
        return jsonify({'success': True, 'token': token, 'username': username})
    
    return jsonify({'success': False, 'message': 'Usuário ou senha incorretos'}), 401


@app.route('/myzuka/browse', methods=['GET'])
def list_musicas():
    token = request.args.get('token')
    if not validate_token(token):
        return jsonify({'success': False, 'message': 'Token inválido'}), 401
    
    conn = get_db()
    musicas = conn.execute("SELECT id, title FROM musicas ORDER BY title").fetchall()
    conn.close()
    
    return jsonify({
        'success': True,
        'musics': [dict(m) for m in musicas]
    })



@app.route('/myzuka/upload', methods=['POST'])
def upload_music():
    token = request.form.get('token')
    if not validate_token(token):
        return jsonify({'success': False, 'message': 'Token inválido'}), 401
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    title = request.form.get('title', '').strip()
    
    if file.filename == '' or not title:
        return jsonify({'success': False, 'message': 'Título e arquivo são obrigatórios'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
  
    conn = get_db()
    conn.execute("INSERT INTO musicas (title, filename) VALUES (?, ?)", (title, filename))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': 'Música enviada com sucesso!',
        'title': title
    })


@app.route('/myzuka/play/<int:music_id>', methods=['GET'])
def play_music(music_id):
    token = request.args.get('token')
    if not validate_token(token):
        return jsonify({'success': False, 'message': 'Token inválido'}), 401
    
    conn = get_db()
    music = conn.execute("SELECT filename FROM musicas WHERE id = ?", (music_id,)).fetchone()
    conn.close()
    
    if not music:
        abort(404)
    
    filepath = os.path.join(UPLOAD_FOLDER, music['filename'])
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='audio/mpeg', as_attachment=False)
    else:
        abort(404)


if __name__ == '__main__':
    init_db()
    print("cMusic.br")
    app.run(host='0.0.0.0', port=5000, debug=True)
