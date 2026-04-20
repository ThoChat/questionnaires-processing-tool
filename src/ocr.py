# MIT License
# Copyright (c) 2026 Marvin Lorber

__license__ = "MIT"
__author__ = "Marvin Lorber"

from PIL import Image
import os
import platform
import pytesseract

if platform.system() == "Windows":
    # Some additional downloading and setup
    # See installation Guide for tesseract: https://pypi.org/project/pytesseract/#installation
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    )

def ocr(filepath):
    if os.path.isfile(filepath):
        with open(os.path.splitext(filepath)[0] + ".txt", mode="x") as output_file:
            text = str(pytesseract.image_to_string(Image.open(filepath), lang="deu"))
            # reattach divided words
            text = text.replace("-\n", "")
            output_file.write(text)
