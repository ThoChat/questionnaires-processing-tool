# MIT License
# Copyright (c) 2026 Alexandra Mielke & Marvin Lorber

__license__ = "MIT"
__author__ = ["Alexandra Mielke", "Marvin Lorber", "Thomas Chatagnon"]

import glob
import os
import re
from PyQt5 import QtWidgets as qtWid
from PyQt5 import QtGui, QtCore

from src.survey_templates import AnkerPos, CheckTable
from src.guiWidgets import BoundDiagramWidget, BoundTableWidget, ImagePage, ParticipantNumberWidget, QuestionWidget
from src.guiWindows import MainWindow, SurveyWindow

# ---------------------------
# Contact Survey Window
# ---------------------------


class HighlightArea:
    def __init__(self, page: int, dx: int, dy: int, size_x: int, size_y: int):
        self.page = page
        self.dx = dx
        self.dy = dy
        self.size_x = size_x
        self.size_y = size_y


class ContactSurveyWindow(SurveyWindow):
    """Same as SurveyWindow, but only shows the participant number and the contact questions
    (body diagram + table), next to the top of the first page and the pages of the contact questions.
    """

    # pixels of the scan kept below the participant number area
    HEADER_MARGIN = 200

    def __init__(self, *args, **kwargs):
        # show every scanned page instead of only the contact pages, e.g. if pages are scrambled
        self.showAllPages = False
        super().__init__(*args, **kwargs)

        self.allPagesButton = qtWid.QPushButton("See whole PDF")
        self.allPagesButton.clicked.connect(self.toggle_all_pages)
        self.buttonLayout.addWidget(self.allPagesButton)

    def toggle_all_pages(self):
        self.showAllPages = not self.showAllPages
        self.allPagesButton.setText("See contact pages only" if self.showAllPages else "See whole PDF")

        # only the images are reloaded, the entries are kept
        for page in self.pageWidgets:
            self.imageScroll.widget().layout().removeWidget(page)
            page.deleteLater()
        self.init_images()
        self.imageScroll.verticalScrollBar().setValue(0)

    def scanned_pages(self):
        pages = []
        for path in glob.glob(os.path.join(self.dataDir, "page-*.jpg")):
            match = re.fullmatch(r"page-(\d+)\.jpg", os.path.basename(path))
            if match:
                pages.append(int(match.group(1)))
        return sorted(pages)

    def contact_questions(self):
        return [q for q in self.typeTemplate.get_questions() if q.diagramms]

    def contact_pages(self):
        pages = set()
        for q in self.contact_questions():
            pages.update(e.page for e in [*q.diagramms, *q.tables])
        return sorted(pages)

    # ----------- QUESTION HANDLING ------------------------------
    def init_questions(self):
        self.questions = []

        participantNr = self.typeTemplate.get_participant_number()
        if participantNr is not None:
            self.questions.append(ParticipantNumberWidget(participantNr, self.data))

        for q in self.contact_questions():
            qw = QuestionWidget(q, self.data[str(q.num)], self.maxWidgetWidth)
            # highlight the table column that is edited
            qw.findChild(BoundTableWidget).focused.connect(self.highlight_element)
            # show the page of the diagram when a symbol is chosen
            diagram = qw.findChild(BoundDiagramWidget)
            diagram.button_group.buttonClicked.connect(
                lambda _, page=q.diagramms[0].page: self.show_page(page)
            )
            self.questions.append(qw)

        for qw in self.questions:
            qw.elementFocused.connect(self.highlight_element)
            self.questionLayout.addWidget(qw)
        self.questionLayout.addStretch()

        self.questionContainer.setSizePolicy(
            qtWid.QSizePolicy.Expanding,
            qtWid.QSizePolicy.Maximum
        )
        self.questionScroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

    # ----------- IMAGE HANDLING ------------------------------
    def init_images(self):
        contact_pages = self.contact_pages()
        participantNr = self.typeTemplate.get_participant_number()

        if self.showAllPages:
            pages = self.scanned_pages()
        else:
            # page 1 is always needed for the participant number
            pages = sorted(set(contact_pages) | {1})

        self.pageWidgets = []
        self.pageWidgetByNr = {}
        scale = None
        for i in pages:
            path = os.path.join(self.dataDir, f"page-{i:03}.jpg")
            pix = QtGui.QPixmap(path)
            if pix.isNull():
                # page missing in the scan
                continue

            if scale is None:
                scale = self.maxWidgetWidth / pix.width()

            # only keep the top of the page if it is not needed for contacts
            if not self.showAllPages and i not in contact_pages and participantNr is not None:
                bottom = AnkerPos.Y.value + participantNr.dy + participantNr.size_y + self.HEADER_MARGIN
                pix = pix.copy(0, 0, pix.width(), min(bottom, pix.height()))

            pix = pix.scaled(
                int(pix.width() * scale),
                int(pix.height() * scale),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )

            page = ImagePage(pix, i)
            page.scale = scale

            self.pageWidgets.append(page)
            self.pageWidgetByNr[i] = page
            self.imageScroll.widget().layout().addWidget(page)

        self.imageScroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

    def get_page_widget(self, page):
        # in the whole PDF the pages may be scrambled, so the entries are not linked to the images
        if self.showAllPages:
            return None
        return self.pageWidgetByNr.get(page)

    def highlight_element(self, element):
        if isinstance(element, CheckTable):
            # highlight all columns of the table
            element = HighlightArea(
                element.page,
                element.dx[0],
                element.dy,
                element.dx[-1] + element.size_x[-1] - element.dx[0],
                element.size_y,
            )
        super().highlight_element(element)

    def show_page(self, page):
        """Scroll the images to the top of a page"""
        for p in self.pageWidgets:
            p.set_highlight(None)
        page_widget = self.get_page_widget(page)
        if page_widget is not None:
            self.imageScroll.verticalScrollBar().setValue(page_widget.y())


# ---------------------------
# Contact Main Window
# ---------------------------


class ContactMainWindow(MainWindow):
    # separate status, as finishing the contacts does not mean the whole survey is done
    statusKey = "contactStatus"
    surveyWindowClass = ContactSurveyWindow

    def __init__(self, experimentDir: str):
        super().__init__(experimentDir)
        self.setWindowTitle("Survey Digitizer - Contacts")

    def get_status(self, surveyMetadata):
        # surveys annotated in the full GUI already include the contacts
        return surveyMetadata.get(self.statusKey, surveyMetadata.get("status", "Open"))
