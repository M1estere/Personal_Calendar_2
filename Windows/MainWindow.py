from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from Windows.NotesWindow import NotesWindow
from Windows.AccountWindow import AccountWindow
from Widgets.CustomCalendar import CustomCalendar
from settings import *
from styles import *
from database_controller import get_user_days_notes


class MainWindow(QMainWindow):
    def __init__(self, current_user_id):
        super().__init__()

        self.user_id = current_user_id
        self.count = 0
        self.notes_windows = list()

        widget = QWidget()
        self.layout = QVBoxLayout()

        self.setMaximumSize(QSize(WINDOW_WIDTH, WINDOW_HEIGHT + 60))
        self.setMinimumSize(QSize(WINDOW_WIDTH, WINDOW_HEIGHT + 60))

        self.personal_cab = QPushButton('PERSONAL PAGE')
        self.personal_cab.clicked.connect(self.open_account_page)
        self.personal_cab.setStyleSheet(CALENDAR_WINDOW_BUTTON)
        self.personal_cab.setMinimumSize(QSize(WINDOW_WIDTH - 50, 50))

        self.layout.addWidget(self.personal_cab)

        self.display_calendar()

        self.unlog_button = QPushButton('EXIT')
        self.unlog_button.clicked.connect(self.exit_app)
        self.unlog_button.setStyleSheet(CALENDAR_WINDOW_BUTTON)
        self.unlog_button.setMinimumSize(QSize(WINDOW_WIDTH - 50, 50))

        self.layout.addWidget(self.unlog_button)

        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

    def display_calendar(self):
        font = QFont('Times', CALENDAR_FONT_SIZE)
        self.calendar = CustomCalendar(self)
        self.calendar.setStyleSheet(CALENDAR)

        self.calendar.setDates(get_user_days_notes(self.user_id), self.user_id)

        self.calendar.setFont(font)

        self.calendar.setGeometry(10, 10, WINDOW_WIDTH - 20, WINDOW_HEIGHT - 30)
        self.calendar.setGridVisible(True)

        self.calendar.clicked.connect(self.date_clicked_processor)

        self.layout.addWidget(self.calendar)

    def update_calendar(self):
        self.calendar.setDates(get_user_days_notes(self.user_id), self.user_id)
        self.calendar.updateCells()

    def open_account_page(self):
        self.account_window = AccountWindow(self.user_id)
        self.account_window.show()

    def exit_app(self):
        self.close()

    def date_clicked_processor(self, qDateClicked):
        notes_window = NotesWindow(qDateClicked, self.user_id, self)
        self.notes_windows.append(notes_window)

        notes_window.show()
