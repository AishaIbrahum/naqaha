from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify, abort
from models import (
    db,
    User,
    Company,
    Admin,
    Doctor,
    Package,
    PackageService,
    BookingServiceSelection,
    BookingStatusHistory,
    Appointment,
    AppointmentStatusHistory,
    DoctorMessage,
    PaymentPlan,
    HealthCard,
    Invoice,
    Booking,
    Consultation,
    ConsultationResponse,
    MedicalReport,
    Payment,
    Notification,
    AdminAction,
    DoctorServiceLink,
    DoctorReview,
    CompanyRole,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user

from flask_migrate import Migrate
from datetime import datetime, timedelta, date
from functools import wraps
from collections import defaultdict
import os
import re
import secrets

from sqlalchemy import case, func
from sqlalchemy.orm import joinedload

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
DOCUMENT_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
STATIC_ROOT = os.path.join(os.path.dirname(__file__), "static")
DOCTOR_PHOTO_FOLDER = os.path.join("uploads", "doctors", "photos")
DOCTOR_DOCS_FOLDER = os.path.join("uploads", "doctors", "documents")

os.makedirs(os.path.join(STATIC_ROOT, DOCTOR_PHOTO_FOLDER), exist_ok=True)
os.makedirs(os.path.join(STATIC_ROOT, DOCTOR_DOCS_FOLDER), exist_ok=True)

DEFAULT_ROLE_PERMISSIONS = {
    "مدير الشركة": {"bookings": True, "doctors": True, "finance": True, "support": True, "analytics": True},
    "الطبيب": {"bookings": True, "doctors": True, "finance": False, "support": False, "analytics": False},
    "المحاسب": {"bookings": False, "doctors": False, "finance": True, "support": False, "analytics": True},
    "خدمة العملاء": {"bookings": True, "doctors": False, "finance": False, "support": True, "analytics": False},
}

PERMISSION_LABELS = {
    "bookings": "إدارة الحجوزات",
    "doctors": "فريق العمل الطبي",
    "finance": "الفواتير والمدفوعات",
    "support": "خدمة العملاء والرسائل",
    "analytics": "التقارير والتحليلات",
}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file_storage, relative_folder, allowed_extensions):
    if not file_storage or not file_storage.filename:
        return None

    filename = secure_filename(file_storage.filename)
    extension = filename.rsplit('.', 1)[1].lower()
    if allowed_extensions and extension not in allowed_extensions:
        raise ValueError("نوع الملف غير مدعوم")

    absolute_folder = os.path.join(STATIC_ROOT, relative_folder)
    os.makedirs(absolute_folder, exist_ok=True)
    unique_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{filename}"
    path = os.path.join(absolute_folder, unique_name)
    file_storage.save(path)
    return f"{relative_folder}/{unique_name}".replace('\\', '/')


def parse_service_links(selection_values):
    package_ids, service_ids = set(), set()
    for raw_value in selection_values:
        if raw_value.startswith('package-'):
            try:
                package_ids.add(int(raw_value.split('-', 1)[1]))
            except (ValueError, IndexError):
                continue
        elif raw_value.startswith('service-'):
            try:
                service_ids.add(int(raw_value.split('-', 1)[1]))
            except (ValueError, IndexError):
                continue
    return package_ids, service_ids


def sync_doctor_service_links(doctor, package_ids, service_ids):
    desired_pairs = set()
    if package_ids:
        packages = Package.query.filter(
            Package.id.in_(package_ids),
            Package.provider_id == doctor.company_id
        ).all()
        for pkg in packages:
            desired_pairs.add((pkg.id, None))

    if service_ids:
        services = (
            PackageService.query
            .join(Package, Package.id == PackageService.package_id)
            .filter(
                PackageService.id.in_(service_ids),
                Package.provider_id == doctor.company_id
            )
            .all()
        )
        for service in services:
            desired_pairs.add((service.package_id, service.id))

    existing_links = DoctorServiceLink.query.filter_by(doctor_id=doctor.id).all()
    existing_pairs = {(link.package_id, link.package_service_id): link for link in existing_links}

    for pair, link in existing_pairs.items():
        if pair not in desired_pairs:
            db.session.delete(link)

    for package_id, service_id in desired_pairs:
        if (package_id, service_id) not in existing_pairs:
            db.session.add(DoctorServiceLink(
                doctor_id=doctor.id,
                package_id=package_id,
                package_service_id=service_id
            ))


def ensure_company_roles(company):
    existing_names = {role.name for role in company.roles}
    created = False
    for role_name, perms in DEFAULT_ROLE_PERMISSIONS.items():
        if role_name not in existing_names:
            db.session.add(CompanyRole(company_id=company.id, name=role_name, permissions=perms))
            created = True
    if created:
        db.session.commit()


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


def notify_company(company_id, title, message):
    if not company_id:
        return None

    notification = Notification(
        company_id=company_id,
        title=title,
        body=message
    )
    db.session.add(notification)
    return notification


def get_logged_in_admin():
    admin_id = session.get('admin_id')
    if not admin_id:
        return None
    return Admin.query.get(admin_id)


def admin_login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        admin = get_logged_in_admin()
        if not admin:
            flash("يجب تسجيل دخول الأدمن أولاً", "danger")
            next_url = request.url if request.method == 'GET' else request.referrer
            return redirect(url_for('admin_login', next=next_url))
        return view_func(*args, **kwargs)

    return wrapper

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
    company_id = session.get('company_id')
    if not company_id:
        flash("يجب تسجيل الدخول للشركة", "danger")
        return redirect(url_for('company_login'))

    company = Company.query.get_or_404(company_id)
    ensure_company_roles(company)

    total_packages = Package.query.filter_by(provider_id=company.id).count()
    pending_packages = Package.query.filter_by(provider_id=company.id, status='pending').count()
    approved_packages = Package.query.filter_by(provider_id=company.id, status='approved').count()
    rejected_packages = Package.query.filter_by(provider_id=company.id, status='rejected').count()

    total_bookings = Booking.query.filter_by(company_id=company.id).count()
    pending_bookings = Booking.query.filter_by(company_id=company.id, status='pending').count()
    awaiting_payment = Booking.query.filter_by(company_id=company.id, status='approved').count()
    completed_bookings = Booking.query.filter_by(company_id=company.id, status='completed').count()

    revenue = (
        db.session.query(func.coalesce(func.sum(Payment.amount), 0.0))
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .join(Booking, Invoice.booking_id == Booking.id)
        .filter(Booking.company_id == company.id, Payment.status == 'completed')
        .scalar()
    )

    recent_bookings = (
        Booking.query
        .filter_by(company_id=company.id)
        .options(
            joinedload(Booking.user),
            joinedload(Booking.package),
            joinedload(Booking.doctor)
        )
        .order_by(Booking.requested_at.desc())
        .limit(5)
        .all()
    )

    recent_notifications = (
        Notification.query
        .filter_by(company_id=company.id)
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )

    top_services = (
        db.session.query(
            BookingServiceSelection.service_name,
            func.count(BookingServiceSelection.id).label('usage_count')
        )
        .join(Booking, BookingServiceSelection.booking_id == Booking.id)
        .filter(Booking.company_id == company.id)
        .group_by(BookingServiceSelection.service_name)
        .order_by(func.count(BookingServiceSelection.id).desc())
        .limit(5)
        .all()
    )

    packages_with_services = (
        Package.query
        .filter_by(provider_id=company.id)
        .options(joinedload(Package.services))
        .order_by(Package.title.asc())
        .all()
    )

    doctors = (
        Doctor.query
        .filter_by(company_id=company.id)
        .options(
            joinedload(Doctor.service_links).joinedload(DoctorServiceLink.package),
            joinedload(Doctor.service_links).joinedload(DoctorServiceLink.package_service),
            joinedload(Doctor.reviews)
        )
        .all()
    )

    doctor_ids = [doctor.id for doctor in doctors if doctor.id]

    doctor_ratings = {}
    if doctor_ids:
        rating_rows = (
            db.session.query(
                DoctorReview.doctor_id,
                func.avg(DoctorReview.rating).label('avg_rating'),
                func.count(DoctorReview.id).label('rating_count')
            )
            .filter(DoctorReview.doctor_id.in_(doctor_ids))
            .group_by(DoctorReview.doctor_id)
            .all()
        )
        doctor_ratings = {
            row.doctor_id: {
                'avg': float(row.avg_rating or 0),
                'count': row.rating_count
            }
            for row in rating_rows
        }

    bookings_by_doctor = {}
    completed_by_doctor = {}
    doctor_revenue = {}
    if doctor_ids:
        booking_rows = (
            db.session.query(Booking.doctor_id, func.count(Booking.id))
            .filter(
                Booking.company_id == company.id,
                Booking.doctor_id.in_(doctor_ids)
            )
            .group_by(Booking.doctor_id)
            .all()
        )
        bookings_by_doctor = {doctor_id: count for doctor_id, count in booking_rows}

        completed_rows = (
            db.session.query(Booking.doctor_id, func.count(Booking.id))
            .filter(
                Booking.company_id == company.id,
                Booking.doctor_id.in_(doctor_ids),
                Booking.status == 'completed'
            )
            .group_by(Booking.doctor_id)
            .all()
        )
        completed_by_doctor = {doctor_id: count for doctor_id, count in completed_rows}

        revenue_rows = (
            db.session.query(Booking.doctor_id, func.coalesce(func.sum(Payment.amount), 0))
            .join(Invoice, Payment.invoice_id == Invoice.id)
            .join(Booking, Invoice.booking_id == Booking.id)
            .filter(
                Booking.company_id == company.id,
                Payment.status == 'completed',
                Booking.doctor_id.in_(doctor_ids)
            )
            .group_by(Booking.doctor_id)
            .all()
        )
        doctor_revenue = {doctor_id: float(total or 0) for doctor_id, total in revenue_rows}

    schedule_map = defaultdict(list)
    if doctor_ids:
        schedule_rows = (
            db.session.query(
                Appointment.doctor_id,
                func.date(Appointment.date).label('slot_date'),
                func.count(Appointment.id).label('slot_count')
            )
            .filter(
                Appointment.company_id == company.id,
                Appointment.doctor_id.in_(doctor_ids),
                Appointment.date >= datetime.utcnow() - timedelta(days=1)
            )
            .group_by(Appointment.doctor_id, func.date(Appointment.date))
            .all()
        )
        for doctor_id, slot_date, slot_count in schedule_rows:
            if not doctor_id:
                continue
            if isinstance(slot_date, (datetime, date)):
                slot_value = slot_date.isoformat()
            else:
                slot_value = str(slot_date)
            schedule_map[doctor_id].append({
                'date': slot_value,
                'count': slot_count
            })

    doctor_cards = []
    for doctor in doctors:
        rating_info = doctor_ratings.get(doctor.id, {'avg': 0, 'count': 0})
        package_badges = []
        selected_package_ids = set()
        selected_service_ids = set()
        for link in doctor.service_links:
            if link.package_service:
                label = f"{link.package.title if link.package else ''} – {link.package_service.service_name}"
                selected_service_ids.add(link.package_service.id)
            elif link.package:
                label = f"{link.package.title}"
                selected_package_ids.add(link.package.id)
            else:
                label = None
            if label:
                package_badges.append(label)

        doctor_cards.append({
            'id': doctor.id,
            'name': doctor.name,
            'specialty': doctor.specialty,
            'status': doctor.status,
            'phone': doctor.phone,
            'email': doctor.email,
            'avg_rating': round(rating_info['avg'], 2) if rating_info['avg'] else 0,
            'rating_count': rating_info['count'],
            'total_bookings': bookings_by_doctor.get(doctor.id, 0),
            'completed_bookings': completed_by_doctor.get(doctor.id, 0),
            'revenue': doctor_revenue.get(doctor.id, 0.0),
            'packages': package_badges,
            'package_ids': list(selected_package_ids),
            'service_ids': list(selected_service_ids),
            'cv_summary': doctor.cv_summary,
            'upcoming_slots': schedule_map.get(doctor.id, []),
            'profile_picture': doctor.profile_picture or 'images/logo.jpg'
        })

    cancellation_rows = (
        db.session.query(
            BookingServiceSelection.service_name,
            func.count(BookingServiceSelection.id).label('total'),
            func.sum(case((Booking.status == 'cancelled', 1), else_=0)).label('cancelled')
        )
        .join(Booking, BookingServiceSelection.booking_id == Booking.id)
        .filter(Booking.company_id == company.id)
        .group_by(BookingServiceSelection.service_name)
        .all()
    )

    cancellation_rates = []
    for service_name, total, cancelled in cancellation_rows:
        if not total:
            continue
        rate = (cancelled or 0) / total
        cancellation_rates.append({
            'service_name': service_name,
            'rate': round(rate * 100, 1),
            'total': total
        })

    specialty_rows = (
        db.session.query(
            Doctor.specialty,
            BookingServiceSelection.service_name,
            func.count(BookingServiceSelection.id).label('usage_count')
        )
        .join(Booking, BookingServiceSelection.booking_id == Booking.id)
        .join(Doctor, Booking.doctor_id == Doctor.id)
        .filter(Booking.company_id == company.id)
        .group_by(Doctor.specialty, BookingServiceSelection.service_name)
        .order_by(func.count(BookingServiceSelection.id).desc())
        .limit(6)
        .all()
    )

    top_services_by_specialty = [
        {
            'specialty': specialty or '—',
            'service': service_name,
            'count': usage
        }
        for specialty, service_name, usage in specialty_rows
    ]

    doctor_alerts = [
        doctor for doctor in doctor_cards
        if doctor['avg_rating'] and doctor['avg_rating'] < 3.5
    ]

    doctor_schedule_payload = {doctor['id']: doctor['upcoming_slots'] for doctor in doctor_cards}

    performance_analytics = {
        'bookings_per_doctor': [
            {
                'name': doctor['name'],
                'total': doctor['total_bookings'],
                'completed': doctor['completed_bookings']
            }
            for doctor in doctor_cards
        ],
        'revenue_per_doctor': [
            {
                'name': doctor['name'],
                'revenue': doctor['revenue']
            }
            for doctor in sorted(doctor_cards, key=lambda d: d['revenue'], reverse=True)
        ][:5],
        'cancellation_rates': cancellation_rates,
        'top_services_by_specialty': top_services_by_specialty
    }

    status_labels = {
        'pending': 'قيد المراجعة',
        'approved': 'بانتظار الدفع',
        'completed': 'مكتمل',
        'cancelled': 'ملغي',
        'rejected': 'مرفوض',
        'in_progress': 'جاري التنفيذ'
    }

    metrics = {
        'packages': {
            'total': total_packages,
            'pending': pending_packages,
            'approved': approved_packages,
            'rejected': rejected_packages,
        },
        'bookings': {
            'total': total_bookings,
            'pending': pending_bookings,
            'awaiting_payment': awaiting_payment,
            'completed': completed_bookings,
        },
        'revenue': revenue or 0.0
    }

    return render_template(
        'company_dashboard.html',
        company=company,
        metrics=metrics,
        recent_bookings=recent_bookings,
        recent_notifications=recent_notifications,
        top_services=top_services,
        status_labels=status_labels,
        doctors=doctor_cards,
        packages_with_services=packages_with_services,
        doctor_schedule_data=doctor_schedule_payload,
        performance_analytics=performance_analytics,
        permission_labels=PERMISSION_LABELS,
        company_roles=company.roles,
        doctor_alerts=doctor_alerts,
        user=None
    )


@app.route('/company/doctors/add', methods=['POST'])
def company_add_doctor():
    company_id = session.get('company_id')
    if not company_id:
        flash("يجب تسجيل دخول الشركة", "danger")
        return redirect(url_for('company_login'))

    company = Company.query.get_or_404(company_id)

    name = (request.form.get('name') or '').strip()
    specialty = (request.form.get('specialty') or '').strip()
    email = (request.form.get('email') or '').strip().lower()
    phone = (request.form.get('phone') or '').strip()
    status = request.form.get('status') or 'pending'
    cv_summary = (request.form.get('cv_summary') or '').strip()
    temp_password = request.form.get('password') or secrets.token_hex(4)

    if not name or not specialty or not email:
        flash('يرجى تعبئة الاسم، التخصص والبريد الإلكتروني', 'danger')
        return redirect(url_for('company_dashboard') + '#doctor-management')

    existing = Doctor.query.filter(func.lower(Doctor.email) == email).first()
    if existing:
        flash('هناك حساب طبيب بنفس البريد الإلكتروني', 'danger')
        return redirect(url_for('company_dashboard') + '#doctor-management')

    doctor = Doctor(
        name=name,
        specialty=specialty,
        email=email,
        phone=phone,
        status=status,
        cv_summary=cv_summary,
        password=generate_password_hash(temp_password),
        company_id=company.id
    )

    profile_file = request.files.get('profile_picture')
    license_file = request.files.get('license_document')
    certificate_file = request.files.get('certificate_document')

    try:
        if profile_file and profile_file.filename:
            doctor.profile_picture = save_uploaded_file(profile_file, DOCTOR_PHOTO_FOLDER, ALLOWED_EXTENSIONS)
        if license_file and license_file.filename:
            doctor.license_document = save_uploaded_file(license_file, DOCTOR_DOCS_FOLDER, DOCUMENT_EXTENSIONS)
        if certificate_file and certificate_file.filename:
            doctor.certificate_document = save_uploaded_file(certificate_file, DOCTOR_DOCS_FOLDER, DOCUMENT_EXTENSIONS)
    except ValueError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('company_dashboard') + '#doctor-management')

    db.session.add(doctor)
    db.session.flush()

    selection_values = request.form.getlist('service_links')
    package_ids, service_ids = parse_service_links(selection_values)
    sync_doctor_service_links(doctor, package_ids, service_ids)
    db.session.commit()

    flash(f"تمت إضافة الطبيب {doctor.name}. كلمة المرور المؤقتة: {temp_password}", 'success')
    return redirect(url_for('company_dashboard') + '#doctor-management')


@app.route('/company/doctors/<int:doctor_id>/status', methods=['POST'])
def company_update_doctor_status(doctor_id):
    company_id = session.get('company_id')
    if not company_id:
        flash("يجب تسجيل دخول الشركة", "danger")
        return redirect(url_for('company_login'))

    doctor = Doctor.query.filter_by(id=doctor_id, company_id=company_id).first_or_404()
    status = request.form.get('status')
    allowed_statuses = {'available', 'busy', 'vacation', 'pending'}
    if status not in allowed_statuses:
        flash('حالة الطبيب غير معتمدة', 'danger')
        return redirect(url_for('company_dashboard') + '#doctor-management')

    doctor.status = status
    db.session.commit()
    flash('تم تحديث حالة الطبيب', 'success')
    return redirect(url_for('company_dashboard') + '#doctor-management')


@app.route('/company/doctors/<int:doctor_id>/services', methods=['POST'])
def company_update_doctor_services(doctor_id):
    company_id = session.get('company_id')
    if not company_id:
        flash("يجب تسجيل دخول الشركة", "danger")
        return redirect(url_for('company_login'))

    doctor = Doctor.query.filter_by(id=doctor_id, company_id=company_id).first_or_404()
    selection_values = request.form.getlist('service_links')
    package_ids, service_ids = parse_service_links(selection_values)
    sync_doctor_service_links(doctor, package_ids, service_ids)
    db.session.commit()
    flash('تم تحديث ارتباطات الطبيب بالخدمات', 'success')
    return redirect(url_for('company_dashboard') + '#doctor-management')


@app.route('/company/roles/<int:role_id>/permissions', methods=['POST'])
def company_update_role_permissions(role_id):
    company_id = session.get('company_id')
    if not company_id:
        flash("يجب تسجيل دخول الشركة", "danger")
        return redirect(url_for('company_login'))

    role = CompanyRole.query.get_or_404(role_id)
    if role.company_id != company_id:
        flash('لا تملك صلاحية تعديل هذا الدور', 'danger')
        return redirect(url_for('company_dashboard') + '#role-settings')

    selected_permissions = set(request.form.getlist('permissions'))
    updated_permissions = {key: (key in selected_permissions) for key in PERMISSION_LABELS.keys()}
    role.permissions = updated_permissions
    db.session.commit()

    flash(f"تم تحديث صلاحيات دور {role.name}", 'success')
    return redirect(url_for('company_dashboard') + '#role-settings')

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
    range_key = request.args.get('range', 'today')
    valid_ranges = {'today': 'اليوم', 'week': 'هذا الأسبوع', 'all': 'الكل'}
    if range_key not in valid_ranges:
        range_key = 'today'

    bookings_query = (
        Booking.query
        .outerjoin(Appointment, Booking.appointment_id == Appointment.id)
        .options(
            joinedload(Booking.user),
            joinedload(Booking.package),
            joinedload(Booking.selected_services),
            joinedload(Booking.invoices),
            joinedload(Booking.appointment)
        )
        .filter(Booking.doctor_id == doctor.id)
    )

    date_expr = func.coalesce(Booking.scheduled_for, Appointment.date)
    now = datetime.utcnow()
    if range_key == 'today':
        start = datetime(now.year, now.month, now.day)
        end = start + timedelta(days=1)
        bookings_query = bookings_query.filter(date_expr >= start, date_expr < end)
    elif range_key == 'week':
        start_of_week = datetime(now.year, now.month, now.day) - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=7)
        bookings_query = bookings_query.filter(date_expr >= start_of_week, date_expr < end_of_week)

    bookings = bookings_query.order_by(date_expr.asc().nullslast()).all()

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
        "waiting": len(new_consultations),
        "bookings": len(bookings)
    }

    booking_status_labels = {
        'pending': 'بانتظار المراجعة',
        'approved': 'مؤكد',
        'completed': 'مكتمل',
        'cancelled': 'ملغي',
        'rejected': 'مرفوض'
    }

    status_choices = [
        ('approved', 'مؤكد'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي')
    ]

    return render_template(
        'doctor_dashboard.html',
        doctor=doctor,
        stats=stats,
        new_consultations=new_consultations,
        active_consultations=active_consultations,
        answered_consultations=answered_consultations,
        bookings=bookings,
        booking_filters=valid_ranges,
        selected_range=range_key,
        booking_status_labels=booking_status_labels,
        booking_status_choices=status_choices
    )


@app.route('/doctor/bookings/<int:booking_id>/status', methods=['POST'])
@doctor_login_required
def doctor_update_booking_status(booking_id):
    doctor = get_logged_in_doctor()
    booking = Booking.query.get_or_404(booking_id)

    if booking.doctor_id != doctor.id:
        flash("لا يمكنك تعديل هذا الحجز", "danger")
        return redirect(url_for('doctor_dashboard'))

    new_status = request.form.get('status')
    allowed_statuses = {'approved', 'completed', 'cancelled'}
    if new_status not in allowed_statuses:
        flash("حالة غير مدعومة", "danger")
        return redirect(url_for('doctor_dashboard'))

    if booking.status == new_status:
        flash("لم يتم تغيير الحالة", "info")
        return redirect(url_for('doctor_dashboard'))

    booking.status = new_status
    history = BookingStatusHistory(
        booking_id=booking.id,
        status=new_status,
        note=f"تم التحديث بواسطة الطبيب {doctor.name}"
    )
    db.session.add(history)

    if booking.appointment:
        if new_status == 'completed':
            booking.appointment.status = 'completed'
        elif new_status == 'cancelled':
            booking.appointment.status = 'cancelled'
        booking.appointment.status_updated_at = datetime.utcnow()

    db.session.commit()
    flash("تم تحديث حالة الحجز", "success")
    return redirect(url_for('doctor_dashboard', range=request.args.get('range', 'today')))


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
    return render_template('admin_login.html', next=request.args.get('next'), user=None)

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session['admin_id'] = admin.id
            flash("تم تسجيل دخول الأدمن!", "success")
            next_url = request.args.get('next') or request.form.get('next')
            return redirect(next_url or url_for('admin_dashboard'))
        else:
            flash("البريد أو كلمة السر خاطئة!", "danger")
    return render_template('admin_login.html', next=request.args.get('next'), user=None)

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
@admin_login_required
def admin_dashboard():
    pending_count = Package.query.filter_by(status='pending').count()
    return render_template('admin_dashboard.html', pending_packages=pending_count, user=None)


@app.route('/admin/packages')
@admin_login_required
def admin_packages():
    status_order = case(
        (Package.status == 'pending', 0),
        (Package.status == 'approved', 1),
        else_=2
    )

    packages = (
        Package.query
        .options(
            joinedload(Package.services),
            joinedload(Package.provider)
        )
        .order_by(status_order, Package.status_updated_at.desc().nullslast())
        .all()
    )

    status_labels = {
        'pending': 'قيد المراجعة',
        'approved': 'معتمد',
        'rejected': 'مرفوض'
    }

    return render_template('admin_packages.html', packages=packages, status_labels=status_labels, user=None)
    


@app.route('/admin/packages/<int:package_id>/decision', methods=['POST'])
@admin_login_required
def admin_package_decision(package_id):
    admin = get_logged_in_admin()
    package = Package.query.get_or_404(package_id)

    decision = request.form.get('decision')
    note = (request.form.get('note') or '').strip()

    if decision not in {'approve', 'reject'}:
        flash('قرار غير صالح', 'danger')
        return redirect(url_for('admin_packages'))

    if decision == 'reject' and not note:
        flash('يرجى كتابة ملاحظات سبب الرفض', 'danger')
        return redirect(url_for('admin_packages'))

    if decision == 'approve':
        package.status = 'approved'
        package.admin_note = None
        package.approved_by = admin.id
        package.status_updated_at = datetime.utcnow()

        notify_company(
            package.provider_id,
            'تم اعتماد الباقة',
            f"تمت الموافقة على باقتكم '{package.title}' وهي متاحة الآن للعملاء."
        )

        flash('تم اعتماد الباقة بنجاح', 'success')

    else:
        package.status = 'rejected'
        package.admin_note = note
        package.approved_by = admin.id
        package.status_updated_at = datetime.utcnow()

        notify_company(
            package.provider_id,
            'تم رفض الباقة',
            f"تم رفض باقتكم '{package.title}'. السبب: {note}"
        )

        flash('تم رفض الباقة', 'info')

    db.session.commit()
    return redirect(url_for('admin_packages'))

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
    all_packages = (
        Package.query
        .options(joinedload(Package.services))
        .filter(Package.status == 'approved')
        .order_by(Package.id.desc())
        .all()
    )
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])

    return render_template('ready_packages.html', packages=all_packages, user=user)

# ------------------- إضافة باقة جديدة -------------------
@app.route("/add_package", methods=["GET", "POST"])
def add_package():
    company_id = session.get('company_id')
    if not company_id:
        flash("يجب تسجيل دخول الشركة لإضافة باقة", "danger")
        return redirect(url_for('company_login'))

    company = Company.query.get_or_404(company_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        service_names = request.form.getlist('service_name[]')
        service_descriptions = request.form.getlist('service_description[]')
        service_prices = request.form.getlist('service_price[]')

        if not title or not description:
            flash("الرجاء تعبئة جميع الحقول المطلوبة", "danger")
            return render_template("add_package.html", company=company)

        if not service_names or all(not name.strip() for name in service_names):
            flash("أضف خدمة واحدة على الأقل للباقة", "danger")
            return render_template("add_package.html", company=company)

        file = request.files.get("image")
        if not file or not allowed_file(file.filename):
            flash("صيغة الصورة غير مدعومة", "danger")
            return render_template("add_package.html", company=company)

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        new_package = Package(
            title=title,
            description=description,
            image=filename,
            provider_id=company.id,
            status="pending",
            status_updated_at=datetime.utcnow()
        )
        db.session.add(new_package)
        db.session.flush()

        for name, desc, price in zip(service_names, service_descriptions, service_prices):
            name = (name or "").strip()
            desc = (desc or "").strip()
            price_value = None
            if not name:
                continue
            try:
                price_value = float(price) if price else 0.0
            except ValueError:
                price_value = 0.0

            service = PackageService(
                package_id=new_package.id,
                service_name=name,
                service_description=desc or None,
                service_price=price_value
            )
            db.session.add(service)

        notify_company(
            company.id,
            "قيد المراجعة",
            f"تم استلام طلب إضافة الباقة '{new_package.title}' وسيتم مراجعته من قبل الأدمن."
        )

        db.session.commit()
        flash("تم إرسال الطلب للمراجعة!", "success")
        return redirect(url_for("company_dashboard"))

    return render_template("add_package.html", company=company)


@app.route('/company/packages')
def company_packages():
    company_id = session.get('company_id')
    if not company_id:
        flash("يجب تسجيل دخول الشركة", "danger")
        return redirect(url_for('company_login'))

    company = Company.query.get_or_404(company_id)
    packages = (
        Package.query
        .filter_by(provider_id=company.id)
        .options(joinedload(Package.services))
        .order_by(Package.status_updated_at.desc().nullslast())
        .all()
    )

    recent_notifications = (
        Notification.query
        .filter_by(company_id=company.id)
        .order_by(Notification.created_at.desc())
        .limit(10)
        .all()
    )

    status_labels = {
        'pending': 'قيد المراجعة',
        'approved': 'معتمد',
        'rejected': 'مرفوض'
    }

    return render_template(
        'company_packages.html',
        company=company,
        packages=packages,
        status_labels=status_labels,
        notifications=recent_notifications,
        user=None
    )


@app.route('/company/bookings', methods=['GET'])
def company_bookings():
    company_id = session.get('company_id')
    if not company_id:
        flash("يجب تسجيل دخول الشركة", "danger")
        return redirect(url_for('company_login'))

    company = Company.query.get_or_404(company_id)

    bookings = (
        Booking.query
        .filter_by(company_id=company.id)
        .options(
            joinedload(Booking.package),
            joinedload(Booking.user),
            joinedload(Booking.selected_services),
            joinedload(Booking.status_history),
            joinedload(Booking.doctor)
        )
        .order_by(Booking.requested_at.desc())
        .all()
    )

    company_doctors = Doctor.query.filter_by(company_id=company.id).order_by(Doctor.name.asc()).all()

    status_labels = {
        'pending': 'قيد المراجعة',
        'approved': 'بانتظار الدفع',
        'completed': 'مكتمل',
        'cancelled': 'ملغي',
        'rejected': 'مرفوض'
    }

    return render_template(
        'company_bookings.html',
        company=company,
        bookings=bookings,
        status_labels=status_labels,
        doctors=company_doctors,
        user=None
    )


@app.route('/company/bookings/<int:booking_id>/decision', methods=['POST'])
def company_booking_decision(booking_id):
    company_id = session.get('company_id')
    if not company_id:
        flash("يجب تسجيل دخول الشركة", "danger")
        return redirect(url_for('company_login'))

    booking = Booking.query.get_or_404(booking_id)
    if booking.company_id != company_id:
        flash("لا تملك صلاحية هذا الحجز", "danger")
        return redirect(url_for('company_bookings'))

    decision = request.form.get('decision')
    note = (request.form.get('note') or '').strip()

    allowed_decisions = {'approved', 'rejected'}
    if decision not in allowed_decisions:
        flash('قرار غير صالح', 'danger')
        return redirect(url_for('company_bookings'))

    if decision == 'rejected' and not note:
        flash('يرجى توضيح سبب الرفض للعميل', 'danger')
        return redirect(url_for('company_bookings'))

    invoice = booking.invoices[0] if booking.invoices else None
    if decision == 'approved':
        total_amount = sum((service.service_price or 0) for service in booking.selected_services)
        if invoice:
            invoice.amount = total_amount
            invoice.status = 'unpaid'
            invoice.paid_at = None
        else:
            invoice = Invoice(
                user_id=booking.user_id,
                booking_id=booking.id,
                amount=total_amount,
                status='unpaid'
            )
            db.session.add(invoice)
    else:
        if invoice:
            invoice.status = 'cancelled'
            invoice.paid_at = None

    booking.status = decision
    history_entry = BookingStatusHistory(
        booking_id=booking.id,
        status=decision,
        note=note or None
    )
    db.session.add(history_entry)

    status_labels = {
        'approved': 'موافق عليه',
        'rejected': 'مرفوض'
    }

    if decision == 'approved':
        message = (
            f"تمت موافقة الشركة على حجز '{booking.package.title if booking.package else ''}'. "
            "يرجى إتمام عملية الدفع لإكمال الحجز."
        )
        if note:
            message += f" ملاحظة الشركة: {note}"
    else:
        message = (
            f"تم رفض حجز '{booking.package.title if booking.package else ''}'."
            + (f" السبب: {note}" if note else '')
        )

    notify_patient(booking.user_id, 'تحديث حالة الحجز', message)

    db.session.commit()

    flash('تم تحديث حالة الحجز', 'success')
    return redirect(url_for('company_bookings'))


@app.route('/company/bookings/<int:booking_id>/assign_doctor', methods=['POST'])
def company_assign_doctor(booking_id):
    company_id = session.get('company_id')
    if not company_id:
        flash("يجب تسجيل دخول الشركة", "danger")
        return redirect(url_for('company_login'))

    booking = Booking.query.get_or_404(booking_id)
    if booking.company_id != company_id:
        flash('لا يمكنك تعديل هذا الحجز', 'danger')
        return redirect(url_for('company_bookings'))

    doctor_id = request.form.get('doctor_id')
    if not doctor_id:
        flash('يرجى اختيار طبيب', 'danger')
        return redirect(url_for('company_bookings'))

    try:
        doctor_id = int(doctor_id)
    except ValueError:
        flash('المعرف غير صالح', 'danger')
        return redirect(url_for('company_bookings'))

    doctor = Doctor.query.filter_by(id=doctor_id, company_id=company_id).first()
    if not doctor:
        flash('لم يتم العثور على الطبيب المطلوب', 'danger')
        return redirect(url_for('company_bookings'))

    booking.doctor_id = doctor.id
    if booking.appointment:
        booking.appointment.doctor_id = doctor.id

    status_note = BookingStatusHistory(
        booking_id=booking.id,
        status=booking.status,
        note=f'تم إسناد الحجز إلى الطبيب {doctor.name}'
    )
    db.session.add(status_note)

    if booking.user_id:
        db.session.add(DoctorMessage(
            user_id=booking.user_id,
            doctor_id=doctor.id,
            message=f"تم تعيينك لمتابعة حجز رقم {booking.id}."
        ))

    db.session.commit()
    flash('تم ربط الحجز بالطبيب المختار', 'success')
    return redirect(url_for('company_bookings'))

@app.route('/appointments')
def appointments():
    user_id = session.get("user_id")
    if not user_id:
        flash("يجب تسجيل الدخول أولاً", "danger")
        return redirect(url_for('login'))

    appointments = (
        Appointment.query
        .filter_by(user_id=user_id)
        .options(
            joinedload(Appointment.bookings)
            .joinedload(Booking.selected_services),
            joinedload(Appointment.bookings).joinedload(Booking.package),
            joinedload(Appointment.bookings).joinedload(Booking.invoices),
            joinedload(Appointment.bookings).joinedload(Booking.reviews),
            joinedload(Appointment.bookings).joinedload(Booking.doctor),
            joinedload(Appointment.doctor_obj)
        )
        .order_by(Appointment.date.desc())
        .all()
    )

    user = User.query.get(user_id)

    return render_template('appointments.html', appointments=appointments, user=user)



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


@app.route('/booking/<int:booking_id>/payment', methods=['GET', 'POST'])
def booking_payment(booking_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("يجب تسجيل الدخول أولاً", "danger")
        return redirect(url_for('login'))

    booking = (
        Booking.query
        .options(
            joinedload(Booking.package),
            joinedload(Booking.selected_services),
            joinedload(Booking.invoices)
        )
        .get_or_404(booking_id)
    )

    if booking.user_id != user_id:
        flash("لا تملك صلاحية لهذا الحجز", "danger")
        return redirect(url_for('appointments'))

    if booking.status not in {'approved', 'completed'}:
        flash("يرجى انتظار موافقة الشركة على الحجز قبل إتمام الدفع", "warning")
        return redirect(url_for('appointments'))

    invoice = booking.invoices[0] if booking.invoices else None
    service_total = sum([s.service_price or 0 for s in booking.selected_services])

    if invoice is None:
        invoice = Invoice(
            user_id=user_id,
            booking_id=booking.id,
            amount=service_total,
            status='unpaid'
        )
        db.session.add(invoice)
        db.session.commit()

    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount') or invoice.amount or 0)
        except ValueError:
            amount = 0

        payment_method = request.form.get('payment_method', 'card')

        if amount < 0:
            flash("المبلغ غير صالح", "danger")
            return redirect(url_for('booking_payment', booking_id=booking.id))

        payment = Payment(
            invoice_id=invoice.id,
            amount=amount,
            method=payment_method,
            status='completed',
            paid_at=datetime.utcnow()
        )

        invoice.amount = amount
        invoice.status = 'paid'
        invoice.paid_at = datetime.utcnow()

        booking.status = 'completed'
        history_entry = BookingStatusHistory(
            booking_id=booking.id,
            status='completed',
            note='تم الدفع الإلكتروني وإتمام الحجز'
        )
        db.session.add(history_entry)
        db.session.add(payment)

        notify_company(
            booking.company_id,
            'تم إتمام الحجز',
            f"قام المستخدم بإكمال الدفع لحجز الباقة '{booking.package.title if booking.package else ''}'."
        )

        db.session.commit()
        flash("تم الدفع بنجاح!", "success")
        return redirect(url_for('appointments'))

    return render_template(
        'payment.html',
        booking=booking,
        invoice=invoice,
        service_total=service_total,
        user=User.query.get(user_id)
    )


@app.route('/bookings/<int:booking_id>/doctor_review', methods=['POST'])
def submit_doctor_review(booking_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("يجب تسجيل الدخول أولاً", "danger")
        return redirect(url_for('login'))

    booking = (
        Booking.query
        .options(
            joinedload(Booking.appointment).joinedload(Appointment.doctor_obj),
            joinedload(Booking.doctor)
        )
        .get_or_404(booking_id)
    )

    if booking.user_id != user_id:
        flash('لا يمكنك تقييم هذا الحجز', 'danger')
        return redirect(url_for('appointments'))

    doctor = booking.doctor or (booking.appointment.doctor_obj if booking.appointment else None)
    if not doctor:
        flash('لم يتم تعيين طبيب لهذا الحجز بعد', 'warning')
        return redirect(url_for('appointments'))

    if booking.status != 'completed':
        flash('لا يمكن إضافة التقييم قبل اكتمال الحجز', 'warning')
        return redirect(url_for('appointments'))

    try:
        rating = int(request.form.get('rating', 0))
    except ValueError:
        rating = 0

    try:
        bedside = int(request.form.get('bedside_manner', 0))
    except ValueError:
        bedside = None

    notes = (request.form.get('notes') or '').strip()

    if rating not in {1, 2, 3, 4, 5}:
        flash('التقييم يجب أن يكون بين 1 و5', 'danger')
        return redirect(url_for('appointments'))

    existing_review = DoctorReview.query.filter_by(booking_id=booking.id, user_id=user_id).first()
    if existing_review:
        existing_review.rating = rating
        existing_review.bedside_manner = bedside
        existing_review.notes = notes or existing_review.notes
        message = 'تم تحديث تقييم الطبيب'
    else:
        review = DoctorReview(
            doctor_id=doctor.id,
            user_id=user_id,
            booking_id=booking.id,
            appointment_id=booking.appointment_id,
            rating=rating,
            bedside_manner=bedside,
            notes=notes
        )
        db.session.add(review)
        message = 'تم إرسال تقييم الطبيب'

    db.session.commit()
    flash(message, 'success')
    return redirect(url_for('appointments'))


# ------------------- إنشاء حجز جديد -------------------
@app.route('/book_package/<int:package_id>', methods=['GET', 'POST'])
def book_package(package_id):
    if 'user_id' not in session:
        flash("يجب تسجيل الدخول أولاً", "danger")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)

    package = (
        Package.query
        .options(joinedload(Package.services))
        .get_or_404(package_id)
    )

    if package.status != 'approved':
        flash("هذه الباقة غير متاحة للحجز حالياً", "danger")
        return redirect(url_for('ready_packages'))

    if not package.services:
        flash("هذه الباقة لا تحتوي على خدمات متاحة للحجز حالياً", "danger")
        return redirect(url_for('ready_packages'))

    if request.method == 'POST':
        service_ids_raw = request.form.getlist('service_ids')
        notes = request.form.get('notes')
        contact_method = request.form.get('contact_method')
        scheduled_for_str = request.form.get('scheduled_for')

        if not service_ids_raw:
            flash("يرجى اختيار خدمة واحدة على الأقل", "danger")
            return redirect(url_for('book_package', package_id=package.id))

        try:
            service_ids = [int(value) for value in service_ids_raw]
        except ValueError:
            flash("معرّفات الخدمات غير صحيحة", "danger")
            return redirect(url_for('book_package', package_id=package.id))

        try:
            scheduled_for = datetime.strptime(scheduled_for_str, "%Y-%m-%dT%H:%M") if scheduled_for_str else None
        except ValueError:
            scheduled_for = None

        if not scheduled_for:
            flash("يرجى تحديد تاريخ ووقت الحجز", "danger")
            return redirect(url_for('book_package', package_id=package.id))

        services = (
            PackageService.query
            .filter(
                PackageService.id.in_(service_ids),
                PackageService.package_id == package.id
            )
            .all()
        )

        if len(services) != len(service_ids):
            flash("تم العثور على خدمات غير صالحة في الطلب", "danger")
            return redirect(url_for('book_package', package_id=package.id))

        if not package.provider_id:
            flash("لا يمكن إتمام الحجز لأن الباقة غير مرتبطة بشركة مقدمة.", "danger")
            return redirect(url_for('ready_packages'))

        note_details = notes.strip() if notes else ""
        if contact_method:
            contact_note = f"طريقة التواصل المفضلة: {contact_method}"
            note_details = f"{note_details}\n{contact_note}" if note_details else contact_note

        appointment = Appointment(
            user_id=user_id,
            company_id=package.provider_id,
            date=scheduled_for,
            notes=note_details
        )
        db.session.add(appointment)
        db.session.flush()

        booking = Booking(
            user_id=user_id,
            package_id=package.id,
            appointment_id=appointment.id,
            company_id=package.provider_id,
            scheduled_for=scheduled_for,
            notes=note_details,
            status="pending"
        )
        db.session.add(booking)
        db.session.flush()

        total_amount = 0.0

        for service in services:
            selection = BookingServiceSelection(
                booking_id=booking.id,
                package_service_id=service.id,
                service_name=service.service_name,
                service_description=service.service_description,
                service_price=service.service_price
            )
            db.session.add(selection)
            if service.service_price:
                total_amount += service.service_price

        invoice = Invoice(
            user_id=user_id,
            booking_id=booking.id,
            amount=total_amount,
            status='unpaid'
        )
        db.session.add(invoice)

        history_entry = BookingStatusHistory(
            booking_id=booking.id,
            status='pending',
            note='تم إرسال طلب الحجز (بانتظار موافقة الشركة)'
        )
        db.session.add(history_entry)

        notify_company(
            package.provider_id,
            'طلب حجز جديد',
            f"لديك طلب حجز جديد لباقتك '{package.title}' من المستخدم {user.first_name if user else user_id}."
        )

        db.session.commit()
        flash("تم إرسال طلب الحجز بنجاح، سنقوم بالتواصل معك قريباً", "success")
        return redirect(url_for('appointments'))

    selected_services = package.services
    return render_template('book_package.html', package=package, services=selected_services, user=user)


# ------------------- تعديل حالة الحجز (Admin) -------------------
@app.route('/booking/<int:booking_id>/update_status', methods=['POST'])
def update_booking_status(booking_id):
    if 'admin_id' not in session:
        flash("يجب تسجيل الدخول كأدمن", "danger")
        return redirect(url_for('admin_login'))
    
    booking = Booking.query.get_or_404(booking_id)
    new_status = request.form.get('status')  # pending / approved / rejected / completed / cancelled
    note = (request.form.get('note') or '').strip()

    previous_status = booking.status
    booking.status = new_status
    db.session.add(BookingStatusHistory(
        booking_id=booking.id,
        status=new_status,
        note=note or None
    ))

    db.session.commit()

    status_labels = {
        'pending': 'قيد المراجعة',
        'approved': 'موافق عليه',
        'completed': 'مكتمل',
        'cancelled': 'ملغي',
        'rejected': 'مرفوض'
    }

    if previous_status != new_status:
        package_title = booking.package.title if booking.package else 'حجزك'
        message = (
            f"تم تحديث حالة حجز '{package_title}' إلى {status_labels.get(new_status, new_status)}"
            + (f". ملاحظة الأدمن: {note}" if note else '')
        )

        notify_patient(
            booking.user_id,
            'تحديث حالة الحجز',
            message
        )

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
    user = User.query.get(user_id)
    return render_template('payments.html', payments=payments, user=user)


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
