"""Generate icon.ico for Claude Meter."""
import os
from PIL import Image, ImageDraw, ImageFont

sizes = [16, 24, 32, 48, 64, 128, 256]
images = []

for s in sizes:
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([1, 1, s - 1, s - 1], fill=(217, 119, 87))
    try:
        font = ImageFont.truetype("arial.ttf", int(s * 0.55))
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "C", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((s - tw) // 2, (s - th) // 2 - 1), "C", fill="white", font=font)
    images.append(img)

# Save next to this script
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
images[0].save(out, format="ICO", sizes=[(s, s) for s in sizes], append_images=images[1:])
print(f"Created {out}")
