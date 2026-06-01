# Network
CARD_DEACTIVATE_URL = "http://mainframe.local:3001/card/deactivate"
CARD_ACTIVATE_URL   = "http://mainframe.local:3001/card/activate"
HEALTH_URL          = "http://mainframe.local:3001/health"
VISITOR_API         = "http://mainframe.local:3001/visitor/data"
WS_URL              = "ws://mainframe.local:5000/"

# Timing
REACTIVATE_DELAY = 10
REQUEST_TIMEOUT  = 5
RECONNECT_DELAY  = 5

# Device
DEVICE_TYPE = "pi"
STATION_ID  = "printer"

# Debug
DEBUG = False

# Printer canvas
PRINTER_WIDTH    = 576
PAGE_HEIGHT      = 1200
BACKGROUND_COLOR = "white"
TEXT_COLOR       = "black"
DEFAULT_MARGIN_X = 30
LINE_SPACING     = 20

# Fonts
FONT_PATH       = "MM_reg.ttf"
HEADING_SIZE    = 52
SUBHEADING_SIZE = 36
BODY_SIZE       = 26

# Sections (ordered)
APP_SECTIONS = [
    {"stationId": "nebula",  "title": "YOU ARE MADE OF"},
    {"stationId": "ar",      "title": "TRACES LEFT BEHIND"},
    {"stationId": "palm",    "title": "MAPPED IN PALMS"},
    {"stationId": "rename",  "title": "BEARING THE NAME GIVEN"},
    {"stationId": "planar",  "title": "WHEN STARS ALIGNED"},
]

ORDER = ["nebula", "ar", "palm", "rename", "planar"]
