"""Draw configured sensor coords onto the Aruba crop for visual calibration."""
from PIL import Image, ImageDraw, ImageFont
import re

# Parse sensor coords from the TS file
text = open(r"D:\AmbiLiving\src\data\homes\arubaSensors.ts", encoding="utf-8").read()
pattern = re.compile(
    r'id:\s*"(?P<id>[^"]+)".*?x:\s*(?P<x>[\d.]+).*?y:\s*(?P<y>[\d.]+)',
    re.S,
)
# Simpler line-based parse
sensors = []
for block in text.split("{")[1:]:
    if "id:" not in block:
        continue
    mid = re.search(r'id:\s*"([^"]+)"', block)
    mx = re.search(r"x:\s*([\d.]+)", block)
    my = re.search(r"y:\s*([\d.]+)", block)
    if mid and mx and my:
        sensors.append((mid.group(1), float(mx.group(1)), float(my.group(1))))

im = Image.open(r"D:\AmbiLiving\public\floorplans\aruba-crop-920.png").convert("RGBA")
overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)

for sid, x, y in sensors:
    color = (220, 40, 40, 220) if sid.startswith("M") else (30, 120, 200, 220) if sid.startswith("T") else (40, 160, 80, 220)
    r = 8 if sid in {"M007", "M019", "M020", "M024", "M027"} else 5
    draw.ellipse([x - r, y - r, x + r, y + r], outline=color, width=2)
    draw.text((x + 6, y - 10), sid, fill=color)

out = Image.alpha_composite(im, overlay)
out.save(r"D:\AmbiLiving\public\floorplans\aruba-sensor-calibration.png")
print(f"wrote {len(sensors)} sensors")
