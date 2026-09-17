#!/usr/bin/env python3
"""Capture actual static frames, preserving ANSI colours and terminal cell layout.

Optional development dependencies: Pillow and Rich. No generated artwork, fonts,
network location, or live user data is used. Native port: --native.
"""
import argparse
import importlib
import math
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont
from rich.console import Console
from rich.text import Text


def raster(frame, target, font_path):
    font = ImageFont.truetype(str(font_path), 20)
    cell_width = math.ceil(font.getlength('M'))
    cell_height = sum(font.getmetrics())
    lines = [Text.from_ansi(line) for line in frame.splitlines()]
    cols = max(len(line.plain) for line in lines)
    padding = 24
    image = Image.new('RGB', (cols * cell_width + padding * 2,
                             len(lines) * cell_height + padding * 2), '#050a0f')
    draw = ImageDraw.Draw(image)
    console = Console(force_terminal=True, color_system='truecolor')
    for row, line in enumerate(lines):
        for col, char in enumerate(line.plain):
            style = line.get_style_at_offset(console, col)
            bg = tuple(style.bgcolor.get_truecolor()) if style.bgcolor else (5, 10, 15)
            fg = tuple(style.color.get_truecolor()) if style.color else (218, 230, 237)
            x, y = padding + col * cell_width, padding + row * cell_height
            draw.rectangle((x, y, x + cell_width - 1, y + cell_height - 1), fill=bg)
            if char != ' ':
                if 0x2800 <= ord(char) <= 0x28ff:
                    # Preserve the exact Unicode 2x4 Braille dot cell even
                    # when the selected terminal font has no Braille glyphs.
                    bits = ord(char) - 0x2800
                    radius = max(1, cell_width // 10)
                    for bit, dot_col, dot_row in ((0, 0, 0), (1, 0, 1), (2, 0, 2),
                                                 (3, 1, 0), (4, 1, 1), (5, 1, 2),
                                                 (6, 0, 3), (7, 1, 3)):
                        if bits & (1 << bit):
                            cx = x + cell_width * (0.28 if dot_col == 0 else 0.72)
                            cy = y + cell_height * (dot_row + 0.5) / 4
                            draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=fg)
                else:
                    draw.text((x, y), char, font=font, fill=fg)
    image.save(target, optimize=True)
    return image.size


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', type=Path, default=Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--native', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not args.native:
        sys.path.insert(0, str(root))
    app = importlib.import_module('linecast.orrery' if args.native else 'app')
    output = args.output or root / 'docs' / 'images'
    output.mkdir(parents=True, exist_ok=True)
    for name, view, theme, help_open in [('orbit', 'orbit', 'orrery', False),
                                        ('sky', 'sky', 'orrery', False),
                                        ('help', 'orbit', 'orrery', True),
                                        ('native-theme', 'orbit', 'native', False)]:
        state = app.State(moment=app.parse_date('2026-09-17T00:00:00Z'),
                          playing=False, selected='saturn', view=view,
                          location=(51.48, 0), theme=theme, loop=True)
        screen = app.OrreryApp(state, 140, 44)
        screen.help_open = help_open
        if view == 'sky':
            screen.select('saturn')
        frame = screen.render_static()
        target = output / (name + '.png')
        size = raster(frame, target, args.font)
        print(f'{target.name}: {size[0]}x{size[1]}')


if __name__ == '__main__':
    main()
