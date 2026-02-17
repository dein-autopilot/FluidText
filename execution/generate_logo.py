"""Generate FluidText logo, icons, and sound assets programmatically."""
import os
import wave
import struct
import math
from PIL import Image, ImageDraw, ImageFilter

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

# New Palette based on screenshot
BG_CIRCLE_COLOR = (40, 40, 40)   # Dark Grey #282828
BORDER_COLOR = (60, 60, 60)      # Slightly lighter border
BAR_TOP_COLOR = (130, 200, 255)  # Light Blue #82c8ff
BAR_BOT_COLOR = (140, 190, 140)  # Sage Green #8cbe8c

def create_gradient_fill(width, height, top_color, bot_color):
    """Create a vertical gradient image."""
    base = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    top_r, top_g, top_b = top_color
    bot_r, bot_g, bot_b = bot_color
    
    pixels = base.load()
    for y in range(height):
        # Interpolate
        t = y / max(1, height - 1)
        r = int(top_r + (bot_r - top_r) * t)
        g = int(top_g + (bot_g - top_g) * t)
        b = int(top_b + (bot_b - top_b) * t)
        for x in range(width):
            pixels[x, y] = (r, g, b, 255)
    return base

def generate_logo(size=512):
    """Generate the new FluidText logo."""
    # 1. Base Canvas
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    cx, cy = size // 2, size // 2
    
    # 2. Draw Background Circle
    # Radius
    r = int(size * 0.48)
    # Border
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BG_CIRCLE_COLOR, outline=BORDER_COLOR, width=int(size*0.02))
    
    # 3. Draw Waveform Mask
    # We will create a mask image for the bars, then composite the gradient onto it.
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    
    num_bars = 5 
    # Heights relative to radius (approx from image)
    # Center is tallest, edges shorter
    bar_heights = [0.25, 0.45, 0.65, 0.45, 0.25] 
    
    # Widths
    total_w = size * 0.4
    bar_w = int(total_w / num_bars * 0.6) # space between
    gap = int(total_w / num_bars * 0.4)
    
    start_x = cx - (num_bars * bar_w + (num_bars - 1) * gap) / 2
    
    for i in range(num_bars):
        h_factor = bar_heights[i]
        bar_h = int(size * h_factor)
        
        bx = start_x + i * (bar_w + gap)
        by_top = cy - bar_h // 2
        by_bot = cy + bar_h // 2
        
        # Draw rounded bar on mask
        corner_r = bar_w // 2
        
        # Rectangle part
        mask_draw.rectangle([bx, by_top + corner_r, bx + bar_w, by_bot - corner_r], fill=255)
        # Caps
        mask_draw.ellipse([bx, by_top, bx + bar_w, by_top + bar_w], fill=255)
        mask_draw.ellipse([bx, by_bot - bar_w, bx + bar_w, by_bot], fill=255)
        
    # 4. Create Gradient Source
    gradient = create_gradient_fill(size, size, BAR_TOP_COLOR, BAR_BOT_COLOR)
    
    # 5. Composite
    # Paste gradient using mask
    img.paste(gradient, (0, 0), mask)
    
    return img

def generate_logo_small(size=64):
    """Generate a small version for tray icon."""
    logo = generate_logo(512)
    return logo.resize((size, size), Image.Resampling.LANCZOS)

def generate_sound():
    print("Skipping sound generation (already done).")

if __name__ == "__main__":
    print("Generating new logo assets...")
    logo = generate_logo(512)
    logo.save(os.path.join(ASSETS_DIR, "logo.png"))
    
    logo_256 = generate_logo(256)
    logo_256.save(os.path.join(ASSETS_DIR, "logo_256.png"))
    
    tray = generate_logo_small(64)
    tray.save(os.path.join(ASSETS_DIR, "tray_icon.png"))
    
    # Generate Window Icon (ICO)
    icon = generate_logo(256)
    icon.save(os.path.join(ASSETS_DIR, "icon.ico"), format="ICO", sizes=[(16,16), (32,32), (64,64), (128,128), (256,256)])
    
    print(f"All assets saved to: {ASSETS_DIR}")
