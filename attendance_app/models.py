from datetime import date

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="teacher")

    courses = db.relationship("Course", backref="teacher", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    enrollments = db.relationship("Enrollment", backref="course", cascade="all, delete-orphan")
    attendance_records = db.relationship("Attendance", backref="course", cascade="all, delete-orphan")


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(30), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)

    enrollments = db.relationship("Enrollment", backref="student", cascade="all, delete-orphan")
    attendance_records = db.relationship("Attendance", backref="student", cascade="all, delete-orphan")


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)

    __table_args__ = (db.UniqueConstraint("course_id", "student_id", name="unique_course_student"),)


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    day = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(10), nullable=False, default="absent")
    marked_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    __table_args__ = (db.UniqueConstraint("course_id", "student_id", "day", name="unique_attendance_record"),)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
