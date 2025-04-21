from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_very_secure_secret_key_here'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Vaish@2005'
app.config['MYSQL_DB'] = 'job_portal'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# Helper Functions
def calculate_profile_score(user_id):
    """Calculate user profile completion percentage"""
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    
    score = 20  # Base score for registration
    if user['phone']: score += 20
    # Add more profile completion criteria as needed
    return min(score, 100)

def get_application_status(user_id):
    """Get counts for each application status"""
    cursor = mysql.connection.cursor()
    cursor.execute('''
        SELECT status, COUNT(*) as count 
        FROM applications 
        WHERE user_id = %s
        GROUP BY status
    ''', (user_id,))
    result = cursor.fetchall()
    
    status_counts = {
        'applied': 0,
        'reviewed': 0,
        'interview': 0,
        'hired': 0
    }
    
    for row in result:
        status = row['status'].lower()
        if status in status_counts:
            status_counts[status] = row['count']
    
    return status_counts

# Routes
@app.route('/')
def home():
    """Landing page"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form.get('phone', '')
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        
        # Validation
        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email address!', 'danger')
        elif not name or not password:
            flash('Please fill out all required fields!', 'danger')
        elif role not in ['job_seeker', 'employer']:
            flash('Invalid role selected!', 'danger')
        else:
            cursor = mysql.connection.cursor()
            try:
                cursor.execute('''
                    INSERT INTO users (name, email, phone, password, role) 
                    VALUES (%s, %s, %s, %s, %s)
                ''', (name, email, phone, password, role))
                mysql.connection.commit()
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            except MySQLdb.IntegrityError:
                flash('Email already exists!', 'danger')
            except Exception as e:
                flash(f'Registration failed: {str(e)}', 'danger')
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    """Main dashboard based on user role"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    if session['role'] == 'job_seeker':
        # Get jobs with application status for seeker
        cursor.execute('''
            SELECT j.*, a.status 
            FROM jobs j
        LEFT JOIN applications a ON j.id = a.job_id AND a.user_id = %s
        ORDER BY j.id DESC
    ''', (session['user_id'],))
        jobs = cursor.fetchall()
        
        profile_score = calculate_profile_score(session['user_id'])
        return render_template('seeker_dashboard.html',
                           jobs=jobs,
                           profile_score=profile_score)
    else:
        # Get jobs posted by employer with applicant count
        cursor.execute('''
            SELECT j.*, COUNT(a.id) as applicant_count
            FROM jobs j
            LEFT JOIN applications a ON j.id = a.job_id
            WHERE j.posted_by = %s
        GROUP BY j.id
        ORDER BY j.id DESC
    ''', (session['user_id'],))
        jobs = cursor.fetchall()
        return render_template('employer_dashboard.html',
                           jobs=jobs)

@app.route('/post_job', methods=['GET', 'POST'])
def post_job():
    """Employer job posting"""
    if 'user_id' not in session or session['role'] != 'employer':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        company = request.form['company']
        location = request.form['location']
        salary = float(request.form['salary'])
        description = request.form['description']
        
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('''
                INSERT INTO jobs 
                (title, company, location, salary, description, posted_by) 
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (title, company, location, salary, description, session['user_id']))
            mysql.connection.commit()
            flash('Job posted successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Failed to post job: {str(e)}', 'danger')
    
    return render_template('post_job.html')

@app.route('/job/<int:job_id>')
def job_details(job_id):
    """Single job view"""
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get job with applicant count
    cursor.execute('''
        SELECT j.*, COUNT(a.id) as applicant_count
        FROM jobs j
        LEFT JOIN applications a ON j.id = a.job_id
        WHERE j.id = %s
        GROUP BY j.id
    ''', (job_id,))
    job = cursor.fetchone()
    
    if not job:
        flash('Job not found!', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if current user has applied (for seekers)
    if session.get('role') == 'job_seeker':
        cursor.execute('''
            SELECT status FROM applications 
            WHERE job_id = %s AND user_id = %s
        ''', (job_id, session.get('user_id')))
        application = cursor.fetchone()
        job['status'] = application['status'] if application else None
    
    return render_template('job_details.html', job=job)

@app.route('/apply_job/<int:job_id>', methods=['POST'])
def apply_job(job_id):
    """Job application endpoint (AJAX)"""
    if 'user_id' not in session or session['role'] != 'job_seeker':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        cursor = mysql.connection.cursor()
        
        # Check if already applied
        cursor.execute('''
            SELECT id FROM applications 
            WHERE job_id = %s AND user_id = %s
        ''', (job_id, session['user_id']))
        existing = cursor.fetchone()
        
        if existing:
            return jsonify({'success': False, 'error': 'Already applied'}), 400
        
        # Create new application
        cursor.execute('''
            INSERT INTO applications (job_id, user_id, status) 
            VALUES (%s, %s, 'applied')
        ''', (job_id, session['user_id']))
        mysql.connection.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/application_status')
def application_status():
    """Get application status counts (AJAX)"""
    if 'user_id' not in session:
        return jsonify({'success': False}), 401
    
    counts = get_application_status(session['user_id'])
    return jsonify({
        'success': True,
        'counts': counts
    })

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)