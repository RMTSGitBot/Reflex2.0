from decimal import Decimal

# ─────────────────────────────────────────────
# 🧼 String Cleaner
# ─────────────────────────────────────────────

def _clean_str(value) -> str | None:
    """
    Strips whitespace and converts to string if not None.
    Returns None for empty or null-like values.
    """
    if value in (None, "", "N/A", "-", "—"):
        return None
    return str(value).strip()

# ─────────────────────────────────────────────
# 🔢 Numeric Parser
# ─────────────────────────────────────────────

def _parse_numeric(value, max_abs=1e12) -> float | None:
    """
    Parses a numeric string, removes commas and percent signs,
    and returns a float if within bounds. Returns None on failure.
    """
    try:
        val = str(value).replace('%', '').replace(',', '').strip()
        if val in ("N/A", "-", "—", "", None):
            return None
        parsed = float(val)
        return parsed if abs(parsed) < max_abs else None
    except Exception:
        return None

# ─────────────────────────────────────────────
# 🧮 Decimal Parser (Optional)
# ─────────────────────────────────────────────

def _parse_decimal(value) -> Decimal | None:
    """
    Converts a value to Decimal safely. Returns None on failure.
    """
    try:
        return Decimal(str(value).strip())
    except Exception:
        return None