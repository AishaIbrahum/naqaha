from flask import Flask, render_template, redirect, url_for, request, flash, session
from models import db, User, Company, Admin, Package, Appointment, DoctorMessage, PaymentPlan, HealthCard, Invoice, Booking, Consultation, MedicalReport, Payment, Notification, AdminAction
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
IMAGE_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "images")


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

@app.route('/appointments')
def appointments():
    user_id = session.get("user_id", 1)  # مؤقتاً
    appointments = Appointment.query.filter_by(user_id=user_id).all()
    return render_template('appointments.html', appointments=appointments)

@app.route('/contact_doctors')
def contact_doctors():
    return render_template('contact_doctors.html')

@app.route('/profile')
def profile():
    user_id = session.get("user_id", 1)
    user = User.query.get(user_id)
    return render_template('profile.html', user=user)

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/invoices')
def invoices():
    user_id = session.get("user_id", 1)
    invoices = Invoice.query.filter_by(user_id=user_id).all()
    return render_template('invoices.html', invoices=invoices)

@app.route('/health_card')
def health_card():
    user_id = session.get("user_id", 1)
    card = HealthCard.query.filter_by(user_id=user_id).first()
    return render_template('health_card.html', card=card)


# ------------------- عرض كل الحجوزات -------------------
@app.route('/bookings')
def bookings():
    user_id = session.get("user_id")
    if not user_id:
        flash("يجب تسجيل الدخول أولاً", "danger")
        return redirect(url_for('login'))
    
    all_bookings = Booking.query.filter_by(user_id=user_id).all()
    return render_template('bookings.html', bookings=all_bookings)


# ------------------- إنشاء حجز جديد -------------------
@app.route('/book_package/<int:package_id>', methods=['GET', 'POST'])
def book_package(package_id):
    if 'user_id' not in session:
        flash("يجب تسجيل الدخول أولاً", "danger")
        return redirect(url_for('login'))
    
    package = Package.query.get_or_404(package_id)
    
    if request.method == 'POST':
        scheduled_for_str = request.form.get('scheduled_for')
        scheduled_for = datetime.strptime(scheduled_for_str, "%Y-%m-%d %H:%M") if scheduled_for_str else None
        notes = request.form.get('notes')

        new_booking = Booking(
            user_id=session['user_id'],
            package_id=package.id,
            company_id=package.provider_id,
            scheduled_for=scheduled_for,
            notes=notes,
            status="pending"
        )
        db.session.add(new_booking)
        db.session.commit()
        flash("تم إنشاء الحجز بنجاح!", "success")
        return redirect(url_for('bookings'))

    return render_template('book_package.html', package=package)


# ------------------- تعديل حالة الحجز (Admin) -------------------
@app.route('/booking/<int:booking_id>/update_status', methods=['POST'])
def update_booking_status(booking_id):
    if 'admin_id' not in session:
        flash("يجب تسجيل الدخول كأدمن", "danger")
        return redirect(url_for('admin_login'))
    
    booking = Booking.query.get_or_404(booking_id)
    new_status = request.form.get('status')  # pending / approved / rejected / completed / cancelled
    booking.status = new_status
    db.session.commit()
    flash("تم تحديث حالة الحجز!", "success")
    return redirect(url_for('admin_dashboard'))


# ------------------- عرض الفواتير -------------------
@app.route('/all_invoices')
def all_invoices():
    user_id = session.get("user_id")
    if not user_id:
        flash("يجب تسجيل الدخول أولاً", "danger")
        return redirect(url_for('login'))
    
    invoices = Invoice.query.filter_by(user_id=user_id).all()
    return render_template('all_invoices.html', invoices=invoices)


# ------------------- دفع فاتورة -------------------
@app.route('/pay_invoice/<int:invoice_id>', methods=['POST'])
def pay_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice.status = "paid"
    invoice.paid_at = datetime.utcnow()
    db.session.commit()
    flash("تم دفع الفاتورة بنجاح!", "success")
    return redirect(url_for('all_invoices'))

# ------------------- عرض الاستشارات -------------------
@app.route('/consultations')
def consultations():
    user_id = session.get("user_id")
    if not user_id:
        flash("يجب تسجيل الدخول أولاً", "danger")
        return redirect(url_for('login'))
    
    consultations = Consultation.query.filter_by(user_id=user_id).all()
    return render_template('consultations.html', consultations=consultations)


# ------------------- جدولة استشارة -------------------
@app.route('/schedule_consultation/<int:doctor_id>', methods=['GET', 'POST'])
def schedule_consultation(doctor_id):
    if 'user_id' not in session:
        flash("يجب تسجيل الدخول أولاً", "danger")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        consultation_type = request.form.get('consultation_type')  # chat/video/in_person/phone
        date_str = request.form.get('date')
        date = datetime.strptime(date_str, "%Y-%m-%d %H:%M") if date_str else datetime.utcnow()
        notes = request.form.get('notes')

        new_consultation = Consultation(
            user_id=session['user_id'],
            doctor_id=doctor_id,
            date=date,
            consultation_type=consultation_type,
            notes=notes,
            status="pending"
        )
        db.session.add(new_consultation)
        db.session.commit()
        flash("تم جدولة الاستشارة!", "success")
        return redirect(url_for('consultations'))

    return render_template('schedule_consultation.html', doctor_id=doctor_id)

# ------------------- عرض التقارير الطبية -------------------
@app.route('/medical_reports')
def medical_reports():
    user_id = session.get("user_id")
    if not user_id:
        flash("يجب تسجيل الدخول أولاً", "danger")
        return redirect(url_for('login'))

    reports = MedicalReport.query.filter_by(user_id=user_id).all()
    return render_template('medical_reports.html', reports=reports)


# ------------------- رفع تقرير طبي جديد -------------------
@app.route('/upload_report', methods=['GET', 'POST'])
def upload_report():
    if 'user_id' not in session:
        flash("يجب تسجيل الدخول أولاً", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files['report_file']
        notes = request.form.get('notes')
        booking_id = request.form.get('booking_id')  # optional

        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            new_report = MedicalReport(
                user_id=session['user_id'],
                booking_id=booking_id if booking_id else None,
                file_path=filename,
                notes=notes,
                created_at=datetime.utcnow()
            )
            db.session.add(new_report)
            db.session.commit()
            flash("تم رفع التقرير بنجاح!", "success")
            return redirect(url_for('medical_reports'))

    return render_template('upload_report.html')


# ------------------- عرض المدفوعات -------------------
@app.route('/payments')
def payments():
    user_id = session.get("user_id")
    if not user_id:
        flash("يجب تسجيل الدخول أولاً", "danger")
        return redirect(url_for('login'))

    payments = Payment.query.join(Invoice).filter(Invoice.user_id==user_id).all()
    return render_template('payments.html', payments=payments)


# ------------------- تسجيل دفعة جديدة -------------------
@app.route('/make_payment/<int:invoice_id>', methods=['POST'])
def make_payment(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    amount = request.form.get('amount')
    method = request.form.get('method')  # card/bank_transfer/cash/apple_pay

    new_payment = Payment(
        invoice_id=invoice.id,
        amount=amount,
        method=method,
        status='completed',
        paid_at=datetime.utcnow()
    )
    invoice.status = 'paid'
    db.session.add(new_payment)
    db.session.commit()
    flash("تم تسجيل الدفع بنجاح!", "success")
    return redirect(url_for('payments'))

# ------------------- عرض الإشعارات -------------------
@app.route('/notifications')
def notifications():
    user_id = session.get("user_id")
    company_id = session.get("company_id")

    notifications = Notification.query.filter(
        (Notification.user_id==user_id) | (Notification.company_id==company_id)
    ).all()
    return render_template('notifications.html', notifications=notifications)


# ------------------- تعليم الإشعار كمقروء -------------------
@app.route('/notifications/<int:notification_id>/mark_read')
def mark_notification_read(notification_id):
    notif = Notification.query.get_or_404(notification_id)
    notif.is_read = True
    db.session.commit()
    flash("تم تعليم الإشعار كمقروء.", "success")
    return redirect(url_for('notifications'))


# ------------------- عرض سجل الأدمن -------------------
@app.route('/admin_actions')
def admin_actions():
    if 'admin_id' not in session:
        flash("يجب تسجيل الدخول كأدمن", "danger")
        return redirect(url_for('admin_login'))

    actions = AdminAction.query.filter_by(admin_id=session['admin_id']).all()
    return render_template('admin_actions.html', actions=actions)

if __name__ == '__main__':
    app.run(debug=True)
