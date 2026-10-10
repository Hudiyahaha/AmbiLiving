"""Detect filled circular markers (sensors) on Aruba crop."""
from PIL import Image
import math

im = Image.open(r"D:\AmbiLiving\public\floorplans\aruba-crop-920.png").convert("L")
w, h = im.size
px = im.load()

# Strict dark threshold for filled markers
dark = [[px[x, y] < 60 for x in range(w)] for y in range(h)]
visited = [[False] * w for _ in range(h)]
blobs = []

for y in range(h):
    for x in range(w):
        if not dark[y][x] or visited[y][x]:
            continue
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
        n = len(cells)
        if n < 20 or n > 700:
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
        # Prefer compact blobs (circles / short temp bars)
        if 0.45 <= aspect <= 2.8 and 4 <= bw <= 40 and 3 <= bh <= 40:
            kind = "rect" if aspect >= 1.7 and bh <= 12 else ("large" if r >= 7 else "small")
            blobs.append((round(cx, 1), round(cy, 1), round(r, 1), kind, bw, bh, n))

blobs.sort(key=lambda b: (b[1], b[0]))
print(f"{w}x{h} blobs={len(blobs)}")
for b in blobs:
    print(f"{b[3]:5} x={b[0]:6.1f} y={b[1]:6.1f} r={b[2]:4.1f} {b[4]}x{b[5]} n={b[6]}")
