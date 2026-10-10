"""Detect colored Milan sensors: red=motion, yellow=temp, green=door."""
from PIL import Image, ImageDraw
import math

im = Image.open(r"D:\AmbiLiving\public\floorplans\milan-reference.png").convert("RGB")
w, h = im.size
px = im.load()
print(f"size {w}x{h}")


def classify(p):
    r, g, b = p
    # red / pink-red motion markers
    if r > 160 and g < 120 and b < 120 and r > g + 40 and r > b + 40:
        return "motion"
    # yellow / amber temperature
    if r > 180 and g > 140 and b < 120 and r - b > 60:
        return "temp"
    # green door/contact
    if g > 140 and r < 140 and b < 140 and g > r + 30:
        return "door"
    return None


visited = [[False] * w for _ in range(h)]
blobs = []

for y in range(h):
    for x in range(w):
        if visited[y][x]:
            continue
        kind = classify(px[x, y])
        if not kind:
            continue
        stack = [(x, y)]
        visited[y][x] = True
        cells = []
        while stack:
            cx, cy = stack.pop()
            cells.append((cx, cy))
            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                    if classify(px[nx, ny]) == kind:
                        visited[ny][nx] = True
                        stack.append((nx, ny))
        n = len(cells)
        if n < 8 or n > 900:
            continue
        xs = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        bw, bh = maxx - minx + 1, maxy - miny + 1
        if bw > 50 or bh > 50:
            continue
        cx = sum(xs) / n
        cy = sum(ys) / n
        blobs.append(
            {
                "kind": kind,
                "x": round(cx, 1),
                "y": round(cy, 1),
                "w": bw,
                "h": bh,
                "n": n,
            }
        )

blobs.sort(key=lambda b: (b["y"], b["x"]))
print(f"blobs={len(blobs)}")
for i, b in enumerate(blobs):
    print(f"{i:02d} {b['kind']:6} x={b['x']:6.1f} y={b['y']:6.1f} {b['w']}x{b['h']} n={b['n']}")

# draw indexed overlay
base = im.convert("RGBA")
ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
dr = ImageDraw.Draw(ov)
for i, b in enumerate(blobs):
    col = {"motion": (255, 0, 0, 220), "temp": (220, 160, 0, 220), "door": (0, 160, 0, 220)}[
        b["kind"]
    ]
    rr = 8
    dr.ellipse([b["x"] - rr, b["y"] - rr, b["x"] + rr, b["y"] + rr], outline=col, width=2)
    dr.text((b["x"] + 8, b["y"] - 8), str(i), fill=col)
Image.alpha_composite(base, ov).save(
    r"D:\AmbiLiving\public\floorplans\milan-detected.png"
)
print("saved milan-detected.png")
