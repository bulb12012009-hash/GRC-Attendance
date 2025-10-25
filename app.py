from flask import Flask, request, render_template_string, redirect, url_for, flash
import sqlite3
from datetime import datetime
import hashlib  # For simple password hashing if needed

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this!

# Initialize DB
def init_db():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id TEXT PRIMARY KEY, name TEXT, role TEXT)''')  # role: 'student', 'management', etc.
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (user_id TEXT, timestamp TEXT, FOREIGN KEY(user_id) REFERENCES users (id))''')
    # Sample data (add your users here)
    sample_users = [
        ('001', 'John Doe', 'student'),
        ('002', 'Jane Smith', 'management'),
        ('003', 'Admin User', 'admin')
    ]
    c.executemany('INSERT OR IGNORE INTO users VALUES (?, ?, ?)', sample_users)
    conn.commit()
    conn.close()

init_db()

# Simple HTML template for scan page
SCAN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head><title>GRC Universal Attendance Scanner</title></head>
<body>
    <h1>Scan Attendance (Any Role Allowed)</h1>
    <form method="POST">
        <label>User ID: <input type="text" name="user_id" required></label><br><br>
        <input type="submit" value="Scan & Mark">
    </form>
    {% with messages = get_flashed_messages() %}
        {% if messages %}
            <ul>
            {% for message in messages %}
                <li>{{ message }}</li>
            {% endfor %}
            </ul>
        {% endif %}
    {% endwith %}
    <p><a href="/">Home</a></p>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def scan():
    if request.method == 'POST':
        user_id = request.form['user_id'].strip()
        conn = sqlite3.connect('attendance.db')
        c = conn.cursor()
        
        # Check if user exists (no section/role restriction)
        c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        if not user:
            flash('User not found! Access denied.')
            conn.close()
            return redirect(url_for('scan'))
        
        # Mark attendance (universal - no section check)
        timestamp = datetime.now().isoformat()
        c.execute('INSERT INTO attendance (user_id, timestamp) VALUES (?, ?)', (user_id, timestamp))
        conn.commit()
        conn.close()
        
        flash(f'Attendance marked for {user[1]} ({user[2]}) at {timestamp}!')
        return redirect(url_for('scan'))
    
    return render_template_string(SCAN_TEMPLATE)

@app.route('/view')
def view_attendance():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('''SELECT u.name, u.role, a.timestamp FROM attendance a
                 JOIN users u ON a.user_id = u.id ORDER BY a.timestamp DESC''')
    records = c.fetchall()
    conn.close()
    return f'<h1>Attendance Log</h1><ul>' + ''.join([f'<li>{r[0]} ({r[1]}) - {r[2]}</li>' for r in records[:50]]) + '</ul>'  # Last 50

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
