# DocFlow Usage Guide

## Quick Start

1. Install dependencies:
   pip install -r requirements.txt

2. Configure API key:
   cp .env.example .env
   (Edit .env with your DeepSeek API key)

3. Launch:
   python app.py

## GUI Walkthrough

### Main Window (1200x800)

1. Select Input Document - Click "选择文件" to pick PDF or Word
2. Configure Parameters:
   - Duration: 3min / 10min / 20-30min
   - Knowledge Level: 初学者 / 进阶者 / 专家
   - Presentation Style: 课堂 / 快板 / 讲故事 / 对话 / 小说 / 精读 / 速讲 / 学术会议 / 产品推广
   - Slide Theme: 12 themes available
   - TTS Voice: Multiple Chinese voices (Xiaoxiao, Yunjian, Yunyang, etc.)
3. Optional: Toggle "AI审校口播" for AI narration review
4. API Configuration: Click "API配置" to set custom endpoint/model
5. Generate: Click "生成视频" and wait for progress bar

### API Configuration Dialog

- 接口地址: API base URL (default: https://api.deepseek.com)
- 协议类型: OpenAI compatible / Anthropic
- API Key: Your API key
- 模型名称: Model name (default: deepseek-v4-flash)

Config is saved to config.json and persists across sessions.

## Output

- Slides: 1920x1080 PNG files in workspace/slides/
- Audio: edge-tts generated WAV/MP3 in workspace/audio/
- Video: Final MP4 in workspace/output/

## PyInstaller Build

```
pip install pyinstaller
pyinstaller build/DocFlow.spec --noconfirm
```

Output: dist/DocFlow/DocFlow.exe
The entire dist/DocFlow/ folder must be deployed (one-folder build).

## Troubleshooting

| Problem             | Solution                                        |
|---------------------|-------------------------------------------------|
| API key error       | Configure in GUI API dialog or .env file        |
| Video stuttering    | Ensure movie.py has no duplicated code blocks  |
| edge-tts timeout    | Check network; falls back with silence          |
| Missing modules     | Add hidden imports to DocFlow.spec              |
| Chinese garbled     | Ensure msyh.ttc / msyhbd.ttc fonts available    |