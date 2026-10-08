import argparse
import src.guiWindows as gui
from src.guiContactWindows import ContactMainWindow

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Launch the annotation GUI for the participant number and the contacts only")
    parser.add_argument("expDir", type=str, help="Directory containing the processed experiment data")
    args = parser.parse_args()

    gui.main(experimentDir=args.expDir, windowClass=ContactMainWindow)
