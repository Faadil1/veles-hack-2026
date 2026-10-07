"""Keep only the official template slides (title + GitHub repo + Summary + Highlights) for the TAIKAI PDF.

Usage: python make_submission_deck.py Hyperion-Steward-VelesHack.pptx Hyperion-Steward-Submission.pptx
then convert to PDF with LibreOffice (soffice --headless --convert-to pdf).
"""
import sys

from pptx import Presentation

src, dst = sys.argv[1], sys.argv[2]
prs = Presentation(src)
ids = prs.slides._sldIdLst
for sid in list(ids)[4:]:
    prs.part.drop_rel(sid.rId)
    ids.remove(sid)
prs.save(dst)
