def normalize_hotkey(hotkey):
    if not hotkey:
        return ""
    
    hotkey = hotkey.lower()
    
    # Map German/Localized keys to English standard
    replacements = {
        "strg": "ctrl",
        "steuerung": "ctrl",
        "umschalt": "shift",
        "nach-links": "left",
        "nach-rechts": "right",
        "nach-oben": "up",
        "nach-unten": "down",
        "windows": "win",
        "eingabe": "enter",
        "rück": "backspace",
        "entf": "delete",
        "einfügen": "insert",
        "bild-auf": "page up",
        "bild-ab": "page down",
        "pos1": "home",
        "ende": "end",
        "druck": "print screen",
        "rollen": "scroll lock",
        "pause": "pause"
    }
    
    parts = hotkey.split('+')
    new_parts = []
    
    for part in parts:
        clean_part = part.strip()
        new_parts.append(replacements.get(clean_part, clean_part))
        
    return "+".join(new_parts)
