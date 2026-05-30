# DocFlow Architecture

## Overview

DocFlow is a Python desktop application that transforms PDF/Word documents into narrated video presentations. The pipeline:

Document -> AI Slides + Narration -> PIL Render (1920x1080) -> ffmpeg Compose -> MP4

## Module Map

```
app.py               CustomTkinter GUI (1200x800), user controls
agent.py             DeepSeek AI agent: slide content + narration generation
slide_renderer.py    PIL-based renderer, 12 themes, 4 layout types
movie.py             Video composition: TTS (edge-tts) + slides -> MP4
runtime_hook.py      PyInstaller runtime bootstrap
```

### app.py (~51KB)
- CustomTkinter GUI with threading for non-blocking pipeline
- Config management (API key, model, style preferences) via config.json
- File picker for PDF/Word input
- PipelineEngine class orchestrates: generate -> render -> compose

### agent.py (~25KB)
- DeepSeek API client with 9 presentation styles
- Slide content generator with structured output (layout commands)
- Narration generator with narrative flow (opening -> transition -> conclusion)
- review_narration() - AI post-processing to remove filler words
- Configurable API endpoint, protocol (OpenAI-compatible), model

### slide_renderer.py (~33KB)
- Pure PIL rendering at 1920x1080, no OpenCV/GPU needed
- 12 themes: 7 original + 5 from guizang-ppt-skill
- 4 layout types: slides, table, comparison, insight
- Auto word wrap with Chinese-aware text fitting
- Card-style data tables with color-coded status (up/down indicators)

### movie.py (~14KB)
- Sentence-aware TTS chunking (<=200 chars per chunk, split on Chinese punctuation)
- edge-tts with async streaming, independent error handling per chunk
- 1-second silence fallback for failed chunks
- ffmpeg concat filter with re-encode (no audio artifacts)
- voice_speed float -> rate string conversion for edge-tts

## Data Flow

1. User selects PDF/Word -> PipelineEngine._start_pipeline()
2. agent.py generates slide content + narration in parallel
3. slide_renderer.py renders each slide as 1920x1080 PNG
4. Slide PNGs -> video segments (5s per slide with Ken Burns zoom)
5. Narration text -> TTS audio via edge-tts (chunked, WAV concat)
6. Video segments + TTS audio -> final MP4 via ffmpeg concat filter
7. Optional AI narration review step (toggle in GUI)

## Key Design Decisions

- No silenceremove: TTS audio is pure speech; silenceremove destroys it
- Re-encode concat: Using ffmpeg concat filter (not -c copy) avoids AAC encoder delay glitches
- Single try/except per method: Prevents duplicated code blocks that cause audio corruption
- Rate string conversion: edge-tts expects rate strings like "+0%", not floats