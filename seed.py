from app import app, db
from models import (
    User,
    Company,
    Admin,
    Doctor,
    Package,
    PackageService,
    Booking,
    BookingServiceSelection,
    BookingStatusHistory,
    Appointment,
    Consultation,
    Invoice,
    Payment,
    MedicalReport,
    Notification,
    AdminAction,
)
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
            provider_id=company.id,
            status="approved",
            approved_by=admin.id if admin else None,
            status_updated_at=datetime.utcnow()
        )
        db.session.add(package)
        db.session.commit()
    else:
        if package.status != "approved":
            package.status = "approved"
            package.approved_by = admin.id if admin else package.approved_by
            package.status_updated_at = datetime.utcnow()
            db.session.commit()

    if not package.services:
        services_seed = [
            ("جلسة استشارة طبية", "استشارة مع طبيب مختص لتقييم الحالة", 150.0),
            ("فحص مخبري", "مجموعة تحاليل أساسية", 200.0),
            ("خطة علاجية", "خطة علاج تفصيلية ومتابعة أسبوعية", 120.0)
        ]
        for name, desc, price in services_seed:
            service = PackageService(
                package_id=package.id,
                service_name=name,
                service_description=desc,
                service_price=price
            )
            db.session.add(service)
        db.session.commit()

    # -------------------- موعد وحجز --------------------
    booking = Booking.query.filter_by(user_id=user.id, package_id=package.id).first()
    if not booking:
        appointment = Appointment(
            user_id=user.id,
            company_id=company.id,
            date=datetime.utcnow(),
            notes="موعد تجريبي",
        )
        db.session.add(appointment)
        db.session.flush()

        booking = Booking(
            user_id=user.id,
            package_id=package.id,
            appointment_id=appointment.id,
            company_id=company.id,
            scheduled_for=appointment.date,
            notes="حجز باقة تجريبية",
            status="pending"
        )
        db.session.add(booking)
        db.session.flush()

        for service in package.services[:2]:
            selection = BookingServiceSelection(
                booking_id=booking.id,
                package_service_id=service.id,
                service_name=service.service_name,
                service_description=service.service_description,
                service_price=service.service_price
            )
            db.session.add(selection)

        db.session.add(BookingStatusHistory(
            booking_id=booking.id,
            status='pending',
            note='تم إنشاء طلب الحجز (بيانات تجريبية)'
        ))

        invoice = Invoice(
            user_id=user.id,
            booking_id=booking.id,
            amount=sum([(service.service_price or 0) for service in package.services[:2]]),
            status='paid',
            paid_at=datetime.utcnow()
        )
        db.session.add(invoice)

        payment = Payment(
            invoice_id=invoice.id,
            amount=invoice.amount,
            method='card',
            status='completed',
            paid_at=datetime.utcnow()
        )
        db.session.add(payment)

        booking.status = 'completed'
        db.session.add(BookingStatusHistory(
            booking_id=booking.id,
            status='completed',
            note='تم الدفع في البيانات التجريبية'
        ))

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
