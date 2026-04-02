"""
output_handler.py — Portfolio Intelligence Briefing System
Output layer: all delivery and persistence. Designed to be extended
(email, Slack, web) without touching other layers.

Functions (Phase 1):
    print_briefing(text)       — formats and prints to terminal with section headers
    save_briefing(text, mode)  — saves to ~/portfolio_briefings/ with dated filename

Future delivery channels (Phase 2 — TBD):
    email_briefing(text)    — Gmail SMTP or SendGrid
    slack_briefing(text)    — Slack/Discord webhook
    imessage_briefing(text) — AppleScript / Shortcuts integration
"""

import os
import datetime

from config import OUTPUT_DIR


# ============================================================================
# TERMINAL OUTPUT
# ============================================================================

def print_briefing(text, mode="intraday"):
    """
    Print the briefing to the terminal with a clean header and section separators.

    Args:
        text: str — the briefing text returned by synthesize_with_claude()
        mode: "intraday" or "eod"
    """
    now       = datetime.datetime.now()
    mode_label = "END-OF-DAY RECAP" if mode == "eod" else "INTRADAY BRIEFING"
    timestamp  = now.strftime("%A, %B %d %Y  \u2022  %I:%M %p").replace(" 0", " ")

    border = "=" * 70

    print(f"\n{border}")
    print(f"  PORTFOLIO INTELLIGENCE  |  {mode_label}")
    print(f"  {timestamp}")
    print(f"{border}\n")
    print(text)
    print(f"\n{border}\n")


# ============================================================================
# SAVE TO FILE
# ============================================================================

def save_briefing(text, mode="intraday"):
    """
    Save the briefing to a dated text file in OUTPUT_DIR.

    Filename format: briefing_<mode>_<YYYYMMDD_HHMM>.txt
    Creates OUTPUT_DIR if it doesn't exist.

    Args:
        text: str — the briefing text
        mode: "intraday" or "eod"

    Returns:
        str: the full path to the saved file, or None on failure.
    """
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        filename  = f"briefing_{mode}_{timestamp}.txt"
        filepath  = os.path.join(OUTPUT_DIR, filename)

        now_str = datetime.datetime.now().strftime("%A, %B %d %Y at %I:%M %p").replace(" 0", " ")
        mode_label = "END-OF-DAY RECAP" if mode == "eod" else "INTRADAY BRIEFING"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"PORTFOLIO INTELLIGENCE BRIEFING\n")
            f.write(f"{mode_label}  |  {now_str}\n")
            f.write("=" * 70 + "\n\n")
            f.write(text)
            f.write("\n")

        return filepath

    except Exception as e:
        print(f"[output_handler] Failed to save briefing: {e}")
        return None


# ============================================================================
# HISTORY VIEWER
# ============================================================================

def list_saved_briefings():
    """
    List all saved briefings in OUTPUT_DIR, newest first.

    Returns:
        list of dicts: [{"filename": str, "path": str, "modified": str}, ...]
        Empty list if OUTPUT_DIR doesn't exist or contains no briefings.
    """
    if not os.path.isdir(OUTPUT_DIR):
        return []

    files = [
        f for f in os.listdir(OUTPUT_DIR)
        if f.startswith("briefing_") and f.endswith(".txt")
    ]

    entries = []
    for fname in files:
        fpath = os.path.join(OUTPUT_DIR, fname)
        mtime = os.path.getmtime(fpath)
        modified = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        entries.append({"filename": fname, "path": fpath, "modified": modified})

    # Sort newest first
    entries.sort(key=lambda x: x["modified"], reverse=True)
    return entries


# ============================================================================
# PHASE 2 STUBS — delivery channels (implementation TBD)
# ============================================================================

def email_briefing(text):
    """[Phase 2] Send briefing via Gmail SMTP or SendGrid."""
    raise NotImplementedError("Email delivery not yet implemented.")


def slack_briefing(text):
    """[Phase 2] Post briefing to a Slack/Discord webhook."""
    raise NotImplementedError("Slack/Discord delivery not yet implemented.")


def imessage_briefing(text):
    """[Phase 2] Send briefing via AppleScript iMessage integration."""
    raise NotImplementedError("iMessage delivery not yet implemented.")
