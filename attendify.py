"""
Attendify - Attendance Management System
Course: Computational Thinking and Programming (2026CSAE100)

A menu-driven command-line program that stores students and date-wise
attendance in CSV files, calculates attendance percentages, and gives
analysis: low-attendance alerts, "classes needed / can skip" predictions,
class ranking, a text bar chart and an exportable report.

Only the Python standard library is used (csv, datetime, os, math).
"""

import csv
import math
import os
from datetime import date, datetime

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
STUDENTS_FILE = "students.csv"      # columns: roll, name
ATTENDANCE_FILE = "attendance.csv"  # columns: date, roll, status
REPORT_FILE = "attendance_report.txt"
REQUIRED_PERCENT = 75.0             # minimum attendance required
DATE_FORMAT = "%Y-%m-%d"


def path_of(filename):
    """Full path of a data file."""
    return os.path.join(DATA_DIR, filename)


# ----------------------------------------------------------------------
# Data structures used
#   students   : dict  {roll_no: name}
#   attendance : dict  {date_string: {roll_no: "P" or "A"}}
# ----------------------------------------------------------------------

# ---------------------------- File handling ---------------------------
def load_students():
    """Read students.csv into a dictionary. Missing file -> empty dict."""
    students = {}
    if not os.path.exists(path_of(STUDENTS_FILE)):
        return students
    with open(path_of(STUDENTS_FILE), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            students[row["roll"]] = row["name"]
    return students


def save_students(students):
    with open(path_of(STUDENTS_FILE), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["roll", "name"])
        for roll in sorted(students):
            writer.writerow([roll, students[roll]])


def load_attendance():
    """Read attendance.csv into {date: {roll: status}}."""
    attendance = {}
    if not os.path.exists(path_of(ATTENDANCE_FILE)):
        return attendance
    with open(path_of(ATTENDANCE_FILE), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            attendance.setdefault(row["date"], {})[row["roll"]] = row["status"]
    return attendance


def save_attendance(attendance):
    with open(path_of(ATTENDANCE_FILE), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "roll", "status"])
        for day in sorted(attendance):
            for roll in sorted(attendance[day]):
                writer.writerow([day, roll, attendance[day][roll]])


# ---------------------------- Input validation ------------------------
def read_text(prompt):
    return input(prompt).strip()


def pause():
    """Wait for Enter so the output stays visible before the menu returns."""
    input("\nPress Enter to return to the menu...")


def read_choice(prompt, valid):
    """Keep asking until the user enters one of the valid options."""
    while True:
        value = read_text(prompt).lower()
        if value in valid:
            return value
        print(f"  Invalid input. Please enter one of: {', '.join(valid)}")


def read_date(prompt):
    """Read a date as YYYY-MM-DD. Blank input means today. No future dates."""
    while True:
        value = read_text(prompt)
        if value == "":
            return date.today().strftime(DATE_FORMAT)
        try:
            parsed = datetime.strptime(value, DATE_FORMAT).date()
        except ValueError:
            print("  Invalid date. Use the format YYYY-MM-DD (e.g. 2026-11-25).")
            continue
        if parsed > date.today():
            print("  Attendance cannot be marked for a future date.")
            continue
        return parsed.strftime(DATE_FORMAT)


def is_valid_name(name):
    """Names may contain letters, spaces, dots and hyphens only."""
    cleaned = name.replace(" ", "").replace(".", "").replace("-", "")
    return len(name) >= 2 and cleaned.isalpha()


def is_valid_roll(roll):
    return roll.isalnum() and 3 <= len(roll) <= 15


def pick_student(students, prompt="Enter roll number: "):
    """Ask for a roll number until it exists. Returns None if user types 'back'."""
    while True:
        roll = read_text(prompt).upper()
        if roll == "BACK":
            return None
        if roll in students:
            return roll
        print("  Roll number not found. Try again (or type 'back').")


# ---------------------------- Calculations ----------------------------
def student_counts(roll, attendance):
    """Return (present_days, total_days) for one student."""
    present = total = 0
    for day in attendance:
        if roll in attendance[day]:
            total += 1
            if attendance[day][roll] == "P":
                present += 1
    return present, total


def percentage(present, total):
    """Attendance % = (present / total) * 100. Zero classes -> 0.0."""
    if total == 0:
        return 0.0
    return present / total * 100


def classes_needed(present, total, required=REQUIRED_PERCENT):
    """
    Minimum number of consecutive classes the student must attend
    to reach the required percentage.
        (present + x) / (total + x) >= required/100
        x >= (r*total - 100*present) / (100 - r)
    """
    if percentage(present, total) >= required:
        return 0
    return math.ceil((required * total - 100 * present) / (100 - required))


def classes_can_skip(present, total, required=REQUIRED_PERCENT):
    """
    Maximum further classes a student can miss and still stay at or above
    the required percentage:  present / (total + s) >= required/100
    """
    if total == 0 or percentage(present, total) < required:
        return 0
    return math.floor(present * 100 / required - total)


def grade_status(pct):
    """Rule-based status label from attendance percentage."""
    if pct >= 90:
        return "Excellent"
    if pct >= REQUIRED_PERCENT:
        return "Safe"
    if pct >= 60:
        return "Warning"
    return "Critical"


def build_summary(students, attendance):
    """List of dicts, one per student, with all computed values."""
    summary = []
    for roll, name in students.items():
        present, total = student_counts(roll, attendance)
        pct = percentage(present, total)
        summary.append({
            "roll": roll, "name": name, "present": present, "total": total,
            "pct": pct, "status": grade_status(pct) if total else "No data",
            "needed": classes_needed(present, total) if total else 0,
            "skip": classes_can_skip(present, total),
        })
    return summary


def rank_students(summary):
    """Sort by percentage (high to low), then by name."""
    return sorted(summary, key=lambda s: (-s["pct"], s["name"]))


def longest_absence_streak(roll, attendance):
    """Pattern identification: longest run of consecutive absences."""
    best = current = 0
    for day in sorted(attendance):
        if roll in attendance[day]:
            if attendance[day][roll] == "A":
                current += 1
                best = max(best, current)
            else:
                current = 0
    return best


# ---------------------------- Menu actions ----------------------------
def add_student(students):
    print()
    print("=== Add Student ===")
    roll = read_text("Roll number (letters/digits, 3-15 chars): ").upper()
    if not is_valid_roll(roll):
        print("  Invalid roll number.")
        return
    if roll in students:
        print(f"  Roll number {roll} already exists ({students[roll]}).")
        return
    name = read_text("Student name: ").title()
    if not is_valid_name(name):
        print("  Invalid name. Use letters, spaces, dots or hyphens only.")
        return
    students[roll] = name
    save_students(students)
    print(f"  Added {name} ({roll}).")


def view_students(students):
    print()
    print("=== Registered Students ===")
    if not students:
        print("  No students registered yet.")
        return
    print(f"  {'Roll No':<16}{'Name'}")
    print("  " + "-" * 36)
    for roll in sorted(students):
        print(f"  {roll:<16}{students[roll]}")
    print(f"  Total: {len(students)}")


def remove_student(students, attendance):
    print()
    print("=== Remove Student ===")
    if not students:
        print("  No students registered yet.")
        return
    roll = pick_student(students, "Roll number to remove (or 'back'): ")
    if roll is None:
        return
    if read_choice(f"  Remove {students[roll]} and all their records? (y/n): ", ("y", "n")) == "y":
        del students[roll]
        for day in list(attendance):
            attendance[day].pop(roll, None)
            if not attendance[day]:
                del attendance[day]
        save_students(students)
        save_attendance(attendance)
        print("  Student removed.")


def mark_attendance(students, attendance):
    print()
    print("=== Mark Attendance ===")
    if not students:
        print("  Add students first.")
        return
    day = read_date("Date (YYYY-MM-DD, blank = today): ")
    if day in attendance:
        choice = read_choice(f"  Attendance for {day} already exists. Overwrite? (y/n): ", ("y", "n"))
        if choice == "n":
            return
    records = {}
    print("  Enter P = Present, A = Absent, all = mark everyone present.")
    for roll in sorted(students):
        records[roll] = None
    # Quick option: mark all present, then correct exceptions
    first = read_choice("  Mark all present first and then list absentees? (y/n): ", ("y", "n"))
    if first == "y":
        for roll in records:
            records[roll] = "P"
        print("  Enter roll numbers of absent students one by one. Type 'done' to finish.")
        while True:
            roll = read_text("  Absent roll no (or 'done'): ").upper()
            if roll == "DONE":
                break
            if roll in records:
                records[roll] = "A"
                print(f"    {students[roll]} marked Absent.")
            else:
                print("    Roll number not found.")
    else:
        for roll in sorted(students):
            records[roll] = read_choice(f"  {roll} {students[roll]} (p/a): ", ("p", "a")).upper()
    attendance[day] = records
    save_attendance(attendance)
    absent = sum(1 for s in records.values() if s == "A")
    print(f"  Saved {day}: {len(records) - absent} present, {absent} absent.")


def view_student_record(students, attendance):
    print()
    print("=== Student Attendance Record ===")
    if not students:
        print("  No students registered yet.")
        return
    roll = pick_student(students, "Roll number (or 'back'): ")
    if roll is None:
        return
    present, total = student_counts(roll, attendance)
    print(f"\n  {students[roll]} ({roll})")
    if total == 0:
        print("  No attendance recorded yet.")
        return
    print("  Date          Status")
    for day in sorted(attendance):
        if roll in attendance[day]:
            label = "Present" if attendance[day][roll] == "P" else "Absent"
            print(f"  {day}    {label}")
    pct = percentage(present, total)
    print(f"\n  Present {present} of {total} classes = {pct:.1f}%  [{grade_status(pct)}]")
    streak = longest_absence_streak(roll, attendance)
    if streak >= 2:
        print(f"  Pattern: longest absence streak is {streak} classes in a row.")
    if pct < REQUIRED_PERCENT:
        print(f"  Must attend the next {classes_needed(present, total)} classes to reach {REQUIRED_PERCENT:.0f}%.")
    else:
        print(f"  Can still miss {classes_can_skip(present, total)} class(es) and stay at {REQUIRED_PERCENT:.0f}%+.")


def view_summary(students, attendance):
    print()
    print("=== Class Attendance Summary ===")
    if not students:
        print("  No students registered yet.")
        return
    print(f"  Classes held so far: {len(attendance)}")
    print(f"  {'Roll No':<14}{'Name':<22}{'P/T':<8}{'%':>7}  Status")
    print("  " + "-" * 62)
    for s in sorted(build_summary(students, attendance), key=lambda s: s["roll"]):
        print(f"  {s['roll']:<14}{s['name']:<22}{str(s['present']) + '/' + str(s['total']):<8}{s['pct']:>6.1f}%  {s['status']}")


def low_attendance_alerts(students, attendance):
    print()
    print(f"=== Low Attendance Alerts (below {REQUIRED_PERCENT:.0f}%) ===")
    low = [s for s in build_summary(students, attendance) if s["total"] and s["pct"] < REQUIRED_PERCENT]
    if not low:
        print("  No students are below the required attendance.")
        return
    for s in sorted(low, key=lambda s: s["pct"]):
        print(f"  {s['name']} ({s['roll']}): {s['pct']:.1f}% [{s['status']}] "
              f"- needs {s['needed']} more consecutive classes to reach {REQUIRED_PERCENT:.0f}%")


def class_analysis(students, attendance):
    print()
    print("=== Class Analysis & Ranking ===")
    summary = [s for s in build_summary(students, attendance) if s["total"]]
    if not summary:
        print("  Not enough data. Mark attendance first.")
        return
    ranked = rank_students(summary)
    average = sum(s["pct"] for s in summary) / len(summary)
    print(f"  Class average: {average:.1f}%")
    print(f"  Highest: {ranked[0]['name']} ({ranked[0]['pct']:.1f}%)")
    print(f"  Lowest : {ranked[-1]['name']} ({ranked[-1]['pct']:.1f}%)")
    counts = {}
    for s in summary:
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    print("  Status count: " + ", ".join(f"{k}: {v}" for k, v in counts.items()))
    print("\n  Rank  Name                  Attendance")
    for i, s in enumerate(ranked, 1):
        bar = "#" * int(s["pct"] / 5)  # 1 block = 5%
        print(f"  {i:<5} {s['name']:<21} {bar:<20} {s['pct']:.1f}%")
    worst = worst_day(attendance, students)
    if worst:
        print(f"\n  Lowest-turnout day: {worst[0]} ({worst[1]:.0f}% present)")


def worst_day(attendance, students):
    """Pattern identification: day with the lowest percentage present."""
    result = None
    for day, records in attendance.items():
        if not records:
            continue
        pct = sum(1 for s in records.values() if s == "P") / len(records) * 100
        if result is None or pct < result[1]:
            result = (day, pct)
    return result


def export_report(students, attendance):
    print()
    print("=== Export Report ===")
    if not students or not attendance:
        print("  Nothing to report yet.")
        return
    lines = [
        "ATTENDIFY - ATTENDANCE REPORT",
        f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Classes held: {len(attendance)}    Required: {REQUIRED_PERCENT:.0f}%",
        "",
        f"{'Rank':<6}{'Roll No':<14}{'Name':<22}{'Present':<10}{'%':>7}  Status",
        "-" * 70,
    ]
    for i, s in enumerate(rank_students(build_summary(students, attendance)), 1):
        lines.append(f"{i:<6}{s['roll']:<14}{s['name']:<22}{str(s['present']) + '/' + str(s['total']):<10}{s['pct']:>6.1f}%  {s['status']}")
    lines.append("")
    lines.append("Students below the required attendance:")
    low = [s for s in build_summary(students, attendance) if s["total"] and s["pct"] < REQUIRED_PERCENT]
    if low:
        for s in low:
            lines.append(f"  - {s['name']} ({s['roll']}): {s['pct']:.1f}%, needs {s['needed']} more classes")
    else:
        lines.append("  None")
    with open(path_of(REPORT_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Report saved to {REPORT_FILE}")


# ---------------------------- Main program ----------------------------
MENU = """
==============================
   ATTENDIFY - Attendance System
==============================
 1. Add Student
 2. View Students
 3. Remove Student
 4. Mark Attendance
 5. View Student Record
 6. Class Summary
 7. Low Attendance Alerts
 8. Class Analysis & Ranking
 9. Export Report
 0. Exit
"""


def main():
    students = load_students()
    attendance = load_attendance()
    while True:
        print(MENU)
        choice = read_text("Select an option (0-9): ")
        if choice == "1":
            add_student(students)
            pause()
        elif choice == "2":
            view_students(students)
            pause()
        elif choice == "3":
            remove_student(students, attendance)
            pause()
        elif choice == "4":
            mark_attendance(students, attendance)
            pause()
        elif choice == "5":
            view_student_record(students, attendance)
            pause()
        elif choice == "6":
            view_summary(students, attendance)
            pause()
        elif choice == "7":
            low_attendance_alerts(students, attendance)
            pause()
        elif choice == "8":
            class_analysis(students, attendance)
            pause()
        elif choice == "9":
            export_report(students, attendance)
            pause()
        elif choice == "0":
            print("Data saved. Goodbye!")
            break
        else:
            print("  Invalid option. Please enter a number from 0 to 9.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nProgram closed. Data is already saved.")
