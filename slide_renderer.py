# -*- coding: utf-8 -*-
"""
PIL-based Slide Renderer v3.0
=============================
Directly renders 1920x1080 slide images with PIL.
Supports 6 visual themes + media overlay + rich layouts (table, comparison, insight).

Based on rendering approach from Hurst Cycle Video Builder (GITHUB example project).
v3.0 — Rich layouts inspired by build_hurst_video.py:
  - Card-style data tables with color-coded status cells
  - Side-by-side comparison cards (like price targets)
  - Insight/warning boxes
  - Better text wrapping and visual hierarchy
"""

import os, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080

# ── Windows fonts ────────────────────────────────────────────────────
FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"
FONT_REG  = "C:/Windows/Fonts/msyh.ttc"


# ══════════════════════════════════════════════════════════════════════
#  THEMES — 6 套
# ══════════════════════════════════════════════════════════════════════

THEMES = {
    "现代简约": {
        "name": "现代简约", "bg_dark": (235, 238, 245), "bg_light": (248, 248, 250),
        "title_start": (70, 80, 150), "title_end": (90, 110, 190),
        "accent": (255, 200, 60), "text": (50, 50, 70), "card": (245, 248, 252),
        "subtitle": (80, 90, 170), "cover_start": (70, 80, 150), "cover_end": (90, 110, 190),
    },
    "商务专业": {
        "name": "商务专业", "bg_dark": (228, 235, 250), "bg_light": (240, 245, 255),
        "title_start": (0, 75, 150), "title_end": (0, 120, 200),
        "accent": (0, 165, 235), "text": (30, 40, 60), "card": (242, 247, 255),
        "subtitle": (0, 80, 165),
    },
    "学术论文": {
        "name": "学术论文", "bg_dark": (242, 240, 232), "bg_light": (250, 248, 242),
        "title_start": (55, 65, 85), "title_end": (75, 85, 110),
        "accent": (160, 130, 60), "text": (40, 40, 35), "card": (248, 246, 238),
        "subtitle": (80, 75, 55),
    },
    "创意彩色": {
        "name": "创意彩色", "bg_dark": (250, 240, 248), "bg_light": (255, 248, 250),
        "title_start": (200, 40, 100), "title_end": (235, 80, 120),
        "accent": (255, 200, 50), "text": (60, 30, 50), "card": (255, 244, 250),
        "subtitle": (190, 50, 110),
    },
    "深色主题": {
        "name": "深色主题", "bg_dark": (20, 22, 32), "bg_light": (28, 30, 40),
        "title_start": (40, 50, 90), "title_end": (60, 70, 130),
        "accent": (80, 180, 255), "text": (200, 205, 215), "card": (35, 40, 55),
        "subtitle": (120, 180, 250),
    },
    "清新留白": {
        "name": "清新留白", "bg_dark": (245, 248, 242), "bg_light": (252, 252, 250),
        "title_start": (150, 195, 170), "title_end": (175, 215, 185),
        "accent": (100, 175, 135), "text": (50, 65, 55), "card": (248, 252, 246),
        "subtitle": (100, 165, 130),
    },
    "GITHUB 项目风格": {
        "name": "GITHUB 项目风格", "bg_dark": (18, 18, 30), "bg_light": (18, 18, 30),
        "title_start": (18, 18, 30), "title_end": (18, 18, 30),
        "accent": (0, 180, 255), "text": (240, 240, 245), "card": (30, 32, 50),
        "subtitle": (200, 205, 215),
    },
    "墨色经典": {
        "name": "墨色经典", "bg_dark": (241, 239, 234), "bg_light": (241, 239, 234),
        "title_start": (10, 10, 11), "title_end": (24, 24, 26),
        "accent": (80, 80, 90), "text": (10, 10, 11), "card": (232, 229, 222),
        "subtitle": (50, 50, 55),
    },
    "靛蓝瓷": {
        "name": "靛蓝瓷", "bg_dark": (241, 243, 245), "bg_light": (241, 243, 245),
        "title_start": (10, 31, 61), "title_end": (21, 42, 74),
        "accent": (60, 100, 160), "text": (10, 31, 61), "card": (228, 232, 236),
        "subtitle": (40, 60, 90),
    },
    "森林墨": {
        "name": "森林墨", "bg_dark": (245, 241, 232), "bg_light": (245, 241, 232),
        "title_start": (26, 46, 31), "title_end": (37, 61, 44),
        "accent": (80, 130, 80), "text": (26, 46, 31), "card": (236, 231, 218),
        "subtitle": (50, 70, 55),
    },
    "牛皮纸": {
        "name": "牛皮纸", "bg_dark": (238, 223, 199), "bg_light": (238, 223, 199),
        "title_start": (42, 30, 19), "title_end": (58, 42, 29),
        "accent": (160, 120, 70), "text": (42, 30, 19), "card": (224, 208, 182),
        "subtitle": (70, 55, 40),
    },
    "沙丘": {
        "name": "沙丘", "bg_dark": (240, 230, 210), "bg_light": (240, 230, 210),
        "title_start": (31, 26, 20), "title_end": (45, 38, 32),
        "accent": (150, 130, 100), "text": (31, 26, 20), "card": (227, 215, 192),
        "subtitle": (60, 52, 42),
    },
}

# Dark-theme accent colors for data status
STATUS_COLORS = {
    "up": (0, 220, 100),    # green
    "down": (255, 70, 70),  # red
    "neutral": (160, 160, 175),  # gray
    "warn": (255, 165, 0),  # orange
}


# ══════════════════════════════════════════════════════════════════════
#  DRAWING HELPERS
# ══════════════════════════════════════════════════════════════════════

def gradient_rect(draw, x, y, w, h, c1, c2):
    """Draw a vertical gradient rectangle."""
    if h <= 0 or w <= 0:
        return
    for i in range(min(h, 1080)):
        r = int(c1[0] + (c2[0] - c1[0]) * i / h) if h > 0 else c1[0]
        g = int(c1[1] + (c2[1] - c1[1]) * i / h)
        b = int(c1[2] + (c2[2] - c1[2]) * i / h)
        draw.line([(x, y + i), (x + w - 1, y + i)], fill=(r, g, b))


def rounded_rect(draw, x, y, w, h, r, fill, outline=None, width=0):
    """Draw a rounded rectangle."""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=fill,
                           outline=outline or fill, width=width or 0)


# ══════════════════════════════════════════════════════════════════════
#  SLIDE RENDERER
# ══════════════════════════════════════════════════════════════════════

class SlideRenderer:
    """Renders presentation slides as 1920x1080 PNG images with PIL.

    Supports media overlay: images placed at user-specified positions.
    Richer layouts: table, comparison, insight, bullet (default).
    """

    def __init__(self, theme_name="现代简约", media_map=None):
        self.theme = THEMES.get(theme_name, THEMES["现代简约"])
        self.media_map = media_map or {}

    def render_slides(self, slides_data, output_dir):
        """
        Render all slides to 1920x1080 PNG.

        Args:
            slides_data: list of dicts [{"title", "content", "notes", "media", "layout"}, ...]
            output_dir: output directory for PNGs

        Returns:
            list of (slide_index, png_path_str) tuples
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        results = []

        for i, slide in enumerate(slides_data):
            idx = i + 1
            path = out / f"slide_{idx}.png"
            self._render_single(slide, path, idx)
            results.append((idx, str(path)))

        return results

    def _render_single(self, slide, output_path, slide_num=1):
        """Render one slide with layout-aware rendering.
        Uses special rendering path for GITHUB style (flat dark bg, centered covers, cards).
        """
        t = self.theme
        GITHUB = (t["name"] == "GITHUB \u9879\u76ee\u98ce\u683c")

        # \u2500\u2500 Cover slide \u2500\u2500
        if slide_num == 1:
            if GITHUB:
                img = Image.new("RGB", (W, H), (18, 18, 30))
                draw = ImageDraw.Draw(img)
                title = slide.get("title", "")
                ft = ImageFont.truetype(FONT_BOLD, 72)
                draw.text((W // 2, 300), title, fill=(0, 180, 255), font=ft, anchor="mt")
                draw.text((W // 2, 400), "AI \u751f\u6210\u6f14\u793a\u89c6\u9891", fill=(200, 200, 220),
                          font=ImageFont.truetype(FONT_REG, 36), anchor="mt")
                draw.text((W // 2, 460), "\u57fa\u4e8e\u539f\u59cb\u6587\u6863\u81ea\u52a8\u751f\u6210", fill=(160, 160, 175),
                          font=ImageFont.truetype(FONT_REG, 28), anchor="mt")
                d = draw
                d.line([(W // 2 - 200, 520), (W // 2 + 200, 520)], fill=(0, 180, 255), width=3)
            else:
                img = Image.new("RGB", (W, H), t.get("title_start", t["bg_dark"]))
                draw = ImageDraw.Draw(img)
                gradient_rect(draw, 0, 0, W, H,
                              t.get("title_start", t["bg_dark"]),
                              t.get("cover_end", t.get("title_end", t["bg_light"])))
                font_title = ImageFont.truetype(FONT_BOLD, 56)
                font_sub = ImageFont.truetype(FONT_REG, 28)
                ttl = slide.get("title", "")
                tw = draw.textlength(ttl, font=font_title)
                draw.text(((W - tw) // 2, 300), ttl, fill=(255, 255, 255), font=font_title)
                draw.rectangle([(W//2 - 150, 390), (W//2 + 150, 396)], fill=t.get("accent", (255, 200, 60)))
                draw.text((W//2, 440), "AI \u751f\u6210\u6f14\u793a\u89c6\u9891", fill=(200, 200, 220),
                          font=font_sub, anchor="mt")
            img.save(str(output_path), "PNG")
            return

        # \u2500\u2500 Last (thank you) slide \u2500\u2500
        if slide.get("is_last", False):
            if GITHUB:
                img = Image.new("RGB", (W, H), (18, 18, 30))
                draw = ImageDraw.Draw(img)
                ttl = slide.get("title", "\u8c22\u8c22\u89c2\u770b")
                draw.text((W // 2, 350), ttl, fill=(240, 240, 245),
                          font=ImageFont.truetype(FONT_BOLD, 48), anchor="mt")
                draw.text((W // 2, 440), "\u8c22\u8c22\u89c2\u770b\uff0c\u518d\u89c1", fill=(160, 160, 175),
                          font=ImageFont.truetype(FONT_REG, 28), anchor="mt")
            else:
                img = Image.new("RGB", (W, H), t.get("title_start", t["bg_dark"]))
                draw = ImageDraw.Draw(img)
                gradient_rect(draw, 0, 0, W, H,
                              t.get("title_start", t["bg_dark"]),
                              t.get("cover_end", t.get("title_end", t["bg_light"])))
                font_title = ImageFont.truetype(FONT_BOLD, 48)
                ttl = slide.get("title", "\u8c22\u8c22\u89c2\u770b")
                tw = draw.textlength(ttl, font=font_title)
                draw.text(((W - tw) // 2, 350), ttl, fill=(255, 255, 255), font=font_title)
            img.save(str(output_path), "PNG")
            return

        # \u2500\u2500 Regular content slide \u2500\u2500
        if GITHUB:
            img = Image.new("RGB", (W, H), (18, 18, 30))
            draw = ImageDraw.Draw(img)
            title_h = 80
            draw.rectangle([0, 0, W, title_h + 4], fill=(24, 24, 38))
            draw.rectangle([0, title_h - 4, W, title_h + 2], fill=(0, 180, 255))
            ttl = slide.get("title", "")
            if ttl:
                draw.text((60, 14), ttl, fill=(240, 240, 245),
                          font=ImageFont.truetype(FONT_BOLD, 40))
            content_y = title_h + 20
            content_h = H - content_y - 40
            rounded_rect(draw, 80, content_y - 5, W - 160, content_h + 10,
                         14, fill=(30, 32, 50), outline=(40, 42, 65))
        else:
            img = Image.new("RGB", (W, H), t["bg_light"])
            draw = ImageDraw.Draw(img)
            gradient_rect(draw, 0, 0, W, H, t["bg_dark"], t["bg_light"])
            title_h = 80
            gradient_rect(draw, 0, 0, W, title_h, t.get("title_start", t["bg_dark"]),
                          t.get("title_end", t["bg_light"]))
            draw.rectangle([0, title_h, W, title_h + 4], fill=t.get("accent", (255, 200, 60)))
            ttl = slide.get("title", "")
            if ttl:
                draw.text((40, 20), ttl, fill=(255, 255, 255),
                          font=ImageFont.truetype(FONT_BOLD, 32))
            content_y = title_h + 30
            content_h = H - content_y - 40
            rounded_rect(draw, 50, content_y - 10, W - 100, content_h + 10,
                         12, fill=t["card"], outline=t["card"])

        # Content area setup
        content = slide.get("content", "")
        layout = slide.get("layout", "")
        media = slide.get("media", [])
        has_media_right = any(m.get("position") in ("right", "top-right") for m in media)
        text_max_w = W - 170
        if has_media_right:
            text_max_w = 900

        lines = []
        if content:
            for line in content.split("\n"):
                l = line.strip()
                if not l or l.startswith("===") or l.startswith("MEDIA:"):
                    continue
                lines.append(l)

        text_font = ImageFont.truetype(FONT_REG, 26)
        bold_font = ImageFont.truetype(FONT_BOLD, 26)

        # Route to layout-specific renderer
        if layout == "table":
            self._render_table(draw, lines, content_y, content_h, text_max_w,
                               text_font, bold_font, t)
        elif layout == "comparison":
            self._render_comparison(draw, lines, content_y, content_h, text_max_w,
                                    text_font, bold_font, t)
        elif layout == "insight":
            self._render_insight(draw, lines, content_y, content_h, text_max_w,
                                 text_font, bold_font, t)
        else:
            self._render_bullets(draw, lines, content_y, content_h, text_max_w,
                                 text_font, bold_font, t)

        if media:
            self._overlay_media(img, media)

        draw.text((W - 80, H - 35), str(slide_num),
                  fill=(150, 150, 150) if not GITHUB else (140, 140, 160),
                  font=ImageFont.truetype(FONT_REG, 16))

        img.save(str(output_path), "PNG")

    # ── Layout: bullet list (default) ──

    def _render_bullets(self, draw, lines, content_y, content_h, mw, tf, bf, t):
        """Default bullet-point layout."""
        y = content_y + 15
        x = 95 if t.get("name") == "GITHUB 项目风格" else 70

        for line in lines[:30]:
            if y > content_y + content_h - 30:
                break
            if line.startswith("# "):
                draw.text((x, y), line[2:].strip(), fill=t["subtitle"],
                          font=ImageFont.truetype(FONT_BOLD, 28))
                y += 38
            elif line.startswith("- "):
                text = line[2:].strip()
                draw.text((x, y), "\u25cf", fill=t["accent"],
                          font=ImageFont.truetype(FONT_REG, 22))
                # Wrap if too long
                if draw.textlength(text, font=tf) > mw - 30:
                    self._draw_wrapped(draw, text, x + 25, y, mw, tf, t["text"])
                    y += (len(text) // 40 + 1) * 36 + 4
                else:
                    draw.text((x + 25, y + 2), text, fill=t["text"], font=tf)
                    y += 34
            elif re.match(r'^\d+[\.\)]\s', line):
                m = re.match(r'^(\d+[\.\)])\s*(.*)', line)
                draw.text((x, y), m.group(1), fill=t["subtitle"], font=bf)
                draw.text((x + 40, y + 2), m.group(2), fill=t["text"], font=tf)
                y += 34
            elif line.startswith("## "):
                draw.text((x, y), line[3:].strip(), fill=t["subtitle"],
                          font=ImageFont.truetype(FONT_REG, 26))
                y += 34
            elif line == "---":
                draw.line([(x, y), (x + mw, y)], fill=(200, 200, 200), width=1)
                y += 16
            else:
                draw.text((x, y), line[:60], fill=t["text"], font=tf)
                y += 38

    # ── Layout: data table (like CCM table from GITHUB) ──

    def _render_table(self, draw, lines, content_y, content_h, mw, tf, bf, t):
        """Render data table: first line is header, remainder are rows.
        Rows can use | to separate columns. Status auto-color if ends with ▶/▲/▼."""
        y = content_y + 15
        x_left = 95 if t.get("name") == "GITHUB 项目风格" else 70

        # Parse header row (first # or -- line)
        headers = []
        data_rows = []

        for line in lines:
            if not headers and (line.startswith("# ") or line.startswith("## ")):
                headers = [h.strip() for h in line[2:].split("|")]
                continue
            if "|" in line:
                cells = [c.strip() for c in line.split("|")]
                if len(cells) >= 2:
                    data_rows.append(cells)
                    continue
            # Non-table line, draw as label
            if line.startswith("- "):
                # Draw as section label
                draw.text((x_left + 10, y), line[2:].strip(), fill=t["subtitle"],
                          font=ImageFont.truetype(FONT_BOLD, 24))
                y += 34

        if not data_rows:
            # Fallback to bullet layout
            self._render_bullets(draw, lines, content_y, content_h, mw, tf, bf, t)
            return

        # ── Determine column widths ──
        col_count = max(len(h) if h else 0 for h in headers) if headers else len(data_rows[0])
        if not col_count:
            col_count = len(data_rows[0])
        table_w = mw - 40
        col_w = table_w // max(col_count, 1)

        # ── Header row ──
        if headers:
            h_bg = (t["bg_dark"][0] + 20, t["bg_dark"][1] + 20, t["bg_dark"][2] + 20)
            rounded_rect(draw, x_left, y, table_w, 40, 6, fill=h_bg,
                         outline=t.get("accent", t["subtitle"]))
            cx = x_left + 12
            for h in headers[:col_count]:
                draw.text((cx, y + 8), h, fill=t.get("accent", t["subtitle"]),
                          font=ImageFont.truetype(FONT_BOLD, 20))
                cx += col_w
            y += 48

        # ── Data rows ──
        for i, row in enumerate(data_rows[:12]):
            if y > content_y + content_h - 60:
                break
            row_h = 40
            bg = (t["card"][0] + 5, t["card"][1] + 5, t["card"][2] + 5) if i % 2 == 0 else t["card"]
            outline = (t["bg_dark"][0] - 5, t["bg_dark"][1] - 5, t["bg_dark"][2] - 5)
            rounded_rect(draw, x_left, y, table_w, row_h, 4, fill=bg, outline=outline)

            cx = x_left + 12
            for ci, cell in enumerate(row[:col_count]):
                # Auto-color: check for trend indicators
                cell_color = t["text"]
                cell_font = tf
                stripped = cell.strip()
                if stripped and stripped[0] in ("▲", "↓", "▼", "→", "—", "↑"):
                    if stripped[0] in ("▲", "↑", "↗"):
                        cell_color = STATUS_COLORS["up"]
                    elif stripped[0] in ("▼", "↓", "↘"):
                        cell_color = STATUS_COLORS["down"]
                    elif stripped[0] == "—":
                        cell_color = STATUS_COLORS["neutral"]
                    cell_font = bf
                elif stripped.startswith("+"):
                    cell_color = STATUS_COLORS["up"]
                    cell_font = bf
                elif stripped.startswith("-"):
                    cell_color = STATUS_COLORS["down"]
                    cell_font = bf

                draw.text((cx, y + 8), stripped[:18], fill=cell_color, font=cell_font)
                cx += col_w
            y += row_h + 4

        # ── Insight box at bottom if extra lines remain ──
        insight_lines = [l for l in lines if l.startswith("[INSIGHT]:")]
        if insight_lines:
            box_y = min(y + 20, content_y + content_h - 70)
            self._draw_insight_box(draw, box_y, insight_lines[0][10:].strip(), t)

    # ── Layout: side-by-side comparison (like price targets from GITHUB) ──

    def _render_comparison(self, draw, lines, content_y, content_h, mw, tf, bf, t):
        """Two-column comparison layout. Lines before --- are left, after are right."""
        y = content_y + 15
        x_left = 95 if t.get("name") == "GITHUB 项目风格" else 70

        left_lines, right_lines = [], []
        current = left_lines
        for line in lines:
            if line == "---":
                current = right_lines
                continue
            current.append(line)

        def _draw_card(card_lines, card_x, card_w, start_y, accent_color):
            """Draw one comparison card."""
            card_h = max(250, len(card_lines) * 32 + 60)
            if start_y + card_h > content_y + content_h - 20:
                card_h = content_y + content_h - 20 - start_y
            rounded_rect(draw, card_x, start_y, card_w, card_h, 12,
                         fill=(*[min(255, c + 10) for c in t["card"]],),
                         outline=accent_color)
            cy = start_y + 12
            for cl in card_lines[:12]:
                if cy > start_y + card_h - 25:
                    break
                if cl.startswith("# "):
                    draw.text((card_x + 15, cy), cl[2:].strip(), fill=accent_color,
                              font=ImageFont.truetype(FONT_BOLD, 26))
                    cy += 34
                elif cl.startswith("- "):
                    draw.text((card_x + 15, cy), "\u2022", fill=accent_color,
                              font=ImageFont.truetype(FONT_BOLD, 22))
                    draw.text((card_x + 30, cy + 2), cl[2:].strip()[:40],
                              fill=t["text"], font=tf)
                    cy += 34
                elif cl.startswith("## "):
                    draw.text((card_x + 15, cy), cl[3:].strip(), fill=t["subtitle"],
                              font=bf)
                    cy += 34
                else:
                    draw.text((card_x + 15, cy), cl[:45], fill=t["text"], font=tf)
                    cy += 28

        # Determine card dimensions
        card_w = (W - 180) // 2
        card1_x = x_left
        card2_x = x_left + card_w + 30

        left_color = STATUS_COLORS["up"] if left_lines and "涨" in " ".join(left_lines[1:4]) else t.get("accent", (0, 165, 235))
        right_color = STATUS_COLORS["down"] if right_lines and "跌" in " ".join(right_lines[1:4]) else t.get("subtitle", (80, 90, 170))

        _draw_card(left_lines, card1_x, card_w, y, left_color)
        _draw_card(right_lines, card2_x, card_w, y, right_color)

        # ── Bottom insight box ──
        insight_lines = [l for l in lines if l.startswith("[INSIGHT]:")]
        if insight_lines:
            box_y = min(content_y + content_h - 80, y + max(len(left_lines), len(right_lines)) * 32 + 60)
            if box_y < y + 50:
                box_y = content_y + content_h - 80
            self._draw_insight_box(draw, box_y, insight_lines[0][10:].strip(), t)

    # ── Layout: insight/recommendation ──

    def _render_insight(self, draw, lines, content_y, content_h, mw, tf, bf, t):
        """Insight layout with highlighted recommendation box at bottom."""
        y = content_y + 15
        x_left = 95 if t.get("name") == "GITHUB 项目风格" else 70

        main_lines = []
        insight_lines = []
        in_insight = False

        for line in lines:
            if line == "---" or line.startswith("> "):
                in_insight = True
                if line.startswith("> "):
                    insight_lines.append(line[2:].strip())
            elif in_insight:
                insight_lines.append(line)
            else:
                main_lines.append(line)

        # Main content: bold key points
        for line in main_lines[:10]:
            if y > content_y + content_h - 150:
                break
            if line.startswith("# "):
                draw.text((x_left, y), line[2:].strip(), fill=t["subtitle"],
                          font=ImageFont.truetype(FONT_BOLD, 28))
                y += 38
            elif line.startswith("- "):
                draw.text((x_left, y), "\u25cf", fill=t["accent"],
                          font=ImageFont.truetype(FONT_REG, 22))
                draw.text((x_left + 25, y + 2), line[2:].strip(), fill=t["text"], font=tf)
                y += 32
            else:
                draw.text((x_left, y), line[:60], fill=t["text"], font=tf)
                y += 28

        if insight_lines:
            box_h = min(120, len(insight_lines) * 28 + 40)
            box_y = max(y + 20, content_y + content_h - box_h - 15)
            accent_c = STATUS_COLORS["warn"]  # orange
            rounded_rect(draw, x_left - 10 if t.get("name") != "GITHUB 项目风格" else x_left - 20, box_y, mw + 20 if t.get("name") != "GITHUB 项目风格" else mw + 40, box_h, 10,
                         fill=(60, 50, 35), outline=accent_c)
            draw.text((x_left + 5, box_y + 8), "推荐意见",
                      fill=accent_c, font=ImageFont.truetype(FONT_BOLD, 24))
            for j, il in enumerate(insight_lines[:3]):
                draw.text((x_left + 15, box_y + 40 + j * 26), il[:70],
                          fill=(240, 230, 200), font=tf)

    # ── Helpers ──

    def _draw_insight_box(self, draw, box_y, text, t):
        """Draw a warning/insight box at given y position."""
        rounded_rect(draw, 60, box_y, W - 120, 55, 10,
                     fill=(50, 40, 35), outline=STATUS_COLORS["warn"])
        label = ImageFont.truetype(FONT_BOLD, 22)
        font = ImageFont.truetype(FONT_REG, 20)
        draw.text((80, box_y + 6), "\U0001f6a81fe0f", fill=STATUS_COLORS["warn"], font=label)
        draw.text((115, box_y + 10), text[:65], fill=(230, 220, 200), font=font)

    def _draw_wrapped(self, draw, text, x, y, mw, font, color):
        """Draw wrapped text at position."""
        while text:
            for ws in range(len(text), 0, -1):
                chunk = text[:ws]
                if draw.textlength(chunk, font=font) <= mw - 30 or ws <= 5:
                    break
            draw.text((x, y), text[:ws], fill=color, font=font)
            text = text[ws:]
            y += 34

    # ── Media overlay ──

    def _overlay_media(self, base_img, media_list):
        """Overlay user-provided images onto the slide canvas."""
        for m in media_list:
            fname = m.get("file", "")
            if fname not in self.media_map:
                continue
            media_path = self.media_map[fname]
            if not os.path.exists(media_path):
                continue

            try:
                layer = Image.open(media_path).convert("RGBA")
            except Exception:
                continue

            pos = m.get("position", "right")
            scale = float(m.get("scale", "0.35"))

            lw = int(W * scale)
            lh = int(lw * layer.height / layer.width) if layer.width > 0 else lw
            layer = layer.resize((lw, lh), Image.LANCZOS)

            layout = {
                "right": (W - lw - 60, 160),
                "left": (60, 160),
                "bottom": ((W - lw) // 2, H - lh - 80),
                "full": (50, 140),
                "top-right": (W - lw - 40, 100),
                "center": ((W - lw) // 2, (H - lh) // 2),
            }
            x, y = layout.get(pos, ((W - lw) // 2, (H - lh) // 2))

            if pos == "full":
                lw = W - 100
                lh = int(lw * layer.height / layer.width) if layer.width > 0 else lw
                layer = layer.resize((lw, lh), Image.LANCZOS)
                x, y = 50, 140

            # Clamp
            x = max(10, min(x, W - lw - 10))
            y = max(90, min(y, H - lh - 10))

            if layer.mode == "RGBA":
                base_img.paste(layer, (x, y), layer)
            else:
                base_img.paste(layer, (x, y))

            # Add thin border around overlaid image
            draw = ImageDraw.Draw(base_img)
            draw.rectangle([x, y, x + lw, y + lh], outline=(200, 200, 200, 128), width=2)


# ══════════════════════════════════════════════════════════════════════
#  MEDIA SCANNER & PROMPT BUILDER
# ══════════════════════════════════════════════════════════════════════

def scan_media_folder(folder_path):
    """Scan a folder for supported media files.
    Returns: (media_map: dict {filename: absolute_path}, manifest: str)
    """
    if not folder_path or not os.path.isdir(folder_path):
        return {}, ""

    img_exts = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}
    vid_exts = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
    aud_exts = {'.mp3', '.wav', '.m4a', '.aac', '.ogg'}

    images, videos, audios = [], [], []
    for f in sorted(os.listdir(folder_path)):
        ext = os.path.splitext(f)[1].lower()
        fpath = os.path.join(folder_path, f)
        if not os.path.isfile(fpath):
            continue
        fsize = os.path.getsize(fpath)
        if ext in img_exts:
            images.append((f, fpath, fsize))
        elif ext in vid_exts:
            videos.append((f, fpath, fsize))
        elif ext in aud_exts:
            audios.append((f, fpath, fsize))

    media_map = {}
    manifest_lines = []

    if images:
        manifest_lines.append(f"【素材图片 ({len(images)}个)】")
        for fname, fpath, fsize in images:
            media_map[fname] = fpath
            try:
                im = Image.open(fpath)
                desc = f"{im.width}x{im.height}"
                im.close()
            except Exception:
                desc = "unknown"
            manifest_lines.append(f"  - {fname} ({desc}, {fsize/1024:.0f}KB)")
        manifest_lines.append("")

    if videos:
        manifest_lines.append(f"【素材视频 ({len(videos)}个)】")
        for fname, fpath, fsize in videos:
            media_map[fname] = fpath
            manifest_lines.append(f"  - {fname} ({fsize/1024/1024:.1f}MB)")
        manifest_lines.append("")

    if audios:
        manifest_lines.append(f"【素材音频 ({len(audios)}个)】")
        for fname, fpath, fsize in audios:
            media_map[fname] = fpath
            manifest_lines.append(f"  - {fname} ({fsize/1024:.0f}KB)")
        manifest_lines.append("")

    manifest = "\n".join(manifest_lines)
    return media_map, manifest


# ══════════════════════════════════════════════════════════════════════
#  PARSE MEDIA TAGS FROM AI OUTPUT
# ══════════════════════════════════════════════════════════════════════

def parse_media_tags(slide_content):
    """Extract MEDIA: tags from slide content, return cleaned content + media list."""
    media_list = []
    clean_lines = []
    for line in slide_content.split("\n"):
        if line.startswith("MEDIA:"):
            parts = line[6:].strip().split("|")
            entry = {"file": "", "position": "right", "scale": "0.35"}
            for p in parts:
                p = p.strip()
                if not p:
                    continue
                if "=" in p:
                    k, v = p.split("=", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k in ("file", "position", "scale"):
                        entry[k] = v
                else:
                    if "." in p:
                        entry["file"] = p
            if entry["file"]:
                media_list.append(entry)
        else:
            clean_lines.append(line)
    return "\n".join(clean_lines), media_list