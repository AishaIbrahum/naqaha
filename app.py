from flask import Flask, render_template, redirect, url_for, request, flash, session
from models import db, User, Company, Admin, Package
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "secretkey123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nqaha.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ربط قاعدة البيانات بالـ app
db.init_app(app)

# تفعيل الـ Migrate
migrate = Migrate(app, db)

# مسار حفظ الصور
IMAGE_UPLOAD_FOLDER = "/mnt/c/Users/-aish/Desktop/naqaha_last_version/static/images"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = IMAGE_UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

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
            return redirect(url_for('add_package'))
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

# ------------------- الصفحات العامة -------------------
@app.route('/custom-plan')
def custom_plan():
    return render_template('custom_plan.html')

@app.route('/consult-doctor')
def consult_doctor():
    return render_template('consult_doctor.html')

@app.route('/recreation')
def recreation():   
    return render_template('recreation.html')

# ------------------- صفحة الباقات الجاهزة -------------------
@app.route('/ready-packages')
def ready_packages():
    all_packages = Package.query.all()
    return render_template('ready_packages.html', packages=all_packages)

# ------------------- إضافة باقة جديدة -------------------
@app.route("/add_package", methods=["GET", "POST"])
def add_package():
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]

        file = request.files["image"]
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            new_package = Package(
                title=title,
                description=description,
                image=filename
            )
            db.session.add(new_package)
            db.session.commit()

            flash("تمت إضافة الباقة بنجاح!", "success")
            return redirect(url_for("ready_packages"))  # بعد إضافة الباقة، ارجع للصفحة الجاهزة

        else:
            flash("صيغة الصورة غير مدعومة", "danger")

    return render_template("add_package.html")

if __name__ == '__main__':
    app.run(debug=True)
