from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

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
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)

# جدول الـ Admin
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
