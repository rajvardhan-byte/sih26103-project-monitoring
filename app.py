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
        
        # Projects Master Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cost TEXT NOT NULL,
                progress INTEGER CHECK (progress BETWEEN 0 AND 100),
                financial_payout_pct INTEGER DEFAULT 0,
                field_engineer_pct INTEGER DEFAULT 0,
                fraud_discrepancy INTEGER DEFAULT 0,
                risk_level TEXT CHECK (risk_level IN ('Low', 'Medium', 'High')),
                predicted_delay TEXT,
                predicted_overrun TEXT,
                contractor TEXT NOT NULL,
                region TEXT NOT NULL,
                assigned_officer TEXT NOT NULL,
                last_reported TEXT
            )
        ''')
        
        # Users Table
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

        # 3-Party Approval Consensus Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS progress_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                requested_by_email TEXT NOT NULL,
                requested_by_role TEXT NOT NULL,
                proposed_progress INTEGER NOT NULL,
                notes TEXT,
                gov_approved INTEGER DEFAULT 0,
                contractor_approved INTEGER DEFAULT 0,
                engineer_approved INTEGER DEFAULT 0,
                status TEXT DEFAULT 'PENDING',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Audit Logs Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                submitted_by TEXT,
                claimed_progress INTEGER,
                financial_pct INTEGER,
                status TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute("SELECT COUNT(*) FROM projects")
        if cursor.fetchone()[0] == 0:
            cursor.executemany('''
                INSERT INTO projects (name, cost, progress, financial_payout_pct, field_engineer_pct, fraud_discrepancy, risk_level, predicted_delay, predicted_overrun, contractor, region, assigned_officer, last_reported)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                ("Nagpur Outer Ring Road (Sec 3)", "₹1,250 Cr", 62, 50, 60, 0, "High", "8 Months", "₹45 Cr", "L&T Infrastructure Ltd.", "Maharashtra Division", "rakesh.sharma@mospi.gov.in", "2026-09-20"),
                ("Pune-Nashik High-Speed Rail Link", "₹16,000 Cr", 40, 42, 38, 0, "Medium", "3 Months", "₹120 Cr", "Mega Infra Corp", "Maharashtra Division", "rakesh.sharma@mospi.gov.in", "2026-09-18"),
                ("Mumbai Metro Line 4 Extension", "₹14,500 Cr", 85, 82, 85, 0, "Low", "0 Months", "₹0 Cr", "Tata Projects", "Maharashtra Division", "rakesh.sharma@mospi.gov.in", "2026-09-22")
            ])
            conn.commit()

# Run database initialization unconditionally on app load
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/projects', methods=['GET'])
def get_projects():
    with sqlite3.connect(DB_NAME, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY CASE WHEN fraud_discrepancy = 1 THEN 0 WHEN risk_level = 'High' THEN 1 WHEN risk_level = 'Medium' THEN 2 ELSE 3 END")
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
        user_email = data.get('user_email', 'unknown')
        new_progress = int(data.get('progress', 65))
        notes = data.get('notes', '')

        if user_role not in ['Government Officer', 'Platform Administrator'] and user_assigned_id and int(user_assigned_id) != project_id:
            return jsonify({
                "status": "error",
                "message": "UNAUTHORIZED ACCESS: You are not assigned to modify this infrastructure project!"
            }), 403

        gov_app = 1 if user_role in ['Government Officer', 'Platform Administrator'] else 0
        contractor_app = 1 if user_role == 'Contractor' else 0
        engineer_app = 1 if user_role == 'Site Engineer' else 0

        with sqlite3.connect(DB_NAME, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO progress_requests (project_id, requested_by_email, requested_by_role, proposed_progress, notes, gov_approved, contractor_approved, engineer_approved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (project_id, user_email, user_role, new_progress, notes, gov_app, contractor_app, engineer_app))
            conn.commit()

        return jsonify({
            "status": "success",
            "message": "Progress change request submitted! Multi-party notification sent to Government Officer, Contractor, and Site Engineer for 3-party approval."
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/approval/requests', methods=['GET'])
def get_approval_requests():
    with sqlite3.connect(DB_NAME, timeout=10) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, p.name as project_name 
            FROM progress_requests r
            JOIN projects p ON r.project_id = p.id
            WHERE r.status = 'PENDING'
            ORDER BY r.created_at DESC
        ''')
        rows = cursor.fetchall()
        requests_list = [dict(row) for row in rows]
    return jsonify({"status": "success", "data": requests_list})

@app.route('/api/approval/vote', methods=['POST'])
def vote_approval():
    try:
        data = request.get_json(force=True) or {}
        request_id = int(data.get('request_id'))
        user_role = data.get('user_role')
        user_email = data.get('user_email')
        action = data.get('action', 'approve')

        if not user_role or not user_email:
            return jsonify({"status": "error", "message": "User login required to cast vote."}), 401

        with sqlite3.connect(DB_NAME, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM progress_requests WHERE id = ?", (request_id,))
            req = cursor.fetchone()

            if not req:
                return jsonify({"status": "error", "message": "Approval Request not found."}), 404

            if action == 'reject':
                cursor.execute("UPDATE progress_requests SET status = 'REJECTED' WHERE id = ?", (request_id,))
                cursor.execute('''
                    INSERT INTO audit_logs (project_id, submitted_by, claimed_progress, financial_pct, status)
                    VALUES (?, ?, ?, 0, ?)
                ''', (req['project_id'], user_email, req['proposed_progress'], f"REJECTED_BY_{user_role.upper()}"))
                conn.commit()
                return jsonify({
                    "status": "success",
                    "message": f"Change request REJECTED by {user_role}. The progress change was not applied."
                })

            gov_app = req['gov_approved']
            contractor_app = req['contractor_approved']
            engineer_app = req['engineer_approved']

            if user_role in ['Government Officer', 'Platform Administrator']:
                gov_app = 1
            elif user_role == 'Contractor':
                contractor_app = 1
            elif user_role == 'Site Engineer':
                engineer_app = 1

            if gov_app == 1 and contractor_app == 1 and engineer_app == 1:
                project_id = req['project_id']
                new_progress = req['proposed_progress']

                cursor.execute("SELECT financial_payout_pct, field_engineer_pct FROM projects WHERE id = ?", (project_id,))
                project = cursor.fetchone()

                financial_pct = project['financial_payout_pct'] if project else 50
                field_pct = project['field_engineer_pct'] if project else 50

                fraud_detected = 0
                if abs(new_progress - financial_pct) > 20 or abs(new_progress - field_pct) > 20:
                    fraud_detected = 1
                    new_risk = "High"
                    predicted_delay = "12 Months (Fraud Flagged)"
                    predicted_overrun = "₹85 Cr (Audit Pending)"
                else:
                    new_risk = "High" if new_progress < 70 else ("Medium" if new_progress < 85 else "Low")
                    predicted_delay = f"{max(0, round((100 - new_progress) / 5))} Months"
                    predicted_overrun = f"₹{max(0, round((100 - new_progress) * 1.2))} Cr"

                cursor.execute('''
                    UPDATE projects 
                    SET progress = ?, fraud_discrepancy = ?, risk_level = ?, predicted_delay = ?, predicted_overrun = ?, last_reported = DATE('now')
                    WHERE id = ?
                ''', (new_progress, fraud_detected, new_risk, predicted_delay, predicted_overrun, project_id))

                cursor.execute("UPDATE progress_requests SET status = 'APPROVED', gov_approved = 1, contractor_approved = 1, engineer_approved = 1 WHERE id = ?", (request_id,))
                
                cursor.execute('''
                    INSERT INTO audit_logs (project_id, submitted_by, claimed_progress, financial_pct, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (project_id, user_email, new_progress, financial_pct, "CONSENSUS_APPROVED"))

                conn.commit()
                return jsonify({
                    "status": "success",
                    "message": "3-Party Consensus Reached! Government, Contractor, and Site Engineer have all approved. Project progress updated."
                })
            else:
                cursor.execute('''
                    UPDATE progress_requests 
                    SET gov_approved = ?, contractor_approved = ?, engineer_approved = ?
                    WHERE id = ?
                ''', (gov_app, contractor_app, engineer_app, request_id))
                conn.commit()
                return jsonify({
                    "status": "success",
                    "message": "Vote recorded! Pending remaining approvals from other stakeholders."
                })
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
    print("Database initialized successfully!")
    app.run(debug=True, host='0.0.0.0', port=5000)