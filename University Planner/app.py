# app.py (COMPLETE UPDATED VERSION)
from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app, origins=["*"])

def get_db():
    conn = sqlite3.connect('planner.db', timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            professor TEXT NOT NULL,
            attendance INTEGER DEFAULT 0,
            total_classes INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER,
            title TEXT NOT NULL,
            deadline TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (subject_id) REFERENCES subjects (id)
        )''')
        conn.commit()

@app.route('/api/dashboard')
def dashboard():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM subjects')
        subjects = c.fetchall()
        low_attendance = [s for s in subjects if s[5] > 0 and (s[4]/s[5]*100) < 75]
        
        c.execute('SELECT a.title, s.code, a.deadline FROM assignments a JOIN subjects s ON a.subject_id = s.id WHERE a.completed = 0 ORDER BY a.deadline LIMIT 3')
        assignments = c.fetchall()
        
        return jsonify({
            'today_classes': [{'code': s[1], 'name': s[2], 'professor': s[3]} for s in subjects[:3]],
            'low_attendance': len(low_attendance),
            'upcoming_assignments': [{'title': a[0], 'subject_code': a[1], 'deadline': a[2]} for a in assignments],
            'total_subjects': len(subjects)
        })

@app.route('/api/subjects', methods=['GET', 'POST'])
def subjects():
    with get_db() as conn:
        c = conn.cursor()
        if request.method == 'POST':
            data = request.json
            try:
                c.execute("INSERT INTO subjects (code, name, professor, attendance, total_classes) VALUES (?, ?, ?, ?, ?)",
                          (data['code'], data['name'], data['professor'], data['attendance'], data['total_classes']))
                conn.commit()
            except sqlite3.IntegrityError:
                return jsonify({'error': 'Subject code already exists'}), 400
        
        c.execute('SELECT * FROM subjects')
        subjects_list = []
        for row in c.fetchall():
            pct = round((row[4]/row[5]*100), 1) if row[5] > 0 else 0
            subjects_list.append({
                'id': row[0], 'code': row[1], 'name': row[2],
                'professor': row[3], 'attendance': row[4],
                'total_classes': row[5], 'attendance_pct': pct
            })
        return jsonify(subjects_list)

@app.route('/api/subjects/<int:subject_id>', methods=['PUT', 'DELETE'])
def manage_subject(subject_id):
    with get_db() as conn:
        c = conn.cursor()
        if request.method == 'PUT':
            data = request.json
            c.execute("UPDATE subjects SET attendance = ?, total_classes = ? WHERE id = ?",
                      (data['attendance'], data['total_classes'], subject_id))
            conn.commit()
        elif request.method == 'DELETE':
            c.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
            conn.commit()
        return jsonify({'message': 'Success'})

@app.route('/api/subjects/<int:subject_id>/attendance', methods=['POST'])
def update_attendance(subject_id):
    data = request.json
    action = data['action']
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT attendance, total_classes FROM subjects WHERE id = ?", (subject_id,))
        result = c.fetchone()
        if result:
            att, total = result
            if action == 'increment':
                att = min(att + 1, total)
            elif action == 'decrement':
                att = max(att - 1, 0)
            c.execute("UPDATE subjects SET attendance = ? WHERE id = ?", (att, subject_id))
            conn.commit()
            pct = round((att/total*100), 1) if total > 0 else 0
            return jsonify({'attendance': att, 'total_classes': total, 'attendance_pct': pct})
    return jsonify({'error': 'Subject not found'}), 404

@app.route('/api/assignments', methods=['GET', 'POST'])
def assignments():
    with get_db() as conn:
        c = conn.cursor()
        if request.method == 'POST':
            data = request.json
            c.execute("INSERT INTO assignments (subject_id, title, deadline) VALUES (?, ?, ?)",
                      (data['subject_id'], data['title'], data['deadline']))
            conn.commit()
        
        c.execute('''SELECT a.id, a.subject_id, a.title, a.deadline, a.completed, s.code, s.name 
                     FROM assignments a JOIN subjects s ON a.subject_id = s.id 
                     ORDER BY a.deadline''')
        assignments_list = []
        for row in c.fetchall():
            assignments_list.append({
                'id': row[0], 'subject_id': row[1], 'title': row[2], 
                'deadline': row[3], 'completed': row[4],
                'subject_code': row[5], 'subject_name': row[6]
            })
        return jsonify(assignments_list)

@app.route('/api/assignments/<int:assignment_id>', methods=['PUT', 'DELETE'])
def manage_assignment(assignment_id):
    with get_db() as conn:
        c = conn.cursor()
        if request.method == 'PUT':
            data = request.json
            c.execute("UPDATE assignments SET completed = ? WHERE id = ?", (data['completed'], assignment_id))
            conn.commit()
        elif request.method == 'DELETE':
            c.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))
            conn.commit()
        return jsonify({'message': 'Success'})

if __name__ == '__main__':
    init_db()
    print("Backend running on http://127.0.0.1:8000")
    print("Test: http://127.0.0.1:8000/api/dashboard")
    app.run(host='127.0.0.1', port=8000, debug=True)
