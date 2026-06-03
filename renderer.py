import base64
import logging
from datetime import date
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import APP_SECTIONS, FONT_PATH, ORDER, PRINTER_WIDTH, TEXT_COLOR, BACKGROUND_COLOR, DEBUG
from drawing import (
    BODY_FONT, create_canvas, draw_subheading, draw_text,
    draw_vertical_title, draw_wrapped_text, get_text_width,
    draw_horizontal_line, draw_vertical_line,
)

logger = logging.getLogger("printer-client")


def is_empty(obj):
    if obj in (None, "", [], {}):
        return True
    if isinstance(obj, dict):
        return all(is_empty(v) for v in obj.values())
    if isinstance(obj, list):
        return all(is_empty(v) for v in obj)
    return False


def _render_data(obj, img, draw, y, content_x, content_width, prefix=""):
    """Recursively render a dict/list onto the canvas, return new y."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if is_empty(value):
                continue
            key_path = f"{prefix}.{key}" if prefix else key

            if key.lower() == "photo" and isinstance(value, str):
                try:
                    y = draw_wrapped_text(draw, f"{key_path}:", content_x, y, content_width)
                    photo = Image.open(BytesIO(base64.b64decode(value))).convert("RGB")
                    max_w = content_width - 20
                    photo = photo.resize((max_w, int(photo.height * (max_w / photo.width))))
                    img.paste(photo, (content_x, y))
                    y += photo.height + 30
                except Exception as e:
                    logger.error(f"Photo render failed: {e}")

            elif isinstance(value, (dict, list)):
                y = _render_data(value, img, draw, y, content_x, content_width, key_path)

            else:
                y = draw_wrapped_text(draw, f"{key_path}: {value}", content_x, y, content_width)

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            y = _render_data(item, img, draw, y, content_x, content_width, f"{prefix}[{i}]")

    return y


TITLE_CHAR_SIZE        = 60
TITLE_CHAR_SIZE_EMPTY  = 70
TITLE_RIGHT_MARGIN     = 5   # pixels between right edge of char box and canvas edge
TITLE_DIVIDER_X        = PRINTER_WIDTH - TITLE_CHAR_SIZE_EMPTY - TITLE_RIGHT_MARGIN - 10

def render_section(img, draw, y, section, section_data):
    """Render a filled section with a rotated title on the right edge."""
    font      = ImageFont.truetype(FONT_PATH, 28)
    char_size = TITLE_CHAR_SIZE
    title_x   = PRINTER_WIDTH - char_size - TITLE_RIGHT_MARGIN
    content_x = 30
    content_width = PRINTER_WIDTH - content_x - 80  # leave room for right-side title

    title_end_y = draw_vertical_title(
        img, section["title"], 0, font, title_x,
        char_size=char_size, char_spacing=2, space_advance=6,
    )

    y = _render_data(
        section_data, img, draw, y, content_x, content_width,
        prefix=section["stationId"],
    )
    
    final_y = max(y, title_end_y) + 40
    
    # Draw vertical line separating right-side title from left content
    draw_vertical_line(draw, TITLE_DIVIDER_X, 0, final_y)

    # Draw horizontal line at bottom of section, stopping at the vertical divider
    draw_horizontal_line(draw, final_y - 40, width=TITLE_DIVIDER_X)

    return final_y


def calculate_vertical_title_height(title, char_size, char_spacing, space_advance):
    """Calculate the height that vertical title will occupy."""
    words = title.split()
    total_height = 0

    char_advance = char_size + char_spacing - 28
    for word_idx, word in enumerate(words):
        for char in word:
            total_height += char_advance
        if word_idx < len(words) - 1:
            total_height += space_advance + 20

    return total_height


def render_empty_section(img, draw, y, section):
    """Render a placeholder section (no data) with zizia image, centered."""
    font      = ImageFont.truetype(FONT_PATH, 28)
    char_size = TITLE_CHAR_SIZE_EMPTY
    title_x   = PRINTER_WIDTH - char_size - TITLE_RIGHT_MARGIN
    char_spacing = -2
    space_advance = 15

    # Calculate vertical title height
    title_height = calculate_vertical_title_height(section["title"], char_size, char_spacing, space_advance)

    # Calculate zizia and text heights
    zizia_height = 0
    try:
        zizia = Image.open("zizia.png").convert("RGB")
        max_w = 220
        zizia = zizia.resize((max_w, int(zizia.height * (max_w / zizia.width))))
        zizia_height = zizia.height + 20
    except Exception as e:
        logger.error(f"Failed to load zizia.png: {e}")

    no_data_font = ImageFont.truetype(FONT_PATH, 30)
    bbox = draw.textbbox((0, 0), "NO DATA FOUND", font=no_data_font)
    text_height = (bbox[3] - bbox[1]) + 20

    content_height = zizia_height + text_height
    section_height = max(title_height, content_height) + 40
    top_padding = (section_height - content_height) // 2

    start_y = y

    # Title always starts at top of section
    draw_vertical_title(
        img, section["title"], 0, font, title_x,
        char_size=char_size, char_spacing=char_spacing, space_advance=space_advance,
    )

    # Content is centered vertically within section
    y = start_y + top_padding

    try:
        zizia = Image.open("zizia.png").convert("RGB")
        max_w = 220
        zizia = zizia.resize((max_w, int(zizia.height * (max_w / zizia.width))))
        zizia_x = (PRINTER_WIDTH - max_w) // 2
        img.paste(zizia, (zizia_x, y))
        y += zizia.height + 20
    except Exception as e:
        logger.error(f"Failed to load zizia.png: {e}")

    no_data_font = ImageFont.truetype(FONT_PATH, 30)
    bbox = draw.textbbox((0, 0), "NO DATA FOUND", font=no_data_font)
    text_width = bbox[2] - bbox[0]
    text_x = (PRINTER_WIDTH - text_width) // 2
    draw_text(draw, "NO DATA FOUND", y, no_data_font, x_override=text_x)

    final_y = start_y + section_height
    
    # Draw vertical line separating right-side title from left content
    draw_vertical_line(draw, TITLE_DIVIDER_X, 0, final_y)

    # Draw horizontal line at bottom of section, stopping at the vertical divider
    draw_horizontal_line(draw, final_y - 40, width=TITLE_DIVIDER_X)

    return final_y


def render_header_section(data):
    """Render header section (title + UID) and return image."""
    img, draw = create_canvas()
    y = 40
    app_data = data.get("appData", {})

    rename_name = app_data.get("rename", {}).get("name")
    name_text = (
        rename_name.strip().upper()
        if isinstance(rename_name, str) and rename_name.strip()
        else "YOU"
    )
    y = draw_text(draw, "ALL ABOUT", y, ImageFont.truetype(FONT_PATH, 42), center=True)
    y -= 5
    y = draw_text(draw, name_text, y, ImageFont.truetype(FONT_PATH, 72), center=True)
    y += 20
    y = draw_subheading(draw, f"UID: {data.get('UID', 'UNKNOWN')}", y, center=True)
    y += 30
    
    # Draw horizontal line after header
    draw_horizontal_line(draw, y)
    y += 10

    img = img.crop((0, 0, PRINTER_WIDTH, y))
    return img


def render_station_section(section, section_data):
    """Render a single station section and return image."""
    img, draw = create_canvas()
    y = 40

    if is_empty(section_data):
        y = render_empty_section(img, draw, y, section)
    else:
        y = render_section(img, draw, y, section, section_data)

    img = img.crop((0, 0, PRINTER_WIDTH, y))
    return img


def combine_images_vertical(images):
    """Stack images vertically and return combined image."""
    if not images:
        return None

    total_height = sum(img.height for img in images)
    combined = Image.new("RGB", (PRINTER_WIDTH, total_height), BACKGROUND_COLOR)

    y_offset = 0
    for img in images:
        combined.paste(img, (0, y_offset))
        y_offset += img.height

    return combined


def save_preview_images(images, section_names):
    """Save preview images for each section with named files."""
    previews_dir = Path("previews")
    previews_dir.mkdir(exist_ok=True)

    preview_paths = []
    for img, name in zip(images, section_names):
        bw_img = img.convert("L").convert("1")
        path = previews_dir / f"section_{name}.png"
        bw_img.save(path)
        preview_paths.append(path)
        logger.info(f"Saved preview: {path}")

    return preview_paths


def print_visitor_ticket(printer_device, data):
    if not printer_device:
        logger.error("Printer not initialized")
        return

    try:
        app_data = data.get("appData", {})
        images = []
        section_names = []

        # Render header
        logger.info("Rendering header section...")
        header_img = render_header_section(data)
        images.append(header_img)
        section_names.append("header")

        # Render sections in ORDER
        ordered = [s for sid in ORDER for s in APP_SECTIONS if s["stationId"] == sid]
        for section in ordered:
            logger.info(f"Rendering section: {section['stationId']}")
            section_data = app_data.get(section["stationId"])
            section_img = render_station_section(section, section_data)
            images.append(section_img)
            section_names.append(section["stationId"])

        # Save individual previews
        save_preview_images(images, section_names)

        # Combine images vertically
        final_img = combine_images_vertical(images)
        final_img = final_img.convert("L").convert("1")
        final_img.save("preview_final.png")
        logger.info("Saved combined preview: preview_final.png")

        # Print
        if DEBUG:
            logger.info("[DEBUG] Skipping printer output")
        else:
            printer_device.image(final_img)
            printer_device.cut()
            logger.info("Ticket printed")

    except Exception as e:
        logger.error(f"Printing failed: {e}")


def generate_test_print(printer_device=None):
    """Generate a test print with zizia.png as the photo in every section."""
    with open("zizia.png", "rb") as f:
        photo_b64 = base64.b64encode(f.read()).decode()

    data = {
        "UID": "TEST-001",
        "appData": {
            "nebula":  {"photo": photo_b64},
            "ar":      {"photo": photo_b64},
            "palm":    {"photo": photo_b64, "palmLength": 10, "palmWidth": 10},
            "rename":  {"photo": photo_b64, "name": "test"},
            "planar":  {"photo": photo_b64, "DOB": str(date.today())},
        },
    }

    print_visitor_ticket(printer_device, data)
