from pathlib import Path
from typing import Tuple, Union

import fitz
import numpy as np
import pandas as pd
from tqdm.auto import tqdm

from .utils import color_dict, linewidth


def extract_textboxes_and_quadrants(pdf_path: Union[str, Path]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    textboxes = []
    coords = []
    doc = fitz.open(pdf_path)
    for page_num in tqdm(range(len(doc)), desc="parse pages", leave=False):
        page = doc.load_page(page_num)
        words = page.get_text("words", sort=True)
        drawings = pd.DataFrame(page.get_drawings(extended=False))
        drawings.color = drawings.color.apply(lambda x: color_dict[x])
        white_fill = drawings.fill == (1, 1, 1)
        is_curve = drawings["items"].apply(lambda x: x[0][0] == "c")
        is_black = drawings.color == "black"
        boxes = drawings[white_fill & (~is_black)]
        coord_signs = drawings[is_curve & is_black]
        for _, box in tqdm(boxes.iterrows(), desc="iterate possible textboxes", total=len(boxes)):
            # Find text contained within the rectangle
            text_in_box = []
            block_nos = []
            line_nos = []
            word_nos = []
            for word in words:
                if box.rect.contains(fitz.Rect(*word[:4])):
                    text_in_box.append(word[4])
                    block_nos.append(word[5])
                    line_nos.append(word[6])
                    word_nos.append(word[7])
            # Append rectangle coordinates and text to the list
            if len(text_in_box) > 0:
                text_array = np.asarray(text_in_box)
                if np.any(np.isin(text_array, ["DD", "WD"])):
                    block_ids = np.asarray(block_nos)
                    textmask = np.isin(block_ids, block_ids[np.isin(text_array, ["DD", "WD"])] + np.arange(2))
                    textboxes.append(
                        {
                            "page": page_num + 1,
                            "rect": box.rect,
                            "text": " ".join(text_array[textmask]),
                            "seqno": box.seqno,
                            "blocks": block_nos,
                            "lines": line_nos,
                            "words": word_nos,
                        }
                    )
        for _, coord_sign in tqdm(coord_signs.iterrows(), desc="iterate possible coordinate signs", total=len(coord_signs)):
            # Find text contained within the rectangle
            text_in_box = []
            for word in words:
                if coord_sign.rect.intersects(fitz.Rect(*word[:4])):
                    text_in_box.append(word[4])
            # Append rectangle coordinates and text to the list
            if len(text_in_box) > 0:
                text = " ".join(text_in_box)
                coord_name = text.split(".")[0]
                if coord_name.isnumeric():
                    ctype = "x"
                    coord_pos = (coord_sign.rect.tl.x + coord_sign.rect.tr.x) / 2
                elif coord_name.isalpha():
                    ctype = "y"
                    coord_pos = (coord_sign.rect.tl.y + coord_sign.rect.bl.y) / 2
                coords.append({"page": page_num + 1, "coord_pos": coord_pos, "coord_name": coord_name, "ctype": ctype})
    textboxes = pd.DataFrame(textboxes)
    coords = pd.DataFrame(coords).sort_values(by=["ctype", "coord_pos"]).drop_duplicates(ignore_index=True)
    doc.close()
    for page in coords.page.unique():
        quadrants = []
        x_coords = coords[(coords.page == page) & (coords.ctype == "x")]
        y_coords = coords[(coords.page == page) & (coords.ctype == "y")]
        for i_x in range(len(x_coords) - 1):
            for i_y in range(len(y_coords) - 1):
                x0, x1 = x_coords.iloc[i_x : i_x + 2].coord_pos.values
                y0, y1 = y_coords.iloc[i_y : i_y + 2].coord_pos.values
                quadrants.append(
                    {
                        "page": page,
                        "qname": f"{x_coords.coord_name.iloc[i_x]}-{x_coords.coord_name.iloc[i_x+1]} | {y_coords.coord_name.iloc[i_y]}-{y_coords.coord_name.iloc[i_y+1]}",
                        "rect": fitz.Rect(x0=x0, y0=y0, x1=x1, y1=y1),
                    }
                )
        quadrants = pd.DataFrame(quadrants)
    textboxes["endpoints"] = [[] for x in range(len(textboxes))]
    textboxes["colors"] = [[] for x in range(len(textboxes))]
    for row_ind, tbox_row in textboxes.iterrows():
        i = tbox_row.seqno
        endpoints = []
        colors = []
        while True:
            i -= 1
            dr_row = drawings[drawings.seqno == i]
            if not dr_row.empty:
                if np.isclose(dr_row.width.values[0], linewidth, atol=0.01):
                    endpoints.append(dr_row["items"].values[0][0][2])
                    colors.append(dr_row.color.values[0])
                else:
                    break
        if len(endpoints) == 0:
            endpoints = [fitz.Point((tbox_row.rect.x0 + tbox_row.rect.x1) / 2.0, (tbox_row.rect.y0 + tbox_row.rect.y1) / 2.0)]

        textboxes.at[row_ind, "endpoints"] = endpoints
        textboxes.at[row_ind, "colors"] = colors

    return textboxes, quadrants


def extract_annotations(textboxes_df: pd.DataFrame, quadrants_df: pd.DataFrame) -> pd.DataFrame:
    annotations = []
    for _, tbox in tqdm(textboxes_df.iterrows(), desc="extract annotations", total=len(textboxes_df)):
        for point, color in zip(tbox.endpoints, tbox.colors):
            for _, quad in quadrants_df[quadrants_df.page == tbox.page].iterrows():
                if quad.rect.contains(point):
                    annotations.append(
                        {
                            "page": tbox.page,
                            "quadrant": quad.qname,
                            "text": tbox.text,
                            "type": color,
                            "coord_x": point.x,
                            "coord_y": point.y,
                        }
                    )

    return pd.DataFrame(annotations)
