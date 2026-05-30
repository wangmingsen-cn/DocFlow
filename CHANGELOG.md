# Changelog

## v2.3 (2026-05-30) - Stuttering Fix & Final Polish
- **Fixed:** Video stuttering caused by duplicated TTS processing code in `_tts_single()`
- **Fixed:** Audio glitches at video segment boundaries (switched from `-c copy` to concat filter with re-encode)
- **Fixed:** `voice_speed` parameter now properly passed to edge-tts as rate string (e.g., "+0%")
- **Fixed:** TTS chunk processing - each chunk has independent error handling with 1s silence fallback
- **Improved:** PyInstaller build stability, reduced output size

## v2.2 (2026-05-24) - Theme Expansion & GUI Polish
- **Added:** 5 new slide themes: 墨色经典, 靛蓝瓷, 森林墨, 牛皮纸, 沙丘
- **Fixed:** All theme deduplication and syntax errors in slide_renderer.py
- **Fixed:** Slide style choices now properly synced with app.py dropdown
- **Fixed:** TTS chunking -- WAV-based concat to avoid MP3 boundary issues
- **Fixed:** API key fallback in review_narration

## v2.1 (2026-05-23) - AI Review & GitHub Style
- **Added:** AI narration review (review_narration function) to clean up filler words
- **Added:** "GITHUB 项目风格" slide theme (dark background, cyan accents)
- **Fixed:** config.json missing path for PyInstaller frozen builds
- **Fixed:** EXE deployment -- one-folder builds require entire directory

## v2.0 (2026-05-22) - UI Redesign
- **Added:** 9 presentation styles (课堂/快板/讲故事/对话/小说/精读/速讲/学术会议/产品推广)
- **Added:** TTS voice selector (Xiaoxiao, Yunjian, Yunyang, etc.)
- **Added:** API key configuration dialog (base URL, protocol, key, model)
- **Added:** Slide style selector (6 themes + GitHub style)
- **Added:** Duration selector (3/10/20-30 min) and knowledge level selector
- **Fixed:** TTS stuttering -- removed aggressive silenceremove filter
- **Fixed:** UI window expanded to 1200x800

## v1.0 (2026-05-21) - Initial Release
- PDF -> AI-generated slides + narration -> MP4 video pipeline
- Basic PyInstaller packaging
- edge-tts Chinese TTS support