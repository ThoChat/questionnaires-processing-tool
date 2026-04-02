from PyQt5 import QtCore, QtGui
from PyQt5 import QtWidgets as qtWid
from PIL import Image
import numpy as np
import pickle

from src.survey_templates import DiagramAreas

__license__ = "MIT"
__author__ = ["Alexandra Mielke", "Marvin Lorber"]

# -------- Helper --------

def status_color(status):
    if status == "Done":
        return "green"
    if status == "Needs checking":
        return "gold"
    return "grey"

def imgIcon_color(id:int):
    if id == 0:
        return QtGui.QColor(43, 29, 90, 120)
    elif id == 1:
        return QtGui.QColor(162, 150, 202, 120)
    elif id == 2:
        return QtGui.QColor(76, 28, 70, 120)
    elif id == 3:
        return QtGui.QColor(142, 204, 185, 120)
    elif id == 4:
        return QtGui.QColor(85,156,158,120)
    else:
        return QtGui.QColor(100,100,100,120) #gray

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
        self.setTabChangesFocus(True)
        self.setLineWrapMode(qtWid.QTextEdit.WidgetWidth)
        self.setMinimumWidth(0)
        self.setSizePolicy(qtWid.QSizePolicy.MinimumExpanding, qtWid.QSizePolicy.Fixed)

    def write_json(self):
        self.json_ref["text"] = self.toPlainText()

    def focusInEvent(self, e):
        self.focused.emit(self.template)
        super().focusInEvent(e)

class ClickableImageLabel(qtWid.QLabel):
    clicked = QtCore.pyqtSignal(int, int)

    def mousePressEvent(self, event):
        if self.pixmap() is None:
            return

        pixmap = self.pixmap()
        label_size = self.size()
        pixmap_size = pixmap.size()

        # scale-aware coordinate mapping
        x_ratio = pixmap_size.width() / label_size.width()
        y_ratio = pixmap_size.height() / label_size.height()

        px = int(event.x() * x_ratio)
        py = int(event.y() * y_ratio)

        self.clicked.emit(px, py)

class BoundDiagramWidget(qtWid.QWidget):
    focused = QtCore.pyqtSignal(object)

    def __init__(self, template, json_ref):
        super().__init__()

        self.template = template
        self.json_ref = json_ref

        areaMapping = Image.open("src/areaMapping.png")
        self.areaMapping = np.array(areaMapping)
        with open("src/outline_figures.pickle", 'rb') as f:
            self.areaDict = pickle.load(f)
        self.value_to_area = {member.value: member for member in DiagramAreas}

        layout = qtWid.QVBoxLayout(self)

        # --- Radio Buttons ---
        self.button_group = qtWid.QButtonGroup(self)
        self.button_group.setExclusive(True)

        radio_layout = qtWid.QHBoxLayout()

        self.buttons = {}
        # TODO: Access directly from template
        labels = ["Kreis", "Dreieck", "Quadrat", "Herz", "Gleich"]

        for i, text in enumerate(labels):
            rb = qtWid.QRadioButton(text)
            self.button_group.addButton(rb, i)
            radio_layout.addWidget(rb)
            self.buttons[text] = rb

        layout.addLayout(radio_layout)
        
        self.button_group.buttonClicked.connect(self.set_curr_symbol)

        # --- Image Stack ---
        self.stack = qtWid.QStackedLayout()
        container = qtWid.QWidget()
        container.setLayout(self.stack)

        # top image (semi-transparent)
        self.image_label = ClickableImageLabel()

        pixmap = QtGui.QPixmap(json_ref["file"])

        # scale to a fixed size (e.g. current label/container size)
        size_x = 1000
        target_size = QtCore.QSize(size_x, int((template.dy/template.dx) * size_x))

        scaled = pixmap.scaled(
            target_size,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )

        self.scaled_pixmap = scaled
        self.image_label.setPixmap(scaled)

        # store scale factors
        self.scale_x = pixmap.width() / scaled.width()
        self.scale_y = pixmap.height() / scaled.height()

        layout.addWidget(self.image_label)

        # click handling
        self.image_label.clicked.connect(self.handle_click)

    def set_curr_symbol(self, button):
        self.selected_id = self.button_group.checkedId()

    def handle_click(self, px, py):
        selected_id = self.button_group.checkedId()
        if selected_id == -1:
            return

        labels = ["Kreis", "Dreieck", "Quadrat", "Herz", "Gleich"]
        selected_shape = labels[selected_id]

        # store selection
        #self.json_ref["selectedShape"] = selected_shape
        #self.json_ref["lastClick"] = {"x": px, "y": py}
        imgVal = self.areaMapping[int(py*self.scale_y), int(px*self.scale_x)]

        areaType = self.value_to_area.get(imgVal)
        if not areaType or areaType == DiagramAreas.SOMETHING_ELSE:
            return
            

        imgPos = np.divide(np.array(self.areaDict[areaType.name]), [self.scale_x, self.scale_y])
        coords = imgPos.astype(np.uint16)

        image = self.scaled_pixmap.toImage()
        ptr = image.bits()
        ptr.setsize(image.byteCount())

        arr = np.frombuffer(ptr, np.uint8).reshape(
            (image.height(), image.width(), 4)
        )

        color = imgIcon_color(selected_id)
        arr[coords[:, 1], coords[:, 0]] = [
            color.red(), color.green(), color.blue(), color.alpha()
        ]

        self.scaled_pixmap = QtGui.QPixmap.fromImage(image)
        self.image_label.setPixmap(self.scaled_pixmap)
        #TODO store in self.json_ref

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

        # diagram
        if "diagram" in question_json:
            w = BoundDiagramWidget(question_template.diagramms[0], question_json["diagram"])
            w.focused.connect(self.elementFocused)
            layout.addWidget(w)
            elements.append(question_template.diagramms[0])
            isTablePage = False

        # tables
        for table_template, table_json in zip(
            question_template.diagramms, question_json.get("diagram", [])
        ):
            # TODO proper table handling
            w = qtWid.QTextEdit("Table would be here. I'm not bound yet though")
            #w.setPlainText("")
            w.setFixedHeight(70)

            layout.addWidget(w)

            elements.append(table_template)
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

# ---------------------------
# Scroll Bar Widget
# ---------------------------
class SnappingScrollBar(qtWid.QScrollBar):
    def __init__(self, positions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fixed_positions = positions
        self.setRange(0, self.fixed_positions[-1])
        self.setSingleStep(1)
        self.sliderReleased.connect(self.snapToNearest)
        self.index = 0
        self.toSync = []
    
    def snapToNearest(self, value=None):
        if value is None:
            value = self.value()
        self.setValue(value)

    def setValue(self, value):
        closest_idx = min(range(len(self.fixed_positions)),
                          key=lambda i: abs(self.fixed_positions[i] - value))
        super().setValue(self.fixed_positions[closest_idx])
        if self.index != closest_idx:
            self.index = closest_idx
            for other in self.toSync:
                other.snapToIndex(closest_idx)
    
    def snapToIndex(self, index):
        if index < len(self.fixed_positions):
            self.setValue(self.fixed_positions[index])
    
    def addSync(self, other):
        self.toSync.append(other)
    

# ---------------------------
# Scroll area hack
# ---------------------------
class NoHorizontalScrollArea(qtWid.QScrollArea):
    def ensureWidgetVisible(self, childWidget, xMargin=0, yMargin=0):
        # Only adjust vertical scrollbar
        if childWidget:
            pos = childWidget.mapTo(self.widget(), QtCore.QPoint(0, 0))
            self.verticalScrollBar().setValue(pos.y())
    
    def focusNextPrevChild(self, next):
        hbar = self.horizontalScrollBar()
        old = hbar.value()

        result = super().focusNextPrevChild(next)

        hbar.setValue(old)  # restore horizontal position
        return result