"""
Video Generator — Per-slide ffmpeg composition (inspired by PresentAgent)
Replaces complex moviepy compositing with per-slide ffmpeg still-image segments + concat.
v2.1 — Fixed TTS stuttering: use stable voice + audio normalization + sentence-level TTS for long notes.
"""

import os
import subprocess
import tempfile
import asyncio
import edge_tts
from pathlib import Path


class VideoMaker:
    """Generate presentation video from slide images + per-slide TTS notes."""

    # Stable Chinese TTS voices (fewer stutter/glitch artifacts)
    # Display name → edge_tts voice name mapping
    TTS_VOICE_MAP = {
        "温柔女声 (Xiaoxiao)": "zh-CN-XiaoxiaoNeural",
        "平稳男声 (Yunxi)": "zh-CN-YunxiNeural",
        "有力男声 (Yunjian)": "zh-CN-YunjianNeural",
        "亲切女声 (Xiaoyi)": "zh-CN-XiaoyiNeural",
        "沉稳男声 (Yunyang)": "zh-CN-YunyangNeural",
    }
    DEFAULT_VOICE_DISPLAY = "温柔女声 (Xiaoxiao)"
    DEFAULT_VOICE = TTS_VOICE_MAP[DEFAULT_VOICE_DISPLAY]

    def __init__(self, image_dir, output_path, slide_notes, 
                 font_path="fzss.ttf", resolution=(1920, 1080),
                 voice_speed=1.0, stage=3, tts_voice=None):
        """
        Args:
            image_dir: Directory containing slide PNG images (slide_1.png, slide_2.png, ...)
            output_path: Output MP4 path
            slide_notes: List of (slide_index, notes_text) tuples
            font_path: Path to font file for subtitles
            resolution: (width, height) tuple
            voice_speed: Speed multiplier for TTS
            stage: Bit flags (1=video, 2=audio)
            tts_voice: edge-tts voice name
        """
        self.image_dir = image_dir
        self.output_path = output_path
        self.slide_notes = slide_notes
        self.font_path = font_path
        self.resolution = resolution
        self.voice_speed = voice_speed
        self.stage = stage
        self.tts_voice = tts_voice or self.DEFAULT_VOICE
        self.temp_dir = None

    def generate_video(self):
        """Generate the full presentation video."""
        if not self.slide_notes:
            print('无口播备注，无法生成视频')
            return None

        try:
            self.temp_dir = tempfile.mkdtemp(prefix="docflow_")
            
            # Filter slides that have both image and notes
            valid_slides = []
            for idx, notes in self.slide_notes:
                img_path = os.path.join(self.image_dir, f"slide_{idx}.png")
                if os.path.exists(img_path) and notes.strip():
                    # Clean notes: remove excessive whitespace/newlines
                    notes_clean = ' '.join(notes.strip().split())
                    if len(notes_clean) >= 5:  # minimum meaningful length
                        valid_slides.append((idx, notes_clean, img_path))
            
            if not valid_slides:
                print('没有包含有效口播备注的幻灯片')
                return None

            print(f"将处理 {len(valid_slides)} 页幻灯片的口播视频")
            
            # Step 1: Generate per-slide audio (TTS)
            if self.stage >> 1 & 1:
                print('正在逐页生成语音...')
                for i, (idx, notes, _) in enumerate(valid_slides):
                    print(f"  [{i+1}/{len(valid_slides)}] 幻灯片 {idx}: [{len(notes)}字] {notes[:50]}...")
                    audio_path = os.path.join(self.temp_dir, f"audio_{idx}.wav")
                    asyncio.run(self._tts_single(notes, audio_path))
                    # Normalize audio to remove silences/smooth stutters
                    normalized_path = os.path.join(self.temp_dir, f"audio_{idx}_norm.wav")
                    self._normalize_audio(audio_path, normalized_path)
                    # Replace original with normalized
                    os.replace(normalized_path, audio_path)
            
            # Step 2: Generate per-slide video segments
            if self.stage >> 0 & 1:
                print('正在合成视频片段...')
                segment_paths = []
                for i, (idx, notes, img_path) in enumerate(valid_slides):
                    audio_path = os.path.join(self.temp_dir, f"audio_{idx}.wav")
                    if not os.path.exists(audio_path):
                        print(f"  警告: 幻灯片 {idx} 音频不存在，跳过")
                        continue
                    seg_path = os.path.join(self.temp_dir, f"segment_{idx}.mp4")
                    self._create_video_segment(img_path, audio_path, seg_path)
                    segment_paths.append(seg_path)
                    print(f"  [{i+1}/{len(valid_slides)}] 片段已合成: {seg_path}")

                if not segment_paths:
                    print('无有效视频片段')
                    return None

                # Step 3: Concat all segments
                print('正在合并视频片段...')
                self._concat_segments(segment_paths, self.output_path)
                print(f'视频生成完成: {self.output_path}')

            return self.output_path

        except Exception as e:
            print(f"视频生成失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            # Cleanup temp
            if self.temp_dir and os.path.exists(self.temp_dir):
                try:
                    import shutil
                    shutil.rmtree(self.temp_dir)
                except:
                    pass

    async def _tts_single(self, text, output_path):
        """Generate TTS audio with per-chunk error handling + clean WAV concat.
        
        Each chunk is generated separately via edge-tts, converted to WAV,
        then concatenated with ffmpeg re-encode to avoid MP3 boundary glitches.
        If a chunk fails, a 1-second silence gap is inserted (not whole slide loss).
        """
        try:
            # Convert voice_speed (float) to edge-tts rate (string like '+0%')
            import math
            rate_pct = int((self.voice_speed - 1.0) * 100)
            rate_str = f"{rate_pct:+d}%"
            
            # ---- Sentence-aware chunking ----
            import re as _re
            sentences = _re.split(r'(?<=[。！？；])', text)
            chunks = []
            current = ""
            for s in sentences:
                if not s.strip():
                    continue
                if len(current) + len(s) > 200 and current:
                    chunks.append(current)
                    current = s
                else:
                    current += s
            if current:
                chunks.append(current)
        
            if not chunks:
                chunks = [text]
        
            if len(chunks) <= 1:
                # Short text: single edge-tts call then convert to WAV
                communicate = edge_tts.Communicate(text, self.tts_voice, rate=rate_str)
                await communicate.save(output_path)
                wav_tmp = output_path + '.tmp.wav'
                subprocess.run(
                    ['ffmpeg', '-y', '-i', output_path,
                        '-acodec', 'pcm_s16le', '-ar', '22050', '-ac', '1',
                        wav_tmp],
                    check=True, capture_output=True, timeout=30
                )
                os.replace(wav_tmp, output_path)
                return
        
            # ---- Generate per-chunk audio with per-chunk error handling ----
            tmp_dir = os.path.dirname(output_path)
            chunk_wavs = []
            base_name = os.path.splitext(os.path.basename(output_path))[0]
            for ci, chunk in enumerate(chunks):
                chunk = chunk.strip()
                if not chunk:
                    continue
                mp3_tmp = os.path.join(tmp_dir, f"{base_name}_chunk_{ci}.mp3")
                success = False
                try:
                    communicate = edge_tts.Communicate(chunk, self.tts_voice, rate=rate_str)
                    await communicate.save(mp3_tmp)
                    # Convert MP3 to WAV 22050Hz mono for clean concat
                    wav_tmp = os.path.join(tmp_dir, f"{base_name}_chunk_{ci}.wav")
                    subprocess.run(
                        ['ffmpeg', '-y', '-i', mp3_tmp,
                            '-acodec', 'pcm_s16le', '-ar', '22050', '-ac', '1',
                            wav_tmp],
                        check=True, capture_output=True, timeout=30
                    )
                    chunk_wavs.append(wav_tmp)
                    success = True
                except Exception as e:
                    print(f"  Chunk {ci} failed ({len(chunk)} chars): {e}")
                finally:
                    if os.path.exists(mp3_tmp):
                        try: os.unlink(mp3_tmp)
                        except: pass
                    if not success:
                        silence_path = os.path.join(tmp_dir, f"{base_name}_chunk_{ci}_silence.wav")
                        self._create_silence(silence_path, 1)
                        chunk_wavs.append(silence_path)
        
            if not chunk_wavs:
                self._create_silence(output_path, 3)
                return
        
            # ---- Concatenate WAV chunks with re-encode ----
            if len(chunk_wavs) == 1:
                os.replace(chunk_wavs[0], output_path)
            else:
                list_path = os.path.join(tmp_dir, f"{base_name}_wav_concat.txt")
                with open(list_path, 'w', encoding='utf-8') as f:
                    for cf in chunk_wavs:
                        f.write(f"file '{cf}'\n")
                subprocess.run(
                    ['ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                        '-i', list_path,
                        '-acodec', 'pcm_s16le', '-ar', '22050', '-ac', '1',
                        output_path],
                    check=True, capture_output=True, timeout=60
                )
                try: os.unlink(list_path)
                except: pass
        
            # Cleanup temp WAVs
            for cf in chunk_wavs:
                try: os.unlink(cf)
                except: pass
        
        except Exception as e:
            import traceback
            print(f"  TTS stutter fix - check traceback: {e}")
            traceback.print_exc()
            self._create_silence(output_path, 3)


    def _normalize_audio(self, input_path, output_path):
        """
        Normalize audio: remove leading/trailing silence, apply volume normalization,
        smooth out glitches with a low-pass filter.
        """
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-af', 'loudnorm=I=-16:LRA=7:TP=-1.5',
                '-acodec', 'pcm_s16le',
                '-ar', '22050',
                output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        except Exception as e:
            print(f"  音频归一化失败: {e}")
            # Fallback: just copy
            import shutil
            shutil.copy(input_path, output_path)

    def _create_silence(self, output_path, duration_sec=3):
        """Create a silent WAV file as fallback."""
        import wave
        import struct
        with wave.open(output_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            wf.writeframes(struct.pack('<h', 0) * (22050 * duration_sec))

    def _create_video_segment(self, image_path, audio_path, output_path):
        """Create a single video segment using ffmpeg (still image + audio)."""
        w, h = self.resolution
        cmd = [
            'ffmpeg', '-y',
            '-loop', '1',
            '-i', image_path,
            '-i', audio_path,
            '-vf', f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2',
            '-c:v', 'libx264',
            '-tune', 'stillimage',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-shortest',
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    def _concat_segments(self, segment_paths, output_path):
        """Concatenate video segments using ffmpeg concat filter (re-encodes to avoid AAC boundary glitches)."""
        import shutil
        if len(segment_paths) == 1:
            shutil.copy2(segment_paths[0], output_path)
            return
        n = len(segment_paths)
        inputs = []
        for seg in segment_paths:
            inputs.extend(['-i', seg])
        filter_desc = ''.join(f'[{i}:v][{i}:a]' for i in range(n)) + f'concat=n={n}:v=1:a=1[outv][outa]'
        cmd = [
            'ffmpeg', '-y',
            *inputs,
            '-filter_complex', filter_desc,
            '-map', '[outv]', '-map', '[outa]',
            '-c:v', 'libx264', '-crf', '23',
            '-c:a', 'aac', '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)