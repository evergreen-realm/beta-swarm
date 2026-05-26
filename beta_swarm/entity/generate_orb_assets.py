import os
import math
import sys
from PIL import Image, ImageDraw, ImageFilter

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

def create_orb_frame(frame_idx, mode="idle"):
    size = (64, 64)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center = (32, 32)
    
    # Using 30 frames for a full loop
    if mode == "idle":
        progress = (math.sin(frame_idx * math.pi / 15) + 1) / 2
        radius = 12 + progress * 2
        glow_alpha = int(76 + progress * 128)
    elif mode == "wake":
        progress = frame_idx / 30
        radius = 14 + progress * 10
        glow_alpha = 200
    else: # active
        progress = (math.sin(frame_idx * math.pi / 7.5) + 1) / 2
        radius = 22 + progress * 2
        glow_alpha = 255

    for i in range(12, 0, -1):
        alpha = int(glow_alpha * (i / 12))
        r = radius + i
        draw.ellipse([center[0]-r, center[1]-r, center[0]+r, center[1]+r], fill=(0, 242, 255, alpha // 4))

    num_facets = 8
    rotation = frame_idx * (math.pi / 15 if mode == "active" else math.pi / 30)
    for i in range(num_facets):
        angle = rotation + (i * 2 * math.pi / num_facets)
        x = center[0] + math.cos(angle) * (radius - 5)
        y = center[1] + math.sin(angle) * (radius - 5)
        draw.regular_polygon((x, y, 4), 3, rotation=angle, fill=(224, 240, 255, 180))

    draw.ellipse([center[0]-radius+4, center[1]-radius+4, center[0]+radius-4, center[1]+radius-4], 
                 fill=(0, 119, 255, 100), outline=(0, 242, 255, 200))
    
    core_r = 5 + (progress * 2 if mode != "idle" else 0)
    draw.ellipse([center[0]-core_r, center[1]-core_r, center[0]+core_r, center[1]+core_r], 
                 fill=(255, 255, 255, glow_alpha))

    if mode == "wake" and frame_idx > 15:
        ring_r = radius + 8
        draw.arc([center[0]-ring_r, center[1]-ring_r, center[0]+ring_r, center[1]+ring_r], 
                 start=frame_idx*10, end=frame_idx*10+90, fill=(0, 242, 255, 255), width=2)

    return img.filter(ImageFilter.GaussianBlur(0.8))

def generate_all():
    print("Generating orb frames (Optimized)...")
    for mode in ["idle", "wake", "active"]:
        print(f"  Processing {mode} state...")
        for i in range(30):
            create_orb_frame(i, mode).save(os.path.join(ASSETS_DIR, f"orb_{mode}_{i}.png"))
            if i % 10 == 0:
                print(f"    {i}/30...")
    print("All frames generated successfully.")

if __name__ == "__main__":
    generate_all()
