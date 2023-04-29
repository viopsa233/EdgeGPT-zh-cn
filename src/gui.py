import asyncio

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QWidget, QPlainTextEdit, QErrorMessage,
)
from qasync import QEventLoop, asyncSlot

from EdgeGPT import Chatbot


class SydneyWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chatbot = Chatbot(cookie_path='./cookies.json')
        self.chat_history = QTextEdit()
        self.user_input = QPlainTextEdit()
        self.send_button = QPushButton("Send")

        layout = QGridLayout()
        layout.addWidget(QLabel("Chat History:"), 0, 0)
        layout.addWidget(self.chat_history, 1, 0, 1, 2)
        layout.addWidget(QLabel("User Input:"), 2, 0)
        layout.addWidget(self.user_input, 3, 0)
        layout.addWidget(self.send_button, 3, 1)

        self.setLayout(layout)

        self.send_button.clicked.connect(self.send_message)
        self.reload_context()

    def reload_context(self):
        self.chat_history.setText(self.chatbot.format_previous_messages())
        self.chat_history.moveCursor(QTextCursor.MoveOperation.End)

    @asyncSlot()
    async def send_message(self):
        user_input = self.user_input.toPlainText()
        self.user_input.clear()
        self.send_button.setEnabled(False)

        async def stream_output():
            self.chat_history.moveCursor(QTextCursor.MoveOperation.End)
            self.chat_history.insertPlainText(f"[user](#message)\n{user_input}\n\n[assistant](#message)\n")
            wrote = 0
            async for final, response in self.chatbot.ask_stream(prompt=user_input):
                if not final:
                    self.chat_history.insertPlainText(response[wrote:])
                    wrote = len(response)

        try:
            await stream_output()
        except Exception as e:
            QErrorMessage(self).showMessage(str(e))
        self.send_button.setEnabled(True)
        self.reload_context()


if __name__ == "__main__":
    app = QApplication()
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    gui = SydneyWindow()
    gui.show()
    with loop:
        loop.run_forever()
