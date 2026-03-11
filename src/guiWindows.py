import sys
import os
from PyQt5 import QtWidgets as qtWid
from PyQt5 import QtGui, QtCore

import qdarktheme

from src.survey_templates import GrabExperiment, AnkerPos
from src.guiWidgets import ImagePage, QuestionWidget, SurveyEntryWidget
from src.guiIO import readData, saveData

__license__ = "MIT"
__author__ = "Alexandra Mielke"

# ---------------------------
# Survey Checking Window
# ---------------------------

class SurveyWindow(qtWid.QWidget):
    # add signal to send out once survey is closed
    surveyClosed = QtCore.pyqtSignal(str, str)

    def __init__(self, name, dataDir, typeTemplate, status):
        super().__init__()

        self.name = name
        self.status = status
        self.dataDir = dataDir

        # General data handling
        self.dataPath = os.path.join(self.dataDir, "surveyData.json")
        self.data = readData(self.dataPath)

        # QT GUI stuff
        self.setWindowTitle(name)

        mainLayout = qtWid.QVBoxLayout()

        doneButton = qtWid.QPushButton("Done")
        doneButton.clicked.connect(self.done)
        mainLayout.addWidget(doneButton)

        noMoreTimeButton = qtWid.QPushButton("Not done yet, but go back")
        noMoreTimeButton.clicked.connect(self.go_back)
        mainLayout.addWidget(noMoreTimeButton)

        weirdButton = qtWid.QPushButton("Report weird things and go back")
        weirdButton.clicked.connect(self.reportWeirdness)
        mainLayout.addWidget(weirdButton)

        splitter = qtWid.QSplitter()

        # Save shortcut
        saveShortcut = qtWid.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        saveShortcut.activated.connect(self.save)

        # LEFT SIDE (questions)
        self.questionScroll = qtWid.QScrollArea()
        self.questionScroll.setWidgetResizable(True)

        questionContainer = qtWid.QWidget()
        qlayout = qtWid.QVBoxLayout()

        # Example questions
        self.pages = []
        self.template = typeTemplate

        self.questions = []
        questions = typeTemplate.get_questions()

        for q in questions:
            q_json = self.data[str(q.num)]
            qw = QuestionWidget(q, q_json)
            qw.elementFocused.connect(self.highlight_element)
            self.questions.append(qw)
            qlayout.addWidget(qw)

        QtCore.QTimer.singleShot(0, self.init_images)

        qlayout.addStretch()
        questionContainer.setLayout(qlayout)

        self.questionScroll.setWidget(questionContainer)

        # RIGHT SIDE (images)
        self.imageScroll = qtWid.QScrollArea()
        self.imageScroll.setWidgetResizable(True)

        imageContainer = qtWid.QWidget()
        ilayout = qtWid.QVBoxLayout()

        ilayout.addStretch()
        imageContainer.setLayout(ilayout)

        self.imageScroll.setWidget(imageContainer)

        splitter.addWidget(self.questionScroll)
        splitter.addWidget(self.imageScroll)

        mainLayout.addWidget(splitter)

        self.setLayout(mainLayout)

        # Sync scrollbars
        self.questionScroll.verticalScrollBar().valueChanged.connect(
            self.imageScroll.verticalScrollBar().setValue
        )

        self.imageScroll.verticalScrollBar().valueChanged.connect(
            self.questionScroll.verticalScrollBar().setValue
        )

        self.showMaximized()

    # Return handling
    def save(self):
        saveData(self.dataPath, self.data)

    def go_back(self):
        self.save()
        self.surveyClosed.emit(self.name, self.status)
        self.close()

    def reportWeirdness(self):
        if "comment" in self.data:
            lastComment = self.data["comment"]
        else:
            lastComment = ""
        self.commentWindow = CommentWindow(lastComment)
        self.commentWindow.commentClosed.connect(self.updateComment)
        self.commentWindow.show()

    def updateComment(self, comment:str):
        self.data["comment"] = comment
        self.status = "Needs checking"
        self.go_back()

    def done(self):
        self.status = "Done"
        self.go_back()

    # image handling

    def highlight_element(self, element):
        page = element.page

        for p in self.pageWidgets:
            p.set_highlight(None)

        page_widget = self.pageWidgets[page-1]

        if hasattr(element, "size_x"):
            w = element.size_x
            h = element.size_y
        else:
            w = 60
            h = 70

        rect = QtCore.QRect(
            int((element.dx + AnkerPos.X.value) * page_widget.scale),
            int((element.dy + AnkerPos.Y.value) * page_widget.scale),
            int(w * page_widget.scale),
            int(h * page_widget.scale)
        )
        page_widget.set_highlight(rect)
        self.center_on(page_widget, rect)

    def get_page_widget_heights(self):
        heights = {}
        for qw in self.questions:
            elements = []
            elements.extend(qw.question.checkboxes)
            if hasattr(qw.question, "texts"):
                elements.extend(qw.question.texts)

            pages = {e.page for e in elements}
            for p in pages:
                heights.setdefault(p, 0)
                heights[p] += qw.sizeHint().height()

        return heights
    
    def init_images(self):
        scales = self.compute_page_scales()
        nr_pages = self.template.get_num_pages()

        self.pageWidgets = []
        for i in range(1, nr_pages + 1):
            path = os.path.join(self.dataDir, f"page-{i:03}.jpg")
            pix = QtGui.QPixmap(path)

            scale = scales.get(i, 0.3)

            pix = pix.scaled(
                int(pix.width() * scale),
                int(pix.height() * scale),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )

            page = ImagePage(pix, i)
            page.scale = scale

            self.pageWidgets.append(page)
            self.imageScroll.widget().layout().addWidget(page)
    
    def compute_page_scales(self):
        page_template_heights = {}
        page_gui_heights = {}
        for q in self.questions:
            page = q.template_page

            template_h = q.template_bottom - q.template_top
            gui_h = q.height()

            page_template_heights.setdefault(page, 0)
            page_gui_heights.setdefault(page, 0)

            page_template_heights[page] += template_h
            page_gui_heights[page] += gui_h

        scales = {}
        for p in page_template_heights:
            scales[p] = page_gui_heights[p] / page_template_heights[p]
        return scales
    
    def center_on(self, page_widget, rect):
        """Move image so it centers on page_widget"""
        scroll = self.imageScroll.verticalScrollBar()
        y = page_widget.y() + rect.y()
        scroll.setValue(y - self.imageScroll.height() // 2)

    # Question handling

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Down:
            self.jump_question(+1)

        elif e.key() == QtCore.Qt.Key_Up:
            self.jump_question(-1)

        else:
            super().keyPressEvent(e)

    def jump_question(self, direction):
        focus = self.focusWidget()

        for i, q in enumerate(self.questions):
            if q.isAncestorOf(focus):
                new_i = max(0, min(len(self.questions)-1, i+direction))
                next_q = self.questions[new_i]
                self.scroll_to_question(next_q)

                # focus first widget in question
                child = next_q.findChild((qtWid.QCheckBox, qtWid.QTextEdit))
                if child:
                    child.setFocus()
                break

    def scroll_to_question(self, qwidget):
        """Move questionScroll so it center on the current question"""
        bar = self.questionScroll.verticalScrollBar()
        y = qwidget.y()
        bar.setValue(y - self.questionScroll.height()//2)

# ---------------------------
# Comment Window
# ---------------------------

# Basic comment input window that returns comment once it's closed
class CommentWindow(qtWid.QWidget):
    #signal to be send once comment is closed
    commentClosed = QtCore.pyqtSignal(str)

    def __init__(self, lastComment):
        super().__init__()

        self.comment = lastComment

        mainLayout = qtWid.QVBoxLayout()
        self.setWindowTitle("Add comment")
        qtWid.QShortcut(QtGui.QKeySequence("Ctrl+Enter"), self, self.done)

        doneButton = qtWid.QPushButton("Done")
        doneButton.clicked.connect(self.done)
        mainLayout.addWidget(doneButton)

        self.textBox = qtWid.QTextEdit("Comment")
        self.textBox.setPlainText(lastComment)
        self.textBox.textChanged.connect(self.changeComment)
        mainLayout.addWidget(self.textBox)

        self.setLayout(mainLayout)
        self.showMaximized()        

    def done(self):
        self.commentClosed.emit(self.comment)
        self.close()

    def changeComment(self):
        self.comment = self.textBox.toPlainText()

# ---------------------------
# Main Window
# ---------------------------

class MainWindow(qtWid.QWidget):

    def __init__(self, experimentDir:str):
        super().__init__()

        self.metadataPath = os.path.join(experimentDir, "metadata.json")
        self.metadata = readData(self.metadataPath)
        self.experimentDir = experimentDir

        # QT stuff
        self.setWindowTitle("Survey Digitizer")

        layout = qtWid.QVBoxLayout()

        scroll = qtWid.QScrollArea()
        scroll.setWidgetResizable(True)

        container = qtWid.QWidget()
        self.vbox = qtWid.QVBoxLayout()

        self.rebuild_list()

        container.setLayout(self.vbox)
        scroll.setWidget(container)

        layout.addWidget(scroll)
        self.setLayout(layout)

    def sortSurveys(self):       
        # Sort entries
        order = {"Open": 0, "Needs checking": 1, "Done": 2}
        return sorted(self.metadata["surveyResponses"].items(), 
                      key=lambda x: order[x[1]["status"]])

    def open_survey(self, name):
        self.surveyWindow = SurveyWindow(name, self.metadata["surveyResponses"][name]["dir"], 
                                         GrabExperiment.initType(self.metadata["Experiment"]["Type"]), 
                                         self.metadata["surveyResponses"][name]["status"])
        self.surveyWindow.surveyClosed.connect(self.update_survey_status)
        self.surveyWindow.show()

    def update_survey_status(self, name, new_status):
        self.metadata["surveyResponses"][name]["status"] = new_status
        saveData(
            os.path.join(self.experimentDir, "metadata.json"),
            self.metadata
        )
        self.rebuild_list()

    def rebuild_list(self):
        # remove old widgets
        while self.vbox.count():
            item = self.vbox.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        sorted_items = self.sortSurveys()
        for name, data in sorted_items[:self.metadata["participants"]]:
            w = SurveyEntryWidget(name, data["status"])
            w.clicked.connect(self.open_survey)
            self.vbox.addWidget(w)

        self.vbox.addStretch()

def main(experimentDir):
    app = qtWid.QApplication(sys.argv)
    qdarktheme.setup_theme()

    window = MainWindow(experimentDir)
    window.resize(900, 600)
    window.show()

    sys.exit(app.exec_())