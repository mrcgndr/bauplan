#! .venv/bin/python
"""
    Extraktion von Markierungen und zugehörigen Annotationen aus vektorisierten Bauplänen.
    Die Ergebnisse werden als Excelsheet gespeichert.
"""
import argparse
from pathlib import Path

import pandas as pd
from tqdm.auto import tqdm

from bauplan.extract import extract_annotations, extract_textboxes_and_quadrants

parser = argparse.ArgumentParser(
    description="Runs the Bodypart Explainer with given config files.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument("-i", "--input_dir", type=str, help="Pfad zum Ordner mit Bauplänen.", required=True)
parser.add_argument("-o", "--output", type=str, help="Pfad ", required=True)

args = parser.parse_args()
dirpath = Path(args.input_dir)
outpath = Path(args.output)

pdfpaths = list(dirpath.rglob("*.pdf"))

all_annotations = []
pbar = tqdm(pdfpaths, total=len(pdfpaths))
for pdfpath in pbar:
    pbar.set_description_str(f"analyze PDFs - {pdfpath.relative_to(dirpath)}")
    try:
        tboxes, quads = extract_textboxes_and_quadrants(pdfpath)
        annotations = extract_annotations(tboxes, quads)
        annotations.insert(0, "file", pdfpath.relative_to(dirpath))
        all_annotations.append(annotations)
    except Exception as e:
        raise Warning(f"File {pdfpath} could not be analyzed. Error: {e}")

all_annotations = pd.concat(all_annotations, ignore_index=True)

print(f"Save to {outpath}")
all_annotations.to_excel(outpath, index=False)
