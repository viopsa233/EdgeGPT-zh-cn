import asyncio

from PySide6.QtGui import QTextCursor, Qt
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QWidget, QPlainTextEdit, QErrorMessage, QHBoxLayout, QFileDialog, QToolButton, QMenu, QSizePolicy,
)
from qasync import QEventLoop, asyncSlot

from EdgeGPT import Chatbot


class UserInput(QPlainTextEdit):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        if key == Qt.Key.Key_Enter or key == Qt.Key.Key_Return:
            match self.parent.enter_mode:
                case "Enter":
                    if modifiers == Qt.KeyboardModifier.NoModifier:
                        self.parent.send_message()
                    else:
                        super().keyPressEvent(event)
                        self.insertPlainText("\n")
                case "Ctrl+Enter":
                    if modifiers == Qt.KeyboardModifier.ControlModifier:
                        self.parent.send_message()
                    else:
                        super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)


class SydneyWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.responding = False
        self.enter_mode = "Enter"
        self.chatbot = Chatbot(cookie_path='./cookies.json')
        self.chat_history = QTextEdit()
        self.user_input = UserInput(self)
        self.user_input.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding))
        self.load_button = QPushButton("Load")
        self.load_button.clicked.connect(self.load_file)
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_file)
        self.load_button.setFixedWidth(40)
        self.save_button.setFixedWidth(40)
        self.send_button = QToolButton()
        self.send_button.setText("Send")
        self.send_button.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum))
        self.send_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        menu = QMenu(self)
        self.enter_action = menu.addAction("Press Enter to send", lambda: self.set_enter_mode("Enter"))
        self.enter_action.setCheckable(True)
        self.enter_action.setChecked(True)
        self.ctrl_enter_action = menu.addAction("Press Ctrl+Enter to send", lambda: self.set_enter_mode("Ctrl+Enter"))
        self.ctrl_enter_action.setCheckable(True)
        self.send_button.setMenu(menu)

        layout = QGridLayout()
        layout.addWidget(QLabel("Chat History:"), 0, 0)
        hbox = QHBoxLayout()
        hbox.addWidget(self.load_button)
        hbox.addWidget(self.save_button)
        layout.addLayout(hbox, 0, 1)
        layout.addWidget(self.chat_history, 1, 0, 1, 2)
        layout.addWidget(QLabel("User Input:"), 2, 0)
        layout.addWidget(self.user_input, 3, 0)
        layout.addWidget(self.send_button, 3, 1)

        layout.setRowStretch(1, 2)
        layout.setRowStretch(3, 1)
        self.setLayout(layout)

        self.send_button.clicked.connect(self.send_message)
        self.reload_context()

    def reload_context(self):
        self.chat_history.setText(self.chatbot.previous_messages)
        self.chat_history.moveCursor(QTextCursor.MoveOperation.End)

    @asyncSlot()
    async def send_message(self):
        if self.responding:
            return
        self.set_responding(True)
        user_input = self.user_input.toPlainText()
        self.user_input.clear()
        self.chat_history.moveCursor(QTextCursor.MoveOperation.End)
        text = self.chat_history.toPlainText()
        if not text.endswith("\n\n"):
            if text.endswith("\n"):
                self.chat_history.insertPlainText("\n")
            else:
                self.chat_history.insertPlainText("\n\n")
        self.chatbot.previous_messages = self.chat_history.toPlainText()

        async def stream_output():
            self.chat_history.moveCursor(QTextCursor.MoveOperation.End)
            self.chat_history.insertPlainText(f"[user](#message)\n{user_input}\n\n[assistant](#message)\n")
            wrote = 0
            async for final, response in self.chatbot.ask_stream(prompt=user_input):
                if not final:
                    self.chat_history.moveCursor(QTextCursor.MoveOperation.End)
                    self.chat_history.insertPlainText(response[wrote:])
                    wrote = len(response)

        try:
            await stream_output()
        except Exception as e:
            QErrorMessage(self).showMessage(str(e))
        self.reload_context()
        self.set_responding(False)

    def load_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilters(["Text files (*.txt)", "All files (*)"])
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        if file_dialog.exec():
            file_name = file_dialog.selectedFiles()[0]
            with open(file_name, "r", encoding='utf-8') as f:
                file_content = f.read()
            self.chatbot.previous_messages = file_content
            self.reload_context()

    def save_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilters(["Text files (*.txt)", "All files (*)"])
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        if file_dialog.exec():
            file_name = file_dialog.selectedFiles()[0]
            with open(file_name, "w", encoding='utf-8') as f:
                f.write(self.chat_history.toPlainText())

    def set_enter_mode(self, key):
        match key:
            case "Enter":
                self.enter_mode = "Enter"
                self.enter_action.setChecked(True)
                self.ctrl_enter_action.setChecked(False)
            case "Ctrl+Enter":
                self.enter_mode = "Ctrl+Enter"
                self.enter_action.setChecked(False)
                self.ctrl_enter_action.setChecked(True)

    def set_responding(self, responding):
        self.responding = responding
        if responding:
            self.send_button.setEnabled(False)
            self.load_button.setEnabled(False)
            self.chat_history.setReadOnly(True)
        else:
            self.send_button.setEnabled(True)
            self.load_button.setEnabled(True)
            self.chat_history.setReadOnly(False)


if __name__ == "__main__":
    app = QApplication()
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    gui = SydneyWindow()
    gui.show()
    with loop:
        loop.run_forever()
