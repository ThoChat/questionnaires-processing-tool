import cv2
import json
import numpy as np
from src.survey_templates import Diagramm, Template, AnkerPos
import glob
import os

__license__ = "MIT"
__author__ = ["Marvin Lorber", "Alexandra Mielke"]


def deskew(img, corners, ids):
    ids = ids.flatten()
    marker_centers = {}

    for marker_corners, marker_id in zip(corners, ids):
        pts = marker_corners[0]  # shape (4,2)
        cx = np.mean(pts[:, 0])
        cy = np.mean(pts[:, 1])
        marker_centers[marker_id] = (cx, cy)

    H_out, W_out, _ = img.shape

    # Source points (from the current image, in correct corner order)
    src_pts = np.array(
        [
            marker_centers[1],  # top-left
            marker_centers[4],  # top-right
            marker_centers[3],  # bottom-right
            marker_centers[2],  # bottom-left
        ],
        dtype=np.float32,
    )

    # Destination points (fixed positions)
    dst_pts = np.array(
        [
            [AnkerPos.X.value, AnkerPos.Y.value],  # top-left
            [3725, 375],  # top-right
            [3725, 5530],  # bottom-right
            [645, 5530],  # bottom-left
        ],
        dtype=np.float32,
    )

    # Find transformation matrix, so source points are morphed to dst_pts (3×3 homography)
    H, _ = cv2.findHomography(src_pts, dst_pts)

    # Warp the whole image
    warped = cv2.warpPerspective(img, H, (W_out, H_out))
    return warped


def non_background_percentage(img) -> float:
    h, w = img.shape[:2]
    total_pixels = h * w

    # Define what counts as background (here: nearly white)
    # e.g. B,G,R all >= 230
    bg_lower = np.array([200, 200, 200], dtype=np.uint8)
    bg_upper = np.array([255, 255, 255], dtype=np.uint8)

    # Mask of background pixels
    bg_mask = cv2.inRange(img, bg_lower, bg_upper)

    # Invert mask: 255 where we consider "color", 0 where background
    color_mask = cv2.bitwise_not(bg_mask)

    color_pixels = cv2.countNonZero(color_mask)
    color_percentage = color_pixels / total_pixels * 100.0

    return color_percentage


class Page:
    def __init__(self, number, img, corners, ids) -> None:
        self.number = number
        self.img = img
        self.corners = corners
        self.ids = ids


def extract_diagramm(diagramm: Diagramm, page: Page):
    ids = page.ids.flatten()
    corners = dict(zip(ids, page.corners))
    top_left_corner = corners[diagramm.corner_ids[0]]
    top_left_point = top_left_corner[0][0]
    bottom_right_corner = corners[diagramm.corner_ids[3]]
    bottom_right_point = bottom_right_corner[0][2]
    return page.img[
        int(top_left_point[1]) : int(bottom_right_point[1]),
        int(top_left_point[0]) : int(bottom_right_point[0]),
    ]


def parse_single_data(imgDir, files, template: Template) -> str:
    threshold = 20  # percentage that has to be black for answer to be accepted
    pages = {}
    for fp in files:
        page_nr = int(fp[-5])
        img = cv2.imread(os.path.join(imgDir, fp))
        # Convert the image to grayscale
        gray = cv2.cvtColor(src=img, code=cv2.COLOR_BGR2GRAY)
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        parameters = cv2.aruco.DetectorParameters()

        # Create the ArUco detector
        detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
        # Detect the markers
        corners, ids, _ = detector.detectMarkers(gray)

        img = deskew(img, corners, ids)

        # redetect markers after transformation
        gray = cv2.cvtColor(src=img, code=cv2.COLOR_BGR2GRAY)
        corners, ids, _ = detector.detectMarkers(gray)

        pages[page_nr] = Page(page_nr, img, corners, ids)

    subjectData = {
        "participantNr": 0,
    }

    for question in template.get_questions():
        checkboxData = []
        for checkbox in question.checkboxes:
            top = int(AnkerPos.Y.value + checkbox.dy)
            left = int(AnkerPos.X.value + checkbox.dx)

            checkbox_img = pages[checkbox.page].img[top : top + 70, left : left + 60]
            grade = non_background_percentage(checkbox_img)
            checkboxData.append(
                {"text": checkbox.text, "answer": True if grade > threshold else False}
            )
            print(f"Question {question.num}-{checkbox.text}:{grade}")

        textfieldData = []
        for textfield in question.texts:
            top = int(AnkerPos.Y.value + textfield.dy)
            left = int(AnkerPos.X.value + textfield.dx)

            filePath = f"{imgDir}/question_{question.num}_freeText.jpg"
            cv2.imwrite(
                filePath,
                pages[textfield.page].img[
                    top : top + textfield.size_y, left : left + textfield.size_x, :
                ],
            )
            textfieldData.append({"text": "", "file": filePath})

        tableData = []
        for table in question.tables:
            top = int(AnkerPos.Y.value + table.dy)
            step_y = (int)(table.size_y / np.size(table.rows))
            for i, row in enumerate(table.rows):
                for dx, size_x, column in zip(table.dx, table.size_x, table.columns):
                    left = int(AnkerPos.X.value + dx)
                    cell_img = pages[table.page].img[
                        (top + i * step_y + 13) : (top + (i + 1) * step_y - 13),
                        (left) : (left + size_x),
                    ]
                    grade = non_background_percentage(cell_img)
                    print(f"{row}-{column}-{grade}")
                    # TODO: Parse table data to json file

        pathToDiagram = ""
        for diagramm in question.diagramms:
            img = extract_diagramm(diagramm, pages[diagramm.page])
            pathToDiagram = os.path.join(
                imgDir, f"question_{question.num}_diagramm.jpg"
            )
            cv2.imwrite(pathToDiagram, img)

        questionData = {}
        questionData["question"] = question.questionText
        if len(checkboxData) > 0:
            questionData["checkboxes"] = checkboxData
        if len(textfieldData) > 0:
            questionData["textFields"] = textfieldData
        if len(tableData) > 0:
            questionData["tables"] = tableData
        if pathToDiagram != "":
            questionData["diagram"] = {"file": pathToDiagram}
        subjectData[str(question.num)] = questionData

    for key, value in pages.items():
        imgFileName = f"page-00{key}.jpg"
        cv2.imwrite(
            os.path.join(imgDir, imgFileName), value.img
        )  # this overwrites the old image

    dataFileName = "surveyData.json"
    with open(os.path.join(imgDir, dataFileName), "w") as f:
        json.dump(subjectData, f, indent=4)
    return dataFileName


def mark_target_areas(path_in: str, template: Template):
    pages = {}
    for fp in glob.glob(path_in + "/page_[0-9][0-9][0-9].jpg"):
        if os.path.isfile(fp):
            page_nr = int(fp[-5])
            img = cv2.imread(fp)
            # Convert the image to grayscale
            gray = cv2.cvtColor(src=img, code=cv2.COLOR_BGR2GRAY)
            aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
            parameters = cv2.aruco.DetectorParameters()

            # Create the ArUco detector
            detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
            # Detect the markers
            corners, ids, _ = detector.detectMarkers(gray)

            img = deskew(img, corners, ids)

            # redetect markers after transformation
            gray = cv2.cvtColor(src=img, code=cv2.COLOR_BGR2GRAY)
            corners, ids, _ = detector.detectMarkers(gray)

            cv2.aruco.drawDetectedMarkers(img, corners, ids)

            pages[page_nr] = Page(page_nr, img, corners, ids)

    for question in template.get_questions():
        for checkbox in question.checkboxes:
            top = int(AnkerPos.Y.value + checkbox.dy)
            left = int(AnkerPos.X.value + checkbox.dx)
            cv2.rectangle(
                pages[checkbox.page].img,
                (left, top),
                (left + 60, top + 70),
                color=(255, 201, 201),
                thickness=2,
            )
            checkbox_img = pages[checkbox.page].img[top : top + 70, left : left + 60]
            grade = non_background_percentage(checkbox_img)
            print(f"Question {question.num}-{checkbox.text}:{grade}")
        for textfield in question.texts:
            top = int(AnkerPos.Y.value + textfield.dy)
            left = int(AnkerPos.X.value + textfield.dx)
            cv2.rectangle(
                pages[textfield.page].img,
                (left, top),
                (left + textfield.size_x, top + textfield.size_y),
                color=(255, 201, 201),
                thickness=2,
            )
        for table in question.tables:
            top = int(AnkerPos.Y.value + table.dy)
            step_y = (int)(table.size_y / np.size(table.rows))
            for i, row in enumerate(table.rows):
                for dx, size_x, column in zip(table.dx, table.size_x, table.columns):
                    left = int(AnkerPos.X.value + dx)
                    cell_img = pages[table.page].img[
                        (top + i * step_y + 13) : (top + (i + 1) * step_y - 13),
                        (left) : (left + size_x),
                    ]
                    cv2.rectangle(
                        pages[table.page].img,
                        (left, top + i * step_y + 13),
                        (left + size_x, top + (i + 1) * step_y - 13),
                        color=(255, 201, 201),
                        thickness=2,
                    )
                    grade = non_background_percentage(cell_img)
                    print(f"{row}-{column}-{grade}")
        for diagramm in question.diagramms:
            img = extract_diagramm(diagramm, pages[diagramm.page])
            cv2.imwrite(f"{path_in}/question_{question.num}_diagramm.jpg", img)

    for key, value in pages.items():
        cv2.imwrite(f"{path_in}/page_00{key}_detected.jpg", value.img)
