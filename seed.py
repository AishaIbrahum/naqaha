from app import app, db
from models import User, Company, Admin, Doctor, Package, Booking, Consultation, Invoice, Payment, MedicalReport, Notification, AdminAction
from werkzeug.security import generate_password_hash
from datetime import datetime

with app.app_context():

    # -------------------- مستخدم --------------------
    user = User.query.filter_by(username="testuser22").first()
    if not user:
        user = User(
            username="testuser22",
            email="user2@test.com",
            password=generate_password_hash("123456"),
            first_name="Hanin",
            last_name="Bin Bishar",
            phone="0500000000",
            gender="female",
            country="Saudi Arabia",
            city="Riyadh",
            address="Street 123",
            birth_date=datetime(2000, 1, 1).date(),
            profile_picture="default.jpg"
        )
        db.session.add(user)
        db.session.commit()

    # -------------------- شركة --------------------
    company = Company.query.filter_by(name="Test Company").first()
    if not company:
        company = Company(
            name="Test Company",
            email="company@test.com",
            password=generate_password_hash("123456")
        )
        db.session.add(company)
        db.session.commit()

    # -------------------- أدمن --------------------
    admin = Admin.query.filter_by(username="admin").first()
    if not admin:
        admin = Admin(
            username="admin",
            password=generate_password_hash("123456")
        )
        db.session.add(admin)
        db.session.commit()

    # -------------------- طبيب --------------------
    doctor = Doctor.query.filter_by(email="doctor@test.com").first()
    if not doctor:
        doctor = Doctor(
            name="د. أحمد العتيبي",
            specialty="طب عام",
            email="doctor@test.com",
            password=generate_password_hash("doctor123"),
            status="available",
            company_id=company.id if company else None
        )
        db.session.add(doctor)
        db.session.commit()

    # -------------------- باقة --------------------
    package = Package.query.filter_by(title="باقة تجريبية").first()
    if not package:
        package = Package(
            title="باقة تجريبية",
            description="باقة للاختبار فقط",
            image="default_package.jpg",
            provider_id=company.id
        )
        db.session.add(package)
        db.session.commit()

    # -------------------- حجز --------------------
    booking = Booking.query.filter_by(user_id=user.id, package_id=package.id).first()
    if not booking:
        booking = Booking(
            user_id=user.id,
            package_id=package.id,
            company_id=company.id,
            scheduled_for=datetime.utcnow(),
            notes="حجز تجريبي",
            status="pending"
        )
        db.session.add(booking)
        db.session.commit()

    # -------------------- استشارة --------------------
    consultation = Consultation.query.filter_by(user_id=user.id, doctor_id=None).first()
    if not consultation:
        consultation = Consultation(
            user_id=user.id,
            doctor_id=None,
            specialization="طب عام",
            question="استشارة تجريبية",
            description="هذه استشارة تجريبية تم إنشاؤها بواسطة seed script",
            question_for="نفسي",
            gender=user.gender,
            age=25,
            medical_history="لا يوجد",
            phone_number=user.phone,
            contact_method="WhatsApp",
            status="new"
        )
        db.session.add(consultation)
        db.session.commit()

    # -------------------- فاتورة --------------------
    invoice = Invoice.query.filter_by(user_id=user.id, booking_id=booking.id).first()
    if not invoice:
        invoice = Invoice(
            user_id=user.id,
            booking_id=booking.id,
            amount=100,
            status="unpaid",
            issued_at=datetime.utcnow()
        )
        db.session.add(invoice)
        db.session.commit()

    # -------------------- دفع --------------------
    payment = Payment.query.filter_by(invoice_id=invoice.id).first()
    if not payment:
        payment = Payment(
            invoice_id=invoice.id,
            amount=100,
            method="card",
            status="completed",
            paid_at=datetime.utcnow()
        )
        invoice.status = "paid"
        db.session.add(payment)
        db.session.commit()

    # -------------------- تقرير طبي --------------------
    report = MedicalReport.query.filter_by(user_id=user.id, booking_id=booking.id).first()
    if not report:
        report = MedicalReport(
            user_id=user.id,
            booking_id=booking.id,
            file_path="report1.pdf",
            notes="تقرير تجريبي",
            created_at=datetime.utcnow()
        )
        db.session.add(report)
        db.session.commit()

    # -------------------- إشعارات --------------------
    notif_user = Notification.query.filter_by(user_id=user.id).first()
    if not notif_user:
        notif_user = Notification(
            user_id=user.id,
            body="إشعار تجريبي للمستخدم",
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.session.add(notif_user)

    notif_company = Notification.query.filter_by(company_id=company.id).first()
    if not notif_company:
        notif_company = Notification(
            company_id=company.id,
            body="إشعار تجريبي للشركة",
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.session.add(notif_company)

    db.session.commit()

    # -------------------- سجل الأدمن --------------------
    admin_action = AdminAction.query.filter_by(admin_id=admin.id).first()
    if not admin_action:
        admin_action = AdminAction(
            admin_id=admin.id,
            action_type="إضافة باقة تجريبية",
            target_table="package",
            target_id=package.id,
            details="تم إضافة باقة تجريبية بواسطة seed script",
            created_at=datetime.utcnow()
        )
        db.session.add(admin_action)
        db.session.commit()

    print("تم إضافة البيانات التجريبية بنجاح!")
