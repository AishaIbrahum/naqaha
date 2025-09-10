from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


db = SQLAlchemy()

# جدول المستخدمين (الأفراد)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # البيانات الأساسية
    username = db.Column(db.String(80), nullable=False, unique=True)   # اسم المستخدم
    email = db.Column(db.String(120), nullable=False, unique=True)     # البريد
    password = db.Column(db.String(200), nullable=False)               # كلمة المرور

    # بيانات إضافية
    first_name = db.Column(db.String(50), nullable=False)              # الاسم الأول
    last_name = db.Column(db.String(50), nullable=False)               # الاسم الأخير
    phone = db.Column(db.String(20), nullable=False, unique=True)      # رقم الجوال (مطلوب ومميز)

    gender = db.Column(db.String(10), nullable=True)                   # الجنس (اختياري: ذكر/أنثى/غير ذلك)
    country = db.Column(db.String(100), nullable=True)                 # البلد (اختياري)
    city = db.Column(db.String(100), nullable=True)                    # المدينة (اختياري)
    address = db.Column(db.String(200), nullable=True)                 # العنوان التفصيلي (اختياري)

    birth_date = db.Column(db.Date, nullable=True)                     # تاريخ الميلاد (اليوم/الشهر/السنة)


# جدول الشركات
class Company(db.Model):
    __tablename__ = 'company'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))

    appointments = db.relationship("Appointment", backref="company", lazy=True)


# جدول الـ Admin
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)

class Package(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    image = db.Column(db.String(200))

#profile_picture = db.Column(db.String(200), default="default.jpg") عشان تشتغل صح لازم يكون جزء من جدول، غالبًا User.


class Appointment(db.Model):
    __tablename__ = 'Appointment'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    doctor = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=False)


class DoctorMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    doctor_name = db.Column(db.String(100))
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime)


class PaymentPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    plan_name = db.Column(db.String(100))
    amount = db.Column(db.Float)
    status = db.Column(db.String(50))  # مدفوع / غير مدفوع


class HealthCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    card_number = db.Column(db.String(50))
    issued_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)


