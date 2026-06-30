import csv
from datetime import datetime
from functools import wraps
from io import StringIO

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db, login_manager
from .models import Attendance, Course, Enrollment, Student, User

main_bp = Blueprint("main", __name__)

login_manager.login_view = "main.login"


def role_required(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("main.login"))
            if current_user.role not in roles:
                flash("You do not have permission to access this page.", "error")
                return redirect(url_for("main.dashboard"))
            return func(*args, **kwargs)

        return wrapper

    return decorator


def can_manage_course(course):
    return current_user.role == "admin" or course.teacher_id == current_user.id


def build_course_report_rows(course, month_text=None):
    enrolled_students = (
        Student.query.join(Enrollment, Enrollment.student_id == Student.id)
        .filter(Enrollment.course_id == course.id)
        .order_by(Student.roll_number)
        .all()
    )

    report_rows = []
    for student in enrolled_students:
        records_query = Attendance.query.filter_by(course_id=course.id, student_id=student.id)
        if month_text:
            records_query = records_query.filter(db.func.strftime("%Y-%m", Attendance.day) == month_text)
        records = records_query.all()
        total_classes = len(records)
        presents = sum(1 for record in records if record.status == "present")
        percentage = round((presents / total_classes) * 100, 2) if total_classes else 0
        report_rows.append(
            {
                "student": student,
                "total": total_classes,
                "present": presents,
                "absent": total_classes - presents,
                "percentage": percentage,
            }
        )

    return report_rows


@main_bp.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))


@main_bp.route("/register", methods=["GET", "POST"])
@login_required
@role_required("admin")
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "teacher").strip()

        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for("main.register"))

        if role not in {"admin", "teacher"}:
            flash("Invalid role selected.", "error")
            return redirect(url_for("main.register"))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists.", "error")
            return redirect(url_for("main.register"))

        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("User created successfully.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("register.html")


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("main.dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "admin":
        courses = Course.query.order_by(Course.code).all()
    else:
        courses = Course.query.filter_by(teacher_id=current_user.id).order_by(Course.code).all()

    total_students = Student.query.count()
    total_courses = len(courses)
    total_records = Attendance.query.count()

    return render_template(
        "dashboard.html",
        courses=courses,
        total_students=total_students,
        total_courses=total_courses,
        total_records=total_records,
    )


@main_bp.route("/students", methods=["GET", "POST"])
@login_required
def students():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        roll_number = request.form.get("roll_number", "").strip()
        email = request.form.get("email", "").strip() or None

        if not full_name or not roll_number:
            flash("Student name and roll number are required.", "error")
            return redirect(url_for("main.students"))

        if Student.query.filter_by(roll_number=roll_number).first():
            flash("Roll number already exists.", "error")
            return redirect(url_for("main.students"))

        if email and Student.query.filter_by(email=email).first():
            flash("Email already exists.", "error")
            return redirect(url_for("main.students"))

        student = Student(full_name=full_name, roll_number=roll_number, email=email)
        db.session.add(student)
        db.session.commit()
        flash("Student added successfully.", "success")
        return redirect(url_for("main.students"))

    all_students = Student.query.order_by(Student.roll_number).all()
    return render_template("students.html", students=all_students)


@main_bp.route("/courses", methods=["GET", "POST"])
@login_required
def courses():
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        name = request.form.get("name", "").strip()
        teacher_id = request.form.get("teacher_id", type=int)

        if not code or not name:
            flash("Course code and name are required.", "error")
            return redirect(url_for("main.courses"))

        if Course.query.filter_by(code=code).first():
            flash("Course code already exists.", "error")
            return redirect(url_for("main.courses"))

        if current_user.role == "teacher":
            teacher_id = current_user.id
        elif not teacher_id:
            flash("Please select a teacher.", "error")
            return redirect(url_for("main.courses"))

        course = Course(code=code, name=name, teacher_id=teacher_id)
        db.session.add(course)
        db.session.commit()
        flash("Course created successfully.", "success")
        return redirect(url_for("main.courses"))

    if current_user.role == "admin":
        all_courses = Course.query.order_by(Course.code).all()
    else:
        all_courses = Course.query.filter_by(teacher_id=current_user.id).order_by(Course.code).all()
    teachers = User.query.filter_by(role="teacher").order_by(User.username).all()

    return render_template("courses.html", courses=all_courses, teachers=teachers)


@main_bp.route("/courses/<int:course_id>")
@login_required
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    if not can_manage_course(course):
        flash("You do not have access to this course.", "error")
        return redirect(url_for("main.dashboard"))

    enrolled_students = (
        Student.query.join(Enrollment, Enrollment.student_id == Student.id)
        .filter(Enrollment.course_id == course.id)
        .order_by(Student.roll_number)
        .all()
    )

    available_students = (
        Student.query.filter(~Student.id.in_([student.id for student in enrolled_students]))
        .order_by(Student.roll_number)
        .all()
    )

    recent_records = (
        Attendance.query.filter_by(course_id=course.id)
        .order_by(Attendance.day.desc())
        .limit(20)
        .all()
    )

    return render_template(
        "course_detail.html",
        course=course,
        enrolled_students=enrolled_students,
        available_students=available_students,
        recent_records=recent_records,
    )


@main_bp.route("/courses/<int:course_id>/enroll", methods=["POST"])
@login_required
def enroll_student(course_id):
    course = Course.query.get_or_404(course_id)
    if not can_manage_course(course):
        flash("You do not have access to this course.", "error")
        return redirect(url_for("main.dashboard"))

    student_id = request.form.get("student_id", type=int)
    student = Student.query.get(student_id) if student_id else None
    if not student:
        flash("Invalid student selected.", "error")
        return redirect(url_for("main.course_detail", course_id=course.id))

    existing = Enrollment.query.filter_by(course_id=course.id, student_id=student.id).first()
    if existing:
        flash("Student is already enrolled in this course.", "error")
        return redirect(url_for("main.course_detail", course_id=course.id))

    enrollment = Enrollment(course_id=course.id, student_id=student.id)
    db.session.add(enrollment)
    db.session.commit()
    flash("Student enrolled successfully.", "success")
    return redirect(url_for("main.course_detail", course_id=course.id))


@main_bp.route("/courses/<int:course_id>/attendance", methods=["GET", "POST"])
@login_required
def mark_attendance(course_id):
    course = Course.query.get_or_404(course_id)
    if not can_manage_course(course):
        flash("You do not have access to this course.", "error")
        return redirect(url_for("main.dashboard"))

    enrolled_students = (
        Student.query.join(Enrollment, Enrollment.student_id == Student.id)
        .filter(Enrollment.course_id == course.id)
        .order_by(Student.roll_number)
        .all()
    )

    if request.method == "POST":
        day_text = request.form.get("day", "").strip()
        try:
            attendance_day = datetime.strptime(day_text, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date.", "error")
            return redirect(url_for("main.mark_attendance", course_id=course.id))

        for student in enrolled_students:
            status = "present" if request.form.get(f"student_{student.id}") == "on" else "absent"
            record = Attendance.query.filter_by(
                course_id=course.id,
                student_id=student.id,
                day=attendance_day,
            ).first()
            if record:
                record.status = status
                record.marked_by = current_user.id
            else:
                record = Attendance(
                    course_id=course.id,
                    student_id=student.id,
                    day=attendance_day,
                    status=status,
                    marked_by=current_user.id,
                )
                db.session.add(record)

        db.session.commit()
        flash("Attendance saved successfully.", "success")
        return redirect(url_for("main.course_detail", course_id=course.id))

    return render_template("mark_attendance.html", course=course, students=enrolled_students)


@main_bp.route("/courses/<int:course_id>/report")
@login_required
def course_report(course_id):
    course = Course.query.get_or_404(course_id)
    if not can_manage_course(course):
        flash("You do not have access to this course.", "error")
        return redirect(url_for("main.dashboard"))

    report_rows = build_course_report_rows(course)

    return render_template("report.html", course=course, rows=report_rows)


@main_bp.route("/courses/<int:course_id>/report.csv")
@login_required
def course_report_csv(course_id):
    course = Course.query.get_or_404(course_id)
    if not can_manage_course(course):
        flash("You do not have access to this course.", "error")
        return redirect(url_for("main.dashboard"))

    rows = build_course_report_rows(course)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Roll Number", "Name", "Total Classes", "Present", "Absent", "Percentage"])
    for row in rows:
        writer.writerow(
            [
                row["student"].roll_number,
                row["student"].full_name,
                row["total"],
                row["present"],
                row["absent"],
                f"{row['percentage']}%",
            ]
        )

    filename = f"{course.code}_attendance_report.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@main_bp.route("/monthly-summary", methods=["GET"])
@login_required
def monthly_summary():
    selected_month = request.args.get("month", "").strip()
    if not selected_month:
        selected_month = datetime.today().strftime("%Y-%m")

    try:
        datetime.strptime(selected_month, "%Y-%m")
    except ValueError:
        flash("Invalid month format.", "error")
        return redirect(url_for("main.monthly_summary"))

    if current_user.role == "admin":
        courses = Course.query.order_by(Course.code).all()
    else:
        courses = Course.query.filter_by(teacher_id=current_user.id).order_by(Course.code).all()

    course_summaries = []
    for course in courses:
        rows = build_course_report_rows(course, selected_month)
        course_summaries.append({"course": course, "rows": rows})

    return render_template(
        "monthly_summary.html",
        selected_month=selected_month,
        course_summaries=course_summaries,
    )
