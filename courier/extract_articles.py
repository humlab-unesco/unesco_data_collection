# %%

import glob
import io
import os
import sys
from typing import List
import re

import ftfy
import pandas as pd
import untangle
from jinja2 import Environment, PackageLoader, select_autoescape

sys.path.insert(0, "~/source/inidun/unesco_data_collection/")

from courier.elements import CourierIssue
from courier.courier_metadata import create_article_index

#pd.set_option("display.max_columns", None)
#pd.set_option("max_colwidth", None)
#pd.set_option("max_rows", 10)

#%%
jinja_env = Environment(
    loader=PackageLoader('courier', 'templates'),
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True,
    lstrip_blocks=True,
)

# %%

# ftfy.fix_text(text, *, fix_entities='auto', remove_terminal_escapes=True, fix_encoding=True, fix_latin_ligatures=True, fix_character_width=True, uncurl_quotes=True, fix_line_breaks=True, fix_surrogates=True, remove_control_chars=True, remove_bom=True, normalization='NFC', max_decode_length=1000000)

#remove_re = re.compile(u'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F%s]')
# FIXME: Fix illegal chars
def read_xml(filename: str) -> untangle.Element:
    with open(filename, "r") as fp:
        content = fp.read()
        # content, _ = remove_re.subn('', content)
        content = ftfy.fixes.remove_terminal_escapes(content)
        content = ftfy.fixes.remove_control_chars(content)
        xml = io.StringIO(content)
        element = untangle.parse(xml)
        return element



# TODO: add template as argument
def extract_articles_from_issue(courier_issue: CourierIssue):

    template = jinja_env.get_template('article.xml.jinja')

    list_of_articles = []

    for article in courier_issue.articles:
        #print(f"Processing {article.record_number}")
        article_text = template.render(article=article)
        list_of_articles.append(article_text)
    
    return list_of_articles

def extract_articles(folder: str, index: pd.DataFrame) -> None:

    missing = set()

    for issue in index["courier_id"].unique():  # FIXME: remove head

        filename_pattern = os.path.join(folder, f"{issue}eng*.xml")
        filename = glob.glob(filename_pattern)

        if len(filename) == 0:
            missing.add(issue)
            print(f"no match for {issue}")
            continue

        if len(filename) > 1:
            print(f"Duplicate matches for: {issue}")
            continue

        try:
            extract_articles_from_issue(CourierIssue(index.loc[index["courier_id"] == issue], read_xml(filename[0])))
        except Exception as e:
            print(filename[0], e)


        # extract_articles_from_issue(filename, index.loc[index["courier_id"] == issue])
        # TODO: Check pages for possible mismatch
        # TODO: Check overlapping pages

    print("Missing courier_ids: ", *missing)


# %%
article_index = create_article_index("UNESCO_Courier_metadata.csv")

# %%
extract_articles("../data/courier/xml", article_index)
# next(article_index.iterrows())[1]

# %%

# %%

# %%
if __name__ == '__main__':
    pass
