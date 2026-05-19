#!/usr/bin/env python3
"""Generate the Sip app icon (1024x1024) — water drop on a blue gradient."""
from PIL import Image, ImageDraw, ImageFilter
import os, math

SIZE = 1024
OUT = os.path.join(os.path.dirname(__file__), "..", "Sip", "Assets.xcassets",
                   "AppIcon.appiconset", "icon-1024.png")

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def main():
    img = Image.new("RGB", (SIZE, SIZE), (10, 132, 255))
    px = img.load()
    top = (90, 200, 250)      # cyan
    bottom = (10, 80, 220)    # deep blue
    for y in range(SIZE):
        c = lerp(top, bottom, y / (SIZE - 1))
        for x in range(SIZE):
            px[x, y] = c

    # Soft highlight blob top-left
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-200, -200, 700, 700), fill=(255, 255, 255, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    img.paste(glow, (0, 0), glow)

    # Water drop shape — teardrop
    drop = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    dd = ImageDraw.Draw(drop)
    cx = SIZE // 2
    # bottom circle
    r = 230
    cy = 640
    dd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, 235))
    # triangle top (pointy)
    dd.polygon([(cx, 220), (cx - r + 30, cy), (cx + r - 30, cy)],
               fill=(255, 255, 255, 235))
    drop = drop.filter(ImageFilter.GaussianBlur(0.6))

    # Drop shadow
    shadow = drop.split()[-1].point(lambda a: int(a * 0.35))
    shadow_img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shadow_img.putalpha(shadow)
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(28))
    img.paste(shadow_img, (0, 24), shadow_img)

    # Drop itself
    img.paste(drop, (0, 0), drop)

    # Inner highlight on the drop
    hl = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.ellipse((cx - 110, 380, cx + 30, 540),
               fill=(255, 255, 255, 140))
    hl = hl.filter(ImageFilter.GaussianBlur(20))
    img.paste(hl, (0, 0), hl)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT}")

if __name__ == "__main__":
    main()
