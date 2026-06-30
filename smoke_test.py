from datetime import date

from attendance_app import create_app
from attendance_app.extensions import db
from attendance_app.models import Attendance, Course, Enrollment, Student, User


def seed_minimum_data():
    admin = User.query.filter_by(username="admin").first()
    if admin is None:
        admin = User(username="admin", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()

    course = Course.query.filter_by(code="CS101").first()
    if course is None:
        course = Course(code="CS101", name="Intro to CS", teacher_id=admin.id)
        db.session.add(course)
        db.session.commit()

    student = Student.query.filter_by(roll_number="R001").first()
    if student is None:
        student = Student(roll_number="R001", full_name="Test Student", email="r001@example.com")
        db.session.add(student)
        db.session.commit()

    enrollment = Enrollment.query.filter_by(course_id=course.id, student_id=student.id).first()
    if enrollment is None:
        db.session.add(Enrollment(course_id=course.id, student_id=student.id))
        db.session.commit()

    record = Attendance.query.filter_by(course_id=course.id, student_id=student.id, day=date(2026, 4, 1)).first()
    if record is None:
        db.session.add(
            Attendance(
                course_id=course.id,
                student_id=student.id,
                day=date(2026, 4, 1),
                status="present",
                marked_by=admin.id,
            )
        )
        db.session.commit()

    return course.id


def main():
    app = create_app()
    with app.app_context():
        course_id = seed_minimum_data()

    client = app.test_client()

    response = client.get("/login")
    print("GET /login:", response.status_code)

    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    print("POST /login:", response.status_code, response.headers.get("Location"))

    with client:
        client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)

        response = client.get("/dashboard")
        print("GET /dashboard:", response.status_code)

        response = client.get("/monthly-summary?month=2026-04")
        print("GET /monthly-summary:", response.status_code)

        response = client.get(f"/courses/{course_id}/report")
        print("GET /courses/<id>/report:", response.status_code)

        response = client.get(f"/courses/{course_id}/report.csv")
        print(
            "GET /courses/<id>/report.csv:",
            response.status_code,
            response.headers.get("Content-Type"),
            response.headers.get("Content-Disposition"),
        )


if __name__ == "__main__":
    main()
