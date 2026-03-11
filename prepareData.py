"""This script prepares data for annotation and verification in the GUI. 

Expected input: File directory with PDFs. Each PDFs has several surveys of the same type appended after each other.
Output:
    mainFolder
    |-<date>_<experiment>
    |   |-metadata.json
    |   |-originalData.pdf
    |   |-surveyResponse_<nr>
    |   |   |-page0
    |   |   |-page1
    |   |   |-...
    |   |   |-data.csv    <-- parsed experiment proband data in here
    |   |
    |   |-surveyResponse_<nr>
    |   |   |...
    |   |...
    
Copyright: Marvin Lorber, Alexandra Mielke 2026
License: MIT
"""

#----- pip imports
import argparse
import json
import os.path
from pathlib import Path
import platform
import warnings

from pdf2image import convert_from_path

if platform.system() == "Windows":
    # We may need to do some additional downloading and setup...
    # Windows also needs poppler_exe
    path_to_poppler_exe = Path(r"C:\\.....")

#----- project includes
from src.survey_templates import GrabExperiment, ExperimentTypes
from src import area_grabbing
    
class pdfConverter():    
    def __init__(self, mainDir, metadataFile):
        self.mainDir = mainDir
        self.tempDir = os.path.join(self.mainDir, "temp")
        self.metadataFile = metadataFile

        self.imgType = "jpg"

        #check for metadata, if not there create default file
        if not self._readMetadata():
            self.metadata = {
                "Experiment": {
                    "Type": "unknown",
                    "Name": ""
                },
                "Description": "",
                "Date": "",
                "Comment": ""
            }
            self._saveMetadata()

    def _readMetadata(self) -> bool:
        if os.path.isfile(self.metadataFile):
            with open(self.metadataFile, "r") as f:
                self.metadata = json.load(f)
            return True
        else:
            return False

    def _saveMetadata(self):
        with open(self.metadataFile, "w") as f:
            json.dump(self.metadata, f, indent=4)

    def _page_name_generator(self):
        while True:
            yield "page" #return value, but continue

    def convert_pages(self, path_to_pdf:str):
        if os.path.isdir(self.tempDir):
            print("Found /temp. Assuming PDF(s) already converted.")
            return 
        os.mkdir(self.tempDir)
        print(f"Converting {path_to_pdf} to images ... ")
        pdf_file = Path(path_to_pdf)
        if platform.system() == "Windows":
            convert_from_path(pdf_file, fmt=self.imgType, dpi=500, 
                                          output_folder=self.tempDir, paths_only=True,
                                          output_file=self._page_name_generator(),
                                          poppler_path=path_to_poppler_exe)
        else:
            convert_from_path(pdf_file, fmt=self.imgType, dpi=500, 
                                          output_file=self._page_name_generator(),
                                          output_folder=self.tempDir, paths_only=True) # Read in the PDF file at 500 DPI

    def sort_pages(self):
        #load metadata again, in case user changed something in conversion time
        self._readMetadata()
        #if not given in metadata, check first page and determine type
        experimentType = self.metadata["Experiment"]["Type"]
        if experimentType not in ExperimentTypes:
            RuntimeError(f"Unknown experiment type {experimentType}. Trying to determine type from data ...")
            #TODO determine type with data

        #Type should be known now, start parsing
        typeTemplate = GrabExperiment.initType(experimentType)
        
        #loop through image files and resort them
        surveyResponses = {}
        nr_pages = typeTemplate.get_num_pages()
        surveyPage = 0
        participantNr = 0
        currDir = ""
        files = []
        for nr in range(0, len(os.listdir(self.tempDir)), 1):
            if surveyPage == 0:
                participantNr += 1 #start at one
                currDir = os.path.join(self.mainDir, f"surveyResponse_{participantNr:03}")
                if not os.path.isdir(currDir):
                    os.mkdir(currDir)

            pathToFile = os.path.join(self.tempDir, f"page-{(nr+1):03}." + self.imgType) #pdf2image starts with page 1
            if os.path.isfile(pathToFile):
                pageName = f"page-{(surveyPage+1):03}." + self.imgType
                os.rename(pathToFile, os.path.join(currDir, pageName))
                files.append(pageName)
            else:
                raise RuntimeError(f"Could not find {pathToFile}. Recheck if expected file names are correct!")

            surveyPage += 1
            if surveyPage >= nr_pages:
                dataFileName = area_grabbing.parse_single_data(currDir, files, typeTemplate)
                surveyResponses[f"surveyResponse_{participantNr:03}"] = {
                    "status": "Open",
                    "dir": currDir,
                    "dataFile": dataFileName
                }
                surveyPage = 0
                files = []

        self.metadata["participants"] = participantNr
        self.metadata["surveyResponses"] = surveyResponses

        # We're done, update metadata
        self._saveMetadata()

        #and delete temp folder
        for file in os.listdir(self.tempDir):
            os.remove(file)
        os.rmdir(self.tempDir)

def main():
    """parser = argparse.ArgumentParser(description="Convert PDF to images with optional Optical Character Recognition")
    parser.add_argument("expDir", type=str, help="Path of the experiment folder to which data is transferred")
    parser.add_argument("dataIn", type=str, help="Path of the PDF to convert", default="")
    args = parser.parse_args()
    
    expDir = args.expDir
    dataInput = args.dataIn
    """

    expDir = "data/2026-01-01_Bottleneck"
    dataInput = ""

    #search for pdfs
    if dataInput == "":
        pdfFile = ""
        metadataFile = ""
        for file in os.listdir(expDir):
            # We're expecting a single pdf and in the best case some metadata
            # If there are several pdf in the dir, this just uses the last it finds
            if file.endswith(".pdf"):
                pdfFile = os.path.join(expDir, file)
            if file.endswith(".json"):
                metadataFile = file
    else:
        pdfFile = dataInput
        metadataFile = "" #Just assume there is none

    if pdfFile == "":
        raise RuntimeError(f"Could not find pdf file in {expDir}.")
    if metadataFile == "":
        metadataFile = "metadata.json"
        warnings.warn(f"Could not find metadata file. Creating new file. Please add experiment description to {metadataFile}")

    converter = pdfConverter(mainDir=expDir, metadataFile=os.path.join(expDir, metadataFile))
    converter.convert_pages(pdfFile)
    converter.sort_pages()

if __name__ == "__main__":
    main()