import sqlite3
import os
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
DB_NAME = "project_monitor.db"

AUTHORIZED_PROJECT_KEYS = {
    "TATA-MUM-4": {"project_id": 3, "project_name": "Mumbai Metro Line 4 Extension", "contractor": "Tata Projects"},
    "LNT-NAG-3": {"project_id": 1, "project_name": "Nagpur Outer Ring Road (Sec 3)", "contractor": "L&T Infrastructure Ltd."},
    "MEGA-PUN-2": {"project_id": 2, "project_name": "Pune-Nashik High-Speed Rail Link", "contractor": "Mega Infra Corp"}
}

def init_db():
    with sqlite3.connect(DB_NAME, timeout=10) as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cost TEXT NOT NULL,
                progress INTEGER CHECK (progress BETWEEN 0 AND 100),
                risk_level TEXT CHECK (risk_level IN ('Low', 'Medium', 'High')),
                predicted_delay TEXT,
                predicted_overrun TEXT,
                contractor TEXT NOT NULL,
                region TEXT NOT NULL,
                assigned_officer TEXT NOT NULL,
                last_reported TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                organization TEXT NOT NULL,
                assigned_project_id INTEGER,
                region TEXT NOT NULL
            )
        ''')

        cursor.execute("SELECT COUNT(*) FROM projects")
        if cursor.fetchone()[0] == 0:
            cursor.executemany('''
                INSERT INTO projects (name, cost, progress, risk_level, predicted_delay, predicted_overrun, contractor, region, assigned_officer, last_reported)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                ("Nagpur Outer Ring Road (Sec 3)", "₹1,250 Cr", 62, "High", "8 Months", "₹45 Cr", "L&T Infrastructure Ltd.", "Maharashtra Division", "rajesh.m@mospi.gov.in", "2026-09-20"),
                ("Pune-Nashik High-Speed Rail Link", "₹16,000 Cr", 40, "Medium", "3 Months", "₹120 Cr", "Mega Infra Corp", "Maharashtra Division", "rajesh.m@mospi.gov.in", "2026-09-18"),
                ("Mumbai Metro Line 4 Extension", "₹14,500 Cr", 85, "Low", "0 Months", "₹0 Cr", "Tata Projects", "Maharashtra Division", "rajesh.m@mospi.gov.in", "2026-09-22")
            ])
            
            cursor.executemany('''
                INSERT INTO users (full_name, email, password, role, organization, assigned_project_id, region)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', [
                ('Rajesh Kumar', 'rajesh.m@mospi.gov.in', 'officer123', 'Government Officer', 'MoSPI IPMD', None, 'Maharashtra Division'),
                ('MoSPI System Administrator', 'admin@mospi.gov.in', 'admin123', 'Platform Administrator', 'MoSPI Central Division', None, 'Maharashtra Division')
            ])
            conn.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/projects', methods=['GET'])
def get_projects():
    with sqlite3.connect(DB_NAME, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY CASE WHEN risk_level = 'High' THEN 1 WHEN risk_level = 'Medium' THEN 2 ELSE 3 END")
        rows = cursor.fetchall()
        projects = [dict(row) for row in rows]
    return jsonify({"status": "success", "data": projects})

@app.route('/api/admin/users', methods=['GET'])
def get_all_users():
    with sqlite3.connect(DB_NAME, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, full_name, email, role, organization, assigned_project_id, region FROM users")
        rows = cursor.fetchall()
        users = [dict(row) for row in rows]
    return jsonify({"status": "success", "data": users})

@app.route('/api/simulate', methods=['POST'])
def simulate():
    data = request.get_json(force=True) or {}
    clearance_days = int(data.get('clearance_days', 10))
    project_id = int(data.get('project_id', 1))
    
    if project_id == 1:
        base_delay = 8
        base_overrun = 45
    elif project_id == 2:
        base_delay = 3
        base_overrun = 120
    else:
        base_delay = 0
        base_overrun = 0

    simulated_delay = max(0, round((clearance_days / 45) * base_delay))
    saved_cost = max(0, base_overrun - round((clearance_days / 45) * base_overrun))
    
    return jsonify({
        "status": "success",
        "simulated_delay_months": simulated_delay,
        "estimated_cost_saved_cr": saved_cost
    })

@app.route('/api/contractor/submit', methods=['POST'])
def contractor_submit():
    try:
        data = request.get_json(force=True) or {}
        project_id = int(data.get('project_id', 1))
        user_assigned_id = data.get('user_assigned_project_id')
        user_role = data.get('user_role')
        new_progress = int(data.get('progress', 65))

        if user_role != 'Platform Administrator' and user_assigned_id and int(user_assigned_id) != project_id:
            return jsonify({
                "status": "error",
                "message": "UNAUTHORIZED ACCESS: You are not assigned to modify this infrastructure project!"
            }), 403

        new_risk = "High" if new_progress < 70 else ("Medium" if new_progress < 85 else "Low")
        predicted_delay = f"{max(0, round((100 - new_progress) / 5))} Months"
        predicted_overrun = f"₹{max(0, round((100 - new_progress) * 1.2))} Cr"

        with sqlite3.connect(DB_NAME, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE projects 
                SET progress = ?, risk_level = ?, predicted_delay = ?, predicted_overrun = ?, last_reported = DATE('now')
                WHERE id = ?
            ''', (new_progress, new_risk, predicted_delay, predicted_overrun, project_id))
            conn.commit()

        return jsonify({
            "status": "success",
            "message": "Contractor progress report verified & submitted successfully! Risk radar updated."
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json(force=True) or {}
        full_name = data.get('full_name')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')
        organization = data.get('organization')
        contract_key = data.get('contract_key', '').strip().upper()
        region = data.get('region', 'Maharashtra Division')
        assigned_project_id = None

        if not all([full_name, email, password, role, organization]):
            return jsonify({"status": "error", "message": "All fields are required!"}), 400

        if role == 'Contractor':
            if not contract_key or contract_key not in AUTHORIZED_PROJECT_KEYS:
                return jsonify({
                    "status": "error", 
                    "message": "VERIFICATION FAILED: Invalid Contract Key! Use 'TATA-MUM-4', 'LNT-NAG-3', or 'MEGA-PUN-2'."
                }), 403
            
            verified_project = AUTHORIZED_PROJECT_KEYS[contract_key]
            assigned_project_id = verified_project['project_id']

        with sqlite3.connect(DB_NAME, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (full_name, email, password, role, organization, assigned_project_id, region)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (full_name, email, password, role, organization, assigned_project_id, region))
            conn.commit()

        return jsonify({
            "status": "success",
            "message": f"Account verified & registered for {full_name} ({role})!",
            "user": {
                "full_name": full_name,
                "email": email,
                "role": role,
                "organization": organization,
                "assigned_project_id": assigned_project_id,
                "region": region
            }
        }), 200
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "Email address is already registered!"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json(force=True) or {}
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"status": "error", "message": "Email and password are required!"}), 400

        with sqlite3.connect(DB_NAME, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
            user = cursor.fetchone()

        if user:
            return jsonify({
                "status": "success",
                "message": f"Welcome back, {user['full_name']}!",
                "user": {
                    "full_name": user['full_name'],
                    "email": user['email'],
                    "role": user['role'],
                    "organization": user['organization'],
                    "assigned_project_id": user['assigned_project_id'],
                    "region": user['region']
                }
            }), 200
        else:
            return jsonify({"status": "error", "message": "Invalid email or password!"}), 401
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")
    app.run(debug=True, host='0.0.0.0', port=5000)