import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from supabase import create_client, Client
from dotenv import load_dotenv
import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Set secret key from environment variable or use a default for dev
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")

# Supabase Setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("WARNING: SUPABASE_URL or SUPABASE_ANON_KEY not set in .env")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# --- Helper Functions ---

def get_user_role(user_id):
    """Fetch user role from users table."""
    try:
        response = supabase.table('users').select('role').eq('id', user_id).single().execute()
        if response.data:
            return response.data['role']
    except Exception as e:
        print(f"Error fetching role: {e}")
    return None

def login_required(role=None):
    """Decorator for route protection."""
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            
            if role and session.get('role') != role:
                flash("Unauthorized access", "error")
                return redirect(url_for('login'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Routes ---

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session.get('role') == 'tenant':
            return redirect(url_for('tenant_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id_input = request.form.get('user_id')
        password_input = request.form.get('password')

        try:
            # Query users table
            response = supabase.table('users').select('*').eq('user_id', user_id_input).eq('password', password_input).execute()
            
            if response.data:
                user = response.data[0]
                if not user.get('is_active', True):
                    flash("Account is inactive.", "error")
                    return render_template('login.html')

                session['user_id'] = user['id']
                session['role'] = user['role']
                
                if user['role'] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('tenant_dashboard'))
            else:
                flash("Invalid credentials.", "error")
        except Exception as e:
            print(f"Login error: {e}")
            flash("An error occurred during login.", "error")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Admin Routes ---

@app.route('/admin/dashboard')
@login_required(role='admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/api/admin/tenants', methods=['GET', 'POST'])
@login_required(role='admin')
def admin_tenants():
    if request.method == 'GET':
        # Fetch all tenants with room info
        # Note: Supabase joins usage depends on foreign keys setup properly
        # We will fetch tenants and then manually merge or use Supabase join syntax if simple
        try:
            # Fetch tenants and rooms separately to keep it simple and join manually or via select
            # Using select with join:
            response = supabase.table('tenants').select('*, rooms(room_number, floor)').execute()
            return jsonify(response.data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    if request.method == 'POST':
        data = request.json
        # Add new user first, then tenant
        try:
            # 1. Create User
            user_data = {
                'user_id': data['user_id'],
                'password': data['password'], # In real app, hash this!
                'role': 'tenant',
                'is_active': True,
                'created_at': datetime.datetime.now().isoformat()
            }
            user_res = supabase.table('users').insert(user_data).execute()
            new_user_id = user_res.data[0]['id']

            # 2. Create Tenant
            tenant_data = {
                'user_id': new_user_id,
                'name': data['name'],
                'phone': data['phone'],
                'email': data['email'],
                'room_id': data['room_id'],
                'deposit': data['deposit'],
                'join_date': datetime.date.today().isoformat()
            }
            client_res = supabase.table('tenants').insert(tenant_data).execute()
            
            # 3. Update Room status
            supabase.table('rooms').update({'occupied': True}).eq('id', data['room_id']).execute()
            
            return jsonify({'message': 'Tenant added successfully', 'data': client_res.data})
        except Exception as e:
            print(e)
            return jsonify({'error': str(e)}), 500

@app.route('/api/admin/rooms')
@login_required(role='admin')
def admin_rooms():
    try:
        response = supabase.table('rooms').select('*').order('room_number').execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/payments')
@login_required(role='admin')
def admin_payments():
    try:
        # Fetch payments with tenant name
        response = supabase.table('rent_payments').select('*, tenants(name, room_id, rooms(room_number))').order('month', desc=True).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/maintenance', methods=['GET', 'PUT'])
@login_required(role='admin')
def admin_maintenance():
    if request.method == 'GET':
        try:
            response = supabase.table('maintenance_requests').select('*, tenants(name, rooms(room_number))').order('created_at', desc=True).execute()
            return jsonify(response.data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    if request.method == 'PUT':
        data = request.json
        try:
            response = supabase.table('maintenance_requests').update({'status': data['status']}).eq('id', data['id']).execute()
            return jsonify(response.data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/admin/vacate', methods=['GET', 'PUT'])
@login_required(role='admin')
def admin_vacate():
    if request.method == 'GET':
        try:
            response = supabase.table('vacate_requests').select('*, tenants(name, rooms(room_number))').execute()
            return jsonify(response.data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    if request.method == 'PUT':
        data = request.json
        try:
            update_data = {}
            if 'status' in data: update_data['status'] = data['status']
            if 'dues' in data: update_data['dues'] = data['dues']
            if 'deposit_returned' in data: update_data['deposit_returned'] = data['deposit_returned']
            
            response = supabase.table('vacate_requests').update(update_data).eq('id', data['id']).execute()
            
            # If completed, logic to empty room and deactivate user could go here
            if data.get('status') == 'completed':
               # Simplified: just update prompt
               pass

            return jsonify(response.data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# --- Tenant Routes ---

@app.route('/tenant/dashboard')
@login_required(role='tenant')
def tenant_dashboard():
    return render_template('tenant_dashboard.html')

@app.route('/api/tenant/profile')
@login_required(role='tenant')
def tenant_profile():
    try:
        # Get tenant details based on logged in user_id
        user_id = session['user_id']
        response = supabase.table('tenants').select('*, rooms(*)').eq('user_id', user_id).single().execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tenant/payments', methods=['GET', 'POST'])
@login_required(role='tenant')
def tenant_payments():
    # Get tenant ID first
    user_id = session['user_id']
    tenant_res = supabase.table('tenants').select('id').eq('user_id', user_id).single().execute()
    if not tenant_res.data:
        return jsonify({'error': 'Tenant profile not found'}), 404
    tenant_id = tenant_res.data['id']

    if request.method == 'GET':
        try:
            response = supabase.table('rent_payments').select('*').eq('tenant_id', tenant_id).order('month', desc=True).execute()
            return jsonify(response.data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    if request.method == 'POST':
        # Upload Proof and Create Payment Record
        # Assumes file is handled by frontend storage upload or getting direct URL
        # For this hackathon version, we'll assume the client uploads to supabase storage directly
        # and sends us the URL, OR we handle file upload here.
        # Let's handle simple file URL pass for now if we want to be "simple" or file upload if we want to be "correct".
        # The prompt said "File upload: Supabase Storage".
        # Easiest way: Frontend uploads to Supabase storage, gets public URL, sends URL to backend.
        # OR Backend proxies the upload. 
        # Let's try backend proxy for simplicity of API usage for user, but frontend direct is better for scale.
        # Given "Frontend fetch API", let's assume JSON body with file info or URL.
        # BUT standard form submit with file is easier for beginners? 
        # The user said "backend: Python(Flask)". Flask handles file uploads well.
        # Let's do: Client sends file -> Flask receives -> Flask uploads to Supabase Storage -> Flask inserts DB record.
        
        file = request.files.get('proof')
        month = request.form.get('month')
        amount = request.form.get('amount')
        
        if not file:
            return jsonify({'error': 'No file uploaded'}), 400
            
        try:
            # Upload to Supabase Storage
            file_content = file.read()
            file_path = f"{tenant_id}/{month}_{file.filename}"
            # bucket name 'payment-proofs'
            res = supabase.storage.from_('payment-proofs').upload(file_path, file_content)
            
            # Get Public URL (assuming bucket is public or we sign urls, public is easier for hackathon)
            public_url = supabase.storage.from_('payment-proofs').get_public_url(file_path)
            
            # Insert into rent_payments
            payment_data = {
                'tenant_id': tenant_id,
                'month': month,
                'amount': amount,
                'status': 'paid', # Auto-mark paid or pending? Let's say paid pending review?
                'proof_url': public_url,
                'paid_date': datetime.date.today().isoformat()
            }
            
            db_res = supabase.table('rent_payments').insert(payment_data).execute()
            return jsonify(db_res.data)
            
        except Exception as e:
            print(e)
            return jsonify({'error': str(e)}), 500

@app.route('/api/tenant/maintenance', methods=['POST', 'GET'])
@login_required(role='tenant')
def tenant_maintenance():
    user_id = session['user_id']
    tenant_res = supabase.table('tenants').select('id').eq('user_id', user_id).single().execute()
    tenant_id = tenant_res.data['id']
    
    if request.method == 'GET':
        try:
             response = supabase.table('maintenance_requests').select('*').eq('tenant_id', tenant_id).order('created_at', desc=True).execute()
             return jsonify(response.data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    if request.method == 'POST':
        data = request.json
        try:
            req_data = {
                'tenant_id': tenant_id,
                'title': data['title'],
                'description': data['description'],
                'status': 'pending',
                'created_at': datetime.datetime.now().isoformat()
            }
            response = supabase.table('maintenance_requests').insert(req_data).execute()
            return jsonify(response.data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/tenant/vacate', methods=['POST', 'GET'])
@login_required(role='tenant')
def tenant_vacate():
    user_id = session['user_id']
    tenant_res = supabase.table('tenants').select('id').eq('user_id', user_id).single().execute()
    tenant_id = tenant_res.data['id']
    
    if request.method == 'GET':
         try:
             response = supabase.table('vacate_requests').select('*').eq('tenant_id', tenant_id).execute()
             return jsonify(response.data)
         except Exception as e:
             return jsonify({'error': str(e)}), 500

    if request.method == 'POST':
        data = request.json
        try:
            req_data = {
                'tenant_id': tenant_id,
                'vacate_date': data['vacate_date'],
                'reason': data['reason'],
                'status': 'pending',
                'deposit_returned': False,
                'dues': 0
            }
            response = supabase.table('vacate_requests').insert(req_data).execute()
            return jsonify(response.data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
