import csv
import datetime
import json
import logging
import os
from app.student import StudentUser
from app.teacher import TeacherUser, Course


class ScheduleManager:
    """The main controller for all business logic and data handling."""

    # Student IDs are 8-digit numbers, starting at 10000000 and counting up by one.
    STUDENT_ID_MIN = 10_000_000
    STUDENT_ID_MAX = 99_999_999

    def __init__(self, data_path="data/msms.json"):
        self.data_path = data_path
        self.students = []
        self.teachers = []
        self.courses = []
        self.attendance_log = []
        self.finance_log = []
        self._load_data()
        # Repair any one-sided student <-> course links left in the JSON file.
        self._reconcile_enrolments()
        # Next student ID = highest existing ID + 1 (10000000 if there are no students yet).
        self.next_student_id = (
            max((s.id for s in self.students), default=self.STUDENT_ID_MIN - 1) + 1
        )
        self.next_teacher_id = max((t.id for t in self.teachers), default=0) + 1
        self.next_course_id = max((c.id for c in self.courses), default=0) + 1
        self.next_lesson_id = (
            max(
                (lesson["lesson_id"] for c in self.courses for lesson in c.lessons),
                default=0,
            )
            + 1
        )

    def _load_data(self):
        """Loads data from the JSON file and populates the object lists."""
        try:
            with open(self.data_path, "r") as f:
                data = json.load(f)
                self.students = []
                for s in data.get("students", []):
                    student = StudentUser(s["id"], s["name"])
                    student.enrolled_course_ids = s.get("enrolled_course_ids", [])
                    self.students.append(student)

                self.teachers = []
                for t in data.get("teachers", []):
                    teacher = TeacherUser(t["id"], t["name"], t.get("speciality", ""))
                    self.teachers.append(teacher)

                self.courses = []
                for c in data.get("courses", []):
                    course = Course(
                        c["id"], c["name"], c["instrument"], c["teacher_id"]
                    )
                    course.enrolled_student_ids = c.get("enrolled_student_ids", [])
                    course.lessons = c.get("lessons", [])
                    self.courses.append(course)

                # Use .get() with a default empty list to prevent errors if the key doesn't exist.
                self.attendance_log = data.get("attendance", [])
                self.finance_log = data.get("finance", [])

        except FileNotFoundError:
            print("Data file not found. Starting with a clean state.")

    def _save_data(self):
        """Converts object lists back to dictionaries and saves to JSON."""
        data_to_save = {
            "students": [s.__dict__ for s in self.students],
            "teachers": [t.__dict__ for t in self.teachers],
            "courses": [c.__dict__ for c in self.courses],
            # Since it's already a list of dicts, no conversion is needed.
            "attendance": self.attendance_log,
            "finance": self.finance_log,
            "next_student_id": self.next_student_id,
            "next_teacher_id": self.next_teacher_id,
            "next_course_id": self.next_course_id,
            "next_lesson_id": self.next_lesson_id,
        }
        with open(self.data_path, "w") as f:
            json.dump(data_to_save, f, indent=4)

    @staticmethod
    def is_valid_student_id(student_id):
        """Returns True if student_id is an 8-digit integer (e.g. 12345678)."""
        # bool is a subclass of int, so exclude it explicitly.
        if isinstance(student_id, bool) or not isinstance(student_id, int):
            return False
        return (
            ScheduleManager.STUDENT_ID_MIN
            <= student_id
            <= ScheduleManager.STUDENT_ID_MAX
        )

    def _reconcile_enrolments(self):
        """Makes student and course enrolment lists consistent with each other.

        Enrolment is stored on both sides (student.enrolled_course_ids and
        course.enrolled_student_ids). If the JSON file only has one side of a
        link, the missing side is added; links to students/courses that no
        longer exist are dropped.
        """
        student_ids = {s.id for s in self.students}
        course_ids = {c.id for c in self.courses}

        # Drop dangling references and duplicates on both sides.
        for student in self.students:
            student.enrolled_course_ids = list(
                dict.fromkeys(cid for cid in student.enrolled_course_ids if cid in course_ids)
            )
        for course in self.courses:
            course.enrolled_student_ids = list(
                dict.fromkeys(sid for sid in course.enrolled_student_ids if sid in student_ids)
            )

        # Fill in the missing side of any one-sided link.
        for student in self.students:
            for cid in student.enrolled_course_ids:
                course = self.find_course_by_id(cid)
                if student.id not in course.enrolled_student_ids:
                    course.enrolled_student_ids.append(student.id)
        for course in self.courses:
            for sid in course.enrolled_student_ids:
                student = self.find_student_by_id(sid)
                if course.id not in student.enrolled_course_ids:
                    student.enrolled_course_ids.append(course.id)

    def check_in(self, student_id, course_id):
        """Records a student's attendance for a course after validation."""
        student = self.find_student_by_id(student_id)
        course = self.find_course_by_id(course_id)

        if not student or not course:
            print("Error: Check-in failed. Invalid Student or Course ID.")
            logging.warning(f"Check-in failed: invalid student ID {student_id} or course ID {course_id}.")
            return False

        # A student can only check in to a course they are actually enrolled in.
        if course_id not in student.enrolled_course_ids:
            print(f"Error: Check-in failed. {student.name} is not enrolled in {course.name}.")
            logging.warning(f"Check-in rejected: student ID {student_id} is not enrolled in course ID {course_id}.")
            return False

        timestamp = datetime.datetime.now().isoformat()
        check_in_record = {
            "student_id": student_id,
            "course_id": course_id,
            "timestamp": timestamp,
        }

        # This line will now work without causing an AttributeError.
        self.attendance_log.append(check_in_record)
        self._save_data()  # This will now correctly save the attendance log.
        print(f"Success: Student {student.name} checked into {course.name}.")
        logging.info(f"Student ID {student_id} checked into course ID {course_id}.")
        return True

    @staticmethod
    def is_valid_name(name):
        """Checks if a name is valid."""
        return (
            bool(name.strip())
            and 2 <= len(name) <= 50
            # Remove the allowed punctuation, then each word must be letters only.
            and all(
                part.replace("-", "").replace("'", "").replace(".", "").isalpha()
                for part in name.split()
            )
        )

    def find_student_by_id(self, student_id):
        """Helper method to find a student by their ID."""
        for student in self.students:
            if student.id == student_id:
                return student
        return None

    def find_teacher_by_id(self, teacher_id):
        """Helper method to find a teacher by their ID."""
        for teacher in self.teachers:
            if teacher.id == teacher_id:
                return teacher
        return None

    def find_course_by_id(self, course_id):
        """Helper method to find a course by its ID."""
        for course in self.courses:
            if course.id == course_id:
                return course
        return None

    def add_lesson(self, course_id, day, start_time, room):
        """Adds a lesson to a specific course."""
        course = self.find_course_by_id(course_id)
        if not course:
            print("Error: Invalid Course ID.")
            return

        lesson = {
            "lesson_id": self.next_lesson_id,
            "day": day,
            "start_time": start_time,
            "room": room,
        }

        course.lessons.append(lesson)
        self.next_lesson_id += 1
        self._save_data()
        print(
            f"Success: Added a session to {course.name} on {day} at {start_time} in {room}."
        )
        logging.info(f"Lesson ID {lesson['lesson_id']} added to course ID {course_id} on {day} at {start_time} in {room}.")
        return lesson

    def get_lessons_for_day(self, day):
        """Returns a list of lessons scheduled for a specific day."""
        lessons = []
        for course in self.courses:
            for lesson in course.lessons:
                if lesson.get("day").lower() == day.lower():
                    lessons.append((course, lesson))
        return lessons

    def cancel_lesson(self, lesson_id, reason):
        """Cancels (removes) a scheduled lesson from its course."""
        # Search every course for the lesson with this ID.
        for course in self.courses:
            for lesson in course.lessons:
                if lesson["lesson_id"] == lesson_id:
                    course.lessons.remove(lesson)
                    self._save_data()
                    print(f"Lesson {lesson_id} of {course.name} cancelled. Reason: {reason}")
                    # Add a log entry.
                    logging.warning(f"Lesson ID {lesson_id} was cancelled. Reason: {reason}")
                    return True

        print(f"Error: Lesson {lesson_id} not found.")
        logging.warning(f"Cancel failed: lesson ID {lesson_id} not found.")
        return False

    def register_new_student(self, name, course_id):
        """Registers a new student and enrols them in their first course.

        Registration is tied to a specific course (rather than just an
        instrument) so every new student is immediately linked on both sides.
        Returns the new StudentUser, or None if validation fails.
        """
        if not self.is_valid_name(name):
            print("Registration failed. Invalid student name.")
            logging.warning(f"Registration failed: invalid student name {name!r}.")
            return None

        course = self.find_course_by_id(course_id)
        if not course:
            print("Registration failed. Invalid course ID.")
            logging.warning(f"Registration failed: invalid course ID {course_id}.")
            return None

        student = StudentUser(self.next_student_id, name.strip())
        self.students.append(student)
        self.next_student_id += 1
        # Reuse enrol_student so both enrolment lists are updated and saved.
        self.enrol_student(student.id, course_id)
        print(
            f"Successfully registered {student.name} (ID: {student.id}) "
            f"and enrolled them in {course.name}."
        )
        logging.info(f"New student {student.name} registered with ID {student.id} in course ID {course_id}.")
        return student

    def enrol_student(self, student_id, course_id):
        """Enrols an existing student in a course."""
        student = self.find_student_by_id(student_id)
        course = self.find_course_by_id(course_id)

        # Check if the student and course exist
        if not student or not course:
            print("Enrolment failed. Invalid student or course ID.")
            return False

        # Check if the student is already enrolled in the course
        if course_id in student.enrolled_course_ids:
            print(f"{student.name} is already enrolled in {course.name}.")
            return False

        student.enrolled_course_ids.append(course_id)
        # Guard the course side too, in case it already lists the student.
        if student_id not in course.enrolled_student_ids:
            course.enrolled_student_ids.append(student_id)
        self._save_data()
        print(f"Enrolled student {student.name} in {course.name}.")
        logging.info(f"Student ID {student_id} enrolled in course ID {course_id}.")
        return True

    def unenrol_student(self, student_id, course_id):
        """Unenrols a student from a course."""
        student = self.find_student_by_id(student_id)
        course = self.find_course_by_id(course_id)

        if not student or not course:
            print("Unenrolment failed. Invalid student or course ID.")
            return False

        if course_id in student.enrolled_course_ids:
            student.enrolled_course_ids.remove(course_id)
        if student_id in course.enrolled_student_ids:
            course.enrolled_student_ids.remove(student_id)

        self._save_data()
        print(f"Unenrolled student {student.name} from {course.name}.")
        logging.info(f"Student ID {student_id} unenrolled from course ID {course_id}.")
        return True

    def switch_student_course(self, student_id, from_course_id, to_course_id):
        """Switches a student from one course to another."""
        student = self.find_student_by_id(student_id)
        from_course = self.find_course_by_id(from_course_id)
        to_course = self.find_course_by_id(to_course_id)

        # Validate everything BEFORE changing any data, so a failed switch
        # never leaves the student half-moved between courses.
        if not student or not from_course or not to_course:
            print("Switch failed. Invalid student or course ID.")
            return False

        if from_course_id == to_course_id:
            print("Switch failed. The two courses are the same.")
            return False

        # Check if the student is enrolled in the current course
        if from_course_id not in student.enrolled_course_ids:
            print(f"{student.name} is not enrolled in {from_course.name}.")
            return False

        # Check if the student is already enrolled in the new course
        if to_course_id in student.enrolled_course_ids:
            print(f"{student.name} is already enrolled in {to_course.name}.")
            return False

        # Remove from the old course. The course-side list may be out of sync
        # with the student-side list, so only remove if the ID is present.
        student.enrolled_course_ids.remove(from_course_id)
        if student_id in from_course.enrolled_student_ids:
            from_course.enrolled_student_ids.remove(student_id)

        # Add to the new course without creating duplicates.
        student.enrolled_course_ids.append(to_course_id)
        if student_id not in to_course.enrolled_student_ids:
            to_course.enrolled_student_ids.append(student_id)

        self._save_data()
        print(f"Switched {student.name} from {from_course.name} to {to_course.name}.")
        logging.info(f"Student ID {student_id} switched from course ID {from_course_id} to course ID {to_course_id}.")
        return True

    def add_teacher(self, name, speciality):
        """Adds a new teacher to the system."""
        if not self.is_valid_name(name):
            print("Error: Invalid teacher name.")
            return None

        teacher = TeacherUser(self.next_teacher_id, name, speciality)
        self.teachers.append(teacher)
        self.next_teacher_id += 1
        self._save_data()
        print(f"Successfully added teacher '{name}' who specializes in {speciality}.")
        logging.info(f"Teacher {name} added with ID {teacher.id}.")

    def create_course(self, name, instrument, teacher_id):
        """Adds a new course to the system."""
        teacher = self.find_teacher_by_id(teacher_id)
        if not teacher:
            print("Error: Invalid teacher ID.")
            return

        course = Course(self.next_course_id, name, instrument, teacher_id)
        self.courses.append(course)
        self.next_course_id += 1
        self._save_data()
        print(
            f"Successfully added course '{name}' for instrument '{instrument}' taught by {teacher.name}."
        )
        logging.info(f"Course {name} added with ID {course.id}, taught by teacher ID {teacher_id}.")
        return course

    def list_students(self):
        """Prints a list of all students."""
        print("\n--- Student List ---")
        if not self.students:
            print("No students found.")
            return
        for student in self.students:
            print(
                f"ID: {student.id}, Name: {student.name}, Enrolled in: {', '.join(course.name for course in self.courses if course.id in student.enrolled_course_ids)}"
            )

    def list_teachers(self):
        """Prints a list of all teachers."""
        print("\n--- Teacher List ---")
        if not self.teachers:
            print("No teachers found.")
            return
        for teacher in self.teachers:
            print(
                f"ID: {teacher.id}, Name: {teacher.name}, Speciality: {teacher.speciality}"
            )

    def list_courses(self):
        """Prints a list of all courses."""
        print("\n--- Course List ---")
        if not self.courses:
            print("No courses found.")
            return
        for course in self.courses:
            teacher = self.find_teacher_by_id(course.teacher_id)
            teacher_name = teacher.name if teacher else "Unknown"
            print(f"ID: {course.id}, Name: {course.name}, taught by {teacher_name}")

    def print_student_card(self, student_id):
        """Creates a text file badge for a student."""
        student_to_print = None
        for s in self.students:
            if s.id == student_id:
                student_to_print = s
                break

        if not student_to_print:
            print(f"Error: Couldn't print card, student {student_id} not found.")
            return

        # Create a text file for the student card
        filename = f"{student_id}_card.txt"

        with open(filename, "w") as f:
            # Write the student's details to the file in a nice format
            f.write("========================\n")
            f.write(f"  MUSIC SCHOOL ID BADGE\n")
            f.write("========================\n")
            f.write(f"ID: {student_to_print.id}\n")
            f.write(f"Name: {student_to_print.name}\n")
            enrolled_courses = [
                course.name
                for course in self.courses
                if course.id in student_to_print.enrolled_course_ids
            ]
            f.write(
                f"Enrolled In: {', '.join(enrolled_courses) if enrolled_courses else 'None'}\n"
            )

        print(f"Printed student card to {filename}.")

    def remove_student(self, student_id):
        """Removes a student and their enrolments."""
        # Clean up enrolments in courses
        for course in self.courses:
            if student_id in course.enrolled_student_ids:
                course.enrolled_student_ids.remove(student_id)

        # Remove the student from the student list
        self.students = [s for s in self.students if s.id != student_id]
        self._save_data()
        print(f"Student {student_id} removed.")
        logging.info(f"Student ID {student_id} removed.")
        return True

    def remove_teacher(self, teacher_id):
        """Removes a teacher."""
        for course in self.courses:
            if course.teacher_id == teacher_id:
                course.teacher_id = None

        self.teachers = [t for t in self.teachers if t.id != teacher_id]

        self._save_data()
        print(f"Teacher {teacher_id} removed.")
        logging.info(f"Teacher ID {teacher_id} removed.")

    def record_payment(self, student_id, amount, method):
        """Adds a payment record to the finance log."""
        # Find the student to ensure they exist.
        student = self.find_student_by_id(student_id)
        if not student:
            print(f"Error: Payment failed. Student {student_id} not found.")
            logging.warning(f"Payment rejected: student ID {student_id} not found.")
            return None

        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
            print("Error: Payment failed. Amount must be greater than 0.")
            logging.warning(f"Payment rejected: invalid amount {amount!r} for student ID {student_id}.")
            return None

        if not method or not method.strip():
            print("Error: Payment failed. Payment method cannot be empty.")
            logging.warning(f"Payment rejected: empty payment method for student ID {student_id}.")
            return None

        # Create a payment dictionary with student_id, amount, method, and a timestamp.
        payment_record = {
            "student_id": student_id,
            "amount": amount,
            "method": method.strip(),
            "timestamp": datetime.datetime.now().isoformat(),
        }

        # Append the record to self.finance_log and save the data.
        self.finance_log.append(payment_record)
        self._save_data()
        print(f"Payment of {amount} for student {student_id} recorded.")
        # Add a log entry after a successful operation.
        logging.info(f"Payment of {amount} recorded for student ID {student_id}.")
        return payment_record

    def get_payment_history(self, student_id):
        """Returns a list of all payments for a given student."""
        return [p for p in self.finance_log if p["student_id"] == student_id]

    def export_report(self, kind, out_path):
        """Exports a log to a CSV file."""
        print(f"Exporting {kind} report to {out_path}...")
        # Select the correct data list and CSV columns based on 'kind'.
        if kind == "finance":
            data_to_export = self.finance_log
            headers = ["student_id", "amount", "method", "timestamp"]
        elif kind == "attendance":
            data_to_export = self.attendance_log
            headers = ["student_id", "course_id", "timestamp"]
        else:
            print("Error: Unknown report type.")
            logging.warning(f"Report export failed: unknown report type {kind!r}.")
            return False

        try:
            # Create the output folder first if it doesn't exist yet.
            folder = os.path.dirname(out_path)
            if folder:
                os.makedirs(folder, exist_ok=True)

            # Write the header row, then one row per record.
            with open(out_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(data_to_export)
        except OSError as e:
            print(f"Error: Could not write report to {out_path}. {e}")
            logging.error(f"Report export failed: could not write {out_path}. {e}")
            return False

        print(f"Exported {len(data_to_export)} {kind} records to {out_path}.")
        logging.info(f"Exported {len(data_to_export)} {kind} records to {out_path}.")
        return True
