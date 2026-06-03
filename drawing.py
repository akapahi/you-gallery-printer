import logging

from PIL import Image, ImageDraw, ImageFont

from config import (
    FONT_PATH, PRINTER_WIDTH, PAGE_HEIGHT,
    BACKGROUND_COLOR, TEXT_COLOR, DEFAULT_MARGIN_X, LINE_SPACING,
    HEADING_SIZE, SUBHEADING_SIZE, BODY_SIZE,
)

logger = logging.getLogger("printer-client")

HEADING_FONT    = ImageFont.truetype(FONT_PATH, HEADING_SIZE)
SUBHEADING_FONT = ImageFont.truetype(FONT_PATH, SUBHEADING_SIZE)
BODY_FONT       = ImageFont.truetype(FONT_PATH, BODY_SIZE)


def create_canvas():
    img = Image.new("RGB", (PRINTER_WIDTH, PAGE_HEIGHT), BACKGROUND_COLOR)
    return img, ImageDraw.Draw(img)


def get_text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def draw_text(draw, text, y, font, center=False, x_override=None):
    if x_override is not None:
        x = x_override
    elif center:
        x = (PRINTER_WIDTH - get_text_width(draw, text, font)) // 2
    else:
        x = DEFAULT_MARGIN_X

    draw.text((x, y), text, font=font, fill=TEXT_COLOR)
    bbox = draw.textbbox((x, y), text, font=font)
    return y + (bbox[3] - bbox[1]) + LINE_SPACING


def draw_heading(draw, text, y, center=True):
    return draw_text(draw, text, y, HEADING_FONT, center)


def draw_subheading(draw, text, y, center=False):
    return draw_text(draw, text, y, SUBHEADING_FONT, center)


def draw_body(draw, text, y, center=False, x_override=None):
    return draw_text(draw, text, y, BODY_FONT, center, x_override)


def draw_wrapped_text(draw, text, x, y, max_width):
    """Word-wrap text into max_width using BODY_FONT, return new y."""
    words = text.split()
    line  = ""
    lines = []

    for word in words:
        test = f"{line} {word}".strip()
        if get_text_width(draw, test, BODY_FONT) > max_width:
            if line:
                lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)

    for ln in lines:
        draw.text((x, y), ln, font=BODY_FONT, fill=TEXT_COLOR)
        bbox = draw.textbbox((x, y), ln, font=BODY_FONT)
        y += (bbox[3] - bbox[1]) + LINE_SPACING

    return y


def draw_vertical_title(img, title, start_y, font, title_x, char_size, char_spacing, space_advance):
    """Stamp each character rotated 270°, stacked top-to-bottom on the right side.
    Letters within a word are close together, words are separated by space_advance."""

    current_y = start_y
    words = title.split()

    char_advance = char_size + char_spacing - 28
    word_gap = space_advance + 20

    for word_idx, word in enumerate(words):
        for char in word:
            char_img = Image.new("RGBA", (char_size, char_size), (255, 255, 255, 0))
            char_draw = ImageDraw.Draw(char_img)

            bbox = char_draw.textbbox((0, 0), char, font=font)

            x = (char_size - (bbox[2] - bbox[0])) // 2 - bbox[0]
            y = (char_size - (bbox[3] - bbox[1])) // 2 - bbox[1]

            char_draw.text((x, y), char, font=font, fill=TEXT_COLOR)

            rotated = char_img.rotate(270, expand=True)

            img.paste(rotated, (title_x, current_y), rotated)

            current_y += char_advance

        if word_idx < len(words) - 1:
            current_y += word_gap

    return current_y


def draw_horizontal_line(draw, y, width=PRINTER_WIDTH, thickness=3):
    """Draw a horizontal line across the full width at position y."""
    draw.line([(0, y), (width, y)], fill=TEXT_COLOR, width=thickness)


def draw_vertical_line(draw, x, start_y, end_y, thickness=1):
    """Draw a vertical line from start_y to end_y at position x."""
    draw.line([(x, start_y), (x, end_y)], fill=TEXT_COLOR, width=thickness)
