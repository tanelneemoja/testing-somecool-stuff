import requests
import os
import xml.etree.ElementTree as ET
from io import BytesIO
from PIL import Image, ImageOps, ImageDraw, ImageFont

# --- 1. CONFIGURATION ---

# 1.1. XML Feed Source
FEED_URL = "https://backend.ballzy.eu/et/amfeed/feed/download?id=102&file=cropink_et.xml"
OUTPUT_DIR = "generated_ads" 
MAX_PRODUCTS_TO_GENERATE = 3 # SET TO 3 FOR TESTING! Change to a higher number (e.g., 9999) for production.

# XML Namespaces (required for parsing Google Shopping/Meta Feed XML)
NAMESPACES = {
    'g': 'http://base.google.com/ns/1.0'
}

# 1.2. Figma Design Layout & Image Fitting
# Adjust W, H, X, Y based on your template design.
# Adjust 'center_y' (0.0=Top, 1.0=Bottom) to control the vertical crop for non-square slots.
LAYOUT_CONFIG = {
    "canvas_size": (1080, 1080), 
    "template_path": "assets/ballzy_template.png", 
    "slots": [
        # Slot 1: Square (Example: 500x500)
        {"x": 50, "y": 200, "w": 500, "h": 500, "center_y": 0.5}, 
        # Slot 2: Semi-Square/Wider (Example: 450x350). Set center_y higher to focus on the shoe bottom.
        {"x": 600, "y": 350, "w": 450, "h": 350, "center_y": 0.6}, 
        # Slot 3: Landscape (Example: 600x300). Set center_y high to keep the sole visible.
        {"x": 50, "y": 750, "w": 600, "h": 300, "center_y": 0.8}
    ],
    "price": {
        "x": 840,
        "y": 880,
        "color": "#0055FF", 
        "font_size": 80,
        "font_path": "assets/fonts/BallzyFont-Bold.ttf" 
    }
}

# --- 2. IMAGE GENERATION LOGIC ---

def create_ballzy_ad(image_urls, price_text, product_id):
    """Generates the single stylized image based on the Ballzy layout."""
    
    try:
        base = Image.open(LAYOUT_CONFIG["template_path"]).convert("RGBA")
    except FileNotFoundError:
        print(f"ERROR: Template not found. Creating white canvas.")
        base = Image.new('RGBA', LAYOUT_CONFIG["canvas_size"], (255, 255, 255, 255))
    
    # Loop through the 3 Image Slots
    for i, slot in enumerate(LAYOUT_CONFIG["slots"]):
        if i >= len(image_urls): 
            continue
            
        url = image_urls[i]
        
        try:
            # Download image
            response = requests.get(url, timeout=10)
            img = Image.open(BytesIO(response.content)).convert("RGBA")
            
            target_size = (slot['w'], slot['h'])
            
            # **IMPROVED FITTING**: Use ImageOps.fit (the 'Cover' method)
            # This fills the slot and crops the source image, using the custom center_y.
            fitted_img = ImageOps.fit(
                img, 
                target_size, 
                method=Image.Resampling.LANCZOS, 
                centering=(0.5, slot.get("center_y", 0.5)) # Use slot's center_y or default 0.5
            )
            
            # The image is now the exact size of the slot, so paste at the top-left of the slot
            paste_x = slot['x']
            paste_y = slot['y']
            
            # Paste image onto the base
            base.paste(fitted_img, (paste_x, paste_y), fitted_img)

        except Exception as e:
            print(f"Error processing image {url} for product {product_id}: {e}")

    # Draw the Price (same logic as before)
    draw = ImageDraw.Draw(base)
    price_conf = LAYOUT_CONFIG["price"]
    
    try:
        font = ImageFont.truetype(price_conf["font_path"], price_conf["font_size"])
    except:
        font = ImageFont.load_default() 

    _, _, w, h = draw.textbbox((0, 0), price_text, font=font)
    text_x = price_conf["x"] - (w / 2)
    text_y = price_conf["y"] - (h / 2)
    
    draw.text((text_x, text_y), price_text, fill=price_conf["color"], font=font)

    # Save Final Ad
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"ad_{product_id}.jpg")
    base.convert("RGB").save(output_path, format="JPEG", quality=95)
    print(f"-> Successfully generated: {output_path} (Price: {price_text})")

# --- 3. XML FEED PROCESSING LOGIC (Unchanged) ---

def process_feed(url):
    """Downloads the XML feed and iterates through products."""
    
    print(f"Downloading feed from: {url}")
    try:
        feed_response = requests.get(url, timeout=30)
        feed_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"FATAL ERROR: Could not download feed. {e}")
        return

    try:
        root = ET.fromstring(feed_response.content)
    except ET.ParseError as e:
        print(f"FATAL ERROR: Could not parse XML feed. {e}")
        return

    product_count = 0
    
    for item in root.iter('item'): 
        if product_count >= MAX_PRODUCTS_TO_GENERATE:
            print(f"Stopping after generating {MAX_PRODUCTS_TO_GENERATE} products for testing.")
            break
            
        product_id_element = item.find('g:id', NAMESPACES)
        if product_id_element is None: continue
        product_id = product_id_element.text.strip()
        
        # Extract Price (sale_price first, then price)
        price_element = item.find('g:sale_price', NAMESPACES)
        if price_element is None:
            price_element = item.find('g:price', NAMESPACES)

        if price_element is None: continue
            
        raw_price = price_element.text.split()[0]
        formatted_price = f"{raw_price}€"
        
        # Extract Image Links (Main + two additional)
        image_urls = []
        main_image = item.find('g:image_link', NAMESPACES)
        if main_image is not None:
            image_urls.append(main_image.text.strip())

        additional_images = item.findall('g:additional_image_link', NAMESPACES)
        for i, img in enumerate(additional_images):
            if i < 2: image_urls.append(img.text.strip())

        if not image_urls: continue
        
        # Generate Image
        create_ballzy_ad(image_urls, formatted_price, product_id)
        product_count += 1

# --- 4. EXECUTION ---

if __name__ == "__main__":
    process_feed(FEED_URL)
