import fitz
import numpy as np
import pandas as pd
from tqdm.auto import tqdm

pdf_path = "documents/SKD_1_C1_5_H_HFI_DB_00_0907_10_V Durchbruchsplanung EG - C1.pdf"
# pdf_path = "/mnt/c/Users/Maurice/Downloads/SKD_1_C1_5_H_HFI_DB_U1_9907_10_V Durchbruchsplanung UG - C1.pdf"

color_dict = {
    (0.5019609928131104, 0.5019609928131104, 0.5019609928131104): "gray",
    (0.0, 1.0, 0.0): "lime",
    (0.0, 0.0, 0.0): "black",
    (0.0, 0.0, 1.0): "blue",
    (1.0, 0.0, 0.0): "red",
    (0.0, 0.6000000238418579, 0.0): "green",
    (0.0, 1.0, 1.0): "cyan",
    (1.0, 0.0, 1.0): "magenta",
    (1.0, 0.4000000059604645, 0.0): "orange",
    (0.6000000238418579, 0.0, 0.0): "darkred",
    (1.0, 1.0, 0.0): "yellow",
    None: np.nan,
}
linewidth = 0.36850398778915405


def extract_boxes_and_text_from_pdf(path):
    textboxes = []
    coords = []
    doc = fitz.open(path)
    for page_num in tqdm(range(len(doc)), desc="parse pages", leave=False):
        page = doc.load_page(page_num)
        words = page.get_text("words", sort=True)
        drawings = pd.DataFrame(page.get_drawings(extended=False))
        drawings.color = drawings.color.apply(lambda x: color_dict[x])
        white_fill = drawings.fill == (1, 1, 1)
        is_curve = drawings["items"].apply(lambda x: x[0][0] == "c")
        # is_line = drawings["items"].apply(lambda x: x[0][0] == "l")
        # has_right_linewidth = drawings["width"] == linewidth
        # is_rect = drawings["items"].apply(lambda x: x[0][0] == "re")
        is_black = drawings.color == "black"
        # not_gray = drawings.color != "gray"
        # has_color = drawings.color.notna()
        boxes = drawings[white_fill & (~is_black)]
        # lines = drawings[is_line & has_right_linewidth & (~is_black) & not_gray & (has_color)]
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
                if coord_sign.rect.contains(fitz.Rect(*word[:4])):
                    text_in_box.append(word[4])
            # Append rectangle coordinates and text to the list
            if len(text_in_box) > 0:
                text = " ".join(text_in_box)
                coord_name = text.split(".")[0]
                if coord_name.isdecimal():
                    ctype = "x"
                    coord_pos = (coord_sign.rect.tl.x + coord_sign.rect.tr.x) / 2
                elif coord_name.isalpha():
                    ctype = "y"
                    coord_pos = (coord_sign.rect.tl.y + coord_sign.rect.bl.y) / 2
                coords.append({"page": page_num + 1, "coord_pos": coord_pos, "coord_name": coord_name, "type": ctype})
        textboxes = pd.DataFrame(textboxes)
        coords = pd.DataFrame(coords).sort_values(by="coord_name").drop_duplicates(ignore_index=True)
    doc.close()
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
                    colors.append(dr_row.color)
                else:
                    break
        if len(endpoints) == 0:
            endpoints = [fitz.Point((tbox_row.rect.x0 + tbox_row.rect.x1) / 2.0, (tbox_row.rect.y0 + tbox_row.rect.y1) / 2.0)]

        textboxes.at[row_ind, "endpoints"] = endpoints
        textboxes.at[row_ind, "colors"] = colors

    return textboxes, coords


tbox, coord = extract_boxes_and_text_from_pdf(pdf_path)
