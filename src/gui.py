import asyncio

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QWidget, QPlainTextEdit, QErrorMessage, QHBoxLayout, QFileDialog,
)
from qasync import QEventLoop, asyncSlot

from EdgeGPT import Chatbot


class SydneyWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chatbot = Chatbot(cookie_path='./cookies.json')
        self.chat_history = QTextEdit()
        self.user_input = QPlainTextEdit()
        self.load_button = QPushButton("Load")
        self.load_button.clicked.connect(self.load_file)
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_file)
        self.load_button.setMaximumWidth(40)
        self.save_button.setMaximumWidth(40)
        self.send_button = QPushButton("Send")

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
        user_input = self.user_input.toPlainText()
        self.user_input.clear()
        self.send_button.setEnabled(False)
        self.load_button.setEnabled(False)
        self.chat_history.setReadOnly(True)
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
        self.send_button.setEnabled(True)
        self.load_button.setEnabled(True)
        self.reload_context()
        self.chat_history.setReadOnly(False)

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


if __name__ == "__main__":
    app = QApplication()
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    gui = SydneyWindow()
    gui.show()
    with loop:
        loop.run_forever()
