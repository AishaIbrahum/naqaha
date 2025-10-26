from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# -------------------- جدول المستخدمين --------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False, unique=True)
    gender = db.Column(db.String(10))
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    address = db.Column(db.String(200))
    birth_date = db.Column(db.Date)
    profile_picture = db.Column(db.String(200), default="default.jpg")

    appointments = db.relationship("Appointment", backref="user", lazy=True)
    messages = db.relationship("DoctorMessage", backref="user", lazy=True)
    payment_plans = db.relationship("PaymentPlan", backref="user", lazy=True)
    health_cards = db.relationship("HealthCard", backref="user", lazy=True)
    bookings = db.relationship("Booking", backref="user", lazy=True)
    invoices = db.relationship("Invoice", backref="user", lazy=True)
    consultations = db.relationship("Consultation", backref="user", lazy=True)
    notifications = db.relationship("Notification", backref="user", lazy=True)
    medical_reports = db.relationship("MedicalReport", backref="user", lazy=True)
    doctor_reviews = db.relationship("DoctorReview", backref="user", lazy=True)


# -------------------- جدول الشركات --------------------
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))

    doctors = db.relationship("Doctor", backref="company", lazy=True)
    packages = db.relationship("Package", backref="provider", lazy=True)
    appointments = db.relationship("Appointment", backref="company", lazy=True)
    bookings = db.relationship("Booking", backref="company", lazy=True)
    notifications = db.relationship("Notification", backref="company", lazy=True)
    roles = db.relationship(
        "CompanyRole",
        backref="company",
        lazy=True,
        cascade="all, delete-orphan"
    )


# -------------------- جدول الأدمن --------------------
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)

    approved_doctors = db.relationship("Doctor", backref="approved_by_admin", lazy=True)
    approved_packages = db.relationship("Package", backref="approved_by_admin", lazy=True)
    actions = db.relationship("AdminAction", backref="admin", lazy=True)


# -------------------- جدول الأطباء --------------------
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialty = db.Column(db.String(100))
    profile_picture = db.Column(db.String(200))
    status = db.Column(db.String(50), default="pending")
    phone = db.Column(db.String(30))
    cv_summary = db.Column(db.Text)
    license_document = db.Column(db.String(200))
    certificate_document = db.Column(db.String(200))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))
    last_login = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('admin.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))

    messages = db.relationship("DoctorMessage", backref="doctor", lazy=True)
    appointments = db.relationship("Appointment", backref="doctor_obj", lazy=True)
    consultations = db.relationship("Consultation", backref="doctor", lazy=True)
    medical_reports = db.relationship("MedicalReport", backref="doctor", lazy=True)
    consultation_responses = db.relationship("ConsultationResponse", backref="doctor", lazy=True)
    service_links = db.relationship(
        "DoctorServiceLink",
        backref="doctor",
        lazy=True,
        cascade="all, delete-orphan"
    )
    reviews = db.relationship(
        "DoctorReview",
        backref="doctor",
        lazy=True,
        cascade="all, delete-orphan"
    )


# -------------------- جدول الباقات --------------------
class Package(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    image = db.Column(db.String(200))
    provider_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    approved_by = db.Column(db.Integer, db.ForeignKey('admin.id'))
    status = db.Column(db.String(50), default="pending")
    admin_note = db.Column(db.Text)
    status_updated_at = db.Column(db.DateTime)

    services = db.relationship("PackageService", backref="package", lazy=True)
    bookings = db.relationship("Booking", backref="package", lazy=True)
    doctor_service_links = db.relationship("DoctorServiceLink", backref="package", lazy=True)


# -------------------- جدول خدمات الباقات --------------------
class PackageService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    package_id = db.Column(db.Integer, db.ForeignKey('package.id'))
    service_name = db.Column(db.String(100))
    service_description = db.Column(db.Text)
    service_price = db.Column(db.Float)

    selections = db.relationship(
        "BookingServiceSelection",
        backref="package_service",
        lazy=True
    )
    doctor_links = db.relationship("DoctorServiceLink", backref="package_service", lazy=True)


class BookingServiceSelection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    package_service_id = db.Column(db.Integer, db.ForeignKey('package_service.id'), nullable=True)
    service_name = db.Column(db.String(100))
    service_description = db.Column(db.Text)
    service_price = db.Column(db.Float)


# -------------------- ربط الطبيب بالخدمات --------------------
class DoctorServiceLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('package.id'), nullable=False)
    package_service_id = db.Column(db.Integer, db.ForeignKey('package_service.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# -------------------- تقييمات الأطباء --------------------
class DoctorReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=True)
    rating = db.Column(db.Integer, nullable=False)
    bedside_manner = db.Column(db.Integer)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# -------------------- جدول المواعيد --------------------
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text)
    status = db.Column(db.String(50), nullable=False, default="pending_confirmation")
    service_type = db.Column(db.String(120))
    proposed_time = db.Column(db.DateTime, nullable=True)
    proposed_note = db.Column(db.Text, nullable=True)
    status_updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=False)

    bookings = db.relationship("Booking", backref="appointment", lazy=True)
    medical_reports = db.relationship("MedicalReport", backref="appointment", lazy=True)
    reviews = db.relationship(
        "DoctorReview",
        backref="appointment",
        lazy=True,
        cascade="all, delete-orphan"
    )
    status_history = db.relationship(
        "AppointmentStatusHistory",
        backref="appointment",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="AppointmentStatusHistory.created_at.asc()"
    )

    def latest_status(self):
        return self.status_history[-1] if self.status_history else None

    def timeline(self):
        return self.status_history


# -------------------- جدول رسائل الطبيب --------------------
class DoctorMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# -------------------- جدول خطط الدفع --------------------
class PaymentPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    plan_name = db.Column(db.String(100))
    amount = db.Column(db.Float)
    status = db.Column(db.String(50))


# -------------------- جدول بطاقة الصحة --------------------
class HealthCard(db.Model):
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    card_number = db.Column(db.String(50))
    issued_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)


# -------------------- جدول الحجز --------------------
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('package.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=True)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_for = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default="pending")

    invoices = db.relationship('Invoice', backref='booking', lazy=True)
    consultations = db.relationship('Consultation', backref='booking', lazy=True)
    medical_reports = db.relationship('MedicalReport', backref='booking', lazy=True)
    selected_services = db.relationship(
        'BookingServiceSelection',
        backref='booking',
        lazy=True,
        cascade="all, delete-orphan"
    )
    doctor = db.relationship('Doctor', backref='bookings', lazy=True)
    reviews = db.relationship(
        'DoctorReview',
        backref='booking',
        lazy=True,
        cascade="all, delete-orphan"
    )
    status_history = db.relationship(
        'BookingStatusHistory',
        backref='booking',
        lazy=True,
        cascade="all, delete-orphan",
        order_by="BookingStatusHistory.created_at.desc()"
    )


class BookingStatusHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# -------------------- جدول الفواتير --------------------
class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='SAR')
    status = db.Column(db.String(50), default='unpaid')
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)
    details = db.Column(db.Text, nullable=True)

    payments = db.relationship('Payment', backref='invoice', lazy=True)


# -------------------- جدول الاستشارات --------------------
class Consultation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=True)
    specialization = db.Column(db.String(100))
    question = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    question_for = db.Column(db.String(50))
    gender = db.Column(db.String(10))
    age = db.Column(db.Integer)
    medical_history = db.Column(db.Text)
    status = db.Column(db.String(50), default="new")
    created_at = db.Column('date', db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    assigned_at = db.Column(db.DateTime, nullable=True)
    answered_at = db.Column(db.DateTime, nullable=True)

    phone_number = db.Column(db.String(20), nullable=False)
    contact_method = db.Column(db.String(20), nullable=False)

    responses = db.relationship(
        "ConsultationResponse",
        backref="consultation",
        lazy=True,
        order_by="ConsultationResponse.created_at"
    )

    @property
    def latest_response(self):
        if not self.responses:
            return None
        return max(self.responses, key=lambda response: response.created_at or datetime.min)


class ConsultationResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consultation_id = db.Column(db.Integer, db.ForeignKey('consultation.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# -------------------- جدول التقارير الطبية --------------------
class MedicalReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=True)
    file_path = db.Column(db.String(300), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AppointmentStatusHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    note = db.Column(db.Text)
    actor = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# -------------------- جدول المدفوعات --------------------
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    method = db.Column(db.String(50))
    transaction_id = db.Column(db.String(200), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='completed')
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)


# -------------------- جدول الإشعارات --------------------
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)
    title = db.Column(db.String(200))
    body = db.Column(db.String(500))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# -------------------- أدوار وصلاحيات الشركة --------------------
class CompanyRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    permissions = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# -------------------- جدول إجراءات الأدمن --------------------
class AdminAction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)
    action_type = db.Column(db.String(100))
    target_table = db.Column(db.String(100), nullable=True)
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
