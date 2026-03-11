import platform
import glob
import os.path
import argparse
from pathlib import Path

import pytesseract
from pdf2image import convert_from_path
from PIL import Image

if platform.system() == "Windows":
    # Some additional downloading and setup

    # See installation Guide for tesseract: https://pypi.org/project/pytesseract/#installation
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    )

    # Check installation guide for pdf2image: https://pypi.org/project/pdf2image/
    path_to_poppler_exe = Path(r"C:\\.")


# Path of the Input pdf
# PDF_file = Path(r"/home/marvin/Dokumente/Temp/pedestriancrowds/Bottleneck_Dienstag_1_10.pdf")
# PDF_file = Path(r"/home/marvin/Dokumente/Temp/pedestriancrowds/Berührung_Seil_Samstag_01.pdf")


def convert_pages(path_in: str, path_out: str):
    """Convert all pages from given pdf to jpeg images.

    The conversion is done with a resolution of 500 dpi.
    The resulting files are saved to the directory in 'path_out' with the name pattern
    page_NNN.jpg where NNN is the page number padded with zeroes, eG. "001".

    Args:
        path_in (str): Path to the PDF file to convert.
        path_out (str): Results will be saved to this directory. Will not be created.   
    """
    pdf_file = Path(path_in)
    if platform.system() == "Windows":
        pdf_pages = convert_from_path(pdf_file, 500, poppler_path=path_to_poppler_exe)
    else:
        pdf_pages = convert_from_path(pdf_file, 500)

    for page_enumeration, page in enumerate(pdf_pages, start=1):
        filename = os.path.join(path_out, f"page_{page_enumeration:03}.jpg")
        page.save(filename, "JPEG")


def ocr(path_in: str, lang:str="deu"):
    """Perform ocr for all files matching the pattern page_NNN.jpg in given directory.

    The results will be saved as page_NNN.txt in the same directory.

    Args:
        path_in (str): Directory with the images to read
        lang (str): language code of the text language 
                    https://tesseract-ocr.github.io/tessdoc/Data-Files-in-different-versions.html
    """
    for fp in glob.glob(path_in + "/page_[0-9][0-9][0-9].jpg"):
        if os.path.isfile(fp):
            with open(os.path.splitext(fp)[0] + ".txt", mode="x") as output_file:
                text = str(pytesseract.image_to_string(Image.open(fp), lang=lang))
                output_file.write(text)


def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF to images with optional Optical Character Recocnition"
    )
    parser.add_argument("path_in", type=str, help="Path of the PDF to convert")
    parser.add_argument("path_out", type=str, help="Path to output directory")
    parser.add_argument("-ocr", action="store_true", help="Perform OCR")

    args = parser.parse_args()
    convert_pages(args.path_in, args.path_out)
    if args.ocr:
        ocr(args.path_out)


if __name__ == "__main__":
    main()
