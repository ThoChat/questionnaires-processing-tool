 
import Image
import os
import platform
import pytesseract

__license__ = "MIT"
__author__ = "Marvin Lorber"

if platform.system() == "Windows":
    # We may need to do some additional downloading and setup...
    # Windows needs a PyTesseract Download
    # https://github.com/UB-Mannheim/tesseract/wiki/

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