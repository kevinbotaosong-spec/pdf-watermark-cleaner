from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
iconset = root / "assets" / "AppIcon.iconset"
iconset.mkdir(parents=True, exist_ok=True)

base = Image.new("RGBA", (1024, 1024), (242, 247, 255, 255))
d = ImageDraw.Draw(base)
# Rounded blue tile
pad = 70
d.rounded_rectangle((pad, pad, 1024-pad, 1024-pad), radius=170, fill=(38, 126, 255, 255))
# White PDF sheet
sheet = (260, 190, 765, 835)
d.rounded_rectangle(sheet, radius=44, fill="white")
# Folded corner
fold = [(640,190),(765,315),(640,315)]
d.polygon(fold, fill=(205, 225, 255, 255))
# "PDF"
try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 120)
except Exception:
    font = ImageFont.load_default()
d.text((330, 380), "PDF", fill=(38,126,255,255), font=font)
# Sparkle / clean mark
cx, cy = 725, 710
for width in (24,):
    d.line((cx, cy-100, cx, cy+100), fill=(255,215,64,255), width=width)
    d.line((cx-100, cy, cx+100, cy), fill=(255,215,64,255), width=width)
    d.line((cx-70, cy-70, cx+70, cy+70), fill=(255,215,64,255), width=width)
    d.line((cx-70, cy+70, cx+70, cy-70), fill=(255,215,64,255), width=width)

sizes = [16,32,128,256,512]
for s in sizes:
    img = base.resize((s,s), Image.Resampling.LANCZOS)
    img.save(iconset / f"icon_{s}x{s}.png")
    img2 = base.resize((s*2,s*2), Image.Resampling.LANCZOS)
    img2.save(iconset / f"icon_{s}x{s}@2x.png")
base.save(root / "assets" / "AppIcon.png")
print(iconset)
