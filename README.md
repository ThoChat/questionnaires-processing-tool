# Annotation GUI for LoStInCrowds

This project was created to digitize the data from scanned paper surveys. It contains two steps, preparation and annotation.
In the preparation step simple data points like check boxes are automatically evaluated and the data structure gets created.
The annotation step then provides a GUI with side by side view for manual review, correction, and completion of the survey data.

## Installation
The project is set up to be managed with uv (https://docs.astral.sh/uv/) and you can install the dependencies with `uv sync`.
It is also possible to set up without uv by manually installing the dependencies listed in `pyproject.toml`.

On Windows some additional setup is necessary to satisfy all dependencies. Please refer to the installation guides for https://pypi.org/project/pdf2image/ and https://pypi.org/project/pytesseract/#installation.

## How to run

The project has two main python scripts. One to prepare data for the GUI and the other is the annotation GUI itself.

### Prepare data for GUI

Run [prepareData](/prepareData.py) to convert the survey PDF into images, create metadata files and extract survey data. This extraction is needed to parse the data into a format suitable for the GUI. 

The script requires at least the experiment's directory. It expects a single PDF file in this directory and, optionally, a json metadata file. Should there be several PDF in the folder, than only the last found PDF is converted. Please be aware that big PDF will need quite some time to be parsed. If the number of pages of the PDF is not a multiple of the number of pages of a survey, a warning is printed: pages are missing in the scan and the surveys after them are shifted. The incomplete last survey is still created, with status `Needs checking` and a comment. If there was no metadata.json when first parsing data, this file will be created. Currently there is no automatic detection of the experiment type, so you have to add this information into `metadata.json`. You should have enough time to do this when the PDF are parsed. Otherwise you'll run into a run time error, but don't worry, just add the info and run again. The images will be kept and you won't need to wait again.

```metadata.json
"Experiment": {
        "Type": "unknown", #<- define the actual experiment type here
        "Name": ""
    },
```

The experiment types are `bottleneck`, `rope` and `rope_short`. `rope_short` is for Rope sessions in which only the two contact pages of the Bottleneck form (pages 5 and 6) were used instead of the Rope form, e.g. Rope_Montag and Rope_Dienstag. A survey whose form differs from the rest of the experiment gets its own `"type"` in its entry of `surveyResponses` in `metadata.json`; the GUI then uses that template for it.

The current output folder structure after parsing is shown below. Changes are possible, but please remember to change the respective experiment directories listed in the experiment's `metadata.json` as well.

```
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
```

### GUI

The Gui is started from [annotateData](/annotateData.py). This is just a starter though, the GUI's main windows can be found in [guiWindows.py](/src/guiWindows.py) and the widgets shown within the Windows can be found in [guiWidgets.py](/src/guiWidgets.py).

The first entry of the question list is the **Participant number**, i.e. the number the participant wrote on the form. It is different from the `surveyResponse_<nr>` number and allows to identify the same participant across different forms. It is stored as `participantNr` in the survey's `surveyData.json` (`null` if not filled yet, as `0` is a valid participant number).

After `Done` or `Report weird things and go back`, the survey closes and the next survey that is still `Open` opens automatically. `Not done yet, but go back` only closes the survey. The survey list shows the participant number and the comment of each survey next to its name (hover over a long comment to see all of it), and a ⚠ warning if another survey of the experiment has the same participant number.

### Contact GUI

[annotateContacts](/annotateContacts.py) starts a simpler version of the GUI that only shows the participant number and the contact questions (body diagram and table), next to the top of the first page and the pages of the contact questions. It is started the same way, e.g. `python annotateContacts.py data/Bottleneck/Bottleneck_Dienstag_1`, and edits the same `surveyData.json`. Its progress is stored separately as `contactStatus` in `metadata.json`, so finishing the contacts does not change the `status` of the full survey. Surveys without a `contactStatus` show their full survey `status`, as the full GUI covers the contacts too.

### Optical character recognition

To detect single lines of printed writing, use `ocr()` in [ocr.py](/src/ocr.py). For detection of handwriting try out `recognize_handwriting()` in [htr.py](/src/htr.py). `htr.py` requires additional pip libraries that are currently commented out in the pyproject.toml

## License

The entire code is currently under MIT License. Make sure, that when you include code from Stack Overflow or similar sides to check the license (usually CC-BY-ND and therefore not compatible with MIT). 
If you add on to the code and are fine with MIT, just add your copyright notice on top of ours in the [license file](/LICENSE.md) and indicate the new authors on the sides you changed. 

## FAQ

**I clicked "Done" by accident**

Although this cannot be reversed within the GUI, you can search for the specific survey in the metadata.json file of the experiment and change the status back to "Open". 

**How do I change a comment?**

A comment can be changed within the GUI by going back to the specific survey and going to `Report weird things and go back` again. Here the old comment should show. Deleting it and clicking `Done` should save the empty comment. 
Alternatively you could go to the specific survey's data.json (surveyData.json) and delete the comment there.

## Ideas / Questions

- Status currently only in overview metadata of experiment. Could be copied into surveyData.json if wanted. Not suitable to only keep it there though, as sorting all surveyData.json files is much slower than just sorting the single metadata.json.
- Currently GUI only handles a single experiment. There could be another mainWindow which then opens into the current Main Window and shows either "Open" or "Done" status, depending on what is left (e.g, if nr_open_survey >1 ? Open : Done). How to handle "Needs checking" then?
- Currently the user/data curator has to add the experiment type. This could be detected automatically by reading the first/second/... question (potentially with ocr?)