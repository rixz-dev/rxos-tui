import subprocess

def copy(text: str) -> bool:
    """Copy text to clipboard. Termux-aware."""
    # Try termux-clipboard-set first
    try:
        subprocess.run(
            ["termux-clipboard-set", text],
            check=True, timeout=3,
            capture_output=True
        )
        return True
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    # Fallback: xclip / xsel for desktop Linux
    for cmd in [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
        try:
            proc = subprocess.run(cmd, input=text.encode(), timeout=3, capture_output=True)
            if proc.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.SubprocessError):
            continue
    # Fallback: pyperclip
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        return False
