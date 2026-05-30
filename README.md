# DocFlow - Document -> Narrated Video Pipeline

> Turn your documents into narrated presentation videos, end to end.

## Features

| Feature            | Description                                          |
|--------------------|------------------------------------------------------|
| AI Presentation Gen| Upload PDF/Word, AI auto-generates slides + narration|
| 9 Speaking Styles  | 课堂 / 快板 / 讲故事 / 对话 / 小说 / 精读 / 速讲 / 学术会议 / 产品推广 |
| 12 Visual Themes   | Modern, Business, Academic, GITHUB Dark, Ink Classic, more |
| AI Narration Review| Auto-clean filler words, optimize flow, control timing|
| Multiple TTS Voices| Xiaoxiao / Yunjian / Yunyang and more Chinese voices |
| HD Output          | 1920x1080 60fps MP4, pure PIL rendering, no GPU needed |
| Flexible API Config| Custom endpoint, protocol, API key, model name        |
| One-click Package  | PyInstaller builds standalone EXE                     |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API key (DeepSeek)
cp .env.example .env
# Edit .env with your API key

# 3. Launch
python app.py
```

## Installation

### Run from source (development)
```bash
git clone <repo-url>
cd DocFlow
pip install -r requirements.txt
python app.py
```

### Run from EXE (packaged)
1. Download DocFlow.zip
2. Extract to any directory
3. Run DocFlow/DocFlow.exe
4. Configure API key in GUI dialog

### Build your own EXE
```bash
pip install pyinstaller
pyinstaller build/DocFlow.spec --noconfirm
```

## Project Structure

```
DocFlow/
  app.py                Main GUI app (CustomTkinter)
  agent.py              AI agent (DeepSeek API)
  movie.py              Video composition engine
  slide_renderer.py     Slide renderer (PIL)
  runtime_hook.py       PyInstaller runtime hook
  build/
    DocFlow.spec        PyInstaller spec
  docs/
    architecture.md     Architecture docs
    usage.md            Usage instructions
  .env.example          Environment template
  .gitignore
  requirements.txt      Python dependencies
  CHANGELOG.md          Version history
  LICENSE               MIT license
  examples/
    screenshot_demo.py  Example: generate a single slide
```

## Tech Stack

| Component           | Technology                          |
|---------------------|-------------------------------------|
| GUI                 | CustomTkinter                       |
| AI                  | DeepSeek API (OpenAI-compatible)    |
| TTS                 | edge-tts (Microsoft Edge)           |
| Slide Rendering     | Pillow (PIL)                        |
| Video Composition   | ffmpeg + moviepy                    |
| Packaging           | PyInstaller                         |
| Document Parsing    | PyMuPDF                             |

## Requirements

- Python 3.10+
- Windows 10/11 (Microsoft YaHei font for Chinese rendering)
- 8GB+ RAM recommended (PyInstaller build needs more)
- DeepSeek API key (sign up at https://platform.deepseek.com/)

## Version History

See [CHANGELOG.md](./CHANGELOG.md)

## Notes

- API key is used locally only, never uploaded to third parties
- Configure API key in GUI on first run
- PyInstaller one-folder mode: deploy the entire dist/DocFlow/ folder
- TTS requires internet; failed chunks fall back to silence

## License

MIT License - Free to use, modify, and distribute