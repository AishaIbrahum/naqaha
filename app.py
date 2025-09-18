from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from models import db, User, Company, Admin, Doctor, Package, Appointment, DoctorMessage, PaymentPlan, HealthCard, Invoice, Booking, Consultation, ConsultationResponse, MedicalReport, Payment, Notification, AdminAction
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user

from flask_migrate import Migrate
from datetime import datetime
from functools import wraps
import os
import re

app = Flask(__name__)
app.secret_key = "secretkey123"
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////mnt/c/Users/hanee/OneDrive/Desktop/naqaha/instance/nqaha.db"
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


def validate_consultation_form(form_data):
    errors = []

    required_fields = {
        "specialization": "يجب اختيار التخصص",
        "question": "الرجاء إدخال سؤالك الطبي",
        "question_for": "حدد لمن هذه الاستشارة",
        "gender": "حدد الجنس",
        "age": "الرجاء إدخال العمر",
        "phone_number": "الرجاء إدخال رقم الجوال",
        "contact_method": "اختر طريقة التواصل المفضلة"
    }

    for field, message in required_fields.items():
        value = form_data.get(field)
        if not value or not str(value).strip():
            errors.append(message)

    # Validate age is an integer >= 0
    age_value = form_data.get("age")
    if age_value:
        try:
            age_int = int(age_value)
            if age_int < 0:
                errors.append("العمر لا يمكن أن يكون سالباً")
        except (TypeError, ValueError):
            errors.append("العمر يجب أن يكون عدداً صحيحاً")

    # Validate phone number (basic 10 digits check)
    phone_value = (form_data.get("phone_number") or "").strip()
    if phone_value and not re.fullmatch(r"\d{9,15}", phone_value):
        errors.append("رقم الجوال يجب أن يحتوي على أرقام فقط (9-15 رقم)")

    return errors


def build_consultation_from_form(form_data, user_id):
    description = form_data.get("description")
    medical_history = form_data.get("medical_history")

    consultation = Consultation(
        user_id=user_id,
        specialization=(form_data.get("specialization") or "").strip(),
        question=(form_data.get("question") or "").strip(),
        description=description.strip() if description else None,
        question_for=form_data.get("question_for"),
        gender=form_data.get("gender"),
        age=int(form_data.get("age")) if form_data.get("age") else None,
        medical_history=medical_history.strip() if medical_history else None,
        phone_number=(form_data.get("phone_number") or "").strip(),
        contact_method=form_data.get("contact_method"),
        status="new"
    )

    return consultation


def normalize_specialty(value):
    if not value:
        return ""
    return str(value).strip().lower()


def get_logged_in_doctor():
    doctor_id = session.get('doctor_id')
    if not doctor_id:
        return None
    return Doctor.query.get(doctor_id)


def doctor_login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        doctor = get_logged_in_doctor()
        if not doctor:
            flash("يجب تسجيل دخول الطبيب أولاً", "danger")
            next_url = request.url if request.method == 'GET' else request.referrer
            return redirect(url_for('doctor_login', next=next_url))
        return view_func(*args, **kwargs)

    return wrapper


def auto_assign_doctor(consultation):
    target_specialty = normalize_specialty(consultation.specialization)
    if not target_specialty:
        return None

    available_doctors = [
        doctor for doctor in Doctor.query.filter(Doctor.status == "available").all()
        if normalize_specialty(doctor.specialty)
        and normalize_specialty(doctor.specialty) == target_specialty
    ]

    if not available_doctors:
        return None

    doctor_ids = [doctor.id for doctor in available_doctors]
    if not doctor_ids:
        return None

    active_counts = {
        doctor_id: count
        for doctor_id, count in db.session.query(
            Consultation.doctor_id,
            db.func.count(Consultation.id)
        ).filter(
            Consultation.doctor_id.in_(doctor_ids),
            Consultation.status.in_(["new", "assigned", "in_progress", "needs_follow_up"])
        ).group_by(Consultation.doctor_id)
    }

    available_doctors.sort(key=lambda doc: active_counts.get(doc.id, 0))

    return available_doctors[0] if available_doctors else None


def notify_doctor(doctor, consultation):
    if not doctor:
        return

    message = (
        f"لديك استشارة جديدة (#{consultation.id}) من المستخدم {consultation.user_id}. "
        f"التخصص: {consultation.specialization}."
    )
    app.logger.info(message)


def notify_patient(user_id, title, message):
    if not user_id:
        return None

    notification = Notification(
        user_id=user_id,
        title=title,
        body=message
    )
    db.session.add(notification)
    return notification

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

# ------------------- بوابة الأطباء -------------------
@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    if 'doctor_id' in session and request.method == 'GET':
        return redirect(url_for('doctor_dashboard'))

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''

        doctor = None
        if email:
            doctor = Doctor.query.filter(db.func.lower(Doctor.email) == email).first()

        if doctor and doctor.password and check_password_hash(doctor.password, password):
            session['doctor_id'] = doctor.id
            doctor.last_login = datetime.utcnow()
            db.session.commit()
            flash("تم تسجيل الدخول بنجاح", "success")

            next_url = request.args.get('next') or request.form.get('next') or url_for('doctor_dashboard')
            return redirect(next_url)

        flash("بيانات الدخول غير صحيحة", "danger")

    return render_template('doctor_login.html')


@app.route('/doctor/logout')
def doctor_logout():
    session.pop('doctor_id', None)
    flash("تم تسجيل خروج الطبيب", "info")
    return redirect(url_for('doctor_login'))


@app.route('/doctor/dashboard')
@doctor_login_required
def doctor_dashboard():
    doctor = get_logged_in_doctor()

    # استشارات جديدة من نفس التخصص وغير معينة
    new_consultations_query = Consultation.query.filter(Consultation.status == 'new')
    doctor_specialty = normalize_specialty(doctor.specialty)
    if doctor_specialty:
        new_consultations_query = new_consultations_query.filter(
            db.func.lower(db.func.trim(Consultation.specialization)) == doctor_specialty
        )

    new_consultations = new_consultations_query.order_by(Consultation.created_at.desc()).all()

    doctor_consultations = (
        Consultation.query
        .filter(Consultation.doctor_id == doctor.id)
        .order_by(Consultation.created_at.desc())
        .all()
    )

    active_consultations = [
        consultation for consultation in doctor_consultations
        if consultation.status in {"assigned", "in_progress", "needs_follow_up"}
    ]

    answered_consultations = [
        consultation for consultation in doctor_consultations
        if consultation.status in {"answered", "closed"}
    ]

    stats = {
        "active": len(active_consultations),
        "answered": len(answered_consultations),
        "waiting": len(new_consultations)
    }

    return render_template(
        'doctor_dashboard.html',
        doctor=doctor,
        stats=stats,
        new_consultations=new_consultations,
        active_consultations=active_consultations,
        answered_consultations=answered_consultations
    )


@app.route('/doctor/consultations/<int:consultation_id>')
@doctor_login_required
def doctor_consultation_detail(consultation_id):
    doctor = get_logged_in_doctor()
    consultation = Consultation.query.get_or_404(consultation_id)

    if consultation.doctor_id not in (None, doctor.id):
        flash("هذه الاستشارة مخصصة لطبيب آخر", "warning")
        return redirect(url_for('doctor_dashboard'))

    recommended_new = []
    target_specialty = normalize_specialty(consultation.specialization) or normalize_specialty(doctor.specialty)
    recommendations_query = Consultation.query.filter(
        Consultation.status == 'new',
        Consultation.id != consultation.id
    )
    if target_specialty:
        recommendations_query = recommendations_query.filter(
            db.func.lower(db.func.trim(Consultation.specialization)) == target_specialty
        )
    recommended_new = recommendations_query.order_by(Consultation.created_at.desc()).limit(3).all()

    return render_template(
        'doctor_consultation_detail.html',
        doctor=doctor,
        consultation=consultation,
        recommended_new=recommended_new
    )


@app.route('/doctor/consultations/<int:consultation_id>/claim', methods=['POST'])
@doctor_login_required
def doctor_claim_consultation(consultation_id):
    doctor = get_logged_in_doctor()
    consultation = Consultation.query.get_or_404(consultation_id)

    if consultation.doctor_id and consultation.doctor_id != doctor.id:
        flash("تم تعيين هذه الاستشارة لطبيب آخر", "danger")
        return redirect(url_for('doctor_dashboard'))

    if consultation.status == 'answered':
        flash("تم الرد على هذه الاستشارة مسبقاً", "info")
        return redirect(url_for('doctor_dashboard'))

    previously_unassigned = consultation.doctor_id is None

    consultation.doctor_id = doctor.id
    consultation.status = 'in_progress'
    if not consultation.assigned_at:
        consultation.assigned_at = datetime.utcnow()

    if previously_unassigned:
        notify_patient(
            consultation.user_id,
            "تم تعيين طبيب",
            f"تم تحويل استشارتك إلى د. {doctor.name}"
        )

    db.session.commit()

    flash("تم استلام الاستشارة والبدء في معالجتها", "success")
    return redirect(url_for('doctor_consultation_detail', consultation_id=consultation.id))


@app.route('/doctor/consultations/<int:consultation_id>/status', methods=['POST'])
@doctor_login_required
def doctor_update_consultation_status(consultation_id):
    doctor = get_logged_in_doctor()
    consultation = Consultation.query.get_or_404(consultation_id)

    if consultation.doctor_id != doctor.id:
        flash("لا تملك صلاحية تعديل هذه الاستشارة", "danger")
        return redirect(url_for('doctor_dashboard'))

    new_status = request.form.get('status')
    allowed_statuses = {"assigned", "in_progress", "answered", "closed", "needs_follow_up"}

    if new_status not in allowed_statuses:
        flash("حالة غير مسموح بها", "danger")
        return redirect(url_for('doctor_consultation_detail', consultation_id=consultation.id))

    previous_status = consultation.status
    consultation.status = new_status

    if new_status in {"assigned", "in_progress"} and not consultation.assigned_at:
        consultation.assigned_at = datetime.utcnow()

    if new_status in {"answered", "closed"}:
        consultation.answered_at = datetime.utcnow()

    db.session.commit()

    if previous_status != new_status:
        status_labels = {
            "assigned": "قيد التعيين",
            "in_progress": "قيد المعالجة",
            "answered": "تم الرد",
            "closed": "مغلقة",
            "needs_follow_up": "تحتاج متابعة"
        }
        notify_patient(
            consultation.user_id,
            "تحديث حالة الاستشارة",
            f"تم تحديث حالة استشارتك إلى: {status_labels.get(new_status, new_status)}"
        )

    flash("تم تحديث الحالة", "success")
    return redirect(url_for('doctor_consultation_detail', consultation_id=consultation.id))

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

@app.route('/consult_doctor', methods=['GET', 'POST'])
def consult_doctor():
    # التحقق من تسجيل الدخول
    if 'user_id' not in session:
        flash("يجب تسجيل الدخول أولاً", "danger")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        errors = validate_consultation_form(request.form)
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('consult_doctor.html', form_data=request.form)

        consultation = build_consultation_from_form(request.form, session['user_id'])
        db.session.add(consultation)

        assigned_doctor = auto_assign_doctor(consultation)
        if assigned_doctor:
            consultation.doctor_id = assigned_doctor.id
            consultation.status = 'assigned'
            consultation.assigned_at = datetime.utcnow()
            notify_doctor(assigned_doctor, consultation)
            notify_patient(
                consultation.user_id,
                "استشارة جديدة",
                f"تم استلام استشارتك وتحويلها إلى د. {assigned_doctor.name}"
            )
        else:
            notify_patient(
                consultation.user_id,
                "استشارة قيد الانتظار",
                "تم استلام استشارتك وسنحولها إلى طبيب مختص في أقرب وقت"
            )

        db.session.commit()

        flash('تم إرسال استشارتك بنجاح! يمكنك متابعة حالتها في سجل الاستشارات.', 'success')
        return redirect(url_for('consultations_history'))

    # عرض صفحة الفورم
    return render_template('consult_doctor.html')


@app.route('/consultations', methods=['GET'])
def consultations_history():
    if 'user_id' not in session:
        flash("يجب تسجيل الدخول أولاً", "danger")
        return redirect(url_for('login'))

    consultations = (
        Consultation.query
        .filter_by(user_id=session['user_id'])
        .order_by(Consultation.created_at.desc())
        .all()
    )

    return render_template('consultations.html', consultations=consultations)


@app.route('/consultations/<int:consultation_id>/reply', methods=['POST'])
def doctor_reply(consultation_id):
    payload = request.get_json(silent=True)
    is_json_request = payload is not None

    if payload is None:
        payload = request.form

    doctor = get_logged_in_doctor()
    doctor_id = None

    if doctor is not None:
        doctor_id = doctor.id
    else:
        doctor_id = payload.get('doctor_id')
        if not doctor_id:
            if is_json_request:
                return jsonify({'status': 'error', 'message': 'doctor_id is required'}), 400
            flash("يجب تحديد الطبيب المجيب", "danger")
            return redirect(request.referrer or url_for('portal_choice'))

        try:
            doctor_id = int(doctor_id)
        except (TypeError, ValueError):
            if is_json_request:
                return jsonify({'status': 'error', 'message': 'doctor_id must be an integer'}), 400
            flash("معرف الطبيب غير صحيح", "danger")
            return redirect(request.referrer or url_for('portal_choice'))

        doctor = Doctor.query.get(doctor_id)
        if not doctor:
            if is_json_request:
                return jsonify({'status': 'error', 'message': 'doctor not found'}), 404
            flash("لم يتم العثور على الطبيب", "danger")
            return redirect(request.referrer or url_for('portal_choice'))

    reply_text = payload.get('reply') or payload.get('response')
    if not reply_text or not str(reply_text).strip():
        if is_json_request:
            return jsonify({'status': 'error', 'message': 'reply text is required'}), 400
        flash("الرجاء كتابة الرد قبل الإرسال", "danger")
        return redirect(request.referrer or url_for('doctor_dashboard'))

    consultation = Consultation.query.get_or_404(consultation_id)

    if consultation.doctor_id not in (None, doctor.id):
        if is_json_request:
            return jsonify({'status': 'error', 'message': 'consultation assigned to another doctor'}), 403
        flash("هذه الاستشارة مخصصة لطبيب آخر", "danger")
        return redirect(url_for('doctor_dashboard'))

    reply_text = str(reply_text).strip()

    response = ConsultationResponse(
        consultation_id=consultation.id,
        doctor_id=doctor.id,
        body=reply_text
    )

    db.session.add(response)

    if consultation.doctor_id is None:
        consultation.doctor_id = doctor.id

    if consultation.status not in {'answered', 'closed'}:
        consultation.status = 'answered'

    if not consultation.assigned_at:
        consultation.assigned_at = datetime.utcnow()

    consultation.answered_at = datetime.utcnow()

    notify_patient(
        consultation.user_id,
        "رد الطبيب",
        reply_text
    )

    db.session.commit()

    if is_json_request:
        return jsonify({
            'status': 'success',
            'consultation_id': consultation.id,
            'doctor_id': doctor.id,
            'reply': reply_text,
            'created_at': response.created_at.isoformat()
        })

    flash("تم إرسال الرد للمريض", "success")
    return redirect(url_for('doctor_consultation_detail', consultation_id=consultation.id))
# ------------------- جدولة استشارة -------------------
@app.route('/schedule_consultation/<int:doctor_id>', methods=['GET', 'POST'])
def schedule_consultation(doctor_id):
    if 'user_id' not in session:
        flash("يجب تسجيل الدخول أولاً", "danger")
        return redirect(url_for('login'))
    
    flash("ميزة جدولة الاستشارات المباشرة سيتم دمجها في سير العمل الجديد قريباً.", "info")
    return redirect(url_for('consultations_history'))

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
