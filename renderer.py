import base64
import logging
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import APP_SECTIONS, FONT_PATH, ORDER, PRINTER_WIDTH, TEXT_COLOR, BACKGROUND_COLOR, DEBUG
from drawing import (
    BODY_FONT, create_canvas, draw_subheading, draw_text,
    draw_vertical_title, draw_wrapped_text, get_text_width,
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


def render_section(img, draw, y, section, section_data):
    """Render a filled section with a rotated title on the right edge."""
    font      = ImageFont.truetype(FONT_PATH, 28)
    title_x   = PRINTER_WIDTH - 55
    content_x = 30
    content_width = PRINTER_WIDTH - content_x - 80  # leave room for right-side title

    title_end_y = draw_vertical_title(
        img, section["title"], y, font, title_x,
        char_size=60, char_spacing=2, space_advance=6,
    )

    y = _render_data(
        section_data, img, draw, y, content_x, content_width,
        prefix=section["stationId"],
    )

    return max(y, title_end_y) + 40


def render_empty_section(img, draw, y, section):
    """Render a placeholder section (no data) with zizia image."""
    font      = ImageFont.truetype(FONT_PATH, 28)
    title_x   = PRINTER_WIDTH - 55
    content_x = 30

    title_end_y = draw_vertical_title(
        img, section["title"], y, font, title_x,
        char_size=70, char_spacing=-2, space_advance=0,
    )

    try:
        zizia = Image.open("zizia.png").convert("RGB")
        max_w = 220
        zizia = zizia.resize((max_w, int(zizia.height * (max_w / zizia.width))))
        img.paste(zizia, (content_x, y))
        y += zizia.height + 20
    except Exception as e:
        logger.error(f"Failed to load zizia.png: {e}")

    no_data_font = ImageFont.truetype(FONT_PATH, 30)
    y = draw_text(draw, "NO DATA FOUND", y, no_data_font, x_override=content_x)

    return max(y, title_end_y) + 40


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
