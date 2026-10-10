"""Overlay a coordinate grid on the Aruba crop for manual tracing."""
from PIL import Image, ImageDraw, ImageFont

im = Image.open(r"D:\AmbiLiving\public\floorplans\aruba-crop-920.png").convert("RGBA")
w, h = im.size
overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)

for x in range(0, w, 50):
    draw.line([(x, 0), (x, h)], fill=(255, 0, 0, 70), width=1)
for y in range(0, h, 50):
    draw.line([(0, y), (w, y)], fill=(255, 0, 0, 70), width=1)
for x in range(0, w, 100):
    draw.line([(x, 0), (x, h)], fill=(255, 0, 0, 140), width=1)
    draw.text((x + 2, 2), str(x), fill=(200, 0, 0, 220))
for y in range(0, h, 100):
    draw.line([(0, y), (w, y)], fill=(255, 0, 0, 140), width=1)
    draw.text((2, y + 2), str(y), fill=(200, 0, 0, 220))

out = Image.alpha_composite(im, overlay)
out.save(r"D:\AmbiLiving\public\floorplans\aruba-grid.png")
print(w, h, "saved grid")
