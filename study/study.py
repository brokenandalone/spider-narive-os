#!/usr/bin/env python3

import os
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import (
    Qt, QTimer,
)
from PyQt5.QtGui import (
    QBrush,
    QFont,
    QPalette,
    QPixmap,
)
from PyQt5.QtWidgets import (
    QApplication, QDialog, QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


if QApplication.instance() is None:
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

SCRIPT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
)

SPIDER_ROOT = Path(
    "/usr/local/lib/spider-os"
)

if not SPIDER_ROOT.exists():
    SPIDER_ROOT = (
        SCRIPT_ROOT.parent
    )


sys.path.insert(
    0,
    str(SCRIPT_ROOT),
)

if __package__:
    from .school_portal import SchoolPortal
    from .store import StudyStore
    from .dashboard import overview
    from .paper_dialog import PaperDialog
else:
    from school_portal import SchoolPortal
    from store import StudyStore
    from dashboard import overview
    from paper_dialog import PaperDialog


WALLPAPER = (
    SPIDER_ROOT
    / "branding"
    / "workspaces"
    / "study.png"
)


class StudyWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.store = StudyStore()

        self.store.ensure_default_course()

        self.current_course_id = None
        self.wallpaper = None

        self.setWindowTitle(
            "School | Spider OS"
        )

        self.resize(
            1200,
            800,
        )

        self.setMinimumSize(
            950,
            650,
        )

        self.set_workspace_context()

        self.build_ui()
        self.load_wallpaper()
        self.load_courses()

    # --------------------------------------------------------
    # SPIDER OS CONTEXT
    # --------------------------------------------------------

    def set_workspace_context(self):
        runtime = Path(
            os.environ.get(
                "XDG_RUNTIME_DIR",
                f"/run/user/{os.getuid()}",
            )
        ) / "spider-os"

        try:
            runtime.mkdir(
                parents=True,
                exist_ok=True,
            )

            (
                runtime
                / "workspace"
            ).write_text(
                "study",
                encoding="utf-8",
            )

        except Exception:
            pass

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def build_ui(self):
        self.setStyleSheet(
            """
            QWidget#root {
                background:
                    rgba(9, 7, 12, 230);
            }

            QLabel {
                color:#f2edf5;
            }

            QListWidget,
            QTableWidget,
            QTextEdit {
                background:
                    rgba(20, 15, 27, 235);

                border:
                    1px solid #4c1d95;

                border-radius:
                    8px;

                color:
                    #f1eaf6;
            }

            QListWidget::item {
                padding:9px;
            }

            QListWidget::item:selected {
                background:#581c87;
            }

            QPushButton {
                background:
                    rgba(88, 28, 135, 225);

                border:
                    1px solid #7e22ce;

                border-radius:
                    8px;

                padding:
                    10px;

                color:
                    white;

                font-weight:
                    bold;
            }

            QPushButton:hover {
                background:#6b21a8;
                border-color:#c084fc;
            }

            QTabWidget::pane {
                border:
                    1px solid #3b2747;

                border-radius:
                    8px;

                background:
                    rgba(10, 8, 13, 220);
            }

            QTabBar::tab {
                background:#17101e;
                color:#c9bdcf;
                padding:10px 18px;
            }

            QTabBar::tab:selected {
                background:#581c87;
                color:white;
            }

            QHeaderView::section {
                background:#291737;
                border:1px solid #784ba1;
                color:#f9f0ff;
                padding:7px;
                font-weight:bold;
            }
            QMenu {
                background:#17101e;
                color:#f9f0ff;
                selection-background-color:#6b21a8;
                selection-color:#ffffff;
            }
            """
        )

        root = QWidget()

        root.setObjectName(
            "root"
        )

        self.setCentralWidget(
            root
        )

        outer = QVBoxLayout(
            root
        )

        outer.setContentsMargins(
            26,
            24,
            26,
            24,
        )

        title = QLabel(
            "SCHOOL"
        )

        title.setFont(
            QFont(
                "Sans Serif",
                34,
                QFont.Bold,
            )
        )

        title.setStyleSheet(
            "color:#c084fc;"
        )

        outer.addWidget(
            title
        )

        subtitle = QLabel(
            "LEARN  •  READ  •  RESEARCH  •  ANALYZE  •  WRITE  •  ACHIEVE"
        )

        subtitle.setStyleSheet(
            """
            color:#b4a7bd;
            font-size:14px;
            padding-bottom:4px;
            """
        )

        outer.addWidget(
            subtitle
        )

        actions = QHBoxLayout()

        self.add_action(
            actions,
            "LEARN",
            self.open_webbie,
        )

        self.add_action(
            actions,
            "READ",
            self.read_document,
        )

        self.add_action(
            actions,
            "RESEARCH",
            self.open_forage,
        )

        self.add_action(
            actions,
            "ANALYZE",
            self.open_deep_forage,
        )

        self.add_action(
            actions,
            "WRITE",
            self.open_writer,
        )

        self.add_action(
            actions,
            "ACHIEVE",
            self.focus_assignments,
        )

        outer.addLayout(
            actions
        )

        school_actions = QHBoxLayout()
        self.add_action(school_actions, "APA PAPER", self.create_apa_paper)
        self.add_action(school_actions, "WEBBIE HOMEWORK", self.open_homework)
        self.add_action(school_actions, "MY SNHU", self.open_snhu)
        self.add_action(school_actions, "SCHOOL ONEDRIVE", self.open_school_onedrive)
        self.add_action(school_actions, "APA GUIDE", self.open_apa_guide)
        self.add_action(school_actions, "WEEKLY PLAN", self.open_weekly_planner)
        outer.addLayout(school_actions)
        self.dashboard = QLabel()
        self.dashboard.setWordWrap(True)
        outer.addWidget(self.dashboard)
        self.refresh_dashboard()
        self.dashboard_timer = QTimer(self)
        self.dashboard_timer.timeout.connect(self.refresh_dashboard)
        self.dashboard_timer.start(30000)

        splitter = QSplitter(
            Qt.Horizontal
        )

        # ----------------------------------------------------
        # COURSES
        # ----------------------------------------------------

        course_panel = QWidget()

        course_layout = QVBoxLayout(
            course_panel
        )

        course_title = QLabel(
            "COURSES"
        )

        course_title.setStyleSheet(
            """
            font-size:18px;
            font-weight:bold;
            color:#d8b4fe;
            """
        )

        course_layout.addWidget(
            course_title
        )

        self.courses = QListWidget()

        self.courses.currentItemChanged.connect(
            self.course_changed
        )

        course_layout.addWidget(
            self.courses,
            1,
        )

        add_course = QPushButton(
            "+ ADD COURSE"
        )

        add_course.clicked.connect(
            self.add_course
        )

        course_layout.addWidget(
            add_course
        )

        open_folder = QPushButton(
            "OPEN COURSE FOLDER"
        )

        open_folder.clicked.connect(
            self.open_course_folder
        )

        course_layout.addWidget(
            open_folder
        )

        remove_course = QPushButton(
            "REMOVE COURSE"
        )

        remove_course.clicked.connect(
            self.remove_course
        )

        course_layout.addWidget(
            remove_course
        )

        splitter.addWidget(
            course_panel
        )

        # ----------------------------------------------------
        # MAIN STUDY AREA
        # ----------------------------------------------------

        main_panel = QWidget()

        main_layout = QVBoxLayout(
            main_panel
        )

        self.course_heading = QLabel(
            "Study"
        )

        self.course_heading.setStyleSheet(
            """
            font-size:24px;
            font-weight:bold;
            color:#e9d5ff;
            """
        )

        main_layout.addWidget(
            self.course_heading
        )

        self.tabs = QTabWidget()

        # Assignments tab
        assignments_tab = QWidget()

        assignments_layout = QVBoxLayout(
            assignments_tab
        )

        self.assignment_table = QTableWidget(
            0,
            3,
        )

        self.assignment_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.assignment_table.setHorizontalHeaderLabels(
            [
                "Assignment",
                "Due",
                "Status",
            ]
        )

        self.assignment_table.horizontalHeader().setStretchLastSection(
            True
        )

        assignments_layout.addWidget(
            self.assignment_table
        )

        assignment_buttons = QHBoxLayout()

        add_assignment = QPushButton(
            "+ ADD ASSIGNMENT"
        )

        add_assignment.clicked.connect(
            self.add_assignment
        )

        assignment_buttons.addWidget(
            add_assignment
        )

        complete_assignment = QPushButton(
            "MARK COMPLETE"
        )

        complete_assignment.clicked.connect(
            self.complete_assignment
        )

        assignment_buttons.addWidget(
            complete_assignment
        )

        reopen_assignment = QPushButton(
            "REOPEN"
        )

        reopen_assignment.clicked.connect(
            self.reopen_assignment
        )

        assignment_buttons.addWidget(
            reopen_assignment
        )

        delete_assignment = QPushButton(
            "DELETE"
        )

        delete_assignment.clicked.connect(
            self.delete_assignment
        )

        assignment_buttons.addWidget(
            delete_assignment
        )

        assignments_layout.addLayout(
            assignment_buttons
        )

        planner_buttons = QHBoxLayout()
        self.add_action(planner_buttons, "IMPORT CSV ASSIGNMENTS", self.import_csv_assignments)
        self.add_action(planner_buttons, "EXPORT COURSE CALENDAR", self.export_course_calendar)
        self.add_action(planner_buttons, "PRIVATE STUDY BACKUP", self.open_study_backup)
        assignments_layout.addLayout(planner_buttons)

        workspace_buttons = QHBoxLayout()
        self.add_action(workspace_buttons, "ASSIGNMENT WORKSPACE",
                        self.open_assignment_workspace)
        self.add_action(workspace_buttons, "COURSE FLASHCARDS",
                        self.open_flashcards)
        self.add_action(workspace_buttons, "MY PROGRESS",
                        self.open_study_progress)
        self.add_action(workspace_buttons, "WEBBIE STUDY COACH",
                        self.open_study_coach)
        self.add_action(workspace_buttons, "COURSE READINGS",
                        self.open_course_readings)
        assignments_layout.addLayout(workspace_buttons)
        self.assignment_table.itemDoubleClicked.connect(
            lambda _: self.open_assignment_workspace())

        self.tabs.addTab(
            assignments_tab,
            "Assignments",
        )

        # Notes tab
        notes_tab = QWidget()

        notes_layout = QVBoxLayout(
            notes_tab
        )

        self.notes = QTextEdit()

        self.notes.setPlaceholderText(
            "Course notes, ideas, study material, "
            "questions, reminders..."
        )

        notes_layout.addWidget(
            self.notes
        )

        save_notes = QPushButton(
            "SAVE NOTES"
        )

        save_notes.clicked.connect(
            self.save_notes
        )

        notes_layout.addWidget(
            save_notes
        )

        self.tabs.addTab(
            notes_tab,
            "Notes",
        )

        main_layout.addWidget(
            self.tabs,
            1,
        )

        self.status = QLabel(
            "Study ready."
        )

        self.status.setStyleSheet(
            "color:#9e92a6;"
        )

        main_layout.addWidget(
            self.status
        )

        splitter.addWidget(
            main_panel
        )

        splitter.setSizes(
            [
                280,
                850,
            ]
        )

        self.school_tabs = QTabWidget()
        self.school_tabs.addTab(splitter, 'Courses & coursework')
        self.school_portal = SchoolPortal(lambda: self.store.course_folder(self.current_course_id))
        self.school_tabs.addTab(self.school_portal, 'My SNHU')
        self.school_tabs.currentChanged.connect(
            lambda index: self.school_portal.open() if index == 1 else None)
        outer.addWidget(self.school_tabs, 1)

        footer = QLabel(
            "SCHOOL · SPIDER OS · YOUR LIFE. ONE WEB."
        )

        footer.setAlignment(
            Qt.AlignCenter
        )

        footer.setStyleSheet(
            """
            color:#665a6e;
            font-weight:bold;
            """
        )

        outer.addWidget(
            footer
        )

    def add_action(
        self,
        layout,
        title,
        callback,
    ):
        button = QPushButton(
            title
        )

        button.clicked.connect(
            callback
        )

        layout.addWidget(
            button
        )

    # --------------------------------------------------------
    # WALLPAPER
    # --------------------------------------------------------

    def load_wallpaper(self):
        if not WALLPAPER.exists():
            return

        self.wallpaper = QPixmap(
            str(WALLPAPER)
        )

        self.apply_wallpaper()

    def apply_wallpaper(self):
        if (
            self.wallpaper is None
            or self.wallpaper.isNull()
        ):
            return

        scaled = self.wallpaper.scaled(
            self.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )

        palette = QPalette(
            self.palette()
        )

        palette.setBrush(
            QPalette.Window,
            QBrush(scaled),
        )

        self.setPalette(
            palette
        )

        self.setAutoFillBackground(
            True
        )

    def resizeEvent(
        self,
        event,
    ):
        self.apply_wallpaper()

        super().resizeEvent(
            event
        )

    # --------------------------------------------------------
    # COURSES
    # --------------------------------------------------------

    def load_courses(self):
        selected = self.current_course_id

        self.courses.clear()

        first_item = None
        selected_item = None

        for course in self.store.courses():
            item = QListWidgetItem(
                course["name"]
            )

            item.setData(
                Qt.UserRole,
                course["id"],
            )

            self.courses.addItem(
                item
            )

            if first_item is None:
                first_item = item

            if (
                selected
                == course["id"]
            ):
                selected_item = item

        target = (
            selected_item
            or first_item
        )

        if target:
            self.courses.setCurrentItem(
                target
            )

    def course_changed(
        self,
        current,
        previous,
    ):
        if not current:
            return

        if (
            previous
            and self.current_course_id
        ):
            self.save_notes(
                quiet=True
            )

        self.current_course_id = (
            current.data(
                Qt.UserRole
            )
        )

        self.course_heading.setText(
            current.text()
        )

        self.load_assignments()

        self.notes.setPlainText(
            self.store.get_notes(
                self.current_course_id
            )
        )

        folder = self.store.course_folder(
            self.current_course_id
        )

        self.status.setText(
            f"Course workspace: {folder}"
        )

    def add_course(self):
        name, ok = QInputDialog.getText(
            self,
            "Add Course",
            "Course name:",
        )

        if (
            not ok
            or not name.strip()
        ):
            return

        self.save_notes(quiet=True)

        self.current_course_id = (
            self.store.add_course(
                name
            )
        )

        self.load_courses()

    def remove_course(self):
        if not self.current_course_id:
            return

        course = self.store.course(
            self.current_course_id
        )

        if not course:
            return

        answer = QMessageBox.question(
            self,
            "Remove Course",
            (
                f"Remove '{course['name']}' "
                "from Study?\n\n"
                "The course folder in Documents "
                "will NOT be deleted."
            ),
        )

        if (
            answer
            != QMessageBox.Yes
        ):
            return

        self.store.remove_course(
            self.current_course_id
        )

        self.current_course_id = None

        self.store.ensure_default_course()

        self.load_courses()

    def open_course_folder(self):
        if not self.current_course_id:
            return

        folder = self.store.course_folder(
            self.current_course_id
        )

        subprocess.Popen(
            [
                "xdg-open",
                str(folder),
            ],
            start_new_session=True,
        )

    # --------------------------------------------------------
    # ASSIGNMENTS
    # --------------------------------------------------------

    def load_assignments(self):
        self.refresh_dashboard()
        self.assignment_table.setRowCount(
            0
        )

        if not self.current_course_id:
            return

        for assignment in (
            self.store.assignments(
                self.current_course_id
            )
        ):
            row = (
                self.assignment_table
                .rowCount()
            )

            self.assignment_table.insertRow(
                row
            )

            title = QTableWidgetItem(
                assignment["title"]
            )

            title.setData(
                Qt.UserRole,
                assignment["id"],
            )

            self.assignment_table.setItem(
                row,
                0,
                title,
            )

            self.assignment_table.setItem(
                row,
                1,
                QTableWidgetItem(
                    assignment["due"]
                ),
            )

            self.assignment_table.setItem(
                row,
                2,
                QTableWidgetItem(
                    assignment["status"]
                ),
            )

        self.assignment_table.resizeColumnsToContents()

    def selected_assignment_id(self):
        row = (
            self.assignment_table
            .currentRow()
        )

        if row < 0:
            return None

        item = self.assignment_table.item(
            row,
            0,
        )

        if not item:
            return None

        return item.data(
            Qt.UserRole
        )

    def add_assignment(self):
        if not self.current_course_id:
            return

        title, ok = QInputDialog.getText(
            self,
            "Add Assignment",
            "Assignment:",
        )

        if (
            not ok
            or not title.strip()
        ):
            return

        due, due_ok = QInputDialog.getText(
            self,
            "Due Date",
            (
                "Due date YYYY-MM-DD "
                "(optional):"
            ),
        )

        if not due_ok:
            due = ""

        self.store.add_assignment(
            self.current_course_id,
            title,
            due,
        )

        self.load_assignments()

    def import_csv_assignments(self):
        """Preview selected CSV assignments before creating local coursework."""
        if not self.current_course_id:
            return
        folder = self.store.course_folder(self.current_course_id)
        filename, _ = QFileDialog.getOpenFileName(
            self, "Choose assignments CSV", str(folder),
            "Comma-separated assignments (*.csv)")
        if not filename:
            return
        try:
            if __package__:
                from .assignment_planner import parse_assignment_csv
            else:
                from assignment_planner import parse_assignment_csv
            result = parse_assignment_csv(filename, self.store.assignments(self.current_course_id))
            rows = result["rows"]
            if not rows:
                self.status.setText(
                    f"No new open assignments. {result['skipped']} duplicates; "
                    f"{result['completed']} completed rows skipped.")
                return
            names = "\n".join(
                f"• {title} ({due or 'date not specified'})"
                for title, due in rows[:8])
            more = f"\n...and {len(rows) - 8} more." if len(rows) > 8 else ""
            answer = QMessageBox.question(
                self, "Import assignment preview",
                f"Add {len(rows)} open assignments to this course?\n"
                f"{result['skipped']} duplicates; {result['completed']} completed rows skipped.\n\n"
                + names + more + "\n\nNo school files will be uploaded.")
            if answer != QMessageBox.Yes:
                self.status.setText("Assignment import cancelled; no changes made.")
                return
            self.store.add_assignments_bulk(self.current_course_id, rows)
            self.load_assignments()
            self.status.setText(f"Imported {len(rows)} assignments to the selected course.")
        except (OSError, UnicodeError, ValueError) as error:
            QMessageBox.warning(self, "Assignment import", str(error))

    def export_course_calendar(self):
        """Owner-triggered .ics export covers all locally tracked courses."""
        if not self.current_course_id:
            return
        if __package__:
            from .assignment_planner import write_calendar
        else:
            from assignment_planner import write_calendar
        folder = self.store.course_folder(self.current_course_id)
        target, _ = QFileDialog.getSaveFileName(
            self, "Export all Study assignment deadlines",
            str(folder / "study-assignments.ics"),
            "Calendar (*.ics)")
        if not target:
            return
        if not target.lower().endswith(".ics"):
            target += ".ics"
        overwrite = False
        if Path(target).exists():
            overwrite = QMessageBox.question(
                self, "Replace calendar file",
                "Replace this calendar file? Existing files are otherwise preserved."
            ) == QMessageBox.Yes
            if not overwrite:
                return
        try:
            count = write_calendar(target, self.store.all_assignments(), overwrite=overwrite)
            self.status.setText(f"Saved {count} open dated deadlines from all Study courses: {target}")
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Calendar export", str(error))

    def open_assignment_workspace(self):
        """Open the selected assignment's persistent local workbook."""
        assignment_id = self.selected_assignment_id()
        if not assignment_id:
            self.status.setText("Select an assignment before opening its workspace.")
            return
        try:
            if __package__:
                from .assignment_workspace_ui import AssignmentWorkspaceDialog
            else:
                from assignment_workspace_ui import AssignmentWorkspaceDialog
            dialog = AssignmentWorkspaceDialog(
                self.store, assignment_id,
                self.store.course_folder(self.current_course_id), self)
            dialog.exec_()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Assignment workspace", str(error))

    def open_flashcards(self):
        """Manual review deck for this course, with optional CSV import."""
        if not self.current_course_id:
            self.status.setText("Select a course to open flashcards.")
            return
        try:
            if __package__:
                from .flashcards_ui import FlashcardsDialog
            else:
                from flashcards_ui import FlashcardsDialog
            dialog = FlashcardsDialog(
                self.store, self.current_course_id,
                self.store.course_folder(self.current_course_id), self)
            dialog.exec_()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Flashcards", str(error))

    def open_study_backup(self):
        """Manually archive a consistent database copy and private course files."""
        try:
            if __package__:
                from .study_backup_ui import StudyBackupDialog
            else:
                from study_backup_ui import StudyBackupDialog
            StudyBackupDialog(self).exec_()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Study backup", str(error))

    def open_weekly_planner(self):
        """Open a user-triggered overview of dates and milestones across courses."""
        try:
            if __package__:
                from .weekly_planner_ui import WeeklyPlannerDialog
            else:
                from weekly_planner_ui import WeeklyPlannerDialog
            WeeklyPlannerDialog(self.store, self).exec_()
            self.refresh_dashboard()
            self.load_assignments()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Weekly planner", str(error))

    def open_course_readings(self):
        """Browse manually imported documents for the selected course only."""
        if not self.current_course_id:
            self.status.setText("Select a course before opening its reading library.")
            return
        try:
            if __package__:
                from .reading_library_ui import ReadingLibraryDialog
            else:
                from reading_library_ui import ReadingLibraryDialog
            ReadingLibraryDialog(self.store, self.current_course_id, self).exec_()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Course Readings", str(error))

    def open_study_coach(self):
        """Study Coach only sees explicitly previewed and selected materials."""
        try:
            if __package__:
                from .study_coach_ui import StudyCoachDialog
            else:
                from study_coach_ui import StudyCoachDialog
            course = self.store.course(self.current_course_id) if self.current_course_id else None
            assignment_id = self.selected_assignment_id() if course else None
            row = self.store.assignment_record(assignment_id) if assignment_id else None
            fields = self.store.get_assignment_workspace(assignment_id) if row else None
            preview = "\n\n".join(
                f"{name.upper()}:\n{fields[name]}"
                for name in ("instructions", "rubric", "research")
                if fields and fields[name].strip())
            dialog = StudyCoachDialog(
                self, course=course["name"] if course else "General Study",
                topic=row["title"] if row else "",
                materials=preview,
                notes=self.store.get_notes(self.current_course_id) if course else "",
                store=self.store if course else None,
                course_id=self.current_course_id if course else None)
            dialog.exec_()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Study Coach", str(error))

    def open_study_progress(self):
        """Private, manually entered scores and logged study sessions."""
        if not self.current_course_id:
            self.status.setText("Choose a course for your progress tracker.")
            return
        try:
            if __package__:
                from .study_progress_ui import StudyProgressDialog
            else:
                from study_progress_ui import StudyProgressDialog
            dialog = StudyProgressDialog(self.store, self.current_course_id, self)
            dialog.exec_()
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "Study progress", str(error))

    def complete_assignment(self):
        assignment_id = (
            self.selected_assignment_id()
        )

        if not assignment_id:
            return

        self.store.set_assignment_status(
            assignment_id,
            "Complete",
        )

        self.load_assignments()

    def reopen_assignment(self):
        assignment_id = (
            self.selected_assignment_id()
        )

        if not assignment_id:
            return

        self.store.set_assignment_status(
            assignment_id,
            "Open",
        )

        self.load_assignments()

    def delete_assignment(self):
        assignment_id = (
            self.selected_assignment_id()
        )

        if not assignment_id:
            return

        record = self.store.assignment_record(assignment_id)
        if not record:
            return
        sections = self.store.get_assignment_workspace(assignment_id)
        has_related = bool(self.store.assignment_steps(assignment_id) or
                           self.store.assignment_sources(assignment_id))
        if any(text.strip() for text in sections.values()) or has_related:
            warning = ("This assignment contains saved coursework. Deleting "
                       "removes its local Study notebook, saved sources, checklist steps and drafts from the "
                       "Study database. Documents already saved in the course "
                       "folder are not deleted.")
        else:
            warning = ("Delete this assignment from Study? Existing course "
                       "files are preserved.")
        if QMessageBox.question(
            self, "Confirm assignment deletion",
            f"{record['title']}\n\n{warning}"
        ) != QMessageBox.Yes:
            return
        self.store.delete_assignment(assignment_id)
        self.load_assignments()

    # --------------------------------------------------------
    # NOTES
    # --------------------------------------------------------

    def save_notes(
        self,
        quiet=False,
    ):
        if not self.current_course_id:
            return

        self.store.save_notes(
            self.current_course_id,
            self.notes.toPlainText(),
        )

        if not quiet:
            self.status.setText(
                "Notes saved."
            )

    # --------------------------------------------------------
    # STUDY ACTIONS
    # --------------------------------------------------------

    def launch(
        self,
        command,
    ):
        try:
            subprocess.Popen(
                [
                    str(part)
                    for part in command
                ],
                start_new_session=True,
            )

            return True

        except Exception as error:
            self.status.setText(
                str(error)
            )

            return False

    def open_webbie(self):
        path = (
            SPIDER_ROOT
            / "webbie"
            / "ui"
            / "webbie-ui.py"
        )

        if path.exists():
            self.launch(
                [
                    "python3",
                    path,
                ]
            )

            self.status.setText(
                "Webbie opened in Study context."
            )

        else:
            self.status.setText(
                "Webbie is unavailable."
            )

    def read_document(self):
        start = (
            self.store.course_folder(
                self.current_course_id
            )
            if self.current_course_id
            else Path.home()
        )

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Study Material",
            str(start),
            (
                "Documents (*.pdf *.epub *.txt "
                "*.odt *.doc *.docx *.ppt *.pptx);;"
                "All Files (*)"
            ),
        )

        if not filename:
            return

        self.launch(
            [
                "xdg-open",
                filename,
            ]
        )

    def open_forage(self):
        path = (
            SPIDER_ROOT
            / "forage"
            / "forage.py"
        )

        if path.exists():
            self.launch(
                [
                    "python3",
                    path,
                ]
            )

            self.status.setText(
                "Forage opened."
            )

        else:
            self.status.setText(
                "Forage has not been installed yet."
            )

    def open_deep_forage(self):
        path = (
            SPIDER_ROOT
            / "forage"
            / "deep-forage"
            / "deep_forage.py"
        )

        if path.exists():
            self.launch(
                [
                    "python3",
                    path,
                ]
            )

            self.status.setText(
                "Deep Forage opened."
            )

        else:
            self.status.setText(
                "Deep Forage has not been installed yet."
            )

    def refresh_dashboard(self):
        summary = overview(self.store.all_assignments())
        text = (f"Across all courses: {summary['open']} open · {summary['complete']} complete · "
                f"{summary['overdue']} overdue · {summary['today']} due today · "
                f"{summary['next_7_days']} due in 7 days · {summary['undated']} need an ISO date")
        if summary['upcoming']:
            next_due = summary['upcoming'][0]
            text += f"\nNext outstanding: {next_due['course']} / {next_due['title']} / {next_due['due']}"
        self.dashboard.setText(text)

    def open_snhu(self):
        self.school_tabs.setCurrentIndex(1)
        self.school_portal.open()

    def open_homework(self):
        """Webbie gets the selected assignment's saved context, with explicit handoff."""
        try:
            if __package__:
                from .homework_ui import HomeworkDialog
                from .assignment_workflow import webbie_directions, webbie_materials
                from .draft_storage import save_snapshot
            else:
                from homework_ui import HomeworkDialog
                from assignment_workflow import webbie_directions, webbie_materials
                from draft_storage import save_snapshot
            course = self.store.course(self.current_course_id) if self.current_course_id else None
            selected_id = self.selected_assignment_id() if course else None
            record = self.store.assignment_record(selected_id) if selected_id else None
            workspace = self.store.get_assignment_workspace(selected_id) if record else None
            folder = self.store.course_folder(self.current_course_id)
            dialog = HomeworkDialog(
                self,
                course=course["name"] if course else "",
                assignment=record["title"] if record else "",
                notes=self.store.get_notes(self.current_course_id) if course else "",
                folder=folder,
                store=self.store if course else None,
                course_id=self.current_course_id if course else None,
            )
            if workspace:
                if workspace["instructions"].strip() or workspace["rubric"].strip():
                    dialog.directions.setPlainText(webbie_directions(workspace))
                dialog.materials.setPlainText(webbie_materials(workspace))
                dialog.draft.setPlainText(workspace["draft"])
            dialog.exec_()
            if workspace:
                candidate = dialog.draft.toPlainText()
                previous = workspace["draft"]
                if candidate.strip() and candidate != previous:
                    answer = QMessageBox.question(
                        self, "Save Webbie draft to assignment",
                        "Copy the edited draft to the selected assignment workspace? "
                        "The previous draft will be backed up first.")
                    if answer == QMessageBox.Yes:
                        if previous.strip():
                            save_snapshot(folder, record["title"], previous)
                        updated = dict(workspace, draft=candidate)
                        self.store.save_assignment_workspace(selected_id, updated)
                        self.status.setText("Webbie draft copied into the saved assignment workspace.")
        except Exception as error:
            QMessageBox.warning(self, "Webbie Homework", str(error))

    def open_school_onedrive(self):
        # School Microsoft identity is independent of personal Webbie storage.
        try:
            if __package__:
                from .school_onedrive import SchoolOneDriveDialog
            else:
                from school_onedrive import SchoolOneDriveDialog
            dialog = SchoolOneDriveDialog(self, self.store.course_folder(self.current_course_id))
            dialog.exec_()
        except Exception as error:
            QMessageBox.warning(self, 'School OneDrive', str(error))

    def open_apa_guide(self):
        self.launch(['xdg-open', 'https://apastyle.apa.org/instructional-aids/student-paper-setup-guide.pdf'])

    def create_apa_paper(self):
        course = self.store.course(self.current_course_id) if self.current_course_id else None
        dialog = PaperDialog(self, course['name'] if course else '')
        if dialog.exec_() != QDialog.Accepted:
            return
        values = dialog.values()
        if any(not values[key] for key in ('title','author','institution','course','instructor','due')):
            QMessageBox.warning(self, 'APA paper', 'Complete all title-page fields.'); return
        folder = self.store.course_folder(self.current_course_id) / 'Assignments'
        path, _ = QFileDialog.getSaveFileName(self, 'Save APA paper', str(folder / 'paper.docx'), 'Word (*.docx)')
        if not path:
            return
        if not path.lower().endswith('.docx'):
            path += '.docx'
        overwrite = False
        if Path(path).exists():
            overwrite = QMessageBox.question(self, 'Replace document',
                'Replace this document?') == QMessageBox.Yes
            if not overwrite:
                return
        try:
            if __package__:
                from .apa import create_paper
            else:
                from apa import create_paper
            create_paper(path, **values, overwrite=overwrite)
        except ImportError:
            QMessageBox.warning(self, 'APA paper', 'APA export needs python3-docx. Install the School dependency and retry.')
            return
        except Exception as error:
            QMessageBox.warning(self, 'APA paper', str(error)); return
        self.status.setText(f'APA paper saved: {path}')

    def open_writer(self):
        if self.current_course_id:
            folder = (
                self.store.course_folder(
                    self.current_course_id
                )
                / "Assignments"
            )
        else:
            folder = Path.home()

        self.launch(
            [
                "libreoffice",
                "--writer",
            ]
        )

        self.status.setText(
            f"Writer opened. Course files: {folder}"
        )

    def focus_assignments(self):
        self.tabs.setCurrentIndex(
            0
        )

        self.assignment_table.setFocus()

        self.status.setText(
            "Assignments in focus."
        )

    # --------------------------------------------------------
    # CLOSE
    # --------------------------------------------------------

    def closeEvent(
        self,
        event,
    ):
        try:
            self.save_notes(quiet=True)
        except Exception as error:
            self.status.setText('Notes could not be saved: ' + str(error))
            event.ignore()
            return
        self.store.close()
        event.accept()


def main():
    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        "Study"
    )

    window = StudyWindow()

    window.show()

    sys.exit(
        app.exec_()
    )


if __name__ == "__main__":
    main()
