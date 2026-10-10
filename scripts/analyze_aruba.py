from PIL import Image

im = Image.open(r"D:\AmbiLiving\aruba.png").convert("RGBA")
w, h = im.size
px = im.load()


def is_ink(p):
    r, g, b, a = p
    return a > 200 and (r + g + b) < 720


minx, miny, maxx, maxy = w, h, 0, 0
for y in range(0, h, 2):
    for x in range(0, w, 2):
        if is_ink(px[x, y]):
            minx = min(minx, x)
            miny = min(miny, y)
            maxx = max(maxx, x)
            maxy = max(maxy, y)
print("content bbox", minx, miny, maxx, maxy)

col_ink = []
for x in range(w):
    c = 0
    for y in range(0, h, 3):
        if is_ink(px[x, y]):
            c += 1
    col_ink.append(c)

bands = []
for x in range(700, w - 20, 5):
    window = sum(col_ink[x : x + 15]) / 15
    bands.append((x, window))
print("sparse cols", sorted(bands, key=lambda t: t[1])[:12])

for x in range(980, 700, -1):
    if col_ink[x] > 8:
        print("likely house right ~", x)
        break

# Crop house portion (exclude legend). Try several candidates.
for right in (920, 960, 1000, 1040):
    house = im.crop((10, 10, right, 656))
    out = rf"D:\AmbiLiving\public\floorplans\aruba-crop-{right}.png"
    house.save(out)
    print("saved", out)
