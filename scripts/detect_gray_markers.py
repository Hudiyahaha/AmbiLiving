"""Detect gray+black circular markers on Aruba crop."""
from PIL import Image, ImageDraw
import math

im = Image.open(r"D:\AmbiLiving\public\floorplans\aruba-crop-920.png").convert("RGB")
w, h = im.size
px = im.load()

# Gray/black ink for markers (not thin wall lines alone)
def is_marker_pixel(p):
    r, g, b = p
    # near-gray dark
    if abs(r - g) > 25 or abs(g - b) > 25:
        return False
    return r < 140


mask = [[is_marker_pixel(px[x, y]) for x in range(w)] for y in range(h)]
visited = [[False] * w for _ in range(h)]
blobs = []

for y in range(h):
    for x in range(w):
        if not mask[y][x] or visited[y][x]:
            continue
        stack = [(x, y)]
        visited[y][x] = True
        cells = []
        while stack:
            cx, cy = stack.pop()
            cells.append((cx, cy))
            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if 0 <= nx < w and 0 <= ny < h and mask[ny][nx] and not visited[ny][nx]:
                    visited[ny][nx] = True
                    stack.append((nx, ny))
        n = len(cells)
        if n < 12 or n > 800:
            continue
        xs = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        bw, bh = maxx - minx + 1, maxy - miny + 1
        aspect = bw / max(bh, 1)
        cx = sum(xs) / n
        cy = sum(ys) / n
        r = math.sqrt(n / math.pi)
        if bw > 45 or bh > 45:
            continue
        if 0.4 <= aspect <= 3.2:
            kind = "rect" if aspect >= 1.65 and bh <= 14 else ("large" if r >= 7.5 else "small")
            blobs.append(
                {
                    "x": round(cx, 1),
                    "y": round(cy, 1),
                    "r": round(r, 1),
                    "kind": kind,
                    "w": bw,
                    "h": bh,
                    "n": n,
                }
            )

# Filter out blobs too close to right edge (legend bleed) and tiny text crumbs
blobs = [b for b in blobs if b["x"] < 880 and b["y"] > 10]
blobs.sort(key=lambda b: (b["y"], b["x"]))
print(f"blobs={len(blobs)}")
for b in blobs:
    print(f"{b['kind']:5} x={b['x']:6.1f} y={b['y']:6.1f} r={b['r']:4.1f}")

# draw
base = im.convert("RGBA")
ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
dr = ImageDraw.Draw(ov)
for i, b in enumerate(blobs):
    col = (255, 0, 0, 200) if b["kind"] == "large" else (0, 100, 255, 200) if b["kind"] == "rect" else (0, 180, 0, 200)
    rr = max(4, int(b["r"]))
    dr.ellipse([b["x"] - rr, b["y"] - rr, b["x"] + rr, b["y"] + rr], outline=col, width=2)
    dr.text((b["x"] + 6, b["y"] - 8), str(i), fill=col)
Image.alpha_composite(base, ov).save(
    r"D:\AmbiLiving\public\floorplans\aruba-detected-markers.png"
)
print("saved aruba-detected-markers.png")
