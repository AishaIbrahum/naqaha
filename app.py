from flask import Flask, render_template, redirect, url_for, request, flash, session
from models import db, User, Company, Admin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate   # ✅ استدعاء المكتبة
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secretkey123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nqaha.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ربط قاعدة البيانات بالـ app
db.init_app(app)

# ✅ تفعيل الـ Migrate
migrate = Migrate(app, db)

# ما نحتاج db.create_all() بعد الآن (خليه مش مُفعل)
# with app.app_context():
#     db.create_all()


# ------------------- الصفحات -------------------

@app.route('/')
def portal_choice():
    return render_template('home.html')

# ------------------- بوابة الأفراد -------------------
@app.route('/individual')
def individual_index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return render_template('index.html', user=user)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash("تم تسجيل الدخول بنجاح!", "success")
            return redirect(url_for('individual_index'))
        else:
            flash("البريد أو كلمة السر خاطئة!", "danger")
    return render_template('login.html')





@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        gender = request.form.get('gender')
        country = request.form.get('country')
        city = request.form.get('city')
        address = request.form.get('address')
        birth_date_str = request.form.get('birth_date')
        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date() if birth_date_str else None

        new_user = User(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            gender=gender,
            country=country,
            city=city,
            address=address,
            birth_date=birth_date
        )
        db.session.add(new_user)
        db.session.commit()
        flash("تم إنشاء الحساب بنجاح!", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


# ------------------- بوابة الشركات -------------------
@app.route('/company')
def company_portal():
    return render_template('company_login.html')

@app.route('/company_login', methods=['GET', 'POST'])
def company_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        company = Company.query.filter_by(email=email).first()
        if company and check_password_hash(company.password, password):
            session['company_id'] = company.id
            flash("تم تسجيل الدخول للشركة!", "success")
            return redirect(url_for('company_dashboard'))
        else:
            flash("البريد أو كلمة السر خاطئة!", "danger")
    return render_template('company_login.html')

@app.route('/company_register', methods=['GET', 'POST'])
def company_register():
    if request.method == 'POST':
        name = request.form['company_name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        new_company = Company(name=name, email=email, password=password)
        db.session.add(new_company)
        db.session.commit()
        flash("تم إنشاء حساب الشركة بنجاح!", "success")
        return redirect(url_for('company_login'))
    return render_template('company_register.html')

@app.route('/company_dashboard')
def company_dashboard():
    if 'company_id' in session:
        return render_template('company_dashboard.html')
    return redirect(url_for('company_login'))

# ------------------- بوابة Admin -------------------
@app.route('/admin')
def admin_portal():
    return render_template('admin_login.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session['admin_id'] = admin.id
            flash("تم تسجيل دخول الأدمن!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("البريد أو كلمة السر خاطئة!", "danger")
    return render_template('admin_login.html')
@app.route('/admin_register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        new_admin = Admin(username=username, password=password)
        db.session.add(new_admin)
        db.session.commit()
        flash("تم إنشاء حساب الأدمن بنجاح! سجل الدخول الآن.", "success")
        return redirect(url_for('admin_login'))
    return render_template('admin_register.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' in session:
        return render_template('admin_dashboard.html')
    return redirect(url_for('admin_login'))

# ------------------- تسجيل الخروج -------------------
@app.route('/logout')
def logout():
    session.clear()
    flash("تم تسجيل الخروج.", "info")
    return redirect(url_for('portal_choice'))

if __name__ == '__main__':
    app.run(debug=True)
