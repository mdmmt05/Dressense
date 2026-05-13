import webcolors
from colorspacious import cspace_convert

def css_to_rgb(color_name: str) -> tuple[int, int, int]:
    try:
        return webcolors.name_to_rgb(color_name)
    except ValueError:
        raise ValueError(f"CSS color '{color_name}' non valido")   # fixed missing quote

def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    try:
        return webcolors.hex_to_rgb(hex_str)
    except ValueError as e:
        raise ValueError(f"Hex color '{hex_str}' non valido: {e}")

def rgb_to_cielab(rgb: tuple) -> list:
    return cspace_convert(rgb, "sRGB255", "CIELab")

def css_to_hex(color_name: str) -> str:
    try:
        return webcolors.name_to_hex(color_name)
    except ValueError:
        raise ValueError(f"CSS color '{color_name}' non valido")