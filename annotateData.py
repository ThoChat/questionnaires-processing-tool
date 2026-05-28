import argparse
import src.guiWindows as gui

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Launch the annotation GUI for survey data")
    parser.add_argument("expDir", type=str, help="Directory containing the processed experiment data")
    args = parser.parse_args()

    gui.main(experimentDir=args.expDir)
