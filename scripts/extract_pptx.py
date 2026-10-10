"""Extract text from AmbiLiving defense PPTX slides."""
import zipfile
import re
from xml.etree import ElementTree as ET
from pathlib import Path

pptx = Path(r"c:\Users\hudiyahaha\Downloads\AmbiLiving_Defense_Repaired.pptx")
ns = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}

with zipfile.ZipFile(pptx) as z:
    slides = sorted(
        [n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)],
        key=lambda n: int(re.search(r"slide(\d+)", n).group(1)),
    )
    out_lines = []
    for name in slides:
        num = re.search(r"slide(\d+)", name).group(1)
        root = ET.fromstring(z.read(name))
        texts = []
        for t in root.findall(".//a:t", ns):
            if t.text and t.text.strip():
                texts.append(t.text.strip())
        # de-dupe consecutive repeats
        cleaned = []
        for t in texts:
            if not cleaned or cleaned[-1] != t:
                cleaned.append(t)
        out_lines.append(f"\n===== SLIDE {num} =====")
        out_lines.append("\n".join(cleaned))

Path(r"D:\AmbiLiving\scripts\slides_extract.txt").write_text(
    "\n".join(out_lines), encoding="utf-8"
)
print(f"wrote {len(slides)} slides")
