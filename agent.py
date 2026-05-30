#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Agent module — Multi-dimensional presentation generation engine.
  - Duration: 3min / 10min / 20-30min
  - Knowledge level: beginner / intermediate / expert
  - Style: 课堂/快板/讲故事/对话/小说/精读/速讲/学术会议/产品推广
  - Slide style: 现代简约/商务专业/学术论文/创意彩色/深色主题/清新留白
  - Media manifest: user-provided images/videos/audio for slide placement
"""

from openai import OpenAI
import dotenv as _dotenv
import os
import re

# ── Load environment ─────────────────────────────────────────────────
_script_dir = os.path.dirname(os.path.abspath(__file__))
_dotenv.load_dotenv(os.path.join(_script_dir, '.env'))

client = OpenAI(
    base_url='https://api.deepseek.com',
    api_key=os.getenv('OPENAI_API_KEY')
)


# ══════════════════════════════════════════════════════════════════════
#  STYLE LIBRARY
# ══════════════════════════════════════════════════════════════════════

DURATIONS = {
    "3分钟":      {"slides": 5,  "depth": "精炼"},
    "10分钟":     {"slides": 10, "depth": "中等"},
    "20~30分钟":  {"slides": 16, "depth": "详尽"},
}

KNOWLEDGE_LEVELS = {
    "初学者": "假设听众对该领域完全陌生，使用通俗语言解释每个概念，多用比喻和类比，避免专业术语",
    "进阶者": "假设听众有基本了解，适当使用专业术语，重点放在方法论和实践上",
    "专家":   "假设听众是该领域专业人士，直接使用行业术语，聚焦前沿进展和深度分析",
}

PRESENTATION_STYLES = {
    "课堂": {
        "desc": "严谨的教学风格，逻辑层次分明，适合知识传授",
        "notes_hint": "使用正式但平易近人的语气，像老师在课堂讲解，每页口播30-60字，逻辑清晰，可适当提问引导思考",
        "slide_hint": "每页一个核心概念，配合示例说明，结构清晰",
    },
    "快板": {
        "desc": "节奏明快、押韵有趣的脱口秀风格",
        "notes_hint": "使用押韵、排比、短句，节奏明快，像说快板或脱口秀，每页口播15-30字，轻松有活力",
        "slide_hint": "标题醒目，内容简洁有力，多用短句",
    },
    "讲故事": {
        "desc": "叙事驱动，如讲故事一般引人入胜",
        "notes_hint": "用故事化的叙述方式，有起承转合和场景描写，每页口播40-70字，让听众有沉浸感",
        "slide_hint": "配合故事节奏，每页揭示一个情节要点",
    },
    "对话": {
        "desc": "以对话问答形式推进内容",
        "notes_hint": "以问答或双人对话形式推进，一问一答，自然流畅，每页口播30-50字",
        "slide_hint": "每页呈现一个核心问题及其答案",
    },
    "小说": {
        "desc": "用小说章节式的语言包装知识",
        "notes_hint": "用小说式的描写和叙事，有场景设定、人物视角，每页口播40-70字，文学性强",
        "slide_hint": "标题像小说章节名，有悬念感",
    },
    "精读": {
        "desc": "逐段深入剖析，适合深度阅读内容",
        "notes_hint": "逐句解读和分析，深入浅出，每页口播50-80字，引用原文关键句并给出深度解读",
        "slide_hint": "正文引用原文精华，下方给出点评和解读",
    },
    "速讲": {
        "desc": "高度浓缩，只讲干货的极简风格",
        "notes_hint": "极致简洁，只说核心结论，每页口播15-25字，语速快",
        "slide_hint": "每页只有一个核心信息，可用加粗大字呈现",
    },
    "学术会议": {
        "desc": "严谨的学术报告风格，适合学术会议展示",
        "notes_hint": "使用规范的学术语言，引用数据和研究结果，每页口播30-50字，客观严谨",
        "slide_hint": "包含数据、图表和引用标注，格式规范",
    },
    "产品推广": {
        "desc": "产品发布和推广的营销风格",
        "notes_hint": "有感染力的营销语言，突出价值和差异化，每页口播30-50字，号召性强",
        "slide_hint": "突出卖点和用户价值，用对比和案例增强说服力",
    },
}

SLIDE_STYLES = {
    "现代简约": "简洁干净，大量留白，使用现代无衬线字体排版",
    "商务专业": "蓝色基调的商务风格，标题栏和内容区分明确，有企业感",
    "学术论文": "学术报告风格，包含引用标注和图表区域，适合论文展示",
    "创意彩色": "使用鲜明色彩和创意布局，适合创新主题展示",
    "深色主题": "深色背景+亮色文字的暗黑风格，有科技感",
    "清新留白": "大量留白+柔和色彩，极简主义，阅读体验轻松",
    "GITHUB 项目风格": "深色背景(18,18,30)暗蓝基调，卡片式布局(30,32,50)，青色强调(0,180,255)，橙色高亮(255,165,0)，红绿趋势标记。数据表格交替行色，左右对比双卡片，推荐/见解用橙色高亮框。标题居中，正文24px微软雅黑。"
}


# ══════════════════════════════════════════════════════════════════════
#  SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════════════

PPT_SYSTEM_PROMPT = """你是专业的中文演示文稿设计师和内容策略师。

【语言规则——必须严格遵守】
1. 源文档使用中文撰写，你全部输出——幻灯片标题、正文、口播备注——必须使用纯中文。
2. 口播备注中绝对不允许出现任何英文单词或英文术语。如果概念在原文中是英文（如"peak"、"underlying trend"、"trading cycle"等），你必须翻译成对应的中文（如"峰值"、"潜在趋势"、"交易周期"）。
3. 幻灯片标题和正文也必须是纯中文。仅在极少数无法翻译的专有名词（如"Sentient Trader"等品牌名）时可以保留英文，但必须用中文括号附加解释。
4. 任何非中文输出都视为严重错误。

【工作流程】
将源文档转化为逐页的幻灯片内容和口播备注：
1. 分析源文档，提炼核心叙事主线
2. 根据要求的幻灯片数量规划页面序列
3. 为每一页同时生成幻灯片内容和口播备注
4. 确保每一页有单一主题、一个核心信息，上下页之间自然衔接

【素材使用】
如果用户提供了素材文件，请仔细阅读每页的素材列表，将合适的素材插入到对应的幻灯片中。
素材应在幻灯片中引用并描述，在口播中提及该素材。

【输出格式】
每页使用：
- 幻灯片内容（Markdown格式：标题用 # 一级标题，要点用 - 无序列表）
- 单独一行 `===NOTES===` 作为分隔标记
- 口播备注段落（纯中文自然口语段落，不含任何英文单词）
- `---` 作为幻灯片之间的分隔符

【布局类型——对每页内容选择合适布局】
如果该页内容适合用数据表格展示（如多行多列数据），在幻灯片内容开头添加：
    该页布局类型：table
如果内容适合做左右对比（如优劣对比、两个方案对比），在开头添加：
    该页布局类型：comparison
如果是推荐/建议/见解类内容，添加：
    该页布局类型：insight
默认不加（使用要点列表布局）。

【口播连贯性要求——非常重要】
请按以下结构组织所有页的口播，从第一页到最后一页形成一个完整、连贯的讲解：
1. 第一页（封面）：开场介绍主题，引起观众兴趣，概述今天要讲什么
2. 中间页：每页开头要有一句承上启下的过渡句（如"了解了XX之后，让我们来看XX"），
   口播要自然、口语化，像真人讲解一样有节奏感
3. 最后一页（总结）：总结核心要点，给出行动建议或思考方向，收尾

口播整体必须像一场完整的中文演讲，不允许有"下面我们来看第X页"这种机械性表述。
禁止在口播中出现任何英文单词，所有英文术语必须翻译成对应中文。"""


# ══════════════════════════════════════════════════════════════════════
#  MEDIA PROMPT BUILDER
# ══════════════════════════════════════════════════════════════════════

def build_media_prompt(media_manifest, source_type="文本"):
    """Build the AI prompt section for media placement guidance."""
    if not media_manifest or not media_manifest.strip():
        return ""

    if source_type.startswith("图片"):
        return f"""
【来源说明】
源文档是图片文件。请根据提供的图片描述和内容生成幻灯片。

【用户提供的素材文件】
{media_manifest}

【素材使用指令】
仔细查看上述素材列表。在生成每页幻灯片时，如果某个素材适合在当前页面展示，
请在幻灯片内容之后、===NOTES=== 之前添加一行：
    MEDIA: 文件名|position=位置|scale=比例

位置参数：right（右侧，默认）/ left（左侧）/ bottom（底部）/ center（居中）/ full（全幅）
比例：0.1~0.8（占画布宽度比例）

例如：若 chart.png 适合在第3页展示：
    MEDIA: chart.png|position=right|scale=0.4

每页最多放1个 MEDIA 行。如果某页没有合适素材就不加。
在口播备注中要自然提及该素材并做解说。
"""
    elif source_type.startswith("视频"):
        return f"""
【来源说明】
源文档是视频文件。已从视频中提取关键帧作为参考。

【用户提供的素材文件】
{media_manifest}

【素材使用指令】
如果素材列表中的图片适合放在某页幻灯片中，请添加：
    MEDIA: 文件名|position=位置|scale=比例

位置：right/left/bottom/center/full  比例：0.1~0.8
在口播备注中自然解说该素材内容。
"""
    else:
        return f"""
【用户提供的素材文件】
{media_manifest}

【素材使用指令】
仔细查看上述素材文件。在生成每页幻灯片时，如果列表中的图片适合在当前幻灯片中展示，
请在幻灯片内容之后、===NOTES=== 之前添加一行：
    MEDIA: 文件名|position=right|scale=0.35

参数：position=right/left/bottom/center/full  scale=0.1~0.8
每页最多1个 MEDIA 行。不适用就不加。
在口播中要自然提及该素材并对它进行解说。
"""


# ══════════════════════════════════════════════════════════════════════
#  USER PROMPT BUILDER
# ══════════════════════════════════════════════════════════════════════

def build_prompt(document_text, duration="10分钟", knowledge_level="进阶者",
                 presentation_style="课堂", slide_style="现代简约",
                 media_manifest="", source_type="文本"):
    """Build the full user prompt for AI presentation generation."""
    dur = DURATIONS.get(duration, DURATIONS["10分钟"])
    kl = KNOWLEDGE_LEVELS.get(knowledge_level, KNOWLEDGE_LEVELS["进阶者"])
    ps = PRESENTATION_STYLES.get(presentation_style, PRESENTATION_STYLES["课堂"])
    ss = SLIDE_STYLES.get(slide_style, SLIDE_STYLES["现代简约"])

    slide_count = dur["slides"]
    depth = dur["depth"]
    media_prompt = build_media_prompt(media_manifest, source_type)

    prompt = f"""请将以下源文档转换成一套完整的中文演示文稿。

【源文档】
{document_text}

【输出要求】
生成 {slide_count} 页幻灯片，覆盖文档的核心内容。目标时长约 {3 if duration == "3分钟" else (10 if duration == "10分钟" else 25)} 分钟。

【幻灯片设计原则】
1. 每一页必须有明确的单一主题
2. 幻灯片内容用简洁的列表或短句，方便投影展示
3. 第一页是封面，最后一页是总结/致谢
4. 使用 `===NOTES===` 分隔幻灯片内容和口播备注
5. 使用 `---` 分隔不同幻灯片（单独一行）

【口播叙事结构】
整个口播要像一场流畅的演讲，而非机械翻页：
- 第一页（封面）：自然开场，介绍主题和背景
- 中间页：每页用一句话承上启下，让听众感觉在听故事而不是翻PPT
- 最后一页：总结升华，给出行动方向
- 口播要口语化、自然，像真人讲师在讲解
- 禁止使用"接下来我们看第X页"这种机械表述
- 全部使用中文，无任何英文单词

【口播备注要求——非常重要】
- 每页口播备注是演示者要朗读的讲稿，必须是纯中文自然段落
- 禁止出现任何英文单词——所有英文术语必须翻译成中文
- 不包含任何Markdown标记、符号或格式化字符

【配置参数】
听众知识水平：{knowledge_level}
{kl}

讲解风格：{presentation_style}
{ps['desc']}
口播语气要求：{ps['notes_hint']}
幻灯片风格要求：{ps['slide_hint']}

幻灯片视觉风格：{slide_style}
{ss}

总体深度：{depth}，{slide_count}页幻灯片

{media_prompt}
请严格按照以下格式输出，不要添加任何额外说明文字：

（对于数据表格页面，在内容开头加一行：LAYOUT: table）
（对于左右对比页面，在内容开头加一行：LAYOUT: comparison）
（对于重点推荐页面，在内容开头加一行：LAYOUT: insight）

# 幻灯片标题
- 要点 1
- 要点 2
===NOTES===
（纯中文口播备注内容）
---
# 下一张幻灯片标题
..."""

    return prompt


# ══════════════════════════════════════════════════════════════════════
#  CORE API
# ══════════════════════════════════════════════════════════════════════

def generate_presentation(text, duration="10分钟", knowledge_level="进阶者",
                          presentation_style="课堂", slide_style="现代简约",
                          api_key=None, api_base=None,
                          media_manifest="", source_type="文本"):
    """Generate per-slide content with speaker notes.

    Args:
        text: Source document text
        duration: 3分钟/10分钟/20~30分钟
        knowledge_level: 初学者/进阶者/专家
        presentation_style: 课堂/快板/讲故事/对话/小说/精读/速讲/学术会议/产品推广
        slide_style: 现代简约/商务专业/学术论文/创意彩色/深色主题/清新留白
        api_key: Optional custom API key override
        api_base: Optional custom API base URL override
        media_manifest: String describing available media files for AI placement
        source_type: 文本/图片/视频/音频
    Returns:
        list of dicts [{"title": str, "content": str, "notes": str, "media": [...]}, ...]
    """
    max_input = 28000
    if len(text) > max_input:
        text = text[:max_input]

    prompt = build_prompt(text, duration, knowledge_level,
                          presentation_style, slide_style,
                          media_manifest, source_type)

    # Use custom client if custom API settings provided
    llm_client = client
    if api_key and api_key != os.getenv('OPENAI_API_KEY'):
        llm_client = OpenAI(
            base_url=api_base or 'https://api.deepseek.com',
            api_key=api_key
        )

    response = llm_client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": PPT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        stream=False,
        max_tokens=16384,
    )

    full_text = response.choices[0].message.content
    slides = parse_slides(full_text)
    return slides


def parse_slides(markdown_text):
    """Robust parser for AI slide output. Also strips MEDIA tags to separate field."""
    slides = []

    # Strategy 1: Split by --- separator
    slide_blocks = re.split(r'\n-{3,}\n', markdown_text)

    if len(slide_blocks) < 2:
        # Strategy 2: Try splitting by # headings
        slide_blocks = re.split(r'(?=^#\s+)', markdown_text, flags=re.MULTILINE)
        slide_blocks = [b.strip() for b in slide_blocks if b.strip()]

    for block in slide_blocks:
        block = block.strip()
        if not block:
            continue

        notes = ""
        content = block

        # Find ===NOTES=== marker
        notes_marker = '===NOTES==='
        idx = block.find(notes_marker)
        if idx >= 0:
            content = block[:idx].strip()
            notes = block[idx + len(notes_marker):].strip()
            notes = re.sub(r'^```\s*', '', notes)
            notes = re.sub(r'\s*```$', '', notes)
        else:
            for marker in ['\nNOTES:', '\n备注：', '\n备注:']:
                idx = block.find(marker)
                if idx >= 0:
                    content = block[:idx].strip()
                    notes = block[idx + len(marker):].strip()
                    break

        # ── Extract MEDIA tags and LAYOUT type ──
        media_list = []
        clean_lines = []
        layout = ""
        for line in content.split("\n"):
            if line.startswith("MEDIA:"):
                entry = _parse_media_tag(line)
                if entry["file"]:
                    media_list.append(entry)
            elif line.startswith("LAYOUT:") or line.startswith("该页布局类型："):
                if line.startswith("LAYOUT:"):
                    layout = line[7:].strip().lower()
                else:
                    layout = line[7:].strip().lower()
            else:
                clean_lines.append(line)
        content = "\n".join(clean_lines)

        # Extract title from first # heading
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
        else:
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            title = lines[0][:60] if lines else f"幻灯片 {len(slides)+1}"

        slides.append({
            "title": title,
            "content": content,
            "notes": notes,
            "media": media_list,
            "layout": layout,
        })

    # Fallback: if no slides but there are # headings
    if not slides:
        headings = re.findall(r'^#\s+(.+)$', markdown_text, re.MULTILINE)
        if headings:
            parts = re.split(r'(?=^#\s+)', markdown_text, flags=re.MULTILINE)
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                notes = ""
                content = part
                idx = part.find('===NOTES===')
                if idx >= 0:
                    content = part[:idx].strip()
                    notes = part[idx + 11:].strip()

                media_list = []
                clean_lines = []
                for line in content.split("\n"):
                    if line.startswith("MEDIA:"):
                        entry = _parse_media_tag(line)
                        if entry["file"]:
                            media_list.append(entry)
                    else:
                        clean_lines.append(line)
                content = "\n".join(clean_lines)

                title = content.split('\n')[0].replace('#', '').strip()
                slides.append({
                    "title": title,
                    "content": content,
                    "notes": notes,
                    "media": media_list,
                })

    return slides


def _parse_media_tag(line):
    """Parse a MEDIA: filename|position=xxx|scale=xxx tag line."""
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
    return entry


def review_narration(slides, total_duration_minutes=10, api_key=None, api_base=None):
    """
    AI审校：对每页口播进行去水词、优化流畅度、检查时长合规。

    Args:
        slides: list of dicts [{"title", "content", "notes", ...}, ...]
        total_duration_minutes: 目标总时长（分钟）
        api_key: Optional custom API key
        api_base: Optional custom API base URL
    Returns:
        list of dicts with cleaned "notes" and added "notes_duration_s" (estimated seconds)
    """
    target_seconds = total_duration_minutes * 60
    avg_per_slide = target_seconds / max(len(slides), 1)

    # Build one combined review prompt for all slides (more efficient)
    review_items = []
    for i, s in enumerate(slides):
        title = s.get("title", "")
        notes = s.get("notes", "")
        review_items.append(f"第{i+1}页（{title}）：{notes}")

    combined = "\n\n".join(review_items)

    prompt = f"""你是一位专业的中文演讲审校。请逐页审校以下口播讲稿，做三项处理：

1. 去水词：删除废话、重复、填充词（如"嗯"、"啊"、"就是说"、"那么"、"对吧"、"好吧"）
2. 优化流畅度：修改不通顺的句子，保持自然口语节奏，不改变原意
3. 时长控制：每页口播建议 {avg_per_slide:.0f} 秒完成，总时长控制在 {total_duration_minutes} 分钟左右。
   如果某页太长，精简内容；如果太短，适当补充展开。中文朗读速度约每秒4-5字。

重要约束：
- 保持口语化、自然的演讲风格
- 绝对不要添加任何新的信息或内容
- 禁止出现任何英文单词，所有英文术语保留翻译
- 保留原文的承上启下结构和过渡句
- 每页输出一段纯文本，不要添加"第X页审校后："之类的前缀标记

逐页输出审校后的口播文本，用 --- 分隔：

{combined}"""

    llm = client
    if api_key:
        llm = OpenAI(base_url=api_base or "https://api.deepseek.com", api_key=api_key)

    try:
        resp = llm.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": "你是专业的中文演讲审校。输出纯文本，用---分隔每页审校结果。不要添加额外说明。"},
                {"role": "user", "content": prompt},
            ],
            stream=False,
            max_tokens=16384,
        )
        cleaned_text = resp.choices[0].message.content

        # Parse cleaned output
        cleaned_parts = re.split(r'\n-{3,}\n', cleaned_text)
        for i, s in enumerate(slides):
            if i < len(cleaned_parts):
                cleaned = cleaned_parts[i].strip()
                if cleaned and len(cleaned) > 5:
                    s["notes"] = cleaned

            # Estimate duration: Chinese ~4.5 chars/sec spoken
            note_len = len(s.get("notes", ""))
            est_seconds = max(5.0, note_len / 4.5)
            s["notes_duration_s"] = round(est_seconds, 1)

    except Exception as e:
        # Fallback: just estimate durations without AI
        for s in slides:
            note_len = len(s.get("notes", ""))
            est_seconds = max(5.0, note_len / 4.5)
            s["notes_duration_s"] = round(est_seconds, 1)

    return slides


def ai_agent(user_input):
    """Generic DeepSeek API call."""
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_input},
        ],
        stream=False,
        max_tokens=16384,
    )
    return response.choices[0].message.content