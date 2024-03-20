import time
from pathlib import Path

PACKAGE_DIR = Path(__file__).absolute().parent
ROOT_DIR = PACKAGE_DIR.parent
SCRIPTS_DIR = ROOT_DIR / "scripts"

_this_year = time.strftime("%Y")
__version__ = "0.1"
__author__ = "Maurice Günder"
__author_email__ = "mauriceguender@yahoo.de"
__license__ = ""
__copyright__ = f"Copyright (c) 2024-{_this_year}, {__author__}."
__homepage__ = ""
__docs__ = "Extraction von Markierungen und Annotationen aus vektorisierten Bauplänen."
