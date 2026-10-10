"""Detect approximate sensor marker centers in Aruba floor-plan crop."""
from PIL import Image
import math

im = Image.open(r"D:\AmbiLiving\public\floorplans\aruba-crop-920.png").convert("L")
w, h = im.size
px = im.load()

# Threshold dark pixels
dark = [[px[x, y] < 90 for x in range(w)] for y in range(h)]

visited = [[False] * w for _ in range(h)]
blobs = []

for y in range(h):
    for x in range(w):
        if not dark[y][x] or visited[y][x]:
            continue
        # flood fill
        stack = [(x, y)]
        visited[y][x] = True
        cells = []
        while stack:
            cx, cy = stack.pop()
            cells.append((cx, cy))
            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if 0 <= nx < w and 0 <= ny < h and dark[ny][nx] and not visited[ny][nx]:
                    visited[ny][nx] = True
                    stack.append((nx, ny))
        if 8 <= len(cells) <= 900:
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            minx, maxx = min(xs), max(xs)
            miny, maxy = min(ys), max(ys)
            bw, bh = maxx - minx + 1, maxy - miny + 1
            aspect = bw / max(bh, 1)
            # circles-ish or short door segments / temp rects
            if aspect < 3.5 and bh < 40 and bw < 50:
                cx = sum(xs) / len(cells)
                cy = sum(ys) / len(cells)
                r = math.sqrt(len(cells) / math.pi)
                kind = "large" if r > 6.5 else "small" if r > 2.2 else "mark"
                if aspect > 1.8:
                    kind = "rect"
                blobs.append(
                    {
                        "x": round(cx, 1),
                        "y": round(cy, 1),
                        "r": round(r, 1),
                        "w": bw,
                        "h": bh,
                        "n": len(cells),
                        "kind": kind,
                    }
                )

blobs.sort(key=lambda b: (b["y"], b["x"]))
print(f"image {w}x{h}, blobs {len(blobs)}")
for b in blobs:
    print(f"{b['kind']:5} x={b['x']:6.1f} y={b['y']:6.1f} r={b['r']:4.1f} {b['w']}x{b['h']} n={b['n']}")
