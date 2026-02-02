"""Constants module - verticals and major players lists."""

from enum import Enum
from typing import Dict, List


class Vertical(str, Enum):
    """Supported newsletter verticals."""
    DATA_CENTERS = "data_centers"
    CONNECTIVITY_FIBRE = "connectivity_fibre"
    TOWERS_WIRELESS = "towers_wireless"


# Deterministic major players lists per vertical
MAJOR_PLAYERS: Dict[Vertical, List[str]] = {
    Vertical.DATA_CENTERS: [
        "Equinix",
        "Digital Realty",
        "CyrusOne",
        "QTS Data Centers",
        "NTT Global Data Centers",
        "Iron Mountain Data Centers",
        "Switch",
        "STACK Infrastructure",
        "Google Cloud",
        "Amazon Web Services (AWS)",
    ],
    Vertical.CONNECTIVITY_FIBRE: [
        "Lumen Technologies",
        "Zayo",
        "Crown Castle Fiber",
        "Colt Technology Services",
        "euNetworks",
        "CityFibre",
        "Openreach",
        "Telxius",
        "Sparkle (Telecom Italia Sparkle)",
        "Subsea7",
    ],
    Vertical.TOWERS_WIRELESS: [
        "American Tower",
        "Cellnex Telecom",
        "Vantage Towers",
        "SBA Communications",
        "IHS Towers",
        "Indus Towers",
        "Crown Castle",
        "Phoenix Tower International",
        "Helios Towers",
        "DigitalBridge",
    ],
}

# Sector keywords for initial search queries
SECTOR_KEYWORDS: Dict[Vertical, List[str]] = {
    Vertical.DATA_CENTERS: [
        "data centre capacity expansion",
        "hyperscale data center",
        "colocation facility",
        "data center power",
        "edge computing infrastructure",
    ],
    Vertical.CONNECTIVITY_FIBRE: [
        "fibre network investment",
        "subsea cable",
        "dark fibre",
        "metro fibre",
        "long-haul connectivity",
    ],
    Vertical.TOWERS_WIRELESS: [
        "tower leasing",
        "5G infrastructure",
        "small cell deployment",
        "wireless tower acquisition",
        "telecom infrastructure",
    ],
}

# Vertical display names for markdown output
VERTICAL_DISPLAY_NAMES: Dict[Vertical, str] = {
    Vertical.DATA_CENTERS: "Data Centers",
    Vertical.CONNECTIVITY_FIBRE: "Connectivity & Fibre",
    Vertical.TOWERS_WIRELESS: "Towers & Wireless Infrastructure",
}

# Default voice profile
DEFAULT_VOICE_PROFILE = "expert_operator"

# Default evidence budget per agent
DEFAULT_EVIDENCE_BUDGET = 12

# Default max review rounds
DEFAULT_MAX_REVIEW_ROUNDS = 2

# Review rubric thresholds
GROUNDING_THRESHOLD = 4
CLARITY_THRESHOLD = 4
