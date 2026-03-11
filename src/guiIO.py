import json
import os

__license__ = "MIT"
__author__ = "Alexandra Mielke"

# ---------------------------
# Json handling
# ---------------------------


def readData(path_to_file: str):
    # currently storage in json format
    if os.path.isfile(path_to_file):
        with open(path_to_file, "r") as f:
            data = json.load(f)
        return data
    else:
        return {}


def saveData(path_to_file: str, jsonDict):
    # currently storage in json format
    with open(path_to_file, "w") as f:
        json.dump(jsonDict, f, indent=4)
