import webcolors
from colorspacious import cspace_convert


def css_to_rgb(color_name: str) -> tuple[int, int, int]:
    try:
        return webcolors.name_to_rgb(color_name)
    except ValueError:
        raise ValueError(f"CSS color '{color_name} not valid")

def hex_to_rgb(hex: str) -> tuple[int, int, int]:
    return webcolors.hex_to_rgb(hex)

def rgb_to_cielab(rgb: tuple) -> list:
    return cspace_convert(rgb, "sRGB255", "CIELab")

def css_to_hex(color_name: str) -> str:
    return webcolors.name_to_hex(color_name)