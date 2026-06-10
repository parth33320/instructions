from PIL import Image, ImageDraw, ImageFont
import os

def generate_sample_label(filename="sample_label.png"):
    # Create a white background image
    width, height = 800, 1000
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Try to load a font, fallback to default
    try:
        # On some systems, this path might work or we can use a generic name
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw Brand Name
    draw.text((width//2, 100), "OLD TOM DISTILLERY", fill=(0, 0, 0), font=font_large, anchor="mm")

    # Draw Class/Type
    draw.text((width//2, 200), "Kentucky Straight Bourbon Whiskey", fill=(0, 0, 0), font=font_medium, anchor="mm")

    # Draw ABV
    draw.text((width//2, 300), "45% ALC./VOL. (90 PROOF)", fill=(0, 0, 0), font=font_medium, anchor="mm")

    # Draw Net Contents
    draw.text((width//2, 400), "750 mL", fill=(0, 0, 0), font=font_medium, anchor="mm")

    # Draw Government Warning
    warning_text = (
        "GOVERNMENT WARNING: (1) According to the Surgeon General, women "
        "should not drink alcoholic beverages during pregnancy because of the risk of "
        "birth defects. (2) Consumption of alcoholic beverages impairs your ability "
        "to drive a car or operate machinery, and may cause health problems."
    )

    # Wrap text for warning
    import textwrap
    lines = textwrap.wrap(warning_text, width=60)
    y_text = 600
    for line in lines:
        draw.text((50, y_text), line, fill=(0, 0, 0), font=font_small)
        y_text += 30

    image.save(filename)
    print(f"Sample label saved as {filename}")

if __name__ == "__main__":
    generate_sample_label()
