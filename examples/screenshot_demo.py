"""DocFlow GUI Demo"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from slide_renderer import render_slide
slide = {"title": "DocFlow Demo", "content": ["Welcome!"], "layout": "slides", "theme": "GITHUB 项目风格"}
img = render_slide(slide)
img.save("demo_slide.png")
