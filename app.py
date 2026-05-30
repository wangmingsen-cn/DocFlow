#!/usr/bin/env python3
"""
DocFlow — Document → PPT + Voice → Demo Video
Mac-style GUI for the full content repurposing pipeline.
v2.0 — Slide style selector, TTS voice selector, API key config dialog
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import threading
import fitz
import os
import sys
import re
import time
import asyncio
import subprocess
import json

# ── Project path setup ──────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    PROJECT_DIR = os.path.dirname(sys.executable)
else:
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)

# ── API Key: env var > .env > config file ──────────────────────────
CONFIG_FILE = os.path.join(PROJECT_DIR, 'config.json')

def _load_config():
    """Load saved user config."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def _save_config(cfg):
    """Save user config to file."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

user_config = _load_config()
DEFAULT_API_KEY = user_config.get('api_key', os.environ.get('OPENAI_API_KEY', 'YOUR_API_KEY_HERE'))
DEFAULT_API_BASE = user_config.get('api_base', 'https://api.deepseek.com')
DEFAULT_MODEL = user_config.get('model', 'deepseek-v4-flash')

if 'OPENAI_API_KEY' not in os.environ:
    os.environ['OPENAI_API_KEY'] = DEFAULT_API_KEY

# Write .env for agent.py
import dotenv as _dotenv
env_path = os.path.join(PROJECT_DIR, '.env')
with open(env_path, 'w', encoding='utf-8') as f:
    f.write(f"OPENAI_API_KEY={os.environ['OPENAI_API_KEY']}\n")

# ── Import project modules ──────────────────────────────────────────
from agent import generate_presentation, review_narration
from pptm import create_ppt_file, create_ppt_pics
from movie import VideoMaker
from slide_renderer import SlideRenderer, scan_media_folder, parse_media_tags


# ══════════════════════════════════════════════════════════════════════
#  MAC-STYLE THEME
# ══════════════════════════════════════════════════════════════════════

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

MAC_BG      = "#1c1c1e"
MAC_SIDEBAR = "#2c2c2e"
MAC_CARD    = "#3a3a3c"
MAC_ACCENT  = "#0A84FF"
MAC_SUCCESS = "#30D158"
MAC_WARNING = "#FF9F0A"
MAC_DANGER  = "#FF453A"
MAC_TEXT    = "#FFFFFF"
MAC_SUBTEXT = "#8E8E93"
MAC_BORDER  = "#48484a"
MAC_HOVER   = "#4a4a4c"


# ══════════════════════════════════════════════════════════════════════
#  API KEY CONFIGURATION DIALOG
# ══════════════════════════════════════════════════════════════════════

class ApiKeyDialog(ctk.CTkToplevel):
    """Modal dialog for API configuration."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("API 配置")
        self.geometry("520x400")
        self.resizable(False, False)
        self.configure(fg_color=MAC_BG)
        self.transient(parent)
        self.grab_set()

        self.result = None

        # Load current config
        cfg = _load_config()

        # Title
        ctk.CTkLabel(self, text="自定义大模型",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=MAC_TEXT).pack(anchor="w", padx=28, pady=(24, 16))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=28, pady=(0, 16))

        fields = [
            ("接口地址:", "api_base", cfg.get('api_base', DEFAULT_API_BASE)),
            ("API Key:", "api_key", cfg.get('api_key', DEFAULT_API_KEY)),
            ("模型名称:", "model", cfg.get('model', DEFAULT_MODEL)),
        ]

        self.entries = {}
        row = 0
        for label, key, default in fields:
            ctk.CTkLabel(form, text=label,
                         font=ctk.CTkFont(size=13), text_color=MAC_TEXT,
                         anchor="w").grid(row=row, column=0, sticky="w", pady=(0, 10))

            entry = ctk.CTkEntry(form, width=420, height=36,
                                 fg_color=MAC_HOVER, border_color=MAC_BORDER,
                                 text_color=MAC_TEXT, font=ctk.CTkFont(size=13))
            entry.insert(0, default)
            entry.grid(row=row+1, column=0, sticky="w", pady=(0, 16))
            self.entries[key] = entry
            row += 2

        # Test connection button
        self.test_btn = ctk.CTkButton(form, text="测试连接", width=120,
                                      fg_color=MAC_HOVER, command=self._test_connection)
        self.test_btn.grid(row=row, column=0, sticky="w", pady=(0, 8))

        self.test_label = ctk.CTkLabel(form, text="", font=ctk.CTkFont(size=12), text_color=MAC_SUCCESS)
        self.test_label.grid(row=row+1, column=0, sticky="w", pady=(0, 0))
        row += 2

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=28, pady=(0, 20))

        ctk.CTkButton(btn_frame, text="取消", width=100,
                      fg_color=MAC_HOVER, command=self.destroy).pack(side="right", padx=(8, 0))

        ctk.CTkButton(btn_frame, text="确定", width=100,
                      fg_color=MAC_ACCENT, command=self._confirm).pack(side="right")

    def _test_connection(self):
        """Test API connection with current settings."""
        from openai import OpenAI
        api_key = self.entries['api_key'].get().strip()
        api_base = self.entries['api_base'].get().strip()
        model = self.entries['model'].get().strip()

        self.test_label.configure(text="正在测试...", text_color=MAC_SUBTEXT)
        self.test_btn.configure(state="disabled")
        self.update()

        def do_test():
            try:
                client = OpenAI(base_url=api_base, api_key=api_key)
                client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=5
                )
                self.after(0, lambda: self.test_label.configure(
                    text="✅ 连接成功！", text_color=MAC_SUCCESS))
            except Exception as e:
                self.after(0, lambda: self.test_label.configure(
                    text=f"❌ 失败: {str(e)[:60]}", text_color=MAC_DANGER))
            finally:
                self.after(0, lambda: self.test_btn.configure(state="normal"))

        threading.Thread(target=do_test, daemon=True).start()

    def _confirm(self):
        """Save settings and close."""
        self.result = {
            'api_base': self.entries['api_base'].get().strip(),
            'api_key': self.entries['api_key'].get().strip(),
            'model': self.entries['model'].get().strip(),
        }
        cfg = _load_config()
        cfg.update({
            'api_base': self.result['api_base'],
            'api_key': self.result['api_key'],
            'model': self.result['model'],
        })
        _save_config(cfg)

        # Update env for current session
        os.environ['OPENAI_API_KEY'] = self.result['api_key']
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(f"OPENAI_API_KEY={self.result['api_key']}\n")

        self.destroy()


# ══════════════════════════════════════════════════════════════════════
#  TTS VOICE & SLIDE STYLE CHOICES
# ══════════════════════════════════════════════════════════════════════

TTS_VOICE_CHOICES = list(VideoMaker.TTS_VOICE_MAP.keys()) if hasattr(VideoMaker, 'TTS_VOICE_MAP') else \
    ["温柔女声 (Xiaoxiao)", "平稳男声 (Yunxi)", "有力男声 (Yunjian)",
     "亲切女声 (Xiaoyi)", "沉稳男声 (Yunyang)"]

SLIDE_STYLE_CHOICES = ["现代简约", "商务专业", "学术论文", "创意彩色", "深色主题", "清新留白", "GITHUB 项目风格", "墨色经典", "靛蓝瓷", "森林墨", "牛皮纸", "沙丘"]
STYLE_CHOICES = ["课堂", "快板", "讲故事", "对话", "小说", "精读", "速讲", "学术会议", "产品推广"]


# ══════════════════════════════════════════════════════════════════════
#  CORE PIPELINE ENGINE
# ══════════════════════════════════════════════════════════════════════

class PipelineEngine:
    """Orchestrates the full Document to Video pipeline."""

    def __init__(self, log_callback=None, progress_callback=None, step_callback=None):
        self.log = log_callback or print
        self.progress = progress_callback or (lambda v: None)
        self.step_cb = step_callback or (lambda s: None)
        self.cancelled = False
        self.output_dir = None
        self.work_dir = None

        # User-configurable options
        self.duration = "10分钟"
        self.knowledge_level = "进阶者"
        self.presentation_style = "课堂"
        self.slide_style = "现代简约"
        self.tts_voice_display = "温柔女声 (Xiaoxiao)"
        self.api_key = DEFAULT_API_KEY
        self.api_base = DEFAULT_API_BASE
        self.model = DEFAULT_MODEL
        self.enable_review = True
        # Multi-modal source & media folder support
        self.media_folder = ""
        self.media_map = {}
        self.media_manifest = ""
        self.source_type = "文本"

    @property
    def tts_voice(self):
        """Get edge-tts voice name from display name."""
        return VideoMaker.TTS_VOICE_MAP.get(self.tts_voice_display, VideoMaker.DEFAULT_VOICE)

    def cancel(self):
        self.cancelled = True

    def load_media_folder(self, folder_path):
        """Scan media folder and update manifest."""
        self.media_folder = folder_path
        self.media_map, self.media_manifest = scan_media_folder(folder_path)
        if self.media_map:
            self.log("素材文件夹: %d 个文件" % len(self.media_map))
            for fname in self.media_map:
                self.log("    - " + fname)
            return True
        else:
            self.log("素材文件夹中未发现支持的图片/视频/音频文件")
            return False

    def _check_cancel(self):
        if self.cancelled:
            raise InterruptedError("Pipeline cancelled by user")

    def extract_pdf(self, pdf_path: str) -> str:
        self.step_cb("\U0001f4c4 提取文档文本...")
        self.log(f"正在读取: {Path(pdf_path).name}")
        doc = fitz.open(pdf_path)
        all_text = []
        total_pages = len(doc)
        for i, page in enumerate(doc):
            self._check_cancel()
            text = page.get_text("text")
            if text.strip():
                all_text.append(text.strip())
            self.progress((i + 1) / total_pages * 0.1)
            if (i + 1) % 5 == 0 or i == total_pages - 1:
                self.log(f"  已提取 {i+1}/{total_pages} 页...")
        doc.close()
        full_text = "\n\n".join(all_text)
        self.log(f"✅ 文本提取完成，共 {len(full_text)} 字符，{total_pages} 页")
        return full_text

    def extract_docx(self, docx_path: str) -> str:
        self.step_cb("\U0001f4c4 提取文档文本...")
        self.log(f"正在读取: {Path(docx_path).name}")
        try:
            from docx import Document
            doc = Document(docx_path)
            all_text = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            full_text = "\n\n".join(all_text)
            self.log(f"✅ 文本提取完成，共 {len(full_text)} 字符")
            return full_text
        except ImportError:
            self.log("尝试使用 Word COM 提取...")
            import win32com.client
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(os.path.abspath(docx_path))
            text = doc.Content.Text
            doc.Close()
            word.Quit()
            self.log(f"✅ 文本提取完成，共 {len(text)} 字符")
            return text

    def extract_image(self, img_path: str) -> str:
        self.log("正在分析图片内容...")
        try:
            from agent import ai_agent
            prompt = (
                "请详细描述这张图片的内容。包括:\n"
                "1. 图片的主题和核心内容\n"
                "2. 图中出现的文字信息（如果有）\n"
                "3. 图表的类型和数据趋势（如果是图表）\n"
                "4. 图片的风格和色彩\n"
                "请用中文详细描述，不少于200字。"
            )
            result = ai_agent("分析图片: " + img_path + "\n\n" + prompt)
            self.log("图片AI分析完成")
            return result
        except Exception as e:
            self.log(f"图片分析失败，使用基础描述: {e}")
            return f"[图片文件: {os.path.basename(img_path)}]"

    def extract_video(self, vid_path: str) -> str:
        self.log("正在分析视频文件...")
        try:
            import subprocess
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", vid_path],
                capture_output=True, text=True, timeout=30
            )
            import json
            data = json.loads(result.stdout) if result.stdout else {}
            dur = float(data.get('format', {}).get('duration', 0))
            duration = f"时长: {int(dur/60)}分{int(dur%60)}秒" if dur else ''
            resolution = ''
            for s in data.get('streams', []):
                if s.get('codec_type') == 'video':
                    w, h = s.get('width', 0), s.get('height', 0)
                    resolution = f"分辨率: {w}x{h}"

            fname = os.path.basename(vid_path)
            size = os.path.getsize(vid_path) / 1024 / 1024
            return (f'[视频文件: {fname} ({size:.1f}MB)]\n'
                    f'{duration}\n{resolution}\n'
                    f'请根据文件名和视频属性为这个视频配一段介绍。')
        except Exception as e:
            self.log(f"视频分析: {e}")
            return f'[视频文件: {os.path.basename(vid_path)}]'

    def extract_audio(self, aud_path: str) -> str:
        fname = os.path.basename(aud_path)
        size = os.path.getsize(aud_path) / 1024 / 1024
        self.log(f"音频文件: {fname} ({size:.1f}MB)")
        return (
            f'[音频文件: {fname} ({size:.1f}MB)]\n'
            f'请根据文件名推测这个音频的主题，生成一套幻灯片框架介绍。'
        )

    def generate_slides_with_notes(self, content: str) -> list:
        self._check_cancel()
        max_input = 28000
        if len(content) > max_input:
            self.log(f"文本过长 ({len(content)} 字符)，截取前 {max_input} 字符")
            content = content[:max_input]

        cfg_str = (f"时长:{self.duration} 水平:{self.knowledge_level} "
                   f"风格:{self.presentation_style} 版式:{self.slide_style}")
        self.log(f"配置: {cfg_str}")

        self.step_cb("AI 生成幻灯片内容和口播备注...")
        self.log("正在调用 DeepSeek 生成逐页内容...")
        self.progress(0.15)

        try:
            cfg = _load_config()
            slides = generate_presentation(
                content,
                duration=self.duration,
                knowledge_level=self.knowledge_level,
                presentation_style=self.presentation_style,
                slide_style=self.slide_style,
                api_key=cfg.get('api_key', self.api_key),
                api_base=cfg.get('api_base', self.api_base),
                media_manifest=self.media_manifest,
                source_type=self.source_type,
            )
            self.log(f"幻灯片内容生成完成，共 {len(slides)} 页")
            for i, s in enumerate(slides):
                notes_preview = s.get('notes', '')[:40]
                media_cnt = len(s.get('media', []))
                media_str = f' [{media_cnt}图]' if media_cnt else ''
                self.log(f"    第 {i+1} 页: {s['title'][:30]}{media_str} -> {notes_preview}...")

            # \u2500\u2500             # ---- AI Review step (if enabled) ----
            if getattr(self, 'enable_review', True):
                self.step_cb("AI 审校口播...")
                self.log("正在 AI 审校口播内容（去水词+优化流畅度+时长控制）...")
                total_min = 25 if self.duration == "20~30分钟" else (10 if self.duration == "10分钟" else 3)
                cfg = _load_config()
                try:
                    slides = review_narration(
                        slides,
                        total_duration_minutes=total_min,
                        api_key=cfg.get('api_key') or self.api_key,
                        api_base=cfg.get('api_base') or self.api_base,
                    )
                    total_note_time = sum(s.get('notes_duration_s', 10) for s in slides)
                    self.log(f"✅ 审校完成，估算口播总时长: {total_note_time:.0f}秒 ({total_note_time/60:.1f}分钟)")
                except Exception as e:
                    import traceback
                    self.log(f"⚠️ AI 审校失败: {e}，使用原始口播")
                    traceback.print_exc()
        except Exception as e:
            self.log(f"幻灯片生成失败: {e}")
            slides = self._fallback_slides(content)
        self.progress(0.45)
        self._check_cancel()
        return slides

    def _fallback_slides(self, content: str) -> list:
        lines = [l.strip() for l in content.split('\n') if l.strip() and len(l.strip()) > 2]
        slides = []
        if not lines:
            lines = ['无法提取文档内容']
        first = lines[0][:50]
        slides.append({
            'title': first,
            'content': f'# {first}',
            'notes': f'今天我们来分享{first}的内容。'
        })
        chunk_size = max(1, min(4, len(lines) // 4))
        chunks = [lines[i:i+chunk_size] for i in range(1, len(lines), chunk_size)]
        for i, chunk in enumerate(chunks[:12]):
            chunk_text = ''.join(f'- {l[:120]}\n' for l in chunk)
            topic = chunk[0][:40]
            notes_text = chunk[0][:150].replace('\n', '').replace('  ', ' ')
            slides.append({
                'title': topic,
                'content': f'## {topic}\n{chunk_text}',
                'notes': f'接下来我们看：{notes_text}'
            })
        slides.append({
            'title': '总结',
            'content': '# 总结\n- 以上是对文档内容的自动提取\n- 更多细节请参考原文',
            'notes': '以上就是这次分享的全部内容，感谢您的观看。如果对内容有疑问，欢迎随时交流。'
        })
        return slides

    def generate_ppt_with_notes(self, slides: list) -> str:
        self._check_cancel()
        self.step_cb("幻灯片渲染...")
        self.log("正在渲染幻灯片图片...")
        self.progress(0.55)

        pic_dir = os.path.join(self.work_dir, 'pic')
        os.makedirs(pic_dir, exist_ok=True)

        # Primary: PIL-based rendering (no PowerPoint dependency)
        try:
            renderer = SlideRenderer(
                theme_name=self.slide_style,
                media_map=self.media_map
            )
            # Mark last slide
            if len(slides) > 1:
                slides[-1]["is_last"] = True
            results = renderer.render_slides(slides, pic_dir)
            self.log("PIL渲染完成: %d 张幻灯片" % len(results))
        except Exception as e:
            self.log("PIL渲染失败: %s, 尝试 PPTX 导出..." % e)
            # Fallback: PPTX + COM export
            self.log("正在生成 PowerPoint 演示文稿...")
            md_lines = []
            for s in slides:
                title = s.get('title', '幻灯片')
                c = s.get('content', '')
                md_lines.append('# ' + title)
                for line in c.split('\n'):
                    stripped = line.strip()
                    if stripped and not stripped.startswith('#') and not stripped.startswith('===NOTES===') and not stripped.startswith('MEDIA:'):
                        md_lines.append('  ' + stripped)
                md_lines.append('')
                md_lines.append('---')
                md_lines.append('')

            md_path = os.path.join(self.work_dir, 'slides.md')
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(md_lines))

            ppt_path = os.path.join(self.work_dir, 'presentation.pptx')
            notes_list = [s.get('notes', '') for s in slides]

            create_ppt_file(md_path, ppt_path, notes_list=notes_list, slide_style=self.slide_style)
            create_ppt_pics(ppt_path, pic_dir)

        # Verify slides
        count = len([f for f in os.listdir(pic_dir) if f.endswith('.png')])
        self.log("共 %d 张幻灯片图片" % count)

        # Ensure 1920x1080
        try:
            from PIL import Image as PIL_Image
            for f in os.listdir(pic_dir):
                if f.endswith('.png'):
                    fp = os.path.join(pic_dir, f)
                    img = PIL_Image.open(fp)
                    if img.size != (1920, 1080):
                        img_resized = img.resize((1920, 1080), PIL_Image.LANCZOS)
                        img_resized.save(fp)
            self.log("已调整图片至 1920x1080")
        except Exception as e:
            self.log("图片尺寸调整失败: " + str(e))

        self.progress(0.80)
        self._check_cancel()
        ppt_path = os.path.join(self.work_dir, 'presentation.pptx')
        return ppt_path

    def generate_video_from_notes(self, slides: list) -> str:
        self._check_cancel()
        self.step_cb("\U0001f3ac 生成演示视频...")
        self.log("正在逐页生成语音视频...")
        self.progress(0.85)
        pic_dir = os.path.join(self.work_dir, 'pic')
        output_video = os.path.join(self.output_dir, 'demo_video.mp4')
        slide_notes = []
        for i, s in enumerate(slides):
            notes = s.get('notes', '')
            slide_idx = i + 1
            img_path = os.path.join(pic_dir, f"slide_{slide_idx}.png")
            if os.path.exists(img_path) and notes.strip():
                slide_notes.append((slide_idx, notes.strip()))
        self.log(f"准备处理 {len(slide_notes)} 页有口播备注的幻灯片...")
        try:
            maker = VideoMaker(
                image_dir=pic_dir,
                output_path=output_video,
                slide_notes=slide_notes,
                font_path=os.path.join(PROJECT_DIR, 'fzss.ttf'),
                resolution=(1920, 1080),
                voice_speed=1.0,
                stage=3,
                tts_voice=self.tts_voice,
            )
            result = maker.generate_video()
            if result:
                self.log(f"视频生成完成: {result}")
            else:
                self.log("视频生成可能不完整")
        except Exception as e:
            self.log(f"视频生成失败: {e}")
            import traceback
            self.log(traceback.format_exc())
            return ""
        self.progress(1.0)
        return output_video

    def run(self, input_path: str, output_dir: str) -> str:
        """Execute the complete pipeline."""
        self.cancelled = False
        self.output_dir = output_dir
        self.work_dir = os.path.join(PROJECT_DIR, 'workspace')
        os.makedirs(self.work_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        ext = Path(input_path).suffix.lower()
        img_exts = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}
        vid_exts = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        aud_exts = {'.mp3', '.wav', '.m4a', '.aac', '.ogg'}
        try:
            if ext == '.pdf':
                self.source_type = '文本'
                content = self.extract_pdf(input_path)
            elif ext in ('.docx', '.doc'):
                self.source_type = '文本'
                content = self.extract_docx(input_path)
            elif ext == '.txt':
                self.source_type = '文本'
                with open(input_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.log(f"✅ 文本读取完成，共 {len(content)} 字符")
            elif ext in img_exts:
                self.source_type = '图片'
                content = self.extract_image(input_path)
            elif ext in vid_exts:
                self.source_type = '视频'
                content = self.extract_video(input_path)
            elif ext in aud_exts:
                self.source_type = '音频'
                content = self.extract_audio(input_path)
            else:
                raise ValueError(f"不支持的文件格式: {ext}")
            if not content.strip():
                raise ValueError("文档内容为空")
            self._check_cancel()
            slides = self.generate_slides_with_notes(content)
            self._check_cancel()
            ppt_path = self.generate_ppt_with_notes(slides)
            self._check_cancel()
            video_path = self.generate_video_from_notes(slides)
            self.step_cb("完成！")
            self.log("\n全流程完成！")
            self.log(f"   PPT: {ppt_path}")
            self.log(f"   视频: {video_path}")
            return video_path
        except InterruptedError:
            self.log("\n⏹️ 用户取消了操作")
            return ""
        except Exception as e:
            self.log(f"\n❌ 流水线执行失败: {e}")
            import traceback
            self.log(traceback.format_exc())
            return ""


# ══════════════════════════════════════════════════════════════════════
#  GUI APPLICATION (1200x800)
# ══════════════════════════════════════════════════════════════════════

class DocFlowApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DocFlow — 文档转演示视频")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        self.configure(fg_color=MAC_BG)
        try:
            icon_path = os.path.join(PROJECT_DIR, 'icon.ico')
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except:
            pass

        self.engine = PipelineEngine(
            log_callback=self.append_log,
            progress_callback=self.update_progress,
            step_callback=self.update_step
        )
        self.pipeline_thread = None
        self.input_file = None
        self.output_dir = r"C:\Users\29494\Desktop\transporter"
        self.video_path = None

        self._build_ui()
        self._reset_steps()

    # ═══════════════ UI BUILD ════════════════

    def _build_ui(self):
        self._build_sidebar()
        self._build_main_area()

    # ── SIDEBAR ──

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=MAC_SIDEBAR)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.pack(pady=(28, 6), padx=20, fill="x")
        ctk.CTkLabel(logo_frame, text="📽️", font=ctk.CTkFont(size=32)).pack(anchor="w")
        ctk.CTkLabel(logo_frame, text="DocFlow", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=MAC_TEXT).pack(anchor="w", pady=(6, 0))
        ctk.CTkLabel(logo_frame, text="文档 → PPT → 演示视频",
                     font=ctk.CTkFont(size=11), text_color=MAC_SUBTEXT).pack(anchor="w", pady=(2, 0))

        ctk.CTkFrame(sidebar, height=1, fg_color=MAC_BORDER).pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(sidebar, text="工作流程", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=MAC_SUBTEXT).pack(anchor="w", padx=24, pady=(0, 8))

        self.step_labels = {}
        steps = [("step1", "📄", "提取文档文本"), ("step2", "🤖", "AI 内容转换"),
                 ("step3", "📊", "生成幻灯片"), ("step4", "🎬", "合成演示视频")]
        for key, icon, label in steps:
            frame = ctk.CTkFrame(sidebar, fg_color="transparent", height=34)
            frame.pack(fill="x", padx=12, pady=1)
            frame.pack_propagate(False)
            dot = ctk.CTkLabel(frame, text="○", font=ctk.CTkFont(size=14),
                               text_color=MAC_SUBTEXT, width=24)
            dot.pack(side="left", padx=(6, 2))
            text = ctk.CTkLabel(frame, text=f"{icon}  {label}", font=ctk.CTkFont(size=13),
                                text_color=MAC_SUBTEXT, anchor="w")
            text.pack(side="left", fill="x", expand=True)
            self.step_labels[key] = (dot, text)

        ctk.CTkFrame(sidebar, fg_color="transparent").pack(expand=True)

        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=20, pady=16)
        ctk.CTkLabel(footer, text="v2.0 · DocFlow", font=ctk.CTkFont(size=10),
                     text_color=MAC_SUBTEXT).pack(anchor="w")

    # ── MAIN AREA ──

    def _build_main_area(self):
        main = ctk.CTkFrame(self, fg_color=MAC_BG, corner_radius=0)
        main.pack(side="left", fill="both", expand=True)

        # Scrollable container for all cards
        container = ctk.CTkScrollableFrame(main, fg_color="transparent", corner_radius=0)
        container.pack(fill="both", expand=True)

        # ── Header ──
        ctk.CTkLabel(container, text="文档转演示视频",
                     font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=MAC_TEXT).pack(anchor="w", padx=32, pady=(24, 4))
        ctk.CTkLabel(container, text="上传 PDF 或 Word 文档，AI 自动生成 PPT 幻灯片和讲解视频",
                     font=ctk.CTkFont(size=12), text_color=MAC_SUBTEXT
                     ).pack(anchor="w", padx=32, pady=(0, 14))

        # ── File Card ──
        file_card = ctk.CTkFrame(container, corner_radius=14, fg_color=MAC_CARD,
                                 border_width=1, border_color=MAC_BORDER)
        file_card.pack(fill="x", padx=32, pady=(0, 10))

        finner = ctk.CTkFrame(file_card, fg_color="transparent")
        finner.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(finner, text="📁", font=ctk.CTkFont(size=28)).pack(side="left", padx=(0, 12))
        finfo = ctk.CTkFrame(finner, fg_color="transparent")
        finfo.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(finfo, text="选择源文档", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=MAC_TEXT).pack(anchor="w")
        self.file_label = ctk.CTkLabel(finfo, text="未选择文件 (支持 PDF / DOCX / TXT)",
                                       font=ctk.CTkFont(size=12), text_color=MAC_SUBTEXT)
        self.file_label.pack(anchor="w", pady=(2, 0))
        self.btn_select = ctk.CTkButton(finner, text="选择文件", width=100, height=34,
                                        corner_radius=9, fg_color=MAC_ACCENT,
                                        font=ctk.CTkFont(size=13), command=self._select_file)
        self.btn_select.pack(side="right", padx=(8, 0))

        # ── Output Card ──
        out_card = ctk.CTkFrame(container, corner_radius=14, fg_color=MAC_CARD,
                                border_width=1, border_color=MAC_BORDER)
        out_card.pack(fill="x", padx=32, pady=(0, 10))

        oinner = ctk.CTkFrame(out_card, fg_color="transparent")
        oinner.pack(fill="x", padx=20, pady=14)
        ctk.CTkLabel(oinner, text="📂", font=ctk.CTkFont(size=28)).pack(side="left", padx=(0, 12))
        oinfo = ctk.CTkFrame(oinner, fg_color="transparent")
        oinfo.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(oinfo, text="输出目录", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=MAC_TEXT).pack(anchor="w")
        self.out_label = ctk.CTkLabel(oinfo, text=self.output_dir,
                                      font=ctk.CTkFont(size=11), text_color=MAC_SUBTEXT)
        self.out_label.pack(anchor="w", pady=(2, 0))
        self.btn_out = ctk.CTkButton(oinner, text="更改", width=80, height=34,
                                     corner_radius=9, fg_color=MAC_HOVER,
                                     font=ctk.CTkFont(size=13), command=self._select_output)
        self.btn_out.pack(side="right", padx=(8, 0))

        # ── API Key Button Row ──
        api_card = ctk.CTkFrame(container, corner_radius=14, fg_color=MAC_CARD,
                                border_width=1, border_color=MAC_BORDER)
        api_card.pack(fill="x", padx=32, pady=(0, 10))
        api_inner = ctk.CTkFrame(api_card, fg_color="transparent")
        api_inner.pack(fill="x", padx=20, pady=14)

        ctk.CTkLabel(api_inner, text="🔑", font=ctk.CTkFont(size=24)
                     ).pack(side="left", padx=(0, 12))
        ai_frame = ctk.CTkFrame(api_inner, fg_color="transparent")
        ai_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(ai_frame, text="AI 大模型配置",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=MAC_TEXT).pack(anchor="w")
        cfg = _load_config()
        model_name = cfg.get('model', 'deepseek-v4-flash')
        api_base = cfg.get('api_base', DEFAULT_API_BASE)
        model_label = f"模型: {model_name} | {api_base}"
        self.api_model_label = ctk.CTkLabel(ai_frame, text=model_label,
                                            font=ctk.CTkFont(size=11), text_color=MAC_SUBTEXT)
        self.api_model_label.pack(anchor="w", pady=(2, 0))
        self.btn_api = ctk.CTkButton(api_inner, text="API 设置", width=80, height=34,
                                     corner_radius=9, fg_color=MAC_HOVER,
                                     font=ctk.CTkFont(size=13), command=self._open_api_settings)
        self.btn_api.pack(side="right", padx=(8, 0))

        # ── Configuration Card (3 rows) ──
        cfg_card = ctk.CTkFrame(container, corner_radius=14, fg_color=MAC_CARD,
                                border_width=1, border_color=MAC_BORDER)
        cfg_card.pack(fill="x", padx=32, pady=(0, 10))

        cfg_inner = ctk.CTkFrame(cfg_card, fg_color="transparent")
        cfg_inner.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(cfg_inner, text="⚙️ 配置",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=MAC_TEXT).pack(anchor="w", pady=(0, 14))

        # Row 1: Duration + Knowledge Level + Style
        row1 = ctk.CTkFrame(cfg_inner, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(row1, text="时长:", font=ctk.CTkFont(size=13),
                     text_color=MAC_TEXT, width=50).pack(side="left")
        self.duration_var = ctk.StringVar(value="10分钟")
        ctk.CTkOptionMenu(row1, variable=self.duration_var,
                          values=["3分钟", "10分钟", "20~30分钟"],
                          fg_color=MAC_HOVER, button_color=MAC_ACCENT,
                          font=ctk.CTkFont(size=13), width=120
                          ).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(row1, text="水平:", font=ctk.CTkFont(size=13),
                     text_color=MAC_TEXT, width=50).pack(side="left")
        self.level_var = ctk.StringVar(value="进阶者")
        ctk.CTkOptionMenu(row1, variable=self.level_var,
                          values=["初学者", "进阶者", "专家"],
                          fg_color=MAC_HOVER, button_color=MAC_ACCENT,
                          font=ctk.CTkFont(size=13), width=120
                          ).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(row1, text="风格:", font=ctk.CTkFont(size=13),
                     text_color=MAC_TEXT, width=50).pack(side="left")
        self.style_var = ctk.StringVar(value="课堂")
        ctk.CTkOptionMenu(row1, variable=self.style_var,
                          values=STYLE_CHOICES,
                          fg_color=MAC_HOVER, button_color=MAC_ACCENT,
                          font=ctk.CTkFont(size=13), width=140
                          ).pack(side="left")

        # Row 2: Slide Style + TTS Voice
        row2 = ctk.CTkFrame(cfg_inner, fg_color="transparent")
        row2.pack(fill="x")

        ctk.CTkLabel(row2, text="版式:", font=ctk.CTkFont(size=13),
                     text_color=MAC_TEXT, width=50).pack(side="left")
        self.slide_style_var = ctk.StringVar(value="现代简约")
        ctk.CTkOptionMenu(row2, variable=self.slide_style_var,
                          values=SLIDE_STYLE_CHOICES,
                          fg_color=MAC_HOVER, button_color=MAC_ACCENT,
                          font=ctk.CTkFont(size=13), width=150
                          ).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(row2, text="TTS:", font=ctk.CTkFont(size=13),
                     text_color=MAC_TEXT, width=50).pack(side="left")
        self.tts_voice_var = ctk.StringVar(value=VideoMaker.DEFAULT_VOICE_DISPLAY)
        ctk.CTkOptionMenu(row2, variable=self.tts_voice_var,
                          values=TTS_VOICE_CHOICES,
                          fg_color=MAC_HOVER, button_color=MAC_ACCENT,
                          font=ctk.CTkFont(size=13), width=180
                          ).pack(side="left")

        # Row 3: AI Review toggle
        row3 = ctk.CTkFrame(cfg_inner, fg_color="transparent")
        row3.pack(fill="x", pady=(4, 0))
        self.review_var = ctk.BooleanVar(value=True)
        self.review_check = ctk.CTkCheckBox(row3, text="AI 审校口播（去水词+优化流畅度+时长控制）",
                                             variable=self.review_var,
                                             font=ctk.CTkFont(size=12),
                                             text_color=MAC_SUBTEXT,
                                             fg_color=MAC_ACCENT,
                                             hover_color=MAC_HOVER,
                                             checkmark_color=MAC_TEXT,
                                             border_color=MAC_BORDER)
        self.review_check.pack(side="left")

        # ── Progress Card ──
        prog_card = ctk.CTkFrame(container, corner_radius=14, fg_color=MAC_CARD,
                                 border_width=1, border_color=MAC_BORDER)
        prog_card.pack(fill="x", padx=32, pady=(0, 10))

        pinner = ctk.CTkFrame(prog_card, fg_color="transparent")
        pinner.pack(fill="x", padx=20, pady=14)

        self.step_label = ctk.CTkLabel(pinner, text="准备就绪",
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       text_color=MAC_SUBTEXT)
        self.step_label.pack(anchor="w", pady=(0, 8))
        self.progress_bar = ctk.CTkProgressBar(pinner, height=10, corner_radius=5,
                                               fg_color=MAC_BORDER, progress_color=MAC_ACCENT)
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)
        self.progress_pct = ctk.CTkLabel(pinner, text="0%", font=ctk.CTkFont(size=11),
                                         text_color=MAC_SUBTEXT)
        self.progress_pct.pack(anchor="e", pady=(4, 0))

        # ── Generate Button ──
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", padx=32, pady=(0, 10))
        self.btn_generate = ctk.CTkButton(btn_frame, text="▶  开始生成", height=48,
                                          corner_radius=12, fg_color=MAC_ACCENT,
                                          font=ctk.CTkFont(size=16, weight="bold"),
                                          command=self._start_pipeline)
        self.btn_generate.pack(fill="x")

        # ── Log Area ──
        log_card = ctk.CTkFrame(container, corner_radius=14, fg_color=MAC_CARD,
                                border_width=1, border_color=MAC_BORDER)
        log_card.pack(fill="both", expand=True, padx=32, pady=(0, 24))

        lh = ctk.CTkFrame(log_card, fg_color="transparent")
        lh.pack(fill="x", padx=16, pady=(10, 4))
        ctk.CTkLabel(lh, text="📋 运行日志", font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=MAC_SUBTEXT).pack(side="left")

        self.log_text = ctk.CTkTextbox(log_card, corner_radius=0, fg_color=MAC_CARD,
                                       border_width=0, font=ctk.CTkFont(size=12, family="Consolas"),
                                       text_color=MAC_TEXT, wrap="word", height=160)
        self.log_text.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.log_text.insert("end", "欢迎使用 DocFlow！请选择源文档开始。\n")
        self.log_text.configure(state="disabled")

    # ── UI Actions ──

    def _select_file(self):
        path = filedialog.askopenfilename(
            title="选择源文档",
            filetypes=[("文档文件", "*.pdf *.docx *.doc *.txt"),
                       ("PDF 文件", "*.pdf"), ("Word 文档", "*.docx *.doc"),
                       ("文本文件", "*.txt"), ("所有文件", "*.*")])
        if path:
            self.input_file = path
            self.file_label.configure(text=Path(path).name, text_color=MAC_TEXT)
            self.append_log(f"已选择: {Path(path).name}")

    def _select_output(self):
        path = filedialog.askdirectory(title="选择输出目录", initialdir=self.output_dir or "")
        if path:
            self.output_dir = path
            self.out_label.configure(text=path, text_color=MAC_TEXT)

    def _open_api_settings(self):
        dialog = ApiKeyDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            cfg = _load_config()
            model_name = cfg.get('model', 'deepseek-v4-flash')
            api_base = cfg.get('api_base', DEFAULT_API_BASE)
            self.api_model_label.configure(text=f"模型: {model_name} | {api_base}")
            self.append_log(f"API 已更新: {model_name} @ {api_base}")

    def _start_pipeline(self):
        if not self.input_file:
            messagebox.showwarning("提示", "请先选择源文档文件")
            return
        if self.pipeline_thread and self.pipeline_thread.is_alive():
            messagebox.showwarning("提示", "正在运行中")
            return
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except Exception as e:
            messagebox.showerror("错误", f"无法创建输出目录:\n{e}")
            return

        self._reset_steps()
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self.progress_bar.set(0)
        self.progress_pct.configure(text="0%")
        self.btn_generate.configure(text="⏹  停止", fg_color=MAC_DANGER, command=self._stop_pipeline)

        # Build engine with current config
        cfg = _load_config()
        self.engine = PipelineEngine(
            log_callback=self.append_log,
            progress_callback=self.update_progress,
            step_callback=self.update_step
        )
        self.engine.duration = self.duration_var.get()
        self.engine.knowledge_level = self.level_var.get()
        self.engine.presentation_style = self.style_var.get()
        self.engine.slide_style = self.slide_style_var.get()
        self.engine.tts_voice_display = self.tts_voice_var.get()
        self.engine.api_key = cfg.get('api_key', DEFAULT_API_KEY)
        self.engine.api_base = cfg.get('api_base', DEFAULT_API_BASE)
        self.engine.model = cfg.get('model', DEFAULT_MODEL)
        self.engine.source_type = getattr(self, 'source_type_var', None).get() if hasattr(self, 'source_type_var') else '文本'
        self.engine.enable_review = self.review_var.get()

        # Load media folder if set
        media_folder = getattr(self, 'media_folder', None) or (getattr(self, 'media_folder_var', None).get() if hasattr(self, 'media_folder_var') else '')
        if media_folder:
            self.engine.load_media_folder(media_folder)

        cfg_str = f"{self.engine.duration} / {self.engine.knowledge_level} / {self.engine.presentation_style} / {self.engine.slide_style}"
        if self.engine.media_map:
            cfg_str += f" | 素材:{len(self.engine.media_map)}个"
        self.append_log(f"配置: {cfg_str}")

        self.pipeline_thread = threading.Thread(target=self._run_pipeline_thread, daemon=True)
        self.pipeline_thread.start()

    def _stop_pipeline(self):
        self.engine.cancel()
        self.append_log("\n⏹️ 正在停止...")

    def _run_pipeline_thread(self):
        try:
            video_path = self.engine.run(self.input_file, self.output_dir)
            self.video_path = video_path
        except Exception as e:
            self.append_log(f"\n❌ 严重错误: {e}")
        finally:
            self.after(0, self._pipeline_done)

    def _pipeline_done(self):
        self.btn_generate.configure(text="▶  开始生成", fg_color=MAC_ACCENT, command=self._start_pipeline)
        self.pipeline_thread = None
        if self.video_path and os.path.exists(self.video_path):
            self._show_success()
        elif not self.engine.cancelled:
            self.step_label.configure(text="❌ 生成失败", text_color=MAC_DANGER)

    def _show_success(self):
        self.step_label.configure(text="✅ 生成完成！", text_color=MAC_SUCCESS)
        self.progress_bar.set(1)
        self.progress_pct.configure(text="100%")
        self.btn_generate.configure(fg_color=MAC_SUCCESS)
        self.after(2000, lambda: self.btn_generate.configure(fg_color=MAC_ACCENT))
        if messagebox.askyesno("完成", "视频生成完成！\n\n是否打开输出文件夹？"):
            os.startfile(self.output_dir)

    def _reset_steps(self):
        for key, (dot, text) in self.step_labels.items():
            dot.configure(text="○", text_color=MAC_SUBTEXT)
            text.configure(text_color=MAC_SUBTEXT)

    def update_step(self, step_text: str):
        self.after(0, lambda: self.step_label.configure(text=step_text, text_color=MAC_TEXT))
        step_map = {"提取": "step1", "AI": "step2", "幻灯片": "step3", "演示": "step4"}
        for kw, key in step_map.items():
            if kw in step_text:
                dot, label = self.step_labels[key]
                dot.configure(text="●", text_color=MAC_ACCENT)
                label.configure(text_color=MAC_TEXT)
                break

    def update_progress(self, value: float):
        self.after(0, lambda: self.progress_bar.set(value))
        self.after(0, lambda: self.progress_pct.configure(text=f"{int(value * 100)}%"))

    def append_log(self, message: str):
        self.after(0, lambda: self._do_append_log(message))

    def _do_append_log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


# ══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

def main():
    app = DocFlowApp()
    app.mainloop()

if __name__ == "__main__":
    main()