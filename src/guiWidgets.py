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
        return QtGui.QColor(43, 29, 90, 255)
    elif id == 1:
        return QtGui.QColor(162, 150, 202, 255)
    elif id == 2:
        return QtGui.QColor(76, 28, 70, 255)
    elif id == 3:
        return QtGui.QColor(142, 204, 185, 255)
    elif id == 4:
        return QtGui.QColor(85,156,158,255)
    elif id == 5:
        return QtGui.QColor(255,255,255,255) #white
    else:
        return QtGui.QColor(100,100,100,255) #gray

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
        self.setSizePolicy(
            qtWid.QSizePolicy.Ignored,   # ignore sizeHint and just use available space
            qtWid.QSizePolicy.Maximum    # do not expand more than defined in sizeHint
        )
        self.setSizePolicy(qtWid.QSizePolicy.Expanding, qtWid.QSizePolicy.Preferred)
        #print(f"Image Page size {self.width()}, {self.height()}.")
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
        self.setSizePolicy(qtWid.QSizePolicy.Expanding, qtWid.QSizePolicy.Fixed)

    def write_json(self):
        self.json_ref["text"] = self.toPlainText()

    def focusInEvent(self, e):
        self.focused.emit(self.template)
        super().focusInEvent(e)

class ClickableImageLabel(qtWid.QLabel):
    clicked = QtCore.pyqtSignal(int, int, bool)

    def mousePressEvent(self, event):
        if self.pixmap() is None:
            return
        
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(event.x(), event.y(), True)
        elif event.button() == QtCore.Qt.RightButton:
            self.clicked.emit(event.x(), event.y(), False)
        
        

class BoundDiagramWidget(qtWid.QWidget):
    focused = QtCore.pyqtSignal(object)
    tableChanged = QtCore.pyqtSignal()

    def __init__(self, template, json_ref, labels, maxWidth:int):
        super().__init__()

        self.template = template
        self.json_ref = json_ref
        self.labels = labels

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

        for i, text in enumerate(self.labels):
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

        self.image_label = ClickableImageLabel()

        pixmap = QtGui.QPixmap(json_ref["diagram"]["file"])

        # scale to a fixed target size (e.g. nearly half of the screen)
        scaled = pixmap.scaled(
            maxWidth,
            int((template.dy/template.dx) * maxWidth),
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

        #load old data
        if "data" in self.json_ref["diagram"]:
            for bodypart in self.json_ref["diagram"]["data"]:
                #match bodypart with DiagramAreas
                areaType = DiagramAreas[bodypart]

                #match selected shape with label number
                selected_shape = self.json_ref["diagram"]["data"][bodypart]
                try:
                    shape_id = self.labels.index(selected_shape)
                    self.color_bodyPart(areaType, shape_id)
                except:
                    pass  
        else:
            self.json_ref["diagram"]["data"] = {}

    def set_curr_symbol(self, button):
        self.selected_id = self.button_group.checkedId()

    def handle_click(self, px, py, leftButton:bool):
        selected_id = self.button_group.checkedId()
        if selected_id == -1:
            return
                
        # check which body part we clicked on
        imgVal = self.areaMapping[int(py*self.scale_y), int(px*self.scale_x)]
        areaType = self.value_to_area.get(imgVal)
        if not areaType or areaType == DiagramAreas.SOMETHING_ELSE:
            # no body area, do nothing
            return
        
        #clicked on something meaningful
        selected_shape = self.labels[selected_id]
        if leftButton:
            self.color_bodyPart(areaType, selected_id)
            self.json_ref["diagram"]["data"][areaType.name] = selected_shape # store selection
        else:
            self.color_bodyPart(areaType, 5)
            # check if entry actually exists
            if areaType.name in self.json_ref["diagram"]["data"]:
                del self.json_ref["diagram"]["data"][areaType.name] #undo selection

        self.tableChanged.emit() #update other widgets that there was change

    def color_bodyPart(self, areaType:DiagramAreas, shape_id:int):
        color = imgIcon_color(shape_id)
        imgPos = np.divide(np.array(self.areaDict[areaType.name]), [self.scale_x, self.scale_y])
        coords = imgPos.astype(np.uint16)

        image = self.scaled_pixmap.toImage()
        ptr = image.bits()
        ptr.setsize(image.byteCount())

        arr = np.frombuffer(ptr, np.uint8).reshape(
            (image.height(), image.width(), 4)
        )
            
        coords[:, 0] = np.clip(coords[:, 0], 0, image.width() - 1)
        coords[:, 1] = np.clip(coords[:, 1], 0, image.height() - 1)
        arr[coords[:, 1], coords[:, 0]] = [color.red(), color.green(), color.blue(), color.alpha()]

        self.scaled_pixmap = QtGui.QPixmap.fromImage(image)
        self.image_label.setPixmap(self.scaled_pixmap)    
        
    def focusInEvent(self, e):
        self.focused.emit(self.template)
        super().focusInEvent(e)


class BoundTableWidget(qtWid.QFrame):
    def __init__(self, template, json_ref):
        super().__init__()

        self.template = template
        self.json_ref = json_ref
        self.labels = template.tables[0].rows

        self.layout = qtWid.QGridLayout(self)

        # ---- HEADER ----
        headers = ["Bodypart", "Frequency", "Intensity", "Safety"]
        for col, text in enumerate(headers):
            wHeader = qtWid.QLabel(text)
            wHeader.setStyleSheet("font-weight:bold")
            self.layout.addWidget(wHeader, 0, col)

        # load table
        self.update_table()

        self.setSizePolicy(qtWid.QSizePolicy.Expanding, qtWid.QSizePolicy.Fixed)

    def update_table(self):
        # ---- CLEAR OLD ROWS (except header row 0) ----
        for i in reversed(range(self.layout.count())):
            item = self.layout.itemAt(i)
            row, col, _, _ = self.layout.getItemPosition(i)

            if row > 0:
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                self.layout.removeItem(item)

        # ---- RESET DATA ----
        self.json_ref["data"] = {}

        if "data" not in self.json_ref["diagram"]:
            return

        # ---- CREATE ROWS ----
        for row_index, bodypart in enumerate(self.json_ref["diagram"]["data"], start=1):
            selected_shape = self.json_ref["diagram"]["data"][bodypart]

            # ---- BODY PART LABEL ----
            self.layout.addWidget(qtWid.QLabel(bodypart), row_index, 0)

            combos = []

            # ---- CREATE DROPDOWNS ----
            for col_index in range(3):
                combo = qtWid.QComboBox()

                # add placeholder first
                combo.addItem("-- select --")

                # add real options
                combo.addItems(self.template.tables[col_index].columns)

                combos.append(combo)
                self.layout.addWidget(combo, row_index, col_index + 1)

            # ---- LOAD EXISTING DATA ----
            if selected_shape in self.json_ref["table"]["data"]:
                data = self.json_ref["table"]["data"][selected_shape]

                values = [
                    data.get("frequency"),
                    data.get("intensity"),
                    data.get("safety")
                ]

                for combo, value in zip(combos, values):
                    if value and combo.findText(value) != -1:
                        combo.setCurrentText(value)
                    else:
                        combo.setCurrentIndex(0)  # "-- select --"

            else:
                # default to placeholder
                for combo in combos:
                    combo.setCurrentIndex(0)

            # ---- SAVE CALLBACK ----
            def make_callback(bp, cbs):
                def callback():
                    self.json_ref["data"][bp] = {
                        "frequency": cbs[0].currentText() if cbs[0].currentIndex() != 0 else "",
                        "intensity": cbs[1].currentText() if cbs[1].currentIndex() != 0 else "",
                        "safety": cbs[2].currentText() if cbs[2].currentIndex() != 0 else ""
                    }
                return callback

            cb = make_callback(bodypart, combos)

            for combo in combos:
                combo.currentIndexChanged.connect(cb)

            # initialize data immediately
            cb()


# ---------------------------
# Question Widget
# ---------------------------


class QuestionWidget(qtWid.QFrame):
    elementFocused = QtCore.pyqtSignal(object)

    def __init__(self, question_template, question_json, maxWidgetWidth:int):
        super().__init__()

        self.setSizePolicy(
            qtWid.QSizePolicy.Ignored,   # ignore sizeHint and just use available space
            qtWid.QSizePolicy.Maximum    # do not expand more than vertically available
        )

        self.qnum = question_template.num

        layout = qtWid.QVBoxLayout()

        title = qtWid.QLabel(f"Q{self.qnum}: {question_template.questionText}")
        title.setWordWrap(True)
        title.setSizePolicy(qtWid.QSizePolicy.Expanding, qtWid.QSizePolicy.Preferred)
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

        # diagram
        if ("diagram" in question_json) and ("table" in question_json):
            wDiagram = BoundDiagramWidget(question_template.diagramms[0], question_json, 
                                   question_template.tables[0].rows, maxWidgetWidth)
            wDiagram.focused.connect(self.elementFocused)
            layout.addWidget(wDiagram)
            elements.append(question_template.diagramms[0])

            # we create single table and do not focus, as mapping 3 tables in template to 1 in GUI impossible
            wTable = BoundTableWidget(question_template, question_json)
            #wTable.focused.connect(self.elementFocused) #Don't focus, so there is no unnecessary jumping
            wDiagram.tableChanged.connect(wTable.update_table)
            layout.addWidget(wTable)
            #elements.append(table_template)

        self.setLayout(layout)

        # ---- compute template bounds ----
        if len(elements) > 0:
            self.template_page = elements[0].page
        else:
            raise RuntimeError("No known elements found on page.")

        self.template_top = min(e.dy for e in elements)
        self.template_bottom = max(
            e.dy + getattr(e, "size_y", 70) for e in elements)

    def sizeHint(self):
        return super().sizeHint()


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