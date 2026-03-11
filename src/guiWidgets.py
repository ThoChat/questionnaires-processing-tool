from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets as qtWid

__license__ = "MIT"
__author__ = ["Alexandra Mielke", "Marvin Lorber"]

# -------- Helper --------


def status_color(status):
    if status == "Done":
        return "green"
    if status == "Needs checking":
        return "gold"
    return "grey"


# ---------------------------
# JSON binding
# ---------------------------


class BoundWidget:
    def __init__(self, json_ref):
        self.json_ref = json_ref

    def update_json(self, value):
        self.json_ref["answer"] = value


# ---------------------------
# Image Widget
# ---------------------------


class ImagePage(qtWid.QLabel):
    def __init__(self, pixmap, page_index):
        super().__init__()
        self.setPixmap(pixmap)
        self.page_index = page_index
        self.highlight_rect = None

    def set_highlight(self, rect):
        self.highlight_rect = rect
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.highlight_rect:
            painter = QtGui.QPainter(self)
            pen = QtGui.QPen(QtGui.QColor("red"))
            pen.setWidth(4)
            painter.setPen(pen)
            painter.drawRect(self.highlight_rect)


# ---------------------------
# Focus Widgets
# ---------------------------


class BoundCheckBox(qtWid.QCheckBox):
    focused = QtCore.pyqtSignal(object)

    def __init__(self, text, template, json_ref):
        super().__init__(text)

        self.template = template
        self.json_ref = json_ref

        self.setChecked(json_ref["answer"])

        self.stateChanged.connect(self.write_json)

    def write_json(self, state):
        self.json_ref["answer"] = bool(state)

    def focusInEvent(self, e):
        self.focused.emit(self.template)
        super().focusInEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.toggle()
        else:
            super().keyPressEvent(e)


class BoundTextEdit(qtWid.QTextEdit):
    focused = QtCore.pyqtSignal(object)

    def __init__(self, template, json_ref):
        super().__init__()

        self.template = template
        self.json_ref = json_ref

        self.setText(json_ref["text"])

        self.textChanged.connect(self.write_json)

    def write_json(self):
        self.json_ref["text"] = self.toPlainText()

    def focusInEvent(self, e):
        self.focused.emit(self.template)
        super().focusInEvent(e)


# ---------------------------
# Question Widget
# ---------------------------


class QuestionWidget(qtWid.QFrame):
    elementFocused = QtCore.pyqtSignal(object)

    def __init__(self, question_template, question_json):
        super().__init__()

        isTablePage = (
            False  # TODO: this is unnecessary once there is proper table handling
        )

        self.qnum = question_template.num
        self.question = question_template

        layout = qtWid.QVBoxLayout()

        title = qtWid.QLabel(f"Q{self.qnum}: {question_template.questionText}")
        title.setStyleSheet("font-weight:bold")
        layout.addWidget(title)

        elements = []

        # checkboxes
        for cb_template, cb_json in zip(
            question_template.checkboxes, question_json.get("checkboxes", [])
        ):
            w = BoundCheckBox(cb_template.text, cb_template, cb_json)
            w.focused.connect(self.elementFocused)
            layout.addWidget(w)

            elements.append(cb_template)

        # free text
        for txt_template, txt_json in zip(
            question_template.texts, question_json.get("textFields", [])
        ):
            w = BoundTextEdit(txt_template, txt_json)
            w.focused.connect(self.elementFocused)
            w.setFixedHeight(70)

            layout.addWidget(w)

            elements.append(txt_template)

        self.setLayout(layout)

        # tables
        for txt_template, txt_json in zip(
            question_template.diagramms, question_json.get("diagram", [])
        ):
            # TODO proper table handling
            w = qtWid.QTextEdit("Table would be here. I'm not bound yet though")
            w.setPlainText("")
            w.setFixedHeight(70)

            layout.addWidget(w)

            elements.append(txt_template)
            isTablePage = True

        # ---- compute template bounds ----
        if len(elements) > 0:
            self.template_page = elements[0].page
        else:
            raise RuntimeError("No known elements found on page.")

        if not isTablePage:
            self.template_top = min(e.dy for e in elements)
            self.template_bottom = max(
                e.dy + getattr(e, "size_y", 70) for e in elements
            )
        else:
            self.template_top = 0
            self.template_bottom = 4300


# ---------------------------
# Survey Entry Widget
# ---------------------------


class SurveyEntryWidget(qtWid.QFrame):
    clicked = QtCore.pyqtSignal(str)

    def __init__(self, name, status):
        super().__init__()

        self.name = name
        self.status = status

        self.setFrameShape(qtWid.QFrame.Box)
        self.setStyleSheet(f"border: 2px solid {status_color(status)};")

        layout = qtWid.QHBoxLayout()

        self.label = qtWid.QLabel(name)
        self.statusLabel = qtWid.QLabel(status)

        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.statusLabel)

        self.setLayout(layout)

    def mousePressEvent(self, event):
        self.clicked.emit(self.name)
