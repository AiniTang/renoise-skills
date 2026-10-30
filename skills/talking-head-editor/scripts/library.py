"""手法库：从 26 个抖音口播剪辑教程和 10 个剪映草稿里蒸馏出的手法登记表，加上「按内容自动搭配」。

分工（判定分层）：Agent 只判语义——在 timeline.json 的 beats 里标每段话是什么内容类型、拆出要上屏的字；
代码负责挑手法和变体（按风格、强度档、轮换规则）、按口播逐字时间对齐出现时刻，展开成 titles。

beats 写法（每条一段话）：
  {"t0": 12.3, "t1": 15.8, "beat": "list", "text": "三个坑", "items": ["没存档", "乱改", "不测"], "conclude": "怎么避开"}
  beat 取值见 BEATS；文字字段按内容给：text / text2（前后两半句）/ left, right（两边对比）/ items（并列项）/
  items_en / en（英文副标）/ chunks（分块）/ number（巨数字）/ value（结论数字，如 "58%"）/ conclude（结论）/ hl（强调词）。
  可选 "use": 手法 id（指定手法）、"variant": 变体、"side": left|right、"y": 纵向位置。
渲染时 render.py 自动展开（不改 timeline 文件）；想看或手改展开结果：python library.py arrange timeline.json --write。

命令：
  python library.py menu [--beat list] [--style premium --tone web]   能用的手法菜单
  python library.py show flank_pair                                     一条手法的全部信息（含没实现的）
  python library.py arrange timeline.json [--write]                     展开 beats，打印挑了什么；--write 写回 titles
  python library.py docs                                                从登记表生成 references/library.md
"""
import argparse
import json
from pathlib import Path

from kvlib import load_json, save_json, style_preset, word_time

HERE = Path(__file__).resolve().parent
CATALOG = HERE.parent / 'assets' / 'library' / 'catalog.json'

BEATS = {
    'hook': '开场钩子', 'topic': '点题', 'chapter': '章节切换', 'list': '并列列举', 'number': '数字数据', 'compare': '对比',
    'steps': '步骤流程', 'quote': '金句结论', 'concept': '新概念', 'evidence': '事实证据', 'emphasis': '重点词', 'negative': '负面警告',
    'question': '提问悬念', 'emotion': '情绪吐槽', 'demo': '操作演示', 'story': '讲故事', 'transition_talk': '过渡句', 'cta': '结尾互动',
}
LIBS = {'opening': '开场', 'structure': '结构与章节', 'subtitle': '常驻字幕', 'keytext': '重点字与花字', 'typeset': '大字排版',
        'font': '字体', 'layout': '画面版式', 'background': '背景', 'camera': '镜头运动', 'card': '信息卡片与图表', 'sticker': '贴纸与手绘',
        'animation': '动效', 'transition': '转场', 'effect': '特效与质感', 'sfx': '音效', 'music': '配乐', 'workflow': '粗剪与流程'}
TEMPLATE_GAP = 30   # 同一种手法隔 30 秒以上（rhythm_check 同一规则）
HEAVY_GAP = 20      # 重手法（intensity 3）之间至少隔 20 秒


def _short(s, n=6):
    return isinstance(s, str) and 0 < len(s) <= n


# 整屏冲击的大包装（单字页、数字滚动、砸屏、速度线、字墙、章节页）：画面砸下来必须有声，自带的声音不受音效密度上限
HIT_LAYOUTS = ('word', 'count', 'number', 'bignum', 'slam', 'burst', 'wordwall', 'chapter', 'fog', 'chapter_page', 'cutnum')


def _roll_sound(b):
    """数字滚动的声音：滴答跟着数字跳（缓出，越到后面越稀），停在终值那一下叮。"""
    roll = b.get('roll', 0.9)
    return [{'type': 'tick', 'at': 0.0, 'dur': round(roll * 0.85, 2), 'db': 5}, {'type': 'ding', 'at': roll}]


# ---------------------------------------------------------------- 已实现手法登记
# 每条：catalog 里的 id → 怎么从 beat 生成一条 titles。
#   beats: 适合的内容类型和优先级（数字越小越优先）  style: 风格标签（premium / web / variety）
#   intensity: 1 轻 / 2 中 / 3 重   ok(b): 这段话的字够不够用这个手法   build(b, v, at): 生成 titles 条目
#   variants: {变体: 风格标签}   sound(st, b, at): 自动配的声音（可无）   demo: 样本册用的示例 beat
def _items_ok(b, lo=2, hi=5, n=7):
    return lo <= len(b.get('items') or []) <= hi and all(_short(x, n) for x in b['items'])


IMPL = {
    'flank_pair': dict(
        beats={'compare': 0, 'quote': 2, 'list': 3}, style=['premium', 'web', 'variety'], intensity=2,
        variants={'white_red': ['premium', 'web'], 'stagger': ['premium'], 'pop': ['variety', 'web']},
        ok=lambda b: (_short(b.get('left'), 5) and _short(b.get('right'), 5)) or (len(b.get('items') or []) == 2 and _items_ok(b, 2, 2, 5)),
        build=lambda b, v, at: {'layout': 'flank', 'variant': v, 'left': b.get('left') or b['items'][0], 'right': b.get('right') or b['items'][1],
                                **({'left_en': b['items_en'][0], 'right_en': b['items_en'][1]} if len(b.get('items_en') or []) == 2 else {}),
                                'right_at': b.get('right_at') or [at(b.get('right') or b['items'][1])]},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0}, {'type': 'pop', 'at': (b.get('right_at') or [at(b.get('right') or b['items'][1])])[0] or 0.5}] if st['tone'] != 'calm' else None,
        demo={'beat': 'compare', 'left': '会剪', 'right': '会想', 'items_en': ['EDIT', 'THINK']},
    ),
    'line_yield_shift': dict(
        beats={'topic': 0, 'hook': 1, 'question': 1, 'compare': 2, 'emphasis': 2}, style=['premium', 'web'], intensity=2,
        variants={'push_up': ['premium', 'web'], 'diagonal': ['premium', 'web'], 'gray_down': ['premium'], 'squeeze': ['web']},
        ok=lambda b: _short(b.get('text'), 12) and _short(b.get('text2'), 10),
        build=lambda b, v, at: {'layout': 'yield', 'variant': v, 'text': b['text'], 'text2': b['text2'], 'hl2': b.get('hl'),
                                'switch_at': [at(b['text2'])]},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': max(0, (at(b['text2']) or 1) - 0.08)}],
        demo={'beat': 'topic', 'text': '你剪的口播没人看', 'text2': '问题出在字幕', 'hl': ['字幕']},
    ),
    'staged_chunk_reveal': dict(
        beats={'quote': 0, 'concept': 1, 'steps': 2}, style=['premium', 'web'], intensity=2,
        ok=lambda b: 2 <= len(b.get('chunks') or []) <= 5,
        build=lambda b, v, at: {'layout': 'chunks', 'chunks': b['chunks'], 'side': b.get('side', 'left'),
                                'chunk_at': [at(c['text'] if isinstance(c, dict) else c) for c in b['chunks']]},
        demo={'beat': 'quote', 'chunks': [{'text': '好的剪辑', 'w': 1}, {'text': '不是加特效', 'w': 2}, {'text': '是做减法', 'w': 3}]},
    ),
    'list_accumulate': dict(
        beats={'list': 0, 'steps': 0, 'question': 3}, style=['premium', 'web', 'variety'], intensity=2,
        variants={'conclude': ['premium', 'web', 'variety'], 'bullets': ['premium', 'web'], 'grid': ['premium', 'web'], 'one': ['web', 'variety']},
        variant_ok={'conclude': lambda b: bool(b.get('conclude')), 'grid': lambda b: 3 <= len(b['items']) <= 6,
                    'one': lambda b: len(b['items']) <= 4 and all(len(x) <= 5 for x in b['items'])},
        ok=lambda b: _items_ok(b, 2, 6, 10),
        build=lambda b, v, at: {'layout': 'list', 'variant': v, 'items': b['items'], 'items_en': b.get('items_en'), 'conclude': b.get('conclude'),
                                'item_at': [at(x) for x in b['items']] + ([at(b['conclude'])] if b.get('conclude') else [])},
        sound=lambda st, b, at: [{'type': 'click', 'at': a} for a in [at(x) for x in b['items']] if a is not None][:5] if st['tone'] != 'calm' else None,
        demo={'beat': 'list', 'items': ['没存档', '乱改代码', '不做测试'], 'items_en': ['NO BACKUP', 'RANDOM EDITS', 'NO TESTS'],
              'conclude': '怎么避开？'},
    ),
    'label_chips_sequence': dict(
        beats={'list': 1, 'concept': 2, 'topic': 2, 'hook': 2, 'evidence': 3}, style=['premium', 'web', 'variety'], intensity=2,
        variants={'bilingual': ['premium', 'web'], 'red_bar': ['premium', 'web'], 'gold': ['premium'], 'capsule': ['web', 'variety'],
                  'stack3': ['premium', 'web']},
        variant_ok={'bilingual': lambda b: len(b.get('items') or [b.get('text')]) <= 2, 'stack3': lambda b: len(b.get('items') or []) == 3},
        ok=lambda b: _items_ok(b, 1, 6, 6) or (_short(b.get('text'), 6) and not b.get('items')),
        build=lambda b, v, at: {'layout': 'chips', 'variant': v, 'items': b.get('items') or [b['text']], 'items_en': b.get('items_en'),
                                'item_at': [at(x) for x in (b.get('items') or [b['text']])]},
        sound=lambda st, b, at: [{'type': 'tap', 'at': a or 0.3} for a in [at(x) for x in (b.get('items') or [b['text']])]][:6] if st['tone'] != 'calm' else None,
        demo={'beat': 'list', 'items': ['选题', '脚本', '剪辑'], 'items_en': ['TOPIC', 'SCRIPT', 'EDIT']},
    ),
    'cn_en_tracked': dict(
        beats={'concept': 0, 'topic': 3}, style=['premium'], intensity=2,
        ok=lambda b: _short(b.get('text'), 6) and bool(b.get('en')),
        build=lambda b, v, at: {'layout': 'concept', 'text': b['text'], 'en': b['en']},
        sound=lambda st, b, at: [{'type': 'swell', 'at': 0.1}],
        demo={'beat': 'concept', 'text': '上下文', 'en': 'Context window'},
    ),
    'giant_number_hook': dict(
        beats={'hook': 0, 'list': 2, 'topic': 1, 'number': 3}, style=['premium', 'web'], intensity=3,
        ok=lambda b: str(b.get('number', '')).isdigit() and len(str(b['number'])) <= 2,
        build=lambda b, v, at: {'layout': 'bignum', 'number': b['number'], 'side': b.get('side', 'left'), 'text': b.get('text')},
        sound=lambda st, b, at: [{'type': 'thump', 'at': 0}, {'type': 'shimmer', 'at': 0.25}],
        demo={'beat': 'hook', 'number': 4, 'text': '4 个方法'},
    ),
    'number_reveal': dict(
        beats={'number': 0, 'evidence': 1}, style=['premium', 'web'], intensity=3,
        variants={'glow': ['premium', 'web'], 'roll': ['premium', 'web']},
        variant_ok={'roll': lambda b: isinstance(b.get('to'), (int, float))},
        ok=lambda b: bool(b.get('value')) or isinstance(b.get('to'), (int, float)),
        build=lambda b, v, at: ({'layout': 'count', 'value': b['to'], 'from': b.get('from', 0), 'suffix': b.get('suffix', ''), 'prefix': b.get('prefix', ''),
                                 'decimals': b.get('decimals', 0), 'lead': b.get('lead'), 'text': b.get('text'), 'log': b.get('log'),
                                 **({'roll': b['roll']} if b.get('roll') else {})} if v == 'roll' else
                                {'layout': 'number', 'value': b.get('value') or f"{b.get('prefix', '')}{b['to']:,}{b.get('suffix', '')}",
                                 'lead': b.get('lead'), 'text': b.get('text')}),
        sound=lambda st, b, at: _roll_sound(b) if b.get('variant') == 'roll' or (not b.get('value') and isinstance(b.get('to'), (int, float))) else [{'type': 'thump', 'at': 0.38}],
        demo={'beat': 'number', 'value': '$1,000,000', 'lead': 'Annual revenue', 'text': '一个人做到的年收入'},
    ),
    'text_typewriter': dict(
        beats={'question': 0, 'quote': 1, 'topic': 2, 'hook': 2}, style=['premium', 'web'], intensity=2,
        ok=lambda b: _short(b.get('text'), 14),
        build=lambda b, v, at: {'layout': 'quote', 'text': b['text'], 'hl': b.get('hl', []), 'anim': 'type', 'en': b.get('en'), 'y': b.get('y', 0.52)},
        sound=lambda st, b, at: [{'type': 'typing', 'at': 0, 'dur': min(2.0, len(b['text']) * 0.07 + 0.1)}],
        demo={'beat': 'question', 'text': '为什么你的视频没人看完？', 'hl': ['没人看完']},
    ),
    'kw_color_block': dict(
        beats={'emphasis': 0, 'concept': 2, 'negative': 1, 'quote': 3}, style=['premium', 'web'], intensity=2,
        variants={'solid': ['premium', 'web'], 'offset': ['web'], 'skew': ['premium', 'web'], 'grow': ['premium', 'web']},
        ok=lambda b: _short(b.get('text'), 8),
        build=lambda b, v, at: {'layout': 'side', 'text': b['text'], 'hl': b.get('hl') or [], 'lead': b.get('lead'), 'en': b.get('en'),
                                'side': b.get('side', 'left'), 'y': b.get('y', 0.54),
                                'block': {'style': v, 'color': {'solid': '#1C46B8', 'offset': '#FF4A1C', 'skew': '#1C46B8', 'grow': '#F2C230'}[v]}},
        sound=lambda st, b, at: [{'type': 'zip_up', 'at': 0}],
        demo={'beat': 'emphasis', 'lead': '真正拉开差距的是', 'text': '信息密度', 'hl': ['信息密度'], 'en': 'information density'},
    ),
    # ---- 第 3 批：卡片与章节（cards.py 逐帧画）
    'info_stat_card': dict(
        beats={'evidence': 0, 'number': 1, 'compare': 3}, style=['premium'], intensity=2, same_look=True,
        variants={'ornate': ['premium'], 'lime': ['web'], 'rows': ['premium']},
        ok=lambda b: _short(b.get('text'), 12) and bool(b.get('value')),
        build=lambda b, v, at: {'layout': 'statcard', 'variant': v, 'title': b['text'], 'en': b.get('en'),
                                'rows': [{'value': b['value'], 'label': b.get('label')}] +
                                        ([{'value': b['value2'], 'label': b.get('label2'), 'at': at(b['value2']) or at(b.get('label2'))}] if b.get('value2') else [])},
        sound=lambda st, b, at: [{'type': 'thump', 'at': 0.05}] + ([{'type': 'ding', 'at': max(0.3, (at(b['value2']) or at(b.get('label2')) or 1.2) - 0.25)}]
                                                                    if b.get('value2') and st['tone'] != 'calm' else []),
        demo={'beat': 'evidence', 'text': 'SpaceX 发射记录', 'en': 'Launch record', 'value': '580', 'label': '完成发射次数',
              'value2': '534', 'label2': '成功着陆次数'},
    ),
    'share_ring_pie': dict(
        beats={'number': 2, 'compare': 2, 'evidence': 3}, style=['premium', 'web'], intensity=2,
        variants={'donut': ['premium', 'web'], 'pie': ['premium', 'web'], 'slice': ['premium', 'web']},
        variant_ok={'donut': lambda b: b.get('pct') is not None, 'slice': lambda b: b.get('pct') is not None and bool(b.get('src')),
                    'pie': lambda b: 2 <= len(b.get('pcts') or []) == len(b.get('items') or [])},
        ok=lambda b: (b.get('pct') is not None and 0 < float(b['pct']) < 100) or 2 <= len(b.get('pcts') or []) <= 4,
        build=lambda b, v, at: {'layout': 'ring', 'variant': v, 'pct': b.get('pct'), 'text': b.get('text'), 'lead': b.get('lead'), 'src': b.get('src'),
                                'items': [[x, p] + ([e] if e else []) for x, p, e in zip(b.get('items') or [], b.get('pcts') or [],
                                                                                        list(b.get('items_en') or []) + [None] * 4)] or None},
        sound=lambda st, b, at: [{'type': 'tick', 'at': 0.2, 'dur': 0.9}],
        demo={'beat': 'number', 'pct': 60, 'lead': '新手里', 'text': '第一周就放弃了'},
        demo_v={'pie': {'items': ['美国', '中国', '其他'], 'pcts': [55, 30, 15], 'items_en': ['USA', 'China', 'Others'], 'text': '全球发射份额'},
                'slice': {'src': '@photo', 'pct': 25, 'text': '四分之一的时间在等'}},
    ),
    'chapter_fog_numeral': dict(
        beats={'chapter': 1}, style=['premium'], intensity=3, same_look=True,
        variants={'panel': ['premium'], 'window': ['premium']},
        ok=lambda b: str(b.get('number', '')).lstrip('0').isdigit() and _short(b.get('text'), 10),
        build=lambda b, v, at: {'layout': 'fog', 'variant': v, 'number': b['number'], 'text': b['text'], 'en': b.get('en'), 'items': b.get('items')},
        demo={'beat': 'chapter', 'number': '02', 'text': '上下文管理', 'en': 'Context', 'items': ['一事一会话', '留两成交接', '先读再动手']},
    ),
    'chapter_title_page': dict(
        beats={'chapter': 1}, style=['premium', 'web', 'variety'], intensity=3, same_look=True,
        variants={'hand': ['premium', 'web'], 'preview': ['premium', 'web'], 'swap': ['web', 'variety']},
        variant_ok={'swap': lambda b: bool(b.get('main'))},
        ok=lambda b: _short(b.get('text'), 10),
        build=lambda b, v, at: {'layout': 'chapter_page', 'variant': v, 'number': b.get('number', '01'), 'text': b['text'], 'en': b.get('en'),
                                'sub': b.get('sub'), 'preview': b.get('preview'), 'main': b.get('main'), 'sign': b.get('sign')},
        demo={'beat': 'chapter', 'number': '02', 'text': '做减法', 'en': 'Less is more', 'sub': '给字幕加戏', 'main': '剪辑三板斧'},
    ),
    # ---- 已有版式，也进入自动搭配
    'side': dict(
        name='人一侧不对称大字',
        beats={'concept': 1, 'topic': 1, 'emphasis': 1, 'quote': 2, 'negative': 2}, style=['premium'], intensity=2,
        ok=lambda b: _short(b.get('text'), 8),
        build=lambda b, v, at: {'layout': 'side', 'text': b['text'], 'lead': b.get('lead'), 'en': b.get('en'), 'hl': b.get('hl') or [],
                                'side': b.get('side', 'left'), **({'y': b['y']} if 'y' in b else {})},
        demo={'beat': 'concept', 'lead': '这一步叫', 'text': '版本管理', 'hl': ['版本'], 'en': 'Version control'},
    ),
    'quote': dict(
        name='金句引号',
        beats={'quote': 0, 'concept': 3}, style=['premium'], intensity=2,
        ok=lambda b: _short(b.get('text'), 24),
        build=lambda b, v, at: {'layout': 'quote', 'text': b['text'], 'hl': b.get('hl') or [], 'en': b.get('en'), 'y': b.get('y', 0.52)},
        demo={'beat': 'quote', 'text': '不要依赖 AI 的记忆\\N来撤回', 'hl': ['记忆']},
    ),
    'chapter': dict(
        name='章节页',
        beats={'chapter': 0}, style=['premium', 'web'], intensity=3, same_look=True,
        ok=lambda b: _short(b.get('text'), 10),
        build=lambda b, v, at: {'layout': 'chapter', 'number': b.get('number', '01'), 'text': b['text'], 'en': b.get('en'), 'sub': b.get('sub')},
        demo={'beat': 'chapter', 'number': '02', 'text': '上下文管理', 'en': 'Context', 'sub': '别让 AI 失忆'},
    ),
    'stack': dict(
        name='编号卡逐条累加',
        beats={'steps': 1, 'list': 2}, style=['premium', 'web'], intensity=2,
        ok=lambda b: _items_ok(b, 2, 5, 12),
        build=lambda b, v, at: {'layout': 'stack', 'text': b.get('text'), 'items': b['items'], 'side': b.get('side', 'left'), 'y': b.get('y', 0.48),
                                'item_at': b.get('item_at') or [at(x) for x in b['items']]},
        sound=lambda st, b, at: [{'type': 'rising_ui', 'step': j, 'at': a if a is not None else 0.3 + 0.6 * j}
                                 for j, a in enumerate(b.get('item_at') or [at(x) for x in b['items']])],
        demo={'beat': 'steps', 'text': '三步走', 'items': ['git init 初始化', 'git commit 存档', 'git revert 回退']},
    ),
    'count': dict(
        name='数字滚动',
        beats={'number': 1}, style=['premium', 'web', 'variety'], intensity=2,
        ok=lambda b: isinstance(b.get('to'), (int, float)),
        build=lambda b, v, at: {'layout': 'count', 'value': b['to'], 'from': b.get('from', 0), 'suffix': b.get('suffix', ''),
                                'prefix': b.get('prefix', ''), 'decimals': b.get('decimals', 0), 'lead': b.get('lead'), 'text': b.get('text'), 'y': b.get('y', 0.50),
                                **({'roll': b['roll']} if b.get('roll') else {})},
        sound=lambda st, b, at: _roll_sound(b),
        demo={'beat': 'number', 'from': 100, 'to': 20, 'suffix': '%', 'text': '上下文只剩两成'},
    ),
    'behind_text': dict(   # 字在人后：人像按这条大字的时间段自动抠（person_matte），这几秒不自动推近
        beats={'topic': 1, 'hook': 2, 'emphasis': 3}, style=['premium', 'web'], intensity=3,
        variants={'brand_head': ['premium', 'web'], 'top_keyword': ['web'], 'hollow_sandwich': ['premium', 'web']},
        variant_ok={'brand_head': lambda b: _short(b.get('text'), 3), 'top_keyword': lambda b: _short(b.get('text'), 4),
                    'hollow_sandwich': lambda b: isinstance(b.get('en'), str) and b['en'].isascii() and 4 <= len(b['en']) <= 16},
        ok=lambda b: _short(b.get('text'), 4),
        build=lambda b, v, at: {'behind': True, 'variant': v, 'text': b['text'], 'en': b.get('en')},
        sound=lambda st, b, at: [{'type': 'drip', 'at': 0}],
        demo={'beat': 'topic', 'text': '剪辑', 'en': 'Cut it right'},
        demo_v={'top_keyword': {'text': '不存档'}},
    ),
    'word': dict(
        name='整屏单字页',
        beats={'emphasis': 2, 'negative': 0, 'emotion': 1}, style=['premium', 'web', 'variety'], intensity=3,
        variants={'blur': ['premium'], 'flash': ['web', 'variety']},
        ok=lambda b: _short(b.get('text'), 3),
        build=lambda b, v, at: {'layout': 'word', 'text': b['text'], 'en': b.get('en'), **({'anim': 'flash'} if v == 'flash' else {})},
        sound=lambda st, b, at: [{'type': 'whoosh_big', 'at': 0.0}, {'type': 'thump', 'at': 0.08}],
        demo={'beat': 'negative', 'text': '失忆', 'en': 'Amnesia'},
    ),
    'split': dict(
        name='左右分列',
        beats={'compare': 1}, style=['premium'], intensity=2,
        ok=lambda b: _short(b.get('left'), 6) and _short(b.get('right'), 6),
        build=lambda b, v, at: {'layout': 'split', 'left': b['left'], 'right': b['right'],
                                **({'left_en': b['items_en'][0], 'right_en': b['items_en'][1]} if len(b.get('items_en') or []) == 2 else {})},
        demo={'beat': 'compare', 'left': '以前', 'right': '现在', 'items_en': ['BEFORE', 'NOW']},
    ),
    'plain': dict(
        name='居中大字',
        beats={'emphasis': 1, 'topic': 2, 'emotion': 0, 'quote': 2}, style=['variety'], intensity=2,
        ok=lambda b: _short(b.get('text'), 10),
        build=lambda b, v, at: {'layout': 'plain', 'text': b['text'], 'hl': b.get('hl') or [], 'sub': b.get('sub')},
        demo={'beat': 'emotion', 'text': '这谁顶得住', 'hl': ['顶不住']},
    ),
}

# ---- 第 6 批：重点字网感（keytext.py 逐帧画）
def _at0(at, w, d):
    t = at(w)
    return d if t is None else t


def _item_times(b, at, every=0.45):
    return [(_at0(at, x, 0.15 + j * every)) for j, x in enumerate(b['items'])]


IMPL.update({
    'kw_slam_stamp': dict(
        beats={'negative': 1, 'emotion': 1, 'hook': 2, 'emphasis': 3}, style=['web', 'variety'], intensity=3, max_n=1,
        variants={'stamp': ['web', 'variety'], 'char': ['web', 'variety']},
        variant_ok={'char': lambda b: _short(b.get('text'), 2)},
        ok=lambda b: _short(b.get('text'), 6),
        build=lambda b, v, at: {'layout': 'slam', 'variant': v, 'text': b['text']},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.0}, {'type': 'hit', 'at': 0.14}],
        demo={'beat': 'negative', 'text': '别这样做'},
        demo_v={'char': {'text': '慌'}},
    ),
    'kw_speedline_burst': dict(
        beats={'emphasis': 1, 'hook': 1, 'quote': 3}, style=['web', 'variety'], intensity=3, max_n=2,
        ok=lambda b: _short(b.get('text'), 6) and len(b['text']) >= 2,
        build=lambda b, v, at: {'layout': 'burst', 'text': b['text']},
        sound=lambda st, b, at: [{'type': 'whoosh_big', 'at': 0.0}, {'type': 'thump', 'at': 0.1}],
        demo={'beat': 'emphasis', 'text': '信息密度'},
    ),
    'kw_crash_knockout': dict(
        beats={'compare': 1, 'negative': 2, 'emotion': 2}, style=['web', 'variety'], intensity=2,
        ok=lambda b: _short(b.get('left'), 5) and _short(b.get('right'), 5),
        build=lambda b, v, at: {'layout': 'knockout', 'left': b['left'], 'right': b['right'], 'hit_at': at(b['right'])},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': max(0.0, _at0(at, b['right'], 0.6) - 0.25)}, {'type': 'thump', 'at': _at0(at, b['right'], 0.6)}],
        demo={'beat': 'compare', 'left': '加功能', 'right': '做减法'},
    ),
    'kw_split_insert': dict(
        beats={'question': 1, 'emphasis': 2, 'emotion': 2, 'negative': 2, 'concept': 2}, style=['premium', 'web'], intensity=2,
        variants={'gap': ['premium', 'web'], 'shift': ['web']},
        ok=lambda b: _short(b.get('text'), 4) and _short(b.get('sub'), 14),
        build=lambda b, v, at: {'layout': 'crack', 'variant': v, 'text': b['text'], 'sub': b['sub'], 'open_at': at(b['sub'])},
        sound=lambda st, b, at: [{'type': 'zip_up', 'at': _at0(at, b['sub'], 0.6)}],
        demo={'beat': 'question', 'text': '上下文', 'sub': '到底满没满？'},
    ),
    'kw_word_replace': dict(
        beats={'transition_talk': 0, 'emphasis': 1, 'question': 2, 'compare': 2}, style=['web'], intensity=2,
        variants={'fold': ['web'], 'ghost': ['web'], 'vblur': ['web']},
        ok=lambda b: _short(b.get('lead'), 6) and _short(b.get('text'), 6),
        build=lambda b, v, at: {'layout': 'swap', 'variant': v, 'lead': b['lead'], 'text': b['text'], 'swap_at': at(b['text'])},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': _at0(at, b['text'], 0.6)}],
        demo={'beat': 'transition_talk', 'lead': '其实只要', 'text': '一个命令'},
    ),
    'text_finish_fx': dict(
        beats={'emphasis': 1, 'emotion': 1, 'hook': 1, 'transition_talk': 2}, style=['web'], intensity=2,
        variants={'striped': ['web'], 'halftone': ['web'], 'neon': ['web'], 'gradient': ['web'], 'glitch': ['web']},
        ok=lambda b: _short(b.get('text'), 6),
        build=lambda b, v, at: {'layout': 'finish', 'variant': v, 'text': b['text']},
        sound=lambda st, b, at: [{'type': 'glitch' if st.get('variant') == 'glitch' else 'pop', 'at': 0.0}],
        demo={'beat': 'emphasis', 'text': '上下文'},
    ),
    'paper_patch_text': dict(
        beats={'topic': 1, 'concept': 1, 'emotion': 2}, style=['web', 'variety'], intensity=2,
        variants={'kraft': ['web', 'variety'], 'torn': ['web', 'variety'], 'chips': ['web', 'variety']},
        variant_ok={'kraft': lambda b: len(b.get('text', '')) >= 4, 'torn': lambda b: _short(b.get('text'), 3),
                    'chips': lambda b: 2 <= len(b.get('text', '')) <= 8},
        ok=lambda b: _short(b.get('text'), 14),
        build=lambda b, v, at: {'layout': 'patch', 'variant': v, 'text': b['text']},
        sound=lambda st, b, at: [{'type': 'page', 'at': 0.0}],
        demo={'beat': 'topic', 'text': 'Claude Code 七个命令'},
        demo_v={'torn': {'text': '慌'}, 'chips': {'text': '后台跑任务'}},
    ),
    'concept_quote_marks': dict(
        beats={'concept': 0, 'quote': 3}, style=['web'], intensity=2,
        variants={'bracket': ['web'], 'curly': ['web']},
        ok=lambda b: _short(b.get('text'), 6),
        build=lambda b, v, at: {'layout': 'qmark', 'variant': v, 'text': b['text'], 'en': b.get('en')},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0.0}],
        demo={'beat': 'concept', 'text': '上下文', 'en': 'context'},
    ),
    'handwritten_note': dict(
        beats={'evidence': 1, 'number': 2}, style=['premium', 'web'], intensity=2,
        ok=lambda b: _short(str(b.get('value', '')), 6),
        build=lambda b, v, at: {'layout': 'scribble', 'value': str(b['value']), 'box': b.get('box', True), 'x': b.get('x'), 'y': b.get('y')},
        sound=lambda st, b, at: [{'type': 'pen_scribble', 'at': 0.0}],
        demo={'beat': 'evidence', 'value': '80%'},
    ),
    'icon_keyword_list': dict(
        beats={'list': 1, 'steps': 2, 'concept': 3}, style=['web', 'variety'], intensity=2,
        variants={'unfold': ['web', 'variety'], 'row': ['web', 'variety'], 'dashbox': ['web', 'variety']},
        ok=lambda b: _items_ok(b, 2, 5, 6) and len(b.get('icons') or []) == len(b['items']),
        build=lambda b, v, at: {'layout': 'icons', 'variant': v, 'items': b['items'], 'icons': b['icons'], 'item_at': _item_times(b, at)},
        sound=lambda st, b, at: [{'type': 'pop', 'at': a} for a in _item_times(b, at)],
        demo={'beat': 'list', 'items': ['看额度', '看日志', '算钱'], 'icons': ['Battery', 'Memo', 'Money bag']},
    ),
})

# ---- 第 7 批：贴纸标注与文字动效（annot.py 逐帧画）
IMPL.update({
    'kw_question_mark': dict(
        beats={'question': 1, 'hook': 3}, style=['web', 'variety'], intensity=2,
        variants={'stand': ['web', 'variety'], 'hop': ['web', 'variety']},
        ok=lambda b: _short(b.get('text'), 12),
        build=lambda b, v, at: {'layout': 'qmarks', 'variant': v, 'text': b['text']},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0.15}] if st.get('variant') == 'hop' else [{'type': 'tap', 'at': 0.1}],
        demo={'beat': 'question', 'text': '到底满没满？'},
    ),
    'speech_bubble_text': dict(
        beats={'question': 2, 'hook': 3, 'list': 3, 'negative': 3}, style=['web'], intensity=2,
        variants={'comic': ['web'], 'tags': ['web']},
        variant_ok={'comic': lambda b: _short(b.get('text'), 14), 'tags': lambda b: _items_ok(b, 2, 4, 6)},
        ok=lambda b: _short(b.get('text'), 14) or _items_ok(b, 2, 4, 6),
        build=lambda b, v, at: ({'layout': 'bubble', 'variant': v, 'text': b.get('text')} if v == 'comic' else
                                {'layout': 'bubble', 'variant': v, 'items': b['items'], 'item_at': [at(x) for x in b['items']]}),
        sound=lambda st, b, at: [{'type': 'typing', 'at': 0.2}] if st.get('variant') == 'comic' else
                                [{'type': 'pop', 'at': _at0(at, x, 0.1 + j * 0.3)} for j, x in enumerate(b.get('items') or [])],
        demo={'beat': 'question', 'text': '它是不是又忘了？', 'items': ['忘了前面', '答非所问', '越改越乱']},
    ),
    'meme_reaction_caption': dict(
        beats={'emotion': 2, 'question': 3, 'negative': 3}, style=['web', 'variety'], intensity=3, max_n=2,
        ok=lambda b: _short(b.get('text'), 8) and bool(b.get('src') or b.get('emoji')),
        build=lambda b, v, at: {'layout': 'meme', 'text': b['text'], 'src': b.get('src'), 'emoji': b.get('emoji')},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0.0}, {'type': 'rimshot', 'at': 0.25}],
        demo={'beat': 'emotion', 'text': '这谁顶得住', 'emoji': 'Face with tears of joy'},
    ),
    'anim_shout_wave': dict(
        beats={'emotion': 1, 'question': 2, 'emphasis': 2, 'hook': 2}, style=['web', 'premium'], intensity=3,
        ok=lambda b: _short(b.get('text'), 6),
        build=lambda b, v, at: {'layout': 'shout', 'text': b['text'], 'sub': b.get('sub')},
        sound=lambda st, b, at: [{'type': 'whoosh_big', 'at': 0.0}],
        demo={'beat': 'emphasis', 'text': '先规划', 'sub': '再动手'},
    ),
    'text_cross_slide': dict(
        beats={'emphasis': 2, 'topic': 2, 'list': 3, 'compare': 2}, style=['web'], intensity=2,
        variants={'diagonal': ['web'], 'cross': ['web']},
        ok=lambda b: _short(b.get('lead'), 7) and _short(b.get('text'), 6),
        build=lambda b, v, at: {'layout': 'crossin', 'variant': v, 'lead': b['lead'], 'text': b['text'], 'key_at': at(b['text'])},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.0}, {'type': 'whoosh', 'at': _at0(at, b['text'], 0.25)}],
        demo={'beat': 'compare', 'lead': '不是写得慢', 'text': '是没想清楚'},
    ),
    'text_wipe_reveal': dict(
        beats={'topic': 1, 'concept': 2, 'quote': 3, 'emphasis': 3}, style=['premium', 'web'], intensity=2,
        variants={'vwipe': ['premium', 'web'], 'center': ['premium', 'web'], 'laser': ['web']},
        ok=lambda b: _short(b.get('text'), 8),
        build=lambda b, v, at: {'layout': 'wipe', 'variant': v, 'text': b['text']},
        sound=lambda st, b, at: [{'type': 'shimmer' if st.get('variant') == 'laser' else 'whoosh', 'at': 0.0}],
        demo={'beat': 'topic', 'text': '上下文窗口'},
    ),
    'anim_per_char': dict(
        beats={'topic': 1, 'story': 1, 'chapter': 3}, style=['premium', 'web'], intensity=2,
        variants={'zoom': ['web'], 'rise': ['premium', 'web']},
        ok=lambda b: _short(b.get('text'), 10),
        build=lambda b, v, at: {'layout': 'perchar', 'variant': v, 'text': b['text'], 'hl': b.get('hl')},
        sound=lambda st, b, at: [{'type': 'rising_ui', 'step': j, 'at': j * 0.07} for j in range(min(4, len(b['text'])))]
                                if st.get('variant') == 'zoom' else [{'type': 'page', 'at': 0.0}],
        demo={'beat': 'topic', 'text': '找回会话', 'hl': ['会话']},
    ),
    'cursor_click': dict(
        beats={'cta': 0, 'demo': 1, 'emphasis': 3}, style=['web'], intensity=2,
        ok=lambda b: _short(b.get('text'), 8),
        build=lambda b, v, at: {'layout': 'cursor', 'text': b['text']},
        sound=lambda st, b, at: [{'type': 'click', 'at': 0.5}],
        demo={'beat': 'cta', 'text': '点这里'},
    ),
})

VNAMES = {'white_red': '左白右红', 'stagger': '错落双字', 'pop': '双词弹出', 'push_up': '上移让位', 'diagonal': '对角错位',
          'gray_down': '变灰下沉', 'squeeze': '缩小挤入', 'conclude': '列举后收拢出结论', 'bullets': '侧边要点配英文', 'grid': '编号淡成底纹网格',
          'one': '一屏一个三连击', 'bilingual': '胸前中英标签卡', 'red_bar': '红条擦入标签', 'gold': '暗红金字错落', 'capsule': '彩色胶囊',
          'stack3': '浅底竖排要点', 'glow': '柔光模糊渐显', 'roll': '数字滚动加日志', 'solid': '实心反白块', 'offset': '错位刷块',
          'skew': '斜切渐隐条', 'grow': '方块拉长成条', 'blur': '模糊渐显', 'flash': '闪现', 'ornate': '暗金角花卡', 'lime': '黄绿发光卡',
          'rows': '分行跟读卡', 'donut': '细圆环填充', 'pie': '饼图加标签', 'slice': '圆形图上扇形长出', 'panel': '底部雾面板',
          'window': '整屏数字窗', 'hand': '毛笔手写体', 'preview': '衬线标题加预告窗', 'swap': '总标题原位换分标题',
          'brand_head': '头部高度点题大字', 'top_keyword': '头顶要点关键词', 'hollow_sandwich': '实心镂空夹人',
          'stamp': '痛点词盖章', 'char': '单个巨字', 'gap': '巨字横缝嵌字', 'shift': '三层错位', 'fold': '折叠弹入',
          'ghost': '引导词放大成底纹', 'vblur': '竖向模糊换字', 'striped': '横纹拖影立体', 'halftone': '网点投影',
          'neon': '霓虹空心', 'gradient': '渐变填充', 'glitch': '故障错位', 'kraft': '牛皮纸胶带标题', 'torn': '撕纸片',
          'chips': '每字彩纸', 'bracket': '方括号', 'curly': '弯引号', 'unfold': '关键词展开配图标', 'row': '图标横排随读高亮',
          'dashbox': '虚线框逐个累加', 'arc': '弧形语气词', 'tag': '便利贴标签',
          'stand': '半透明大问号站起', 'hop': '手绘问号连蹦', 'comic': '头顶漫画气泡', 'tags': '黄色气泡散布',
          'cross': '横穿压中', 'vwipe': '竖向擦除', 'center': '中间左右展开', 'laser': '激光雕刻', 'zoom': '逐字缩放', 'rise': '随机上升'}
# 章节载体：全片只用一种（规律「同类包装全片用同一个模板」），第一次按强度档的 chapter_look 挑
CHAPTER_TECH = {'chapter': 'chapter', 'fog': 'chapter_fog_numeral', 'chapter_page': 'chapter_title_page'}

# 不跟内容走、全片一次选定的手法（写在 timeline 顶层）
GLOBAL = {
    'sub_soft_shadow': ('sub_look', {'box': '半透明黑底条（高级感默认）', 'shadow': '无底柔阴影白字', 'serif': '胸口粗宋白字（杂志感）',
                                     'low': '小号压底（大字多的片子）'}),
    'sub_key': ('sub_key_look', {'weight': '换粗一档不变色（高级感默认）', 'red': '同号深红', 'yellow': '亮黄放大 1.2 倍（网感）',
                                 'bracket': '加【】（教程类）', 'stripe': '黄字放大弹一下（综艺感）'}),
    'font_palette': ('font_palette', {'sans': '干货黑体（默认）', 'serif': '杂志宋体：标题和字幕都换思源宋体', 'heavy': '网感粗斜黑：标题换得意黑',
                                      'hand': '标题换毛笔字'}),
    'anim_flash_in': ('titles[].anim', {'flash': '先亮白闪一下再定住，任何大字都能用，网感档的整屏单字页默认'}),
}


# 不跟内容走、写在 timeline 某个字段里的手法（第 2 批画面与镜头起，第 3 批卡片与章节接着加）。每条：
#   where: 在 timeline 里怎么写   variants: {变体: (风格标签, 说明)}   auto: 不写也会自动做的部分
#   demo(A, v): 样本册用的时间线片段（0~3.6 秒），A 是素材 {'shot': 截图, 'photo': 照片, 'rec': 录屏}
def _card(A, t0=0.7, t1=3.5, **kw):
    return {'t0': t0, 't1': t1, 'src': A['shot'], 'fit': 'card', 'w': 0.82, 'y': 0.46, **kw}


FIELDS = {
    'bg_dim_focus': dict(
        where='broll 的 "dim"：sync / pre / false', style=['premium'],
        auto='高级感里卡片、截图、透视卡浮在口播全屏上时默认 sync；相接的几张共用一层',
        variants={'sync': (['premium', 'web'], '同帧压暗：卡片入场同一刻，背景 0.3 秒压到六成亮'),
                  'pre': (['premium', 'web'], '先暗后出：提前 0.4 秒压到四成亮，像灯光暗下来，卡片才浮上来')},
        demo=lambda A, v: {'broll': [_card(A, dim=v)]},
    ),
    'talk_zoom_punch': dict(
        where='顶层 "auto_zoom"：jump / snap / mixed / false', style=['premium', 'web', 'variety'],
        auto='网感档和综艺感默认 mixed，克制档 jump',
        variants={'jump': (['premium'], '跳切三档：停顿处硬切 100% / 115% / 125%'),
                  'snap': (['premium', 'web', 'variety'], '句首快推：粗剪接缝或重点句开口 0.15 秒推进 7%，遮跳剪'),
                  'two_step': (['web', 'variety'], '一句两推：重点句先推 5%，说到第二个强调词再推 5%（mixed 里自动用）')},
        demo=lambda A, v: {'auto_zoom': False, 'zoom': {
            'jump': [{'t0': 1.4, 't1': 3.6, 'from': 1.15, 'to': 1.15, 'ease': 0.01}],
            'snap': [{'t0': 1.0, 't1': 3.6, 'from': 1.0, 'to': 1.07, 'ease': 0.15}],
            'two_step': [{'t0': 0.6, 't1': 1.999, 'from': 1.0, 'to': 1.05, 'ease': 0.12}, {'t0': 2.0, 't1': 3.6, 'from': 1.05, 'to': 1.10, 'ease': 0.12}]}[v]},
    ),
    'frame_card_scale': dict(
        where='layout 的 inset 版式：{"mode": "inset", "anim": ..., "at": 相对秒, "to": 目标大小, "bg": "dots", "gray": true}', style=['web', 'premium'],
        variants={'expand': (['web', 'premium'], '卡片撑满讲重点'), 'shrink': (['web'], '缩小压抑讲负面（可加 gray 变黑白）'),
                  'badge': (['web'], '章节编号缩框，右上弹编号圆章'), 'static': (['premium', 'web'], '点阵底上的静止人物卡')},
        demo=lambda A, v: {'layout': [{'t0': 0.2, 't1': 3.6, 'mode': 'inset', 'anim': v, 'at': 1.2, 'bg': 'dots', 'gray': v == 'shrink',
                                       **({'badge': '02'} if v == 'badge' else {})}]},
    ),
    'punch_zoom_detail': dict(
        where='broll 的 "punch"（截图硬切放大）或 "focus"（平滑放大，card / contain / cover 都能用，写 hold 停一下再缩回）', style=['premium', 'web'],
        variants={'screenshot_punch': (['premium', 'web'], '截图硬切放大 2.2 倍对准关键数字，停一下硬切回'),
                  'recording_zoom': (['premium', 'web'], '平滑放大：0.5 秒推到 2.4 倍，停 1 秒再缩回全景')},
        demo=lambda A, v: {'broll': [_card(A, t0=0.3, t1=3.6, **({'punch': {'t': 1.0, 'dur': 1.6, 'scale': 2.2, 'cx': 0.3, 'cy': 0.35}} if v == 'screenshot_punch'
                                                                else {'focus': {'t': 0.8, 'dur': 0.5, 'scale': 2.4, 'cx': 0.3, 'cy': 0.35, 'hold': 1.0}}))]},
    ),
    'slow_push_drift': dict(
        where='zoom 的 "push"：suspense / settle（可加 dx 横向漂移）；broll 的 "motion": "drift"', style=['premium', 'web'],
        variants={'suspense': (['premium', 'web'], '慢推做悬疑：1.5 秒推到 115%'), 'segment_end': (['premium', 'web'], '段尾整段慢推到 112%'),
                  'drift': (['premium', 'web'], '素材缓推加横向漂移'), 'card_drift': (['premium', 'web'], '卡片往右下漂')},
        demo=lambda A, v: {'auto_zoom': False, **(
            {'zoom': [{'t0': 0.3, 't1': 3.6, 'push': 'suspense'}]} if v == 'suspense' else
            {'zoom': [{'t0': 0.0, 't1': 3.6, 'push': 'settle', 'dx': 0.03}]} if v == 'segment_end' else
            {'layout': [{'t0': 0.3, 't1': 3.6, 'mode': 'hidden'}], 'broll': [{'t0': 0.3, 't1': 3.6, 'src': A['photo'], 'fit': 'cover', 'motion': 'drift'}]} if v == 'drift' else
            {'broll': [_card(A, motion='drift')]})},
    ),
    'broll_band_layout': dict(
        where='broll 的 "fit": "band"，"bg"：dim / blur / metal；"ratio" 默认 4:3，"y" 默认 0.45', style=['premium'],
        variants={'dim_copy': (['premium'], '同素材压暗加网点颗粒做底（财经知识口播常用的版式）'), 'blur': (['premium', 'web'], '同素材虚化压暗做底'),
                  'metal': (['premium'], '拉丝金属底，横条加白边')},
        demo=lambda A, v: {'broll': [{'t0': 0.3, 't1': 3.6, 'src': A['rec'], 'fit': 'band', 'bg': {'dim_copy': 'dim'}.get(v, v)}],
                           'layout': [{'t0': 0.3, 't1': 3.6, 'mode': 'pip', 'pos': 'bottom_right'}]},
    ),
    'aside_blur_stack': dict(
        where='aside 版式的 "stack": [截图, ...]，"interval" 进场间隔（默认 0.5 秒），每张可写 at', style=['web', 'premium'],
        variants={},
        demo=lambda A, v: {'layout': [{'t0': 0.3, 't1': 3.6, 'mode': 'aside', 'stack': [A['shot'], A['photo'], A['shot']]}]},
    ),
    'pip_circle_avatar': dict(
        where='pip 版式的 "look"：ring / feather / shadow；"pos"：top_right / top_left / bottom_left / bottom_right / center', style=['premium', 'web'],
        auto='整屏大字、章节页、巨数字、章节转场时小窗自动让开（"hide_on_peak": false 关掉）',
        variants={'ring': (['premium', 'web'], '细环硬边，右上'), 'feather': (['premium', 'web'], '羽化虚边，左下'),
                  'stroke_shadow': (['premium', 'web'], '白描边加投影，右下')},
        demo=lambda A, v: {'layout': [{'t0': 0.3, 't1': 3.6, 'mode': 'hidden'},
                                      {'t0': 0.3, 't1': 3.6, 'mode': 'pip', 'look': {'stroke_shadow': 'shadow'}.get(v, v),
                                       'pos': {'ring': 'top_right', 'feather': 'bottom_left', 'stroke_shadow': 'bottom_right'}[v]}],
                           'broll': [{'t0': 0.3, 't1': 3.6, 'src': A['rec'], 'fit': 'cover'}]},
    ),
    'pip_shrink_circle': dict(
        where='layout 的 circle 版式：{"mode": "circle", "anim": ..., "bg": "blur|black|grid|dots|none", "ring": "gold|white|pink_dash|none"}；'
              'to_corner 后面接同位置的 pip', style=['premium', 'web'],
        variants={'to_corner': (['premium', 'web'], '先缩后移进角落变头像'), 'quick': (['web'], '0.2 秒猛收成圆'),
                  'center_ring': (['web', 'premium'], '居中大圆加环，圆外网格底')},
        demo=lambda A, v: {'layout': [{'t0': 0.3, 't1': 3.6, 'mode': 'circle', 'anim': v}]},
    ),
    'compare_split_panels': dict(
        where='layout 的 split 版式：{"mode": "split", "variant": ..., "panels": [{"src", "label"}], "focus_at": [相对秒]}；src 写 aroll 用口播', style=['web', 'premium'],
        variants={'torn': (['web'], '撕纸竖条'), 'diagonal': (['web'], '15° 斜线上下分割'), 'focus': (['web', 'premium'], '圆角双窗切焦点'),
                  'triptych': (['web', 'premium'], '三屏并排')},
        demo=lambda A, v: {'layout': [{'t0': 0.3, 't1': 3.6, 'mode': 'split', 'variant': v, 'focus_at': [0, 1.6], 'panels': {
            'torn': [{'src': A['shot'], 'label': '以前'}, {'src': A['photo'], 'label': '现在'}],
            'diagonal': [{'src': A['photo'], 'label': '原版'}, {'src': 'aroll', 'label': '复刻'}],
            'focus': [{'src': A['shot'], 'label': '方案 A'}, {'src': A['photo'], 'label': '方案 B'}],
            'triptych': [{'src': A['photo'], 'label': '原图'}, {'src': 'aroll', 'label': '口播'}, {'src': A['shot'], 'label': '截图'}]}[v]}]},
    ),
    'perspective_card': dict(
        where='broll 的 "fit": "tilt"，"tilt"：left / right / pair（pair 用 "srcs" 给三张）；默认从下方升入再缓缓上升', style=['premium', 'web'],
        auto='连续几张没写方向的透视卡左右交替',
        variants={'tilt_rise': (['premium', 'web'], '斜放缓升，相邻页左右交替'), 'mirror_pair': (['premium', 'web'], '镜像三联')},
        demo=lambda A, v: {'broll': [{'t0': 0.3, 't1': 1.9, 'src': A['shot'], 'fit': 'tilt'}, {'t0': 1.9, 't1': 3.6, 'src': A['photo'], 'fit': 'tilt'}]
                           if v == 'tilt_rise' else [{'t0': 0.3, 't1': 3.6, 'src': A['shot'], 'srcs': [A['shot'], A['photo'], A['shot']], 'fit': 'tilt', 'tilt': 'pair'}]},
    ),
    'grid_bg': dict(
        where='layout 的 bg 版式：{"mode": "bg", "bg": "grid", "variant": ...}，人用 pip、inset 或抠像放上面；inset / circle / split 的 "bg" 也能写 "grid:rainbow"', style=['web', 'premium'],
        variants={'white': (['web'], '黑底白网格'), 'rainbow': (['premium', 'web'], '灰细网格透彩虹光晕'), 'neon': (['web'], '彩虹细线网格'),
                  'plaid': (['web'], '卡其底波浪格纹')},
        demo=lambda A, v: {'layout': [{'t0': 0.3, 't1': 3.6, 'mode': 'bg', 'bg': 'grid', 'variant': v},
                                      {'t0': 0.3, 't1': 3.6, 'mode': 'pip', 'pos': 'center', 'hide_on_peak': False}]},
    ),
    'dot_matrix_bg': dict(
        where='layout 的 bg 版式 {"mode": "bg", "bg": "dots", "variant": ...}，或 inset 的 "bg": "dots"', style=['premium', 'web'],
        variants={'static_card': (['premium', 'web'], '静态点阵配人物卡'), 'scroll_rainbow': (['web', 'premium'], '炫彩波点漂移')},
        demo=lambda A, v: {'layout': [{'t0': 0.3, 't1': 3.6, 'mode': 'inset', 'bg': 'dots:' + ('static' if v == 'static_card' else 'rainbow')}]},
    ),
    'match_motion_cut': dict(
        where='broll 的 "link": "left|right|up"（写在后一张上）', style=['premium', 'web'],
        auto='两张卡片首尾相接、都没写进出场时，前一张往左加速移出、后一张从右减速移入（"auto_link": false 关掉）',
        variants={},
        demo=lambda A, v: {'broll': [_card(A, t0=0.3, t1=1.9), {**_card(A, t0=1.9, t1=3.6), 'src': A['photo']}]},
    ),
}


# 第 3 批卡片与章节里写在字段上的手法（成片由 cards.py、motion.py 逐帧画）
from cards import COMBO_VARIANTS, ENDCARD_VARIANTS, MOCKUP_VARIANTS, OVERVIEW_VARIANTS   # noqa: E402
from kvlib import OPENINGS   # noqa: E402
from motion import CARD_FRAMES, MARK_LOOKS, PAGES_VARIANTS   # noqa: E402
from matte import BG_LOOKS, BREAKOUT_VARIANTS, CORNER_VARIANTS, OUTLINES   # noqa: E402
from kvlib import COMBOS   # noqa: E402


FIELDS.update({
    'screenshot_highlight': dict(
        where='broll（card / contain 的图片）的 "marks"：{"boxes": [[x, y, w, h], ...]（相对截图）, "look": "yellow|inverse", "at": [每道开始的相对秒], "wipe": 0.4}',
        style=['premium', 'web'], auto='每划一道自带一声上滑音',
        variants={'yellow': (['premium', 'web'], MARK_LOOKS['yellow']), 'inverse': (['premium', 'web'], MARK_LOOKS['inverse'])},
        demo=lambda A, v: {'broll': [_card(A, t0=0.3, t1=3.6, marks={'boxes': [[0.13, 0.405, 0.72, 0.115], [0.10, 0.615, 0.77, 0.115]],
                                                                      'look': v, 'at': [0.6, 1.6]})]},
    ),
    'clip_card_frame': dict(
        where='broll（card / contain）的 "frame"：glow / viewfinder；写了 frame 默认宽 0.68、中心在 0.57 高、从下往上滑入', style=['premium', 'web'],
        variants={'glow': (['premium', 'web'], CARD_FRAMES['glow']), 'viewfinder': (['web', 'premium'], CARD_FRAMES['viewfinder'])},
        demo=lambda A, v: {'broll': [{'t0': 0.3, 't1': 3.6, 'src': A['rec'] if v == 'viewfinder' else A['photo'], 'fit': 'card', 'frame': v}]},
    ),
    'doc_pages_fly_in': dict(
        where='broll 的 "fit": "pages"，"srcs": [报告截图, ...]（不够就轮着用），"variant"：cascade / scatter / stack / curl', style=['premium', 'web'],
        auto='自带翻页声；浮在口播全屏上时背景跟卡片一样压暗',
        variants={'cascade': (['web', 'premium'], PAGES_VARIANTS['cascade']), 'scatter': (['web'], PAGES_VARIANTS['scatter']),
                  'stack': (['premium', 'web'], PAGES_VARIANTS['stack']), 'curl': (['premium', 'web'], PAGES_VARIANTS['curl'])},
        demo=lambda A, v: {'broll': [{'t0': 0.2, 't1': 3.6, 'fit': 'pages', 'variant': v, 'src': A['shot'], 'srcs': [A['shot'], A['photo']]}]},
    ),
    'device_mockup': dict(
        where='layout 的 mockup 版式：{"mode": "mockup", "variant": ..., "src": 录屏或成片, "title", "sub", "steps": [...], "at": [每步出现秒], '
              '"src2", "at2", "labels": [两个标签]}', style=['web', 'premium'], auto='样机入场自带唰声',
        variants={k: (['web', 'premium'], v) for k, v in MOCKUP_VARIANTS.items()},
        demo=lambda A, v: {'layout': [{'t0': 0.2, 't1': 3.6, 'mode': 'mockup', 'variant': v, 'src': A['rec'], **{
            'steps': {'title': '第 1 种：问答结构', 'steps': ['先抛一个问题', '马上给答案', '再举一个例子'], 'at': [0.5, 1.3, 2.1]},
            'screen': {'title': 'tutorial', 'sub': '三分钟学会版本管理'},
            'stack': {'src2': A['shot'], 'at2': 1.0, 'labels': ['示例一', '示例二']}}[v]}]},
    ),
    'avatar_content_combo': dict(
        where='layout 的 combo 版式：{"mode": "combo", "variant": ..., "cards": [图片], "at": [每张出现秒], "title", "sub", "note", "hl", '
              '"bg"（band 的底素材）, "crop"（头像取口播哪块，同 pip）}', style=['web', 'premium'], auto='每张卡出现自带啵一声',
        variants={k: (['web', 'premium'], v) for k, v in COMBO_VARIANTS.items()},
        demo=lambda A, v: {'layout': [{'t0': 0.2, 't1': 3.6, 'mode': 'combo', 'variant': v, **{
            'band': {'bg': A['rec'], 'title': '为什么新手总踩坑', 'sub': '三个原因', 'cards': [A['photo']]},
            'head_top': {'cards': [A['photo']]},
            'corner': {'cards': [A['photo'], A['shot']], 'at': [0.3, 1.0]},
            'tutorial': {'title': '第二步：开新会话', 'sub': 'Step 2', 'cards': [A['shot'], A['photo']], 'at': [0.3, 0.9],
                         'note': '动手之前先读交接文件', 'hl': ['交接文件']}}[v]}]},
    ),
    'points_overview': dict(
        where='layout 的 overview 版式：{"mode": "overview", "variant": ..., "items": [{"num", "text", "src"}], "title", "en", "every"}；'
              '不写 items 就从时间线的章节页自动取（编号、章节名、这一章第一张图片，没有就截口播）', style=['premium', 'web'],
        auto='目录在画面上时常驻字幕让开；卡片一张张出现自带啵一声',
        variants={'grid': (['premium', 'web'], OVERVIEW_VARIANTS['grid']), 'toc': (['web'], OVERVIEW_VARIANTS['toc']),
                  'list': (['premium', 'web'], OVERVIEW_VARIANTS['list']), 'tilted_collage': (['premium', 'web'], OVERVIEW_VARIANTS['tilted_collage'])},
        demo=lambda A, v: {'layout': [{'t0': 0.2, 't1': 3.6, 'mode': 'overview', 'variant': v, 'title': '新手三个坑', 'en': 'Three traps',
                                       'items': [{'num': '01', 'text': '不存档', 'src': A['shot']}, {'num': '02', 'text': '乱改代码', 'src': A['photo']},
                                                 {'num': '03', 'text': '不做测试'}, {'num': '04', 'text': '不写交接', 'src': A['shot']}]}]},
    ),
    'follow_endcard': dict(
        where='layout 的 endcard 版式：{"mode": "endcard", "variant": "follow|name", "avatar": 头像图片, "name": "@账号", "text": "感谢关注"}；'
              '不给头像就用口播画面里的人脸', style=['web', 'variety'], auto='尾帧在画面上时常驻字幕让开；头像弹出和加号翻勾自带声音',
        variants={k: (['web', 'variety'], v) for k, v in ENDCARD_VARIANTS.items()},
        demo=lambda A, v: {'layout': [{'t0': 0.2, 't1': 3.6, 'mode': 'endcard', 'variant': v, 'name': '@口播剪辑课', 'text': '学会了，去练'}]},
    ),
    'opening_entry_hit': dict(
        where='顶层 "opening"：flash / zoom / boom / iris / spotlight / false', style=['premium', 'web', 'variety'],
        auto='不写就按强度档自动加：网感档 zoom、克制档 spotlight、综艺感 flash；开头就是铺满素材或别的版式时不加',
        variants={'zoom': (['web', 'premium'], OPENINGS['zoom']['use']), 'spotlight': (['premium'], OPENINGS['spotlight']['use']),
                  'flash': (['web', 'variety'], OPENINGS['flash']['use']), 'iris': (['web'], OPENINGS['iris']['use']),
                  'boom': (['variety'], OPENINGS['boom']['use'])},
        demo=lambda A, v: {'opening': v},
    ),
    # 第 4 批抠像：人像由 person_matte 按段自动抠、缓存，不用准备抠好的素材
    'matte_bg_blur': dict(
        where='layout 的 matte 版式：{"mode": "matte", "bg": "blur", "blur": 12}；想整片用就写一段从头到尾', style=['premium'],
        auto='背景虚化前先把人挖掉，人身边不会糊出一圈人的颜色；这几秒不自动推近',
        variants={'blur': (['premium', 'web'], BG_LOOKS['blur'])},
        demo=lambda A, v: {'layout': [{'t0': 0.2, 't1': 3.6, 'mode': 'matte', 'bg': 'blur'}]},
    ),
    'matte_bg_swap': dict(
        where='layout 的 matte 版式：{"mode": "matte", "src": 话题画面, "title": "话题标题", "outline": "solid_white"}；切换点对齐口播关键词',
        style=['web'], auto='背景压到八成亮（dim 可改）；硬切那一下自带啵一声',
        variants={'swap': (['web', 'premium'], BG_LOOKS['swap'])},
        demo=lambda A, v: {'layout': [{'t0': 0.2, 't1': 3.6, 'mode': 'matte', 'src': A['photo'], 'title': '上下文管理', 'outline': 'solid_white'}]},
    ),
    'matte_outline': dict(
        where='matte、corner 版式的 "outline"：solid_white / color_thin / dashed / torn_edge（color_thin 可配 "outline_color": "green"）',
        style=['web'], auto='描边前先把飘起来的头发丝收掉，不会描成一坨白；虚线背景自动压暗',
        variants={k: (['web'] if k != 'color_thin' else ['web', 'premium'], d) for k, d in OUTLINES.items()},
        demo=lambda A, v: {'layout': [{'t0': 0.2, 't1': 3.6, 'mode': 'matte', 'bg': 'keep' if v != 'color_thin' else 'blur', 'outline': v}]},
    ),
    'matte_corner_person': dict(
        where='layout 的 corner 版式：{"mode": "corner", "variant": 变体, "items": [文字 或 {text, en, src}], "src": 录屏}；'
              '人默认站的一边录屏右下有关键内容时写 "side": "left"', style=['web', 'premium'],
        auto='开头 0.4 秒人从原位缩进角落，卡片之后每 0.3 秒弹一张，各带一声',
        variants={'over_recording': (['web', 'premium'], CORNER_VARIANTS['over_recording']),
                  'point_cards': (['web', 'premium'], CORNER_VARIANTS['point_cards']),
                  'glass_cards': (['web'], CORNER_VARIANTS['glass_cards']),
                  'tilted_cards': (['web'], CORNER_VARIANTS['tilted_cards'])},
        demo=lambda A, v: {'layout': [{'t0': 0.2, 't1': 3.6, 'mode': 'corner', 'variant': v, 'src': A['rec'],
                                       'items': [{'text': '一事一会话', 'en': 'one task', 'src': A['photo']},
                                                 {'text': '留两成交接', 'en': 'handoff', 'src': A['shot']},
                                                 {'text': '先读再动手', 'en': 'read first', 'src': A['photo']}]}]},
    ),
    'matte_frame_breakout': dict(
        where='layout 的 breakout 版式：{"mode": "breakout", "variant": 变体, "title": 标题或相框手写字, "src": 素材, "src2": 横条下方的图}',
        style=['web'], auto='头出框多少按头顶位置自动算（overflow 可改）；进来那一下 0.15 秒叠化，自带啵一声',
        variants={k: (['web'], d) for k, d in BREAKOUT_VARIANTS.items()},
        demo=lambda A, v: {'layout': [{'t0': 0.2, 't1': 3.6, 'mode': 'breakout', 'variant': v, 'src': A['photo'] if v == 'band_pop' else A['shot'],
                                       'src2': A['shot'], 'title': {'head_over_frame': 'Day 1', 'band_pop': '新手三个坑'}.get(v, '上下文管理')}]},
    ),
})


# 第 5 批声音与粗剪。样本册素材 A 里多了：bgm 主配乐、calm / dense / hype 三首演示曲、raw 没粗剪的口播、
# rough_web / rough_premium 两档粗剪结果目录、rec_wait 带等待段的竖屏录屏、lines 样本口播的逐字时间。
# 示例里的 dur 是这段样片多长（声音类要听一会儿），_aroll / _lines 换样片用的口播和逐字时间，_wave 在画面底部叠一条声音波形。
def _items(at, sound=None):
    t = {'t0': 0.2, 't1': 3.5, 'layout': 'list', 'variant': 'bullets', 'items': ['选题', '脚本', '剪辑', '复盘'], 'item_at': at, 'sfx': False}
    if sound:
        t['sound'] = sound
    return t


_AT4 = [0.3, 0.9, 1.5, 2.1]
_UI = {'click': 'click', 'ding': 'ding', 'pop': 'pop', 'slide_ui': 'zip_up'}
_NEW_SOUNDS = {'door': '开门', 'mech_door': '机械开合', 'mech_robot': '机器启动', 'mech_wind': '上发条', 'zoom_in': '推近',
               'zoom_out': '拉远', 'suspense_tap': '悬念', 'dun_dun_duun': '戏剧重音', 'cheer_shout': '欢呼', 'bass_hit': '贝斯单音',
               'blade_swish': '利刃'}


def _music(A, v):
    """按段落换曲的示例：前 3.5 秒一段、后面一段，换在 3.5 秒。"""
    calm, dense = {'src': A['calm'], 'mood': 'calm'}, {'src': A['dense'], 'mood': 'dense'}
    hard = {'broll': [{'t0': 3.5, 't1': 7.0, 'src': A['photo'], 'fit': 'cover', 'sfx': False}]}
    if v == 'open_boost':
        return {'audio': {'bgm': [{'src': A['bgm'], 't0': 0, 't1': 7.0}], 'open_boost': {'src': A['hype'], 'len': 3.5}, 'bed': False}}
    seam = {'density_bpm': None, 'chapter_switch': 'xfade', 'mood_switch': 'cut', 'sfx_seam': 'whoosh', 'silence_gap': 'gap'}[v]
    second = {'t0': 3.5, 'name': '后一段', 'mood': 'dense' if v in ('density_bpm', 'sfx_seam', 'mood_switch') else 'calm',
              **({'seam': seam} if seam else {}), **({'shout': True} if v == 'mood_switch' else {}), **({'gap': 1.0} if v == 'silence_gap' else {})}
    tracks = [calm, dense] if second['mood'] == 'dense' else [calm, {'src': A['bgm'], 'mood': 'calm'}]
    fast = [{'t0': 3.5 + i * 0.7, 't1': 4.2 + i * 0.7, 'src': (A['photo'], A['shot'])[i % 2], 'fit': 'cover', 'sfx': False} for i in range(5)]
    return {'sections': [{'t0': 0, 'name': '前一段', 'mood': 'calm'}, second], 'audio': {'tracks': tracks, 'bed': False},
            **({'broll': fast} if v == 'density_bpm' else hard if v in ('mood_switch', 'chapter_switch') else {})}


FIELDS.update({
    'sfx_event_engine': dict(
        where='自动：画面上每个事件（大字、素材、版式、转场、定格）开始那一帧按事件类型配声音；手写在素材、大字、版式的 "sound" 或顶层 "sounds"。'
              'sound 可以写声音清单里的名字、组合名（swing 挥动落定、shuttle 穿梭、rising_ui 升调串），也可以直接写剪映音效原名（「综艺叮」「唰」），'
              '按对照表换算。密度写 audio.sfx_density：sparse / dense', style=['premium', 'web', 'variety'],
        auto='起音对准画面事件开始那一帧（蓄力类反向镲、上升音是最响处对准）；同一时刻最多叠两个；重音类每种全片两次；'
             '一句话里提示音最多 3 个；纯口播段不加。渲染加 --stems 后用 audio_check.py 出频谱检查图和逐个音效差几帧',
        variants={'premium_sparse': (['premium', 'web'], '高级感稀疏：每分钟最多 12 个，只挂画面事件'),
                  'variety_dense': (['variety', 'web'], '综艺感密集：每分钟最多 30 个，每个花字、每次弹出都配一声'),
                  'new_sounds': (['premium', 'web', 'variety'], '新增声音试听：开门、机械开合、机器启动、上发条、推近、拉远、悬念、戏剧重音、欢呼、贝斯单音、利刃')},
        demo=lambda A, v: {
            'premium_sparse': {'dur': 7.0, 'audio': {'sfx_density': 'sparse'}, 'titles': [{'t0': 0.4, 't1': 2.6, 'layout': 'side', 'lead': '真正拉开差距的是', 'text': '信息密度', 'hl': ['密度']}],
                               'broll': [{'t0': 3.0, 't1': 5.4, 'src': A['shot'], 'fit': 'card', 'enter': 'slide_up'}],
                               'transitions': [{'t': 5.9, 'type': 'flash'}]},
            'variety_dense': {'dur': 7.0, 'style': 'variety', 'audio': {'sfx_density': 'dense'},
                              'titles': [_items(_AT4, [{'type': '综艺叮', 'at': a} for a in _AT4]),
                                         {'t0': 3.8, 't1': 6.6, 'layout': 'word', 'text': '全踩坑', 'anim': 'drop', 'sound': 'thump'}],
                              'sounds': [{'t': 4.6, 'type': 'pop'}, {'t': 5.4, 'type': 'error'}]},
            'new_sounds': {'dur': 11 * 1.0 + 0.6, 'titles': [{'t0': 0.3 + i, 't1': 1.25 + i, 'layout': 'side', 'text': zh, 'anim': 'none', 'sfx': False,
                                                            'sound': n} for i, (n, zh) in enumerate(_NEW_SOUNDS.items())]},
        }[v],
    ),
    'sfx_impact': dict(
        where='大字、素材、sounds 写 "sound"：swing（挥动落定）/ hit（击中）/ thump（综艺咚）', style=['web', 'variety'],
        auto='重音前 0.2 秒配乐自动压低 6 dB 让出位置；hit 这类重音每种全片最多两次',
        variants={'swing': (['web', 'variety'], COMBOS['swing']['use']), 'hit': (['web', 'variety'], '击中：标题砸下、数据炸出'),
                  'dong': (['web', 'variety'], '综艺咚：低沉一声把观众摁住（thump）')},
        demo=lambda A, v: {'dur': 4.0, 'audio': {'bgm': [{'src': A['bgm'], 't0': 0, 't1': 4.0}], 'bed': False},
                           'titles': [{'t0': 0.6, 't1': 3.8, 'layout': 'word', 'text': '暴涨 3 倍', 'anim': 'drop',
                                       'sound': {'swing': 'swing', 'hit': 'hit', 'dong': 'thump'}[v]}]},
    ),
    'sfx_ui_pop': dict(
        where='大字、素材、sounds 写 "sound"：click / ding / pop / rising_ui（写 step 0、1、2…一个比一个高）/ zip_up（电子滑音）',
        style=['web', 'variety'], auto='提示音一句话里最多 3 个，多了自动去掉或压低；同一组并列词用同一个声音',
        variants={'click': (['web', 'variety'], '点击：标签、按钮、卡片弹出'), 'ding': (['web', 'variety'], '叮：花字关键词弹出'),
                  'pop': (['web', 'variety'], '啵：图片、气泡冒出'), 'rising_ui': (['web', 'variety'], COMBOS['rising_ui']['use']),
                  'slide_ui': (['web', 'variety'], '电子滑音：图标、贴纸飞入（zip_up）')},
        demo=lambda A, v: {'dur': 3.6, 'titles': [_items(_AT4, [{'type': 'rising_ui', 'step': i, 'at': a} for i, a in enumerate(_AT4)] if v == 'rising_ui'
                                                          else [{'type': _UI[v], 'at': a} for a in _AT4])]},
    ),
    'sfx_whoosh': dict(
        where='transitions 写 "sound"：whoosh（唰）/ whoosh_big（旋风）/ shuttle（穿梭）；不写按转场种类自动配', style=['web', 'premium'],
        auto='效果转场自带：闪白、模糊扫屏配唰，压黑配旋风，漏光配穿梭，故障配电流；起音对准转场开始那一帧；硬切不配',
        variants={'speed': (['web', 'premium'], '速度感：短促的唰，配动态模糊甩切'), 'gust': (['web', 'premium'], '呼啸感：更长更厚的风声'),
                  'shuttle': (['web', 'premium'], '穿梭感：嗖一声叠高音闪光')},
        demo=lambda A, v: {'dur': 3.6, 'broll': [{'t0': 1.6, 't1': 3.6, 'src': A['photo'], 'fit': 'cover', 'sfx': False}],
                           'transitions': [{'t': 1.6, 'type': {'speed': 'blur_swipe', 'gust': 'dip_black', 'shuttle': 'light_leak'}[v],
                                            'sound': {'speed': 'whoosh', 'gust': 'whoosh_big', 'shuttle': 'shuttle'}[v]}]},
    ),
    'music_bed_levels': dict(
        where='audio.bed：{"open": 13, "lift": 5, "fade": 0.9}（默认就开，写 false 关掉）', style=['premium', 'web', 'variety'],
        auto='开头 13 秒配乐比正文高 5 dB，0.9 秒过渡到正文；人一说话配乐自动让开（阈值 -30 dB、压缩比 6），说话时配乐比人声低约 18~22 dB',
        variants={'bed': (['premium', 'web', 'variety'], '开头高一档、正文压低（样片把开头缩成 4 秒）')},
        demo=lambda A, v: {'dur': 9.0, '_wave': True, 'audio': {'bgm': [{'src': A['bgm'], 't0': 0, 't1': 9.0}], 'bed': {'open': 4.0}}},
    ),
    'music_hit_stop_gap': dict(
        where='段落留白：sections 的段落写 "seam": "gap"（"gap": 秒）；重音收住：audio.stops [{"t": 数字放大那一帧, "gap": 1.0}]',
        style=['premium', 'web'], auto='留白和重音收住后面必须跟一个大变化（换段、章节页、硬切画面）；只有一首配乐、没写段落时，章节页前自动压低一下',
        variants={'plain_gap': (['premium', 'web'], '段落留白：配乐停 0.8 秒，再带新一段进来'),
                  'hit_stop': (['premium', 'web'], '重音收住再硬切：数字放大那一帧一声重音鼓，配乐跟着收，空 1 秒硬切进下一段')},
        demo=lambda A, v: {'dur': 7.0, '_wave': True, 'audio': {'bgm': [{'src': A['bgm'], 't0': 0, 't1': 7.0}], 'bed': False,
                                                                **({'stops': [{'t': 2.6, 'gap': 1.0}]} if v == 'hit_stop' else {})},
                           **({'sections': [{'t0': 0, 'name': '前一段'}, {'t0': 3.6, 'name': '后一段', 'seam': 'gap', 'gap': 0.8}]} if v == 'plain_gap' else {}),
                           'titles': [{'t0': 2.6, 't1': 3.6, 'layout': 'word', 'text': '90%', 'anim': 'pop', 'sfx': False}] if v == 'hit_stop' else [],
                           'broll': [{'t0': 3.6, 't1': 7.0, 'src': A['photo'], 'fit': 'cover', 'sfx': False}]},
    ),
    'music_section_switch': dict(
        where='顶层 sections 分段（写 mood：calm / dense / happy / hype，可写 seam、shout），audio.tracks 给几首曲子 [{"src", "mood"}]；'
              '开场提气写 audio.open_boost {"src", "len": 7}', style=['premium', 'web', 'variety'],
        auto='段落没写情绪按画面密度判（每 10 秒 3.5 个以上画面事件算快剪段），曲子没写情绪按速度判（108 BPM 以上算快）；'
             '换到没放过的曲子从它第一个有劲的重拍起播；舒缓切快节奏默认嗖一声盖接缝，快切慢默认留白，同情绪交叉淡化且早 0.3 秒进来；'
             '只给一首曲子时在同一首里按段落跳到能量高的一段；不生成任何音乐',
        variants={'open_boost': (['premium', 'web', 'variety'], '开场提气再切主曲：提气曲 0.34 秒淡出，主曲 0.33 秒淡入'),
                  'density_bpm': (['premium', 'web'], '按信息密度换快慢：快剪段自动换快歌'),
                  'chapter_switch': (['premium', 'web'], '大章节换曲：交叉淡化，声音比画面早 0.3 秒'),
                  'mood_switch': (['web', 'variety'], '情绪突变换曲：画面切的那一帧直接换，叠一声欢呼'),
                  'sfx_seam': (['premium', 'web'], '音效盖接缝：嗖起来时前一首淡出，后一首在嗖最响处起播'),
                  'silence_gap': (['premium', 'web'], '音乐留白：前一首先停 1 秒，再进下一首')},
        demo=lambda A, v: {'dur': 7.0, '_wave': True, **_music(A, v)},
    ),
    'jcut_audio_lead': dict(
        where='自动（timeline 写 "jcut": false 关掉，写数字改提前量 0.3~1 秒）', style=['premium', 'web'],
        auto='铺满画面的素材、遮住人的版式、章节页在下一句开口前后结束时，延长到开口后 0.35 秒：先听到下一句，画面再切回口播。'
             '画面盖住了嘴，口型不会对不上；单机位口播之间不做（声音先进来时人嘴没动，口型会穿帮）。配乐换曲的交叉淡化也早 0.3 秒进来',
        variants={'off': (['premium', 'web'], '对比：素材在开口前就切回口播'), 'audio_lead_jcut': (['premium', 'web'], '声音先入：开口 0.35 秒后画面才切回')},
        demo=lambda A, v: {'dur': 4.8, '_lines': A['lines'], 'jcut': False if v == 'off' else 0.35,
                           'broll': [{'t0': 0.3, 't1': 2.1, 'src': A['photo'], 'fit': 'cover', 'sfx': False}]},
    ),
    'rough_cut_breath_trim': dict(
        where='粗剪：auto_edl.py 从转写起草 edl.json（重录留最后一遍、半句和语气词删掉），edl 写 "breath": web_tight / premium_breath，'
              '段落结尾那句写 "para": true；rough_cut.py 照着剪', style=['premium', 'web', 'variety'],
        auto='网感紧剪句间只留 0.08 秒、一句里超过 0.15 秒的停顿也收短；高级感句间留 0.3 秒、段落结尾多留 1 秒；'
             '句中收短留下的刀口写进 lines.json，渲染时在那里跳景别遮跳剪',
        variants={'raw': (['premium', 'web', 'variety'], '原始素材（口播 02 前 20 秒，没剪）'),
                  'web_tight': (['web', 'variety'], '网感紧剪：41.7 秒原片剪成 18.2 秒，平均 2.6 秒一刀'),
                  'premium_breath': (['premium', 'web'], '高级感留气口：剪成 20.6 秒，段落处多留一口气')},
        demo=lambda A, v: {'raw': {'dur': 20.0, '_aroll': A['raw'], '_aroll_in': 2.0},
                           'web_tight': {'dur': 18.2, '_aroll': A['rough_web'] + '/aroll.mp4', '_lines': A['rough_web'] + '/lines.json'},
                           'premium_breath': {'dur': 20.6, '_aroll': A['rough_premium'] + '/aroll.mp4', '_lines': A['rough_premium'] + '/lines.json'}}[v],
    ),
    'speed_adjust': dict(
        where='口播整体：edl.json 的 "speed"（真人 1.05~1.09，AI 配音写 "ai_voice": true 可到 1.2）；录屏：broll 写 "speed": "auto"',
        style=['web', 'premium'], auto='录屏里 1 秒以上画面不动的等待段加速 2~10 倍正好塞进这段，加速处右上角标「快进 ×N」；录屏比这段短时整体放慢（最慢 0.36 倍）',
        variants={'voice_1x': (['web', 'premium'], '对比：口播原速'), 'voice_global': (['web', 'premium'], '口播整体提速 1.07 倍，听不出变调'),
                  'screenrec_1x': (['web', 'premium'], '对比：6 秒录屏原速放进 3.3 秒，后半截看不到'),
                  'screenrec_ramp': (['web', 'premium'], '录屏等待段加速：三段等待加速，整段操作都看得到')},
        demo=lambda A, v: {'voice_1x': {'dur': 6.0, '_aroll': A['raw'], '_aroll_in': 14.0},
                           'voice_global': {'dur': 5.6, '_aroll': A['raw'], '_aroll_in': 14.0, '_speed': 1.07},
                           'screenrec_1x': {'broll': [{'t0': 0.3, 't1': 3.6, 'src': A['rec_wait'], 'fit': 'cover', 'sfx': False}]},
                           'screenrec_ramp': {'broll': [{'t0': 0.3, 't1': 3.6, 'src': A['rec_wait'], 'fit': 'cover', 'speed': 'auto', 'sfx': False}]}}[v],
    ),
    'voice_cleanup_loudness': dict(
        where='audio.voice：{"lufs": -16, "denoise": true, "deess": true, "compress": true}（默认全开；"cleanup": false 只做响度）',
        style=['premium', 'web', 'variety'],
        auto='先量素材底噪定降噪强度，再高通去嗡声、去齿音、轻压缩，最后两遍法把响度拉到 -16 LUFS（综艺感 -15），峰值不超过 -1.5 dBFS；结果按素材缓存',
        variants={'raw': (['premium', 'web', 'variety'], '对比：原声没处理'), 'clean': (['premium', 'web', 'variety'], '降噪、去齿音、压缩、响度 -16 LUFS')},
        demo=lambda A, v: {'dur': 6.0, '_aroll': A['raw'], '_aroll_in': 14.0, '_wave': True,
                           'audio': {'voice': {'raw': True} if v == 'raw' else {}}},
    ),
    'script_segment_plan': dict(
        where='顶层 sections：[{"t0", "name", "mood"}]，开场、第一点…结束语各一段；plan.md 先写段落表再逐句包装', style=['premium', 'web'],
        auto='3 段以上或 3 分钟以上没写 sections，rhythm_check 会提醒；配乐换曲、留白、声音先入都按段落走；没写就按章节页切',
        variants={}, demo=None,
    ),
})

# ---- 第 6 批：声音、配乐和小补充（不跟大字版式走）
_SAY = lambda t0, t1, text: {'t0': t0, 't1': t1, 'text': text, 'level': 'base'}
FIELDS.update({
    'title_aside_note': dict(
        where='beats 的一条写 "note": "小补充"、"note_look": arc / tag；主标题出来 0.3 秒后弹到它右上角', style=['web'],
        auto='位置按主标题排好的外框算；每个画面最多一个',
        variants={'tag': (['web'], '便利贴标签：橙底黑字小色块歪 5 度'), 'arc': (['web'], '弧形语气词：一行黄色小字沿弧线斜排')},
        demo=lambda A, v: {'beats': [{'t0': 0.3, 't1': 3.5, 'beat': 'concept', 'use': 'side', 'lead': '这一步叫', 'text': '版本管理',
                                      'note': '亲测好用' if v == 'tag' else '真的很香', 'note_look': v, 'sfx': False}]},
    ),
    'sfx_comic_sting': dict(
        where='自动：beats 里 emotion（情绪、吐槽）句的句末；negative（负面）句写 "sting": true 或声音名才配（提醒类的负面句配梗会错位）；'
              '写 false 关；audio.stings false 全关',
        style=['web', 'variety'],
        auto='负面句轮换失落类（悲伤长号、失败钢琴、答错；放屁声只在综艺感），情绪句轮换滑稽类（打脸、弹簧、被打懵、小丑喇叭、梗鼓点）；'
             '两个梗音效至少隔 12 秒；戏剧三连（dun_dun_duun）只能手写，全片一次；克制档不加',
        variants={'drama': (['web', 'variety'], '戏剧三连：反转、真相揭晓'), 'slap': (['web', 'variety'], '打脸重击：被怼、被驳回、想法撞墙'),
                  'fail': (['web', 'variety'], '翻车滑稽：白忙一场、失落')},
        demo=lambda A, v: {'dur': 4.0, 'beats': [{'t0': 0.4, 't1': 2.6, 'beat': {'drama': 'emotion', 'slap': 'emotion', 'fail': 'negative'}[v],
                                                   'use': 'word', 'text': {'drama': '真相', 'slap': '被怼', 'fail': '翻车'}[v],
                                                   'sting': {'drama': 'dun_dun_duun', 'slap': 'punch', 'fail': 'sad_trombone'}[v], 'sfx': False}]},
    ),
    'sfx_mechanical': dict(
        where='自动：版式 inset、split、frame 出现或变化那一刻；手写 sound 写 mech_door / mech_robot / mech_wind', style=['web'],
        auto='口播卡片放大或缩小（推拉）配气压开门，画框形变配机器人启动，分屏拼接配上发条；柔和治愈的片子写 sfx: false 关',
        variants={'door': (['web'], '气压开门：口播卡片推拉'), 'robot': (['web'], '机器人启动：画框形变'), 'wind': (['web'], '上发条：分屏拼接')},
        demo=lambda A, v: {'dur': 3.6, 'layout': [{'t0': 0.4, 't1': 3.4, **{
            'door': {'mode': 'inset', 'anim': 'expand', 'at': 0.6, 'bg': 'dots'},
            'robot': {'mode': 'frame'},
            'wind': {'mode': 'split', 'variant': 'torn', 'focus_at': [0, 1.6], 'panels': [{'src': 'aroll', 'label': '以前'}, {'src': A['photo'], 'label': '现在'}]}}[v]}]},
    ),
    'bass_pre_entry': dict(
        where='自动（audio.bass_pre 写 false 关）', style=['premium', 'web'],
        auto='数据卡、数字、整屏单字、章节页出现前 0.4 秒先响一个贝斯单音，让情绪先进场；综艺感不加；不和砸屏的重击叠',
        variants={'bass': (['premium', 'web'], '包装前垫低音')},
        demo=lambda A, v: {'dur': 4.0, 'audio': {'bgm': [{'src': A['bgm'], 't0': 0, 't1': 4.0}], 'bed': False},
                           'titles': [{'t0': 1.2, 't1': 3.8, 'layout': 'word', 'text': '暴涨 3 倍', 'anim': 'drop'}]},
    ),
    'sfx_ambience': dict(
        where='自动：beats 里 question（提问）句底下铺悬念小鼓；beat 写 "ambience": suspense / calm / false', style=['web', 'premium'],
        auto='悬念最多铺 4 秒，比配乐低一档；calm 是闪亮一声加平静氛围底，用在温柔、治愈的段落',
        variants={'suspense': (['web', 'premium'], '悬疑紧张：抛出问题等答案'), 'calm': (['web', 'premium'], '温柔治愈：闪亮一声加平静氛围')},
        demo=lambda A, v: {'dur': 4.0, 'beats': [{'t0': 0.3, 't1': 3.8, 'beat': 'question' if v == 'suspense' else 'story', 'use': 'side',
                                                   'text': '到底满没满？' if v == 'suspense' else '慢慢来', 'ambience': v, 'sfx': False}]},
    ),
    'voice_fx_swap': dict(
        where='顶层 voice_fx：[{"t0", "t1", "type": megaphone / bleep, "label"}]', style=['web', 'variety'],
        auto='扩音器：这几秒人声只留中频再轻微失真，画面叠四角取景框和闪烁的 REC；哔声：原声静音换成 1000 Hz 的哔，嘴边贴黄底「消音」（label 可改）。'
             'AI 配音的内心独白要接语音合成，还没做；剪映草稿里变声要在剪映里手动加',
        variants={'megaphone': (['web', 'variety'], '扩音器念原话'), 'bleep': (['web', 'variety'], '哔声消音')},
        demo=lambda A, v: {'dur': 4.0, '_lines': A['lines'], 'voice_fx': [{'t0': 0.6, 't1': 2.8 if v == 'megaphone' else 1.4, 'type': v}]},
    ),
    'music_beat_loop': dict(
        where='audio.tracks 里那首写 "loop": true（或 {"bars": 4}）', style=['premium', 'web'],
        auto='挑这首里能量平稳的 4 小节（短于 8 秒的拍子取 8 小节），首尾按重拍对齐反复接、接缝 10 毫秒交叉淡化，铺满它负责的段落；'
             '循环 2 分钟以上会腻，中间用段落换曲打断',
        variants={'loop': (['premium', 'web'], '节奏段无缝循环（样片用 2 小节，5.3 秒处接回开头）')},
        demo=lambda A, v: {'dur': 9.0, '_wave': True, 'audio': {'tracks': [{'src': A['bgm'], 'mood': 'calm', 'loop': {'bars': 2}}], 'bed': False}},
    ),
    'music_climax_splice': dict(
        where='sections 的段落写 "climax": true（或秒数）', style=['premium', 'web'],
        auto='这一段最后约 4 小节（6~10 秒）换成同一首里能量最高的 4 小节，切点落在重拍上听不出接缝，推到段落结束；后面接段落留白或换曲',
        variants={'climax': (['premium', 'web'], '截高潮段推到段落末尾（样片 3 秒处切进高潮）')},
        demo=lambda A, v: {'dur': 9.0, '_wave': True, 'sections': [{'t0': 0, 'name': '前一段', 'mood': 'calm', 'climax': 6.0},
                                                                   {'t0': 8.0, 'name': '后一段', 'mood': 'calm', 'seam': 'gap'}],
                           'audio': {'tracks': [{'src': A['bgm'], 'mood': 'calm'}], 'bed': False}},
    ),
})

# ---- 第 7 批：要写坐标或字段的贴纸标注、入场退场
FIELDS.update({
    'arrow_stickers': dict(
        where='titles 写 {"layout": "arrow", "variant": point / up / corners, "from": [x, y], "to": [x, y], "color", "dir": "down"}，坐标按画面比例，'
              'to 是箭头要指的那一点（截图上的按钮、数字），一定要对准真实目标', style=['web', 'variety'],
        auto='0.2 秒从尾巴长到箭头，到了沿方向轻轻弹；同屏箭头风格不超过 2 种',
        variants={'point': (['web', 'variety'], '粗箭头指向目标：带白边的黄色粗箭头'), 'up': (['web', 'variety'], '3D 上升箭头：绿色立体箭头往右上冲，dir 写 down 是红色下跌'),
                  'corners': (['web', 'variety'], '四角视线引导：四个箭头从画面四角指向主体')},
        demo=lambda A, v: {'titles': [{'t0': 0.4, 't1': 3.4, 'layout': 'arrow', 'variant': v,
                                       **({'from': [0.85, 0.78], 'to': [0.62, 0.6]} if v == 'point' else {'to': [0.7, 0.58]} if v == 'up' else {'to': [0.5, 0.33]})}]},
    ),
    'focus_box': dict(
        where='titles 写 {"layout": "focus", "variant": brackets / callout / glow, "box": [x, y, w, h], "text"}，box 按画面比例圈出要看的地方',
        style=['web', 'premium'], auto='同屏只一个焦点；glow 写了 text 就在框里重写那句话（字少于两行）',
        variants={'brackets': (['web', 'premium'], '对焦角标：四个白色角标从大一圈收紧'), 'callout': (['web', 'premium'], '黄色细框：框外压暗两成'),
                  'glow': (['web'], '发光框重写重点句：黄绿发光框里重写那句话')},
        demo=lambda A, v: {'broll': [{'t0': 0.2, 't1': 3.5, 'src': A['shot'], 'fit': 'card', 'w': 0.86, 'y': 0.45, 'sfx': False}],
                           'titles': [{'t0': 0.8, 't1': 3.4, 'layout': 'focus', 'variant': v, 'box': [0.12, 0.4, 0.76, 0.1],
                                       **({'text': '先写交接文档'} if v == 'glow' else {})}]},
    ),
    'card_slide_pair': dict(
        where='titles 写 {"layout": "cardpair", "src": 第一张, "src2": 第二张, "at": 第二张进场秒数, "y", "w"}', style=['premium', 'web'],
        auto='第一张居中出现，到 at 秒 0.5 秒缓入缓出往左让到画面左边（露出约半张），第二张从右边滑到右半边，两张并排；底下口播压暗',
        variants={'pair': (['premium', 'web'], '先说 A 再说 B 的并列截图')},
        demo=lambda A, v: {'titles': [{'t0': 0.3, 't1': 3.5, 'layout': 'cardpair', 'src': A['shot'], 'src2': A['photo'], 'at': 1.4}]},
    ),
    'divider_line_reveal': dict(
        where='titles 写 {"layout": "divider", "y": 0.42, "w": 0.8}', style=['premium'],
        auto='0.6 秒从中间往两边展开，两端渐隐，1080 宽画布上 3 像素，压一层淡投影浅色墙上也看得见',
        variants={'line': (['premium'], '肩膀高度金色细线，把标题区和人分开')},
        demo=lambda A, v: {'titles': [{'t0': 0.3, 't1': 3.5, 'layout': 'divider', 'y': 0.42},
                                      {'t0': 0.6, 't1': 3.5, 'layout': 'side', 'text': '版本管理', 'y': 0.3, 'sfx': False}]},
    ),
    'doodle_marks': dict(
        where='doodles 写 {"type": multicircle / spiral / exclaim / sparkle / circle, "x", "y", "w", "h"} 或 "target": {"text": 大字里的词}',
        style=['web', 'variety'], auto='逐笔画出 0.4 秒；同一画面涂鸦圈不超过 3 个、放射线一个，每分钟贴纸点缀不超过 4 个，不压脸不压大字',
        variants={'multicircle': (['web', 'variety'], '多圈涂鸦圈：一笔绕两圈半'), 'spiral': (['web', 'variety'], '螺旋圈：从外往里收'),
                  'exclaim': (['web', 'variety'], '三短线放射：情绪点上冒三道短线'), 'sparkle': (['web', 'variety'], '星光：亮点、灵感')},
        demo=lambda A, v: {'titles': [{'t0': 0.3, 't1': 3.5, 'layout': 'side', 'text': '改坏了', 'y': 0.56, 'sfx': False}],
                           'doodles': [{'t0': 0.7, 't1': 3.4, 'type': v, 'target': {'text': '改坏了'}} if v in ('multicircle', 'spiral') else
                                       {'t0': 0.7, 't1': 3.4, 'type': v, 'x': 0.78, 'y': 0.3, 'w': 0.16, 'h': 0.09}]},
    ),
    'entry_preset_extra': dict(
        where='titles 写 "anim"：fall（上方落下）/ graypop（灰变白放大）/ flip（镜面翻转）', style=['premium'],
        auto='都不回弹、干净利落，克制档用；flip 适合面板、章节名',
        variants={'fall': (['premium'], '上方落下：从一成画面高处落下，模糊变清'), 'graypop': (['premium'], '灰变白放大：灰色半透明小字放大成白字'),
                  'flip': (['premium'], '镜面翻转：像卡片一样绕竖轴翻进来')},
        demo=lambda A, v: {'titles': [{'t0': 0.3, 't1': 3.5, 'layout': 'side', 'lead': '这一步叫', 'text': '版本管理', 'anim': v, 'sfx': False}]},
    ),
    'read_then_dim': dict(
        where='titles 写 "dim_after": 秒（从出现算起，说完的时刻）', style=['premium'],
        auto='说完后 2.5 秒慢慢暗到三成多亮度，留在画面上可以回看，下一个版式硬切掉',
        variants={'dim': (['premium'], '读完压暗留底（样片 1.2 秒后开始暗）')},
        demo=lambda A, v: {'titles': [{'t0': 0.3, 't1': 3.6, 'layout': 'quote', 'text': '不要依赖 AI 的记忆\\N来撤回', 'hl': ['记忆'], 'dim_after': 1.2, 'sfx': False}]},
    ),
})


# ---- 第 8 批：画面特效与转场（effects.py）。整屏特效写顶层 fx，转场写 transitions（或章节页自动加），插片写 inserts
from kvlib import FACE_FX, FX, TRANSITIONS   # noqa: E402
from effects import BOOM_VARIANTS   # noqa: E402

IMPL.update({
    'radial_burst_bg': dict(
        beats={'emotion': 1, 'negative': 2, 'emphasis': 2}, style=['web', 'variety'], intensity=3, max_n=2,
        variants={'behind': ['web', 'variety'], 'cartoon': ['web', 'variety']},
        variant_ok={'cartoon': lambda b: _short(b.get('text'), 1)},
        ok=lambda b: _short(b.get('text'), 4),
        build=lambda b, v, at: {'layout': 'boom', 'variant': v, 'text': b['text'], **({'cover': True} if v == 'cartoon' else {})},
        sound=lambda st, b, at: [{'type': 'whoosh_big', 'at': 0.0}, {'type': 'thump', 'at': 0.15}] if st.get('variant') == 'cartoon'
        else [{'type': 'hit', 'at': 0.0}],
        demo={'beat': 'emotion', 'text': '炸了'},
        demo_v={'cartoon': {'text': '爽'}},
    ),
    'text_persist_bg_swap': dict(
        beats={'quote': 1, 'transition_talk': 2, 'emphasis': 3}, style=['premium', 'web'], intensity=2,
        ok=lambda b: _short(b.get('text', '').replace('\\N', ''), 12),
        build=lambda b, v, at: {'layout': 'persist', 'text': b['text']},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.3}, {'type': 'whoosh', 'at': 0.9}],
        demo={'beat': 'quote', 'text': '慢就是快'},
    ),
})
VNAMES.update({'behind': BOOM_VARIANTS['behind'].split('：')[0], 'cartoon': BOOM_VARIANTS['cartoon'].split('：')[0]})


def _fxd(A, t0, t1, kind, v=None, **kw):
    return {'fx': [{'t0': t0, 't1': t1, 'type': kind, **({'variant': v} if v else {}), **kw}]}


def _cut(A, kind, v=None, at=1.8, **kw):
    """转场样片：at 秒从口播硬切到一张照片，转场盖在切点上；open 光圈反过来，从照片切回口播。"""
    if kind == 'iris' and v == 'open':
        b = {'t0': 0.2, 't1': at, 'src': A['photo'], 'fit': 'cover', 'sfx': False}
    else:
        b = {'t0': at, 't1': 3.6, 'src': A['photo'], 'fit': 'cover', 'sfx': False}
    return {'broll': [b], 'transitions': [{'t': at, 'type': kind, **({'variant': v} if v else {}), **kw}]}


_FACE_DEMO = {'bighead': ['大头', '懵'], 'hot': ['红温大头'], 'stab': ['中刀'], 'stone': ['石化了'], 'idea': ['灵机一动'], 'crash': ['宕机中', '尴尬住了']}
_FOG = {'layout': 'fog', 'number': 2, 'text': '先规划再动手', 'en': 'plan first', 'sfx': False}

FIELDS.update({
    'screen_reaction_fx': dict(
        where='顶层 fx 写 {"t0", "t1", "type": bw / shake / crack / magnifier / the_end / blur}；crack 的 "at": [x, y] 是裂开的点，'
              'magnifier 的 "at" 是要放大的点（"zoom" 倍数、"r" 镜片半径占画面宽），blur 的 "box": [x, y, w, h]', style=['web', 'variety'],
        auto='每种自带声音（变黑白低音下沉、震动落地、裂开重击、放大镜推近、全剧终反向镲片）；剪映草稿里变黑白、震动、裂开了、全剧终放剪映真特效，'
             '放大镜和模糊遮挡那几秒铺成片画面',
        variants={k: (['web', 'variety'], FX[k]['use']) for k in ('bw', 'shake', 'crack', 'magnifier', 'the_end', 'blur')},
        demo=lambda A, v: {'bw': _fxd(A, 0.6, 3.4, 'bw'), 'shake': _fxd(A, 0.8, 1.5, 'shake'),
                           'crack': _fxd(A, 0.8, 3.4, 'crack'), 'the_end': _fxd(A, 0.6, 3.6, 'the_end'),
                           'magnifier': {'broll': [{'t0': 0.2, 't1': 3.5, 'src': A['shot'], 'fit': 'card', 'w': 0.86, 'y': 0.45, 'motion': 'static', 'sfx': False}],
                                         **_fxd(A, 0.9, 3.4, 'magnifier', at=[0.5, 0.44])},
                           'blur': {'broll': [{'t0': 0.2, 't1': 3.5, 'src': A['shot'], 'fit': 'card', 'w': 0.86, 'y': 0.45, 'motion': 'static', 'sfx': False}],
                                    **_fxd(A, 0.8, 3.4, 'blur', box=[0.1, 0.36, 0.8, 0.08])}}[v],
    ),
    'spotlight_vignette': dict(
        where='fx 写 {"type": "spotlight", "variant": push / drama, "y": 亮区中心高}；只用在开头或重大转折，一期一两次',
        style=['premium', 'web', 'variety'], auto='push 同时整句缓推到 112%（"push": false 不推）；drama 加荧幕噪点、配重音；剪映草稿放「聚光灯」',
        variants={'push': (['premium', 'web', 'variety'], '聚光加推近：四周压成椭圆暗角只有人亮，同时缓推到 112%'),
                  'drama': (['web', 'variety'], '戏剧聚焦：聚光加荧幕噪点，关键反转词处配重音')},
        demo=lambda A, v: _fxd(A, 0.3, 3.4, 'spotlight', v),
    ),
    'dim_spotlight_box': dict(
        where='fx 写 {"type": "dimbox", "boxes": [{"at": 秒, "box": [x, y, w, h], "shape": rect / circle}]}，at 相对特效开始；'
              '不写 boxes 就先框脸、一半时移到胸口', style=['web'],
        auto='每个框至少停 0.6 秒；移动 0.4 秒缓入缓出，每移一次滴答一声',
        variants={'walk': (['web'], '压暗聚光框游走：整屏压到四成亮，白色虚线框里保持原亮度，在脸、胸口之间移动变形')},
        demo=lambda A, v: _fxd(A, 0.3, 3.5, 'dimbox'),
    ),
    'crt_scanline': dict(
        where='fx 写 {"type": "crt", "variant": emphasis / section}；emphasis 只铺说到节目名、栏目名那 1.5 秒，section 铺段落收尾的总结句',
        style=['web'], auto='前后 0.1 秒渐入渐出，起头一声故障音；section 加桶形弯曲、强暗角和轻推近；全片别一直开，会发灰累眼',
        variants={'emphasis': (['web'], '一句话强调：细横向扫描线加暗角'), 'section': (['web'], '段落质感：扫描线、强暗角、桶形弯曲，配推近')},
        demo=lambda A, v: _fxd(A, 0.5, 3.4, 'crt', v),
    ),
    'halftone_texture': dict(
        where='fx 写 {"type": "halftone", "variant": screenprint / bg_grain}；波普底写在版式里：抠像换底 {"mode": "matte", "bg": "popart:pink"}'
              '（或 popart:red），纸页底 {"mode": "bg", "bg": "popart", "variant": "pink"}', style=['premium', 'web'],
        auto='screenprint 扣掉人像，网点只在背景上；bg_grain 只叠在压暗的背景层（aside、hidden）上；红色波普底刺眼，别超过 2 秒',
        variants={'screenprint': (['premium', 'web'], '整体丝印叠加：细密网点略偏蓝，只在亮部和背景看得出来'),
                  'bg_grain': (['premium', 'web'], '暗背景颗粒：压暗的背景上一层网点，大片暗底不空不廉价'),
                  'popart': (['web'], '波普网点底：粉紫底上从大到小的网点，人抠出来站在上面')},
        demo=lambda A, v: {'screenprint': _fxd(A, 0.3, 3.5, 'halftone', 'screenprint'),
                           'bg_grain': {'layout': [{'t0': 0.2, 't1': 3.6, 'mode': 'aside'}],
                                        'titles': [{'t0': 0.4, 't1': 3.5, 'layout': 'quote', 'text': '先规划\\N再动手', 'sfx': False}],
                                        **_fxd(A, 0.3, 3.5, 'halftone', 'bg_grain')},
                           'popart': {'layout': [{'t0': 0.2, 't1': 3.6, 'mode': 'matte', 'bg': 'popart:pink', 'outline': 'solid_white'}]}}[v],
    ),
    'color_grade_shift': dict(
        where='fx 写 {"type": "grade", "variant": desat_cool / band}；band 可写 "colors" 三个色块颜色', style=['premium', 'web'],
        auto='desat_cool 整段换影调（降饱和、偏冷灰、暗角两成），人和红字反而跳出来；band 只在讲「颜色」「变化」时偶尔用一次，每条色块扫过一声',
        variants={'desat_cool': (['premium', 'web'], '去色冷灰：整段降饱和、偏冷、压暗部'),
                  'band': (['web'], '黑白加色块扫：先变黑白，红绿橙横色块依次从脸部扫过，色块里恢复颜色')},
        demo=lambda A, v: _fxd(A, 0.3, 3.5, 'grade', v),
    ),
    'letterbox_bars': dict(
        where='fx 写 {"type": "letterbox", "text": 下黑边里滚动的小字（可不写）}，持续 1~3 秒；常配一行引用大字', style=['premium'],
        auto='上下各 0.11 画面高，进出各 0.2 秒；常驻字幕在 0.8 画面高，不会被黑边压住',
        variants={'bars': (['premium', 'web'], '宽银幕黑边：上下黑边滑进来变成电影比例')},
        demo=lambda A, v: {**_fxd(A, 0.3, 3.4, 'letterbox', text='EP.06  Claude Code 常用命令'),
                           'titles': [{'t0': 0.6, 't1': 3.3, 'layout': 'quote', 'text': '慢就是快', 'sfx': False}]},
    ),
    'window_shape_morph': dict(
        where='layout 写 {"mode": "morph", "at": [每次变形的秒数], "steps": [[宽, 高, 圆角, 中心高], ...]}；at 对准口播的节拍，不写就均匀排开',
        style=['web'], auto='默认五步：小圆、大圆、圆角方、竖长圆角、接近满屏；背后是同画面放大 1.2 倍虚化压暗，每变一次啵一声；没有节拍感的平稳口播别用',
        variants={'steps': (['web'], '窗口按节拍变形：人在小窗里，窗口形状一下一下变大变形')},
        demo=lambda A, v: {'layout': [{'t0': 0.2, 't1': 3.6, 'mode': 'morph', 'at': [0.0, 0.6, 1.2, 1.8, 2.5]}]},
    ),
    'face_effect_emotion': dict(
        where='fx 写 {"type": "face", "names": [剪映人物特效名，常叠两个]}，0.6~3 秒；可用：' + '、'.join(FACE_FX), style=['variety', 'web'],
        auto='剪映草稿里放剪映真的人物特效（剪映里没有的名字那几秒铺成片画面）；成片里用抠像放大头、头边贴 3D 表情和手写问号近似；中刀、打击自带整屏震一下',
        variants={k: (['variety', 'web'], '、'.join(n)) for k, n in _FACE_DEMO.items()},
        demo=lambda A, v: _fxd(A, 0.5, 3.4, 'face', names=_FACE_DEMO[v]),
    ),
    'rgb_glitch': dict(
        where='transitions 写 {"t", "type": "glitch"} 整屏故障（综艺感章节页会自动轮到）；文字故障换字 titles 写 {"layout": "glitchswap", "text", "text2", "swap_at"}',
        style=['web'], auto='整屏 0.3 秒红青错开加横切片跳动，配故障音；高级感片子只在片头用一次',
        variants={'frame': (['web'], TRANSITIONS['glitch']['use'].split('（')[0]),
                  'text_swap': (['web'], '文字故障换字：一句大字被红青错位撕开，故障中间换成下一句')},
        demo=lambda A, v: _cut(A, 'glitch') if v == 'frame' else
        {'titles': [{'t0': 0.3, 't1': 3.5, 'layout': 'glitchswap', 'text': '学会了吗', 'text2': '收藏起来吧', 'swap_at': 1.4,
                     'sound': [{'type': 'glitch', 'at': 1.3}]}]},
    ),
    'whip_blur': dict(
        where='transitions 写 {"t", "type": "whip", "dir": left / right / up / down} 整屏甩切；只甩底在字不动底在换的 bgs 里写 "whip"',
        style=['web', 'premium'], auto='网感档章节页自动轮到；配唰一声；只甩底常和字不动底在换一起用',
        variants={'whip': (['web', 'premium'], '整屏甩切：往一边甩走，下一段同方向甩进来'),
                  'bg_only': (['web', 'premium'], '只甩底：底层横向拉丝扫过，上面的字不动')},
        demo=lambda A, v: _cut(A, 'whip') if v == 'whip' else
        {'titles': [{'t0': 0.3, 't1': 3.5, 'layout': 'persist', 'text': '一个命令', 'bgs': ['aroll', 'whip', 'aroll'], 'seg': [1.1, 0.45],
                     'sound': [{'type': 'whoosh', 'at': 1.1}]}]},
    ),
    'iris_circle': dict(
        where='transitions 写 {"t", "type": "iris", "variant": swap / open, "x", "y": 圆心}；圆心要对准脸', style=['web', 'premium'],
        auto='网感档章节页自动轮到；swap 0.3 秒收成中下部 0.6 宽的圆，圆里换段，0.4 秒放大；open 从黑底小圆张开到圆头像再打开',
        variants={'swap': (['web', 'premium'], '收圆换镜：画面收成一个圆，圆里换成下一段再放大到满屏'),
                  'open': (['web', 'premium'], '小圆打开：黑底上人从很小的圆张开成圆头像，再打开到满屏')},
        demo=lambda A, v: _cut(A, 'iris', v, at=1.6 if v == 'open' else 1.8),
    ),
    'light_leak': dict(
        where='transitions 写 {"t", "type": "light_leak", "variant": flash / zoom_reveal}', style=['premium', 'web'],
        auto='高级感两档章节页都会轮到；30 秒内最多一次；配一声穿梭声',
        variants={'flash': (['premium', 'web'], '光斑扫过：橙黄暖光从左边扫过，几乎铺满时换段'),
                  'zoom_reveal': (['premium', 'web'], '漏光后放大出成片：光退去时下一段从六成大小放大回满屏')},
        demo=lambda A, v: _cut(A, 'light_leak', v),
    ),
    'occlusion_wipe': dict(
        where='transitions 写 {"t", "type": "occlude", "src": 主题物图（透明底最好）}，或 "emoji": 3D 表情英文名；只在章节点用',
        style=['premium', 'web'], auto='主题物放大到 1.7 倍画面宽，纵向强模糊从下往上冲过 0.4 秒，切点前后各一帧整屏盖满；配大段唰声',
        variants={'object': (['premium', 'web'], '主题物遮挡扫屏：火箭、产品、logo 从下往上冲过，盖满那一帧换段')},
        demo=lambda A, v: _cut(A, 'occlude', emoji='Rocket'),
    ),
    'panel_carrier_transition': dict(
        where='白雾章节页 fog 上写，后一页 window 写 "enter": "cover"（前一页底部面板放大盖屏）；"shapes": ["2", "?"] 加 "shape_at"（镂空换形）；'
              '"exit": "door"（最后 0.5 秒像门一样转开）', style=['premium'],
        auto='只在要点切换处用，和白雾镂空序号配套；开门配开门声，换形配唰声；人一直在雾上面，两段人物位置要接近',
        variants={'zoom_cover': (['premium', 'web'], '放大盖屏：底部白雾面板往上急速放大盖满，变成整屏白雾数字页'),
                  'shape_rotate': (['premium', 'web'], '镂空换形旋转：白雾里的镂空数字逆时针转一下换成问号'),
                  'door_open': (['premium', 'web'], '透视开门：整屏白雾带着镂空数字以左边为轴转开，露出下一段')},
        demo=lambda A, v: {'auto_transitions': False, 'titles': {
            'zoom_cover': [{**_FOG, 't0': 0.2, 't1': 1.6, 'variant': 'panel', 'number': 1, 'text': '先存档'},
                           {**_FOG, 't0': 1.6, 't1': 3.6, 'variant': 'window', 'enter': 'cover'}],
            'shape_rotate': [{**_FOG, 't0': 0.2, 't1': 3.6, 'variant': 'window', 'number': 3, 'shapes': ['3', '?'], 'shape_at': 1.5}],
            'door_open': [{**_FOG, 't0': 0.2, 't1': 2.4, 'variant': 'window', 'exit': 'door'}]}[v]},
    ),
    'paper_tear_reveal': dict(
        where='transitions 写 {"t", "type": "tear", "variant": diagonal / split, "angle": 撕边角度}', style=['web', 'variety'],
        auto='网感档章节页自动轮到；切点前最后一帧定格被撕掉，白纸芯撕边程序画；配揉纸声；效果转场 30 秒内最多一个。揉纸展开要素材，没做',
        variants={'diagonal': (['web', 'variety'], '斜向撕开：一条带白纸芯的不规则撕边斜着划过，露出下一段'),
                  'split': (['web', 'variety'], '中间撕开：从中间撕开，上下两半往外退')},
        demo=lambda A, v: _cut(A, 'tear', v),
    ),
    'meme_clip_insert': dict(
        where='顶层 inserts 写 [{"t": 插入点, "src": 用户给的片段, "in": 从片段第几秒起, "dur": 1~1.5}]；插在抖完包袱之后的停顿处',
        style=['web', 'variety'], auto='成片渲完后在 t 秒硬切插入：横版居中黑底，不带字幕和头像，用片段自己的声音（统一响度），配乐在这一段留空；'
                                       '片子变长 dur 秒；剪映草稿里不插，要在剪映里手动放；只用用户自己提供的片段（版权）',
        variants={'insert': (['web', 'variety'], '插入影视梗片段：硬切进一段 1.2 秒左右的梗，再硬切回口播')},
        demo=lambda A, v: {'inserts': [{'t': 1.6, 'src': A['meme'], 'dur': 1.2}]},
    ),
})


# ---------------------------------------------------------------- 第 9 批：大字排版与字幕（bigtype.py 逐帧画，mixline 走 ASS）
from bigtype import CIRCLE_VARIANTS, CORNER_VARIANTS as BT_CORNERS, GHOST_VARIANTS, GIANT_VARIANTS, TYPEPANEL_VARIANTS   # noqa: E402
from typeset import MIXLINE_VARIANTS   # noqa: E402


def _cjk(s, n):
    return _short(s, n) and all(not c.isascii() for c in s)


IMPL.update({
    'giant_word_page': dict(
        beats={'quote': 1, 'emotion': 2, 'concept': 2}, style=['premium', 'web'], intensity=3, max_n=2,
        variants={'metal': ['premium', 'web'], 'red_bleed': ['premium', 'web'], 'collage': ['premium']},
        variant_ok={'red_bleed': lambda b: _short(b.get('text'), 2), 'collage': lambda b: _short(b.get('text'), 2)},
        ok=lambda b: _cjk(b.get('text'), 4),
        build=lambda b, v, at: {'layout': 'giant', 'variant': v, 'text': b['text'], 'en': b.get('en'), 'trad': b.get('trad'),
                                **({'cover': True} if v != 'metal' else {})},
        sound=lambda st, b, at: [{'type': 'swell', 'at': 0.0}] if st.get('variant') == 'metal' else [{'type': 'thump', 'at': 0.05}],
        demo={'beat': 'quote', 'text': '稳', 'en': 'Steady'},
        demo_v={'collage': {'text': '简', 'trad': '簡', 'en': 'Less is more'}, 'red_bleed': {'text': '慢'}},
    ),
    'ghost_bg_word': dict(
        beats={'topic': 1, 'question': 1, 'quote': 2}, style=['premium', 'web'], intensity=2,
        variants={'hollow': ['premium', 'web'], 'edge': ['premium', 'web'], 'emboss': ['premium', 'web'], 'grunge': ['premium', 'web']},
        variant_ok={'hollow': lambda b: bool(b.get('en')), 'edge': lambda b: bool(b.get('en')),
                    'grunge': lambda b: b.get('beat') == 'question' or bool(b.get('left'))},
        ok=lambda b: _short(b.get('text'), 10),
        build=lambda b, v, at: {'layout': 'ghostword', 'variant': v, 'text': b['text'], 'lead': b.get('lead'), 'en': b.get('en'),
                                'ghost': b.get('ghost'), 'left': b.get('left'), 'right': b.get('right'),
                                **({'cover': True} if v in ('emboss', 'grunge') else {})},
        sound=lambda st, b, at: [{'type': 'swell', 'at': 0.0}],
        demo={'beat': 'topic', 'text': '先想清楚', 'lead': '动手之前', 'en': 'Think', 'ghost': '想'},
        demo_v={'grunge': {'beat': 'question', 'text': '你真的需要吗？', 'lead': '下单之前问自己', 'left': '需要', 'right': '想要'}},
    ),
    'boxed_char_title': dict(
        beats={'topic': 1, 'quote': 2}, style=['premium'], intensity=2,
        ok=lambda b: _cjk(b.get('text'), 4) and len(b['text']) >= 2,
        build=lambda b, v, at: {'layout': 'boxed', 'text': b['text'], 'tag': b.get('tag') or b.get('en'), 'sub': b.get('sub'),
                                'behind': b.get('behind'), 'y': b.get('y')},
        sound=lambda st, b, at: [{'type': 'thump', 'at': 0.12}],
        demo={'beat': 'topic', 'text': '上下文', 'tag': 'Context', 'sub': 'AI 一次能记住的全部内容'},
    ),
    'mix_size_line': dict(
        beats={'emphasis': 1, 'number': 2, 'quote': 3}, style=['premium', 'web'], intensity=1,
        variants={'static': ['premium', 'web'], 'focus': ['premium', 'web']},
        ok=lambda b: bool(b.get('key')) and b['key'] in b.get('text', '') and len(b['text']) <= 16,
        build=lambda b, v, at: {'layout': 'mixline', 'variant': v, 'text': b['text'], 'key': b['key'],
                                **({'focus_at': at(b['key']) or 0.8} if v == 'focus' else {})},
        sound=lambda st, b, at: [{'type': 'pop', 'at': at(b['key']) or 0.8}] if st.get('variant') == 'focus' else None,
        demo={'beat': 'emphasis', 'text': '3秒 决定观众走不走', 'key': '3秒'},
    ),
    'corner_chars_frame': dict(
        beats={'cta': 1, 'topic': 2, 'hook': 2, 'quote': 3}, style=['web'], intensity=2,
        variants={'four': ['web'], 'shrink': ['web'], 'flank': ['web']},
        variant_ok={'four': lambda b: len(b['text']) == 4, 'shrink': lambda b: len(b['text']) == 4, 'flank': lambda b: len(b['text']) == 2},
        ok=lambda b: _cjk(b.get('text'), 4) and len(b['text']) in (2, 4),
        build=lambda b, v, at: {'layout': 'corners', 'variant': v, 'text': b['text'], **({'cover': True} if v == 'shrink' else {})},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0.0}] + ([{'type': 'pop', 'at': 0.15 if st.get('variant') == 'flank' else 0.3}]),
        demo={'beat': 'cta', 'text': '一键三连'},
        demo_v={'flank': {'text': '去练'}},
    ),
    'circle_pip_text': dict(
        beats={'hook': 1, 'topic': 2, 'list': 2, 'cta': 2}, style=['web'], intensity=3, max_n=2,
        variants={'arc': ['web'], 'tangent': ['web'], 'sandwich': ['web']},
        variant_ok={'tangent': lambda b: len(b.get('items') or []) == 3 and all(_short(x, 4) for x in b['items']),
                    'sandwich': lambda b: _short(b.get('text2'), 8)},
        ok=lambda b: _short(b.get('text'), 6) or len(b.get('items') or []) == 3,
        build=lambda b, v, at: {'layout': 'circletext', 'variant': v, 'text': b.get('text'), 'text2': b.get('text2'), 'hl': b.get('hl'),
                                'items': b.get('items'), 'item_at': [at(x) for x in b['items']] if v == 'tangent' else None},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.0}] + [{'type': 'pop', 'at': 0.45 + 0.4 * j} for j in range(len(b.get('items') or [])
                                                                                                    if st.get('variant') == 'tangent' else 1)],
        demo={'beat': 'hook', 'text': '剪辑技巧', 'text2': '新手必看', 'hl': ['技巧'], 'items': ['快', '准', '稳']},
    ),
    'split_pip_word_swap': dict(
        beats={'list': 1, 'quote': 3}, style=['web', 'premium'], intensity=3, max_n=2,
        ok=lambda b: bool(b.get('src')) and 2 <= len(b.get('items') or []) <= 5 and all(_short(x, 4) for x in b['items']),
        build=lambda b, v, at: {'layout': 'splitswap', 'items': b['items'], 'item_at': [at(x) for x in b['items']], 'src': b['src'],
                                'src_in': b.get('src_in', 0), 'crop': b.get('crop')},
        sound=lambda st, b, at: [{'type': 'tap', 'at': a if a is not None else 0.25 + 0.8 * j} for j, a in enumerate([at(x) for x in b['items']])],
        demo={'beat': 'list', 'items': ['看', '想', '做']},
        demo_v={None: {'src': '@rec'}},
    ),
    'typewriter_panel': dict(
        beats={'evidence': 1, 'story': 1, 'steps': 2, 'quote': 3}, style=['web', 'premium'], intensity=2,
        variants={'accumulate': ['web', 'premium'], 'top_card': ['web']},
        ok=lambda b: len(b.get('lines') or []) >= 2 or len(b.get('text') or '') >= 16,
        build=lambda b, v, at: {'layout': 'typepanel', 'variant': v, 'text': b.get('text'), 'lines': b.get('lines'),
                                'line_at': [at(x) for x in b['lines']] if b.get('lines') else None, **({'cover': True} if v == 'top_card' else {})},
        sound=lambda st, b, at: [{'type': 'typing', 'at': 0.3, 'dur': min(6.0, sum(len(x) for x in (b.get('lines') or [b.get('text', '')])) / 7)}],
        demo={'beat': 'evidence', 'lines': ['第一步：需求写成文档', '第二步：拆成小任务', '第三步：做完一步提交一次', '第四步：跑测试再继续',
                                             '第五步：每天收尾写交接', '第六步：卡住就换个会话', '第七步：别一次改太多']},
        demo_v={'top_card': {'lines': None, 'text': '好的口播剪辑不是把特效堆满，而是让观众在每一秒都知道你在讲什么'}},
    ),
    'chapter_sentence_card_top': dict(
        beats={'chapter': 1}, style=['web', 'variety'], intensity=3, same_look=True,
        ok=lambda b: _short(b.get('sentence') or b.get('text'), 25),
        build=lambda b, v, at: {'layout': 'topcard', 'number': b.get('number'), 'text': b.get('sentence') or b['text']},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0.1}, {'type': 'typing', 'at': 0.25, 'dur': min(2.0, len(b.get('sentence') or b['text']) * 0.08)}],
        demo={'beat': 'chapter', 'number': '02', 'text': '上下文满了怎么办'},
    ),
    'chapter_vertical_flank': dict(
        beats={'chapter': 1}, style=['premium'], intensity=3, same_look=True,
        ok=lambda b: _cjk((b.get('text') or '').replace(' ', ''), 8) and len(b['text'].replace(' ', '')) >= 2,
        build=lambda b, v, at: {'layout': 'vflank', 'number': b.get('number'), 'text': b['text'], 'en': b.get('en'), 'subject': b.get('subject')},
        sound=lambda st, b, at: [{'type': 'swell', 'at': 0.0}],
        demo={'beat': 'chapter', 'number': '03', 'text': '先规划再动手', 'en': 'Plan first'},
    ),
})
VNAMES.update({**{k: v.split('：')[0] for k, v in GIANT_VARIANTS.items()}, **{k: v.split('：')[0] for k, v in GHOST_VARIANTS.items()},
               **{k: v.split('：')[0] for k, v in BT_CORNERS.items()}, **{k: v.split('：')[0] for k, v in CIRCLE_VARIANTS.items()},
               **{k: v.split('：')[0] for k, v in TYPEPANEL_VARIANTS.items()}, **{k: v.split('：')[0] for k, v in MIXLINE_VARIANTS.items()}})
CHAPTER_TECH.update({'topcard': 'chapter_sentence_card_top', 'vflank': 'chapter_vertical_flank'})
GLOBAL.update({
    'sub_box': ('sub_look', {'bar': '不透明黑条访谈字幕：任何背景上都能读'}),
    'sub_outline': ('sub_look', {'outline': '白字黑边（综艺感默认）', 'chest': '胸口深蓝圆体白边', 'huazi': '整句蓝边黄字垫黑底'}),
})
FIELDS.update({
    'sub_phrase_per_cut': dict(
        where='顶层 "phrase_subs": [{"t0", "t1", "cut": true}]，这段里的跟读字幕按逐字时间拆成 2~6 字一个的短语', style=['web', 'premium'],
        auto='短语按分词断、不拆词，标点处必断、停顿长的地方优先断；起止吸附到 0.2 秒内的素材、版式、粗剪刀口；'
             'cut 为 true 时每个短语换一档景别（100% / 118% / 132% / 110% 硬切），一个机位也像在快剪',
        variants={'cut': (['web', 'premium'], '一词一镜：每个短语换一档景别，字幕和镜头同一帧切'),
                  'plain': (['web', 'premium'], '只拆短语不换景别：配真的快剪素材时用')},
        demo=lambda A, v: {'_lines': A['lines'], 'auto_zoom': False, 'phrase_subs': [{'t0': 0, 't1': 3.6, 'cut': v == 'cut'}]},
    ),
})


# ---------------------------------------------------------------- 第 10 批：开场与结构（structure.py）
from structure import ASK_VARIANTS, COLLAGE_VARIANTS, MONTAGE_VARIANTS, POINT_VARIANTS, POSTER_VARIANTS, TEXTFIRST_VARIANTS   # noqa: E402

_POOL = ['@shot', '@photo', '@rec', '@rec2']   # 样本册素材池，preview_library 换成真路径

IMPL.update({
    'montage_flash_open': dict(
        beats={'hook': 1, 'topic': 4}, style=['web'], intensity=3, max_n=1,
        variants={'macro': ['web'], 'chaos': ['web']},
        ok=lambda b: len(b.get('srcs') or []) >= 3,
        build=lambda b, v, at: {'layout': 'montage', 'variant': v, 'srcs': b['srcs'], 'text': b.get('text'), 'cover': True},
        sound=lambda st, b, at: [{'type': 'glitch', 'at': 0.0}] if st.get('variant') == 'chaos' else [{'type': 'whoosh', 'at': 0.0}, {'type': 'thump', 'at': 2.0}],
        demo={'beat': 'hook', 'srcs': _POOL, 'text': '剪辑三板斧'},
    ),
    'collage_cards_title': dict(
        beats={'evidence': 1, 'hook': 2, 'topic': 2, 'list': 3}, style=['web', 'premium'], intensity=3, max_n=2,
        variants={'fan': ['web', 'premium'], 'scatter': ['web'], 'wall': ['web'], 'paper': ['web', 'premium']},
        ok=lambda b: len(b.get('srcs') or []) >= 2,
        build=lambda b, v, at: {'layout': 'collage', 'variant': v, 'srcs': b['srcs'], 'text': b.get('text'), 'text2': b.get('text2'),
                                'big': b.get('big'), 'numbers': b.get('numbers'), **({'cover': True} if v != 'scatter' else {})},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.1}] + [{'type': 'pop', 'at': 0.2 + 0.2 * j} for j in range(3)],
        demo={'beat': 'evidence', 'srcs': _POOL, 'text': '这期讲 7 个场景', 'text2': '每个都能直接用', 'big': '七种', 'numbers': ['103.6W', '2.4W']},
    ),
    'opening_text_first': dict(
        beats={'hook': 1}, style=['web'], intensity=3, max_n=1,
        variants={'stack': ['web'], 'meme': ['web'], 'warning': ['web']},
        variant_ok={'meme': lambda b: bool(b.get('src'))},
        ok=lambda b: len(b.get('lines') or []) >= 2,
        build=lambda b, v, at: {'layout': 'textfirst', 'variant': v, 'lines': b['lines'], 'hl': b.get('hl'), 'src': b.get('src'),
                                'title': b.get('title'), 'line_at': [at(x) for x in b['lines']], 'cover': True},
        sound=lambda st, b, at: [{'type': 'typing', 'at': 0.1, 'dur': 1.2}, {'type': 'pop', 'at': 2.6}],
        demo={'beat': 'hook', 'lines': ['剪了三个月口播', '播放量还是两位数', '问题不在内容', '在包装'], 'hl': ['包装', '两位数'],
              'title': '警告'},
        demo_v={'meme': {'src': '@photo', 'lines': ['我想要高级感', '但不想学剪辑']}},
    ),
    'opening_question_frame': dict(
        beats={'question': 1, 'hook': 2}, style=['web'], intensity=3, max_n=1,
        ok=lambda b: _short(b.get('text'), 8),
        build=lambda b, v, at: {'layout': 'qframe', 'text': b['text'], 'cover': True},
        sound=lambda st, b, at: [{'type': 'ding', 'at': 0.0}, {'type': 'pop', 'at': 0.3}],
        demo={'beat': 'question', 'text': '留不住人？'},
    ),
    'poster_title_page': dict(
        beats={'topic': 2, 'hook': 2, 'concept': 3}, style=['premium', 'web'], intensity=3, max_n=2,
        variants={'cinema': ['premium', 'web'], 'film': ['premium', 'web'], 'grid': ['premium', 'web'], 'popart': ['web'],
                  'magazine': ['premium', 'web']},
        ok=lambda b: _short(b.get('text'), 6),
        build=lambda b, v, at: {'layout': 'poster', 'variant': v, 'text': b['text'], 'en': b.get('en'), 'sub': b.get('sub'), 'issue': b.get('issue'),
                                'lines': b.get('lines'), 'hl': b.get('hl'), 'badge': b.get('badge'), 'cover': True},
        sound=lambda st, b, at: [{'type': 'shimmer', 'at': 0.1}],
        demo={'beat': 'topic', 'text': '高级感', 'en': 'Editing Lab', 'sub': '口播剪辑', 'issue': '第三期', 'lines': ['口播剪辑', '第三期：高级感'],
              'hl': ['高级感'], 'badge': 'NEW'},
    ),
    'engagement_ask_page': dict(
        beats={'cta': 1, 'transition_talk': 3}, style=['premium', 'web'], intensity=3, max_n=1,
        variants={'flank': ['premium', 'web'], 'lines': ['premium', 'web']},
        variant_ok={'flank': lambda b: _short(b.get('left'), 2) and _short(b.get('right'), 2)},
        ok=lambda b: (_short(b.get('left'), 2) and _short(b.get('right'), 2)) or bool(b.get('lines')),
        build=lambda b, v, at: {'layout': 'askpage', 'variant': v, 'left': b.get('left'), 'right': b.get('right'), 'left_en': b.get('left_en'),
                                'right_en': b.get('right_en'), 'arc': b.get('arc'), 'lines': b.get('lines'), 'cover': True},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0.05}, {'type': 'ding', 'at': 0.5}],
        demo={'beat': 'cta', 'left': '上点', 'right': '干货', 'left_en': 'like', 'right_en': 'dry goods', 'arc': '先赞后看~',
              'lines': ['视频很长', '干货很多', '记得收藏']},
    ),
    'chapter_avatar_gesture': dict(
        beats={'chapter': 1}, style=['web'], intensity=3, same_look=True,
        ok=lambda b: str(b.get('number', '')).lstrip('0').isdigit(),
        build=lambda b, v, at: {'layout': 'gesture', 'number': b['number'], 'text': b.get('text'), 'unit': b.get('unit', '招')},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0.05}, {'type': 'ding', 'at': 0.25}],
        demo={'beat': 'chapter', 'number': '2', 'text': '上下文满了'},
    ),
    'chapter_cutout_numeral': dict(
        beats={'chapter': 1}, style=['web', 'variety'], intensity=3, same_look=True,
        ok=lambda b: str(b.get('number', '')).lstrip('0').isdigit() and _short(b.get('text'), 10),
        build=lambda b, v, at: {'layout': 'cutnum', 'number': b['number'], 'text': b['text']},
        sound=lambda st, b, at: [{'type': 'thump', 'at': 0.05}, {'type': 'whoosh', 'at': 0.8}],
        demo={'beat': 'chapter', 'number': '3', 'text': '先规划再动手'},
    ),
    'ending_echo_keyword': dict(
        beats={'cta': 2, 'quote': 3}, style=['premium'], intensity=2, max_n=1,
        ok=lambda b: _short(b.get('echo') or b.get('text'), 6),
        build=lambda b, v, at: {'layout': 'inkecho', 'text': b.get('echo') or b['text'], 'color': b.get('color'), 'y': b.get('echo_y')},
        sound=lambda st, b, at: [{'type': 'swell', 'at': 0.0}],
        demo={'beat': 'cta', 'text': '新手崩溃', 'color': '#F5D547'},
    ),
    'cta_action_row': dict(
        beats={'cta': 1}, style=['web', 'premium'], intensity=2, max_n=1,
        ok=lambda b: True,
        build=lambda b, v, at: {'layout': 'actionrow', 'items': b.get('items') if len(b.get('items') or []) == 3 else None, 'name': b.get('name')},
        sound=lambda st, b, at: [{'type': 'ding', 'at': 0.1 + 0.3 * j} for j in range(3)],
        demo={'beat': 'cta', 'name': '@口播剪辑课'},
    ),
    'signature_outro': dict(
        beats={'cta': 1, 'quote': 4}, style=['web'], intensity=3, max_n=1,
        ok=lambda b: _short(b.get('text'), 6) and _short(b.get('text2'), 2) and len(b['text2']) == 2,
        build=lambda b, v, at: {'layout': 'slogan', 'text': b['text'], 'text2': b['text2'], 'at2': at(b['text2'][0]) or 0.8},
        sound=lambda st, b, at: [{'type': 'glitch', 'at': 0.25}, {'type': 'thump', 'at': at(b['text2'][0]) or 0.8}],
        demo={'beat': 'cta', 'text': '学会了', 'text2': '去练'},
    ),
})
VNAMES.update({k: v.split('：')[0] for D in (MONTAGE_VARIANTS, COLLAGE_VARIANTS, TEXTFIRST_VARIANTS, POSTER_VARIANTS, ASK_VARIANTS)
               for k, v in D.items() if k not in VNAMES})
CHAPTER_TECH.update({'gesture': 'chapter_avatar_gesture', 'cutnum': 'chapter_cutout_numeral'})
FIELDS.update({
    'cover_first_frame': dict(
        where='顶层 "cover": {"text", "text2", "frame_at": 抠哪一秒的人, "bg", "bg2", "dur": 0.15}；标题要和第一句口播呼应', style=['web'],
        auto='片头 0.15 秒（3~6 帧）铺一张封面：抠像人带白贴纸描边，上下两行倾斜彩色标题，随后硬切进第一句；有封面时不再自动加开场冲击',
        variants={'cover': (['web'], '首帧封面图：平台自动截的第一帧就是包装好的封面（样本册放慢到 0.8 秒好看清）')},
        demo=lambda A, v: {'cover': {'text': '剪辑三板斧', 'text2': '新手直接抄', 'frame_at': 0.5, 'dur': 0.8}},
    ),
    'point_index_marker': dict(
        where='顶层 "points": {"variant": glow / film / brush, "items": [{"t0", "t1", "n", "text"}]}；不写 items 就按章节页自动排：'
              '每个章节页结束起到下一章开始，编号是章节号、旁边是章节名', style=['web', 'premium'],
        auto='换一点的 0.4 秒做光扫、故障闪或斜切弹入，之后静止常驻；压在常驻字幕下面',
        variants={k: (['web', 'premium'] if k != 'film' else ['web'], d) for k, d in POINT_VARIANTS.items()},
        demo=lambda A, v: {'points': {'variant': v, 'items': [{'t0': 0.3, 't1': 1.9, 'n': '1', 'text': '找回会话'},
                                                              {'t0': 1.9, 't1': 3.6, 'n': '2', 'text': '上下文满了'}]}},
    ),
    'persistent_hud': dict(
        where='顶层 "hud": {"variant": "watermark", "text": 系列名, "y": 0.04} 或 {"variant": "progress", "y": 0.24, "mascot": Fluent Emoji 名}', style=['premium', 'web'],
        auto='水印整片不动、灰色低亮度；进度条从 0 走到 100%（按成片时长），前端小人跟着走；进度条默认放 24% 高，避开平台顶部按钮',
        variants={'watermark': (['premium', 'web'], '系列名水印：最上方一行灰色斜体系列名，整片不动'),
                  'progress': (['premium', 'web'], '进度条小人：上方一根黄色进度条随播放走完，前端一个小人跟着走')},
        demo=lambda A, v: {'hud': {'variant': v, 'text': 'vibe coding 从 0 到实战'}},
    ),
    'fast_cut_word_montage': dict(
        where='顶层 "montage_cuts": [{"t0", "t1", "srcs": [素材，或 {"src", "crop"} 同一段录屏裁不同地方当不同景别], "pip": true 或 {"pip": {x, y, d}}, "pos": 小窗位置, "subs": true, '
              '"broll": {"fit": "band", "crop": [...]}}]', style=['web', 'premium'],
        auto='这段话按逐字时间拆成短语（同一词一镜字幕），每个短语换一个素材铺满（素材轮着用，视频从不同位置截），头像小窗不动，'
             '字幕一个镜头一个短语；没有逐字时间就 0.75 秒一镜',
        variants={'montage': (['web', 'premium'], '一词一镜快剪：一句话拆成六到九个短语，每个短语换一个镜头')},
        demo=lambda A, v: {'_lines': A['lines'], 'montage_cuts': [{'t0': 0.2, 't1': 3.6, 'srcs': [A['shot'], A['photo'], A['rec'], A['rec2']]}]},
    ),
    'section_end_climax': dict(
        where='顶层 "section_ends": [{"t0", "t1": 快剪段, "srcs", "talk": [问题句起, 止], "silence": 1.2}]，接在下一个章节页前', style=['premium', 'web'],
        auto='t0~t1 按短语快剪（同一词一镜快剪）；talk 那句跳到 115% 一档；下一个章节页那一下配乐停 1.2 秒再进下一部分；'
             '配乐高潮段用 sections 的 climax 接在快剪下面',
        variants={'climax': (['premium', 'web'], '段落收尾推高收束：快剪推情绪，跳一档说出问题句，硬切章节页、配乐戛然而止')},
        demo=lambda A, v: {'_lines': A['lines'], 'section_ends': [{'t0': 0.2, 't1': 1.8, 'srcs': [A['shot'], A['photo'], A['rec']], 'talk': [1.8, 2.4]}],
                           'titles': [{'t0': 2.4, 't1': 3.6, 'layout': 'chapter', 'number': '03', 'text': '先规划再动手', 'en': 'Plan first'}]},
    ),
    'reaction_cutaway': dict(
        where='顶层 inserts 写 [{"t": 插入点, "src": 用户给的反应镜头, "in", "dur": 1~1.5, "text": "嘿嘿"}]；text 是叠在镜头上的荧光绿花字', style=['web', 'variety'],
        auto='同插入影视梗片段：横版居中黑底、不带字幕和头像、片子变长 dur 秒；一期最多两次；只用用户自己提供的镜头',
        variants={'host_cam': (['web', 'variety'], '博主另一机位：自己在别处鼓掌大笑 1 秒，加荧光绿「嘿嘿」'),
                  'meme_clip': (['web', 'variety'], '影视梗片段：一段 1.2 秒左右的梗，原片字幕留着')},
        demo=lambda A, v: {'inserts': [{'t': 1.6, 'src': A['meme'], 'dur': 1.2, **({'text': '嘿嘿'} if v == 'host_cam' else {})}]},
    ),
})


# ---------------------------------------------------------------- 第 11 批：信息卡片（infocard.py）
from infocard import AXIS_VARIANTS, COMMENT_VARIANTS, PERSON_VARIANTS, PHOTOSTACK_VARIANTS, RESLIST_VARIANTS, TYPEROW_VARIANTS, WIDGET_VARIANTS   # noqa: E402

IMPL.update({
    'ui_callout_card': dict(
        beats={'demo': 1, 'steps': 2}, style=['web'], intensity=2,
        ok=lambda b: bool(b.get('src')) and bool(b.get('mark')),
        build=lambda b, v, at: {'layout': 'callout', 'src': b['src'], 'crop': b.get('crop'), 'mark': b['mark'], 'label': b.get('label'),
                                'side': b.get('side')},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.0}, {'type': 'pop', 'at': 0.35}],
        demo={'beat': 'demo', 'src': '@shot', 'mark': [0.3, 0.3], 'label': '点这里切模型'},
    ),
    'ui_widget_mock': dict(
        beats={'concept': 2, 'demo': 2}, style=['web'], intensity=2,
        variants={'search': ['web'], 'sfx': ['web']},
        variant_ok={'search': lambda b: _short(b.get('key') or b.get('text'), 12), 'sfx': lambda b: bool(b.get('items'))},
        ok=lambda b: _short(b.get('key') or b.get('text'), 12) or bool(b.get('items')),
        build=lambda b, v, at: {'layout': 'widget', 'variant': v, 'text': b.get('key') or b.get('text'), 'title': b.get('title'),
                                'items': b.get('items'), 'item_at': [at(x if isinstance(x, str) else x.get('name')) for x in b['items']] if v == 'sfx' else None,
                                **({'cover': True} if v == 'search' else {})},
        sound=lambda st, b, at: ([{'type': 'typing', 'at': 0.35, 'dur': min(2.5, len(b.get('key') or b.get('text') or '') / 6)}]
                                 if st.get('variant') == 'search' else [{'type': 'pop', 'at': 0.1}]),
        demo={'beat': 'concept', 'key': '口播剪辑 网感', 'title': '去哪找灵感',
              'items': [{'name': '综艺 叮', 'author': '剪映音效', 'dur': '00:01'}, {'name': '嗖 转场', 'author': '音效库', 'dur': '00:02'}]},
    ),
    'flowchart_nodes': dict(
        beats={'steps': 1, 'concept': 3}, style=['premium'], intensity=2,
        ok=lambda b: _items_ok(b, 3, 5, 10),
        build=lambda b, v, at: {'layout': 'flow', 'items': b['items'], 'item_at': [at(x) for x in b['items']], 'title': b.get('title'), 'cover': True},
        sound=lambda st, b, at: [{'type': 'rising_ui', 'step': j, 'at': a if a is not None else 0.3 + 0.7 * j} for j, a in enumerate([at(x) for x in b['items']])],
        demo={'beat': 'steps', 'items': ['写需求', '拆任务', '跑测试', '提交'], 'title': '一次改动的流程'},
    ),
    'timeline_axis': dict(
        beats={'steps': 2, 'story': 1, 'concept': 3}, style=['premium', 'web'], intensity=2,
        variants={'two_point': ['premium', 'web'], 'events': ['premium', 'web'], 'year': ['premium', 'web'], 'wave': ['premium', 'web']},
        variant_ok={'two_point': lambda b: len(b.get('items') or []) == 2, 'events': lambda b: _items_ok(b, 2, 6, 6),
                    'year': lambda b: bool(b.get('target')), 'wave': lambda b: b.get('beat') == 'concept' or bool(b.get('wave'))},
        ok=lambda b: _items_ok(b, 2, 10, 6) or bool(b.get('target')),
        build=lambda b, v, at: {'layout': 'axis', 'variant': v, 'items': b.get('items'), 'title': b.get('title'), 'target': b.get('target'),
                                'item_at': [at(str(x)) for x in b['items']] if b.get('items') and v in ('two_point', 'events') else None,
                                **({'cover': True} if v == 'two_point' else {})},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.2}] if st.get('variant') == 'year' else [{'type': 'tick', 'at': 0.3}],
        demo={'beat': 'story', 'items': ['开头', '结尾'], 'title': '从第一帧到最后一帧', 'target': 2025},
        demo_v={'events': {'items': ['鼓点', '换镜', '花字', '音效']}, 'year': {'items': [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]}},
    ),
    'step_mosaic_wall': dict(
        beats={'steps': 1}, style=['premium'], intensity=3, max_n=1,
        ok=lambda b: _items_ok(b, 3, 8, 6),
        build=lambda b, v, at: {'layout': 'stepwall', 'items': b['items'], 'cover': True},
        sound=lambda st, b, at: [{'type': 'swell', 'at': 0.0}],
        demo={'beat': 'steps', 'items': ['表达先行', '提取文字', '找素材', '粗剪', '包装', '复盘']},
    ),
    'resource_list_page': dict(
        beats={'list': 2, 'evidence': 2}, style=['web', 'premium'], intensity=2,
        variants={'paper': ['web', 'premium'], 'poster': ['web', 'premium']},
        ok=lambda b: _items_ok(b, 3, 7, 14),
        build=lambda b, v, at: {'layout': 'reslist', 'variant': v, 'items': b['items'], 'item_at': [at(x) for x in b['items']], 'title': b.get('title'),
                                'category': b.get('category'), 'note': b.get('note_line'), **({'cover': True} if v == 'paper' else {})},
        sound=lambda st, b, at: [{'type': 'pop', 'at': a if a is not None else 0.3 + 0.35 * j} for j, a in enumerate([at(x) for x in b['items']][:4])],
        demo={'beat': 'list', 'items': ['思源黑体', '得意黑', '霞鹜文楷', '站酷快乐体', '抖音美好体'], 'title': '免费可商用字体', 'category': '中文无衬线',
              'note_line': '均可免费商用'},
    ),
    'type_card_row': dict(
        beats={'list': 2, 'compare': 2, 'concept': 3}, style=['premium', 'web'], intensity=3, max_n=2,
        variants={'screenshot': ['premium', 'web'], 'wireframe': ['premium', 'web']},
        variant_ok={'screenshot': lambda b: len(b.get('srcs') or []) >= 3, 'wireframe': lambda b: b.get('beat') == 'concept' or bool(b.get('kinds'))},
        ok=lambda b: len(b.get('srcs') or []) >= 3 or bool(b.get('kinds')),
        build=lambda b, v, at: {'layout': 'typerow', 'variant': v, 'srcs': b.get('srcs'), 'items': b.get('items'), 'pinyin': b.get('pinyin'),
                                'kinds': b.get('kinds'), 'focus': b.get('focus'), 'giant': b.get('giant'), 'note': b.get('note_line'),
                                'item_at': [at(x) for x in b['items']] if v == 'screenshot' and b.get('items') else None, 'cover': True},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.2}, {'type': 'pop', 'at': 0.95}],
        demo={'beat': 'list', 'srcs': _POOL, 'items': ['截图', '照片', '录屏', '素材'], 'pinyin': ['jie tu', 'zhao pian', 'lu ping', 'su cai'],
              'kinds': ['topbottom', 'corners', 'center', 'leftright', 'diagonal'], 'focus': 2, 'giant': '居中', 'note_line': '人在中间，字压上下'},
    ),
    'photo_card_stack': dict(
        beats={'list': 1}, style=['web'], intensity=2,
        variants={'tab': ['web'], 'tilted': ['web']},
        ok=lambda b: len(b.get('srcs') or []) == 3 and _items_ok(b, 3, 3, 6),
        build=lambda b, v, at: {'layout': 'photostack', 'variant': v, 'srcs': b['srcs'], 'items': b['items'], 'item_at': [at(x) for x in b['items']],
                                'cover': True},
        sound=lambda st, b, at: [{'type': 'pop', 'at': a if a is not None else 0.25 + 0.5 * j} for j, a in enumerate([at(x) for x in b['items']])],
        demo={'beat': 'list', 'srcs': ['@shot', '@photo', '@rec'], 'items': ['看截图', '拍照片', '录屏幕']},
    ),
    'comment_bubbles': dict(
        beats={'question': 1, 'negative': 2, 'evidence': 3, 'emotion': 3}, style=['web'], intensity=2, max_n=2,
        variants={'behind': ['web'], 'pileup': ['web']},
        variant_ok={'pileup': lambda b: b.get('beat') == 'negative' or len(b.get('items') or []) >= 6},
        ok=lambda b: 3 <= len(b.get('items') or []) <= 8,
        build=lambda b, v, at: {'layout': 'comments', 'variant': v, 'items': b['items']},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0.1 + (0.1 if st.get('variant') == 'pileup' else 0.15) * j} for j in range(3)],
        demo={'beat': 'question', 'items': [{'text': '剪辑软件用哪个？', 'likes': '1.2w'}, {'text': '字幕怎么做得这么好看', 'likes': '3896'},
                                            {'text': '音效从哪找的？', 'likes': '826'}, {'text': '求出教程！', 'likes': '2.4w'}]},
        demo_v={'pileup': {'items': ['真心不好用~', '太难用了!', '看不懂', '又卡了', '学不会', '放弃了', '劝退', '太复杂']}},
    ),
    'fan_window_cards': dict(
        beats={'list': 2, 'demo': 2, 'evidence': 3}, style=['premium'], intensity=2,
        ok=lambda b: len(b.get('srcs') or []) >= 2,
        build=lambda b, v, at: {'layout': 'fanwin', 'srcs': b['srcs']},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.35}],
        demo={'beat': 'demo', 'srcs': ['@rec', '@shot', '@photo']},
    ),
    'news_ticker_box': dict(
        beats={'evidence': 1}, style=['premium'], intensity=2,
        ok=lambda b: bool(b.get('src') or b.get('lines')) and _short(b.get('title'), 30),
        build=lambda b, v, at: {'layout': 'ticker', 'src': b.get('src'), 'crop': b.get('crop'), 'lines': b.get('lines'), 'title': b['title'], 'hl': b.get('hl')},
        sound=lambda st, b, at: [{'type': 'glitch', 'at': 0.0}],
        demo={'beat': 'evidence', 'title': '剪辑软件全面接入 AI 自动包装', 'hl': ['AI 自动包装'], 'src': '@shot'},
    ),
    'quote_typewriter_dim': dict(
        beats={'quote': 2, 'evidence': 2}, style=['premium'], intensity=2,
        ok=lambda b: 2 <= len(b.get('lines') or []) <= 5,
        build=lambda b, v, at: {'layout': 'quotetype', 'lines': b['lines'], 'by': b.get('by'), 'item_at': [at(x) for x in b['lines']], 'cover': True},
        sound=lambda st, b, at: [{'type': 'typing', 'at': 0.35, 'dur': min(5.0, 1.4 * len(b['lines']))}],
        demo={'beat': 'quote', 'lines': ['好的剪辑', '是让观众忘了剪辑的存在'], 'by': '沃尔特·默奇'},
    ),
    'paper_label_column': dict(
        beats={'list': 2, 'concept': 2}, style=['premium'], intensity=2,
        ok=lambda b: 2 <= len(b.get('items') or []) <= 4 and all(isinstance(x, dict) and x.get('src') for x in b['items']),
        build=lambda b, v, at: {'layout': 'labelcol', 'items': b['items'], 'item_at': [at(x['label']) for x in b['items']], 'cover': True},
        sound=lambda st, b, at: [{'type': 'tap', 'at': 0.2}],
        demo={'beat': 'list', 'items': [{'label': '补充背景', 'en': 'Background', 'src': '@shot'}, {'label': '解释潜台词', 'en': 'Subtext', 'src': '@photo'},
                                        {'label': '强化情绪', 'en': 'Emotion', 'src': '@rec'}]},
    ),
    'person_info_card': dict(
        beats={'story': 2, 'hook': 2, 'concept': 3, 'evidence': 3}, style=['web', 'variety'], intensity=1,
        variants={'profile': ['web', 'variety'], 'nameplate': ['web', 'variety']},
        variant_ok={'profile': lambda b: bool(b.get('fans')), 'nameplate': lambda b: bool(b.get('titles'))},
        ok=lambda b: _short(b.get('name'), 12),
        build=lambda b, v, at: {'layout': 'person', 'variant': v, 'name': b['name'], 'fans': b.get('fans'), 'avatar': b.get('avatar'),
                                'titles': b.get('titles')},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0.0}] if st.get('variant') == 'profile' else [{'type': 'shimmer', 'at': 0.0}],
        demo={'beat': 'story', 'name': '口播剪辑研究所', 'fans': '粉丝 128.6w', 'titles': ['十年剪辑师', '带过 300 个口播账号']},
    ),
    'product_cards_dim': dict(
        beats={'compare': 2, 'number': 3, 'list': 3}, style=['web'], intensity=2,
        ok=lambda b: 2 <= len(b.get('items') or []) <= 3 and all(isinstance(x, dict) and x.get('price') for x in b['items']),
        build=lambda b, v, at: {'layout': 'products', 'items': b['items'], 'item_at': [at(x.get('name')) for x in b['items']], 'cover': True},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0.3 + 0.5 * j} for j in range(len(b['items']))],
        demo={'beat': 'compare', 'items': [{'name': '基础版 · 月付', 'price': '¥29', 'icon': 'Package'}, {'name': '专业版 · 月付', 'price': '¥69', 'icon': 'Gem stone'},
                                           {'name': '团队版 · 年付', 'price': '¥599', 'icon': 'Trophy'}]},
    ),
    'doc_translation_bar': dict(
        beats={'evidence': 2, 'concept': 3}, style=['premium'], intensity=2,
        ok=lambda b: bool(b.get('src')) and bool(b.get('line')) and _short(b.get('text'), 40),
        build=lambda b, v, at: {'layout': 'translate', 'src': b['src'], 'crop': b.get('crop'), 'line': b['line'], 'text': b['text'], 'hl': b.get('hl'),
                                'cover': True},
        sound=lambda st, b, at: [{'type': 'tick', 'at': 0.3}, {'type': 'pop', 'at': 1.3}],
        demo={'beat': 'evidence', 'src': '@shot', 'line': [0.04, 0.42, 0.92, 0.08], 'text': '这里写的是：上下文满了会自动压缩', 'hl': ['自动压缩']},
    ),
})
VNAMES.update({k: v.split('：')[0] for D in (WIDGET_VARIANTS, AXIS_VARIANTS, RESLIST_VARIANTS, TYPEROW_VARIANTS, PHOTOSTACK_VARIANTS, COMMENT_VARIANTS,
                                             PERSON_VARIANTS) for k, v in D.items() if k not in VNAMES})
FIELDS.update({
    'privacy_mosaic': dict(
        where='broll 或带 src 的大字写 "mosaic": [[x, y, 宽, 高], ...]（相对素材画面的比例），"mosaic_block" 改颗粒大小（默认 24，按素材宽 1080 算）；'
              '框的位置先跑 detect_sensitive.py 找手机号、邮箱、人名、二维码，确认后抄进来', style=['premium', 'web'],
        auto='渲染前把素材打成马赛克副本（缓存在 ~/.cache/koubo/mosaic）：框里缩到 1/24 再按最近邻放大回去，认不出字；视频每帧同样位置打码',
        variants={'mosaic': (['premium', 'web'], '截图隐私打码：头像、名字、内容打成大颗粒马赛克，只留要佐证的那一条可读')},
        demo=lambda A, v: {'broll': [{'t0': 0.3, 't1': 3.5, 'src': A['shot'], 'fit': 'card', 'mosaic': [[0.0, 0.0, 1.0, 0.35], [0.0, 0.62, 1.0, 0.38]]}]},
    ),
})


# ---------------------------------------------------------------- 第 12 批：版式、背景与镜头（scene.py、backgrounds.py）
from scene import BANDS_VARIANTS, MATTEBAND_VARIANTS, PARALLAX_VARIANTS, WINDOW_VARIANTS   # noqa: E402

IMPL.update({
    'detail_split_windows': dict(
        beats={'demo': 1, 'emphasis': 3}, style=['web'], intensity=2,
        ok=lambda b: b.get('beat') == 'demo' or bool(b.get('hands')),
        build=lambda b, v, at: {'layout': 'splitwin', 'hands': b.get('hands')},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.0}],
        demo={'beat': 'demo'},
    ),
    'example_window': dict(
        beats={'demo': 1, 'evidence': 2, 'compare': 3}, style=['premium', 'web'], intensity=2,
        variants={'thin': ['premium', 'web'], 'glow': ['premium', 'web'], 'shadow': ['premium', 'web']},
        variant_ok={'glow': lambda b: _short(b.get('label'), 6), 'shadow': lambda b: _short(b.get('title'), 8)},
        ok=lambda b: bool(b.get('src')),
        build=lambda b, v, at: {'layout': 'window', 'variant': v, 'src': b['src'], 'src_in': b.get('src_in'), 'crop': b.get('crop'),
                                'label': b.get('label'), 'sub': b.get('sub'), 'title': b.get('title')},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.0}],
        demo={'beat': 'demo', 'src': '@rec', 'label': '第1段', 'sub': '开头三秒抓人', 'title': '案例拆解'},
        demo_v={'glow': {'src': '@rec2'}},
    ),
    'keyword_band_stack': dict(
        beats={'list': 1, 'compare': 3}, style=['web'], intensity=3, max_n=2,
        variants={'push': ['web'], 'drop': ['web'], 'gray': ['web']},
        ok=lambda b: _items_ok(b, 2, 3, 6) and len(b.get('srcs') or []) >= len(b['items']),
        build=lambda b, v, at: {'layout': 'bands', 'variant': v, 'items': b['items'], 'srcs': b['srcs'], 'item_at': [at(x) for x in b['items']]},
        sound=lambda st, b, at: [{'type': 'thump' if st.get('variant') != 'gray' else 'pop', 'at': a if a is not None else 0.15 + 0.6 * j}
                                 for j, a in enumerate([at(x) for x in b['items']])],
        demo={'beat': 'list', 'items': ['截图', '照片', '录屏'], 'srcs': ['@shot', '@photo', '@rec']},
    ),
    'matte_band_stack': dict(
        beats={'topic': 1, 'evidence': 3}, style=['web'], intensity=3, max_n=2,
        variants={'three': ['web'], 'tech': ['web']},
        variant_ok={'tech': lambda b: bool(b.get('tag'))},
        ok=lambda b: len(b.get('srcs') or []) >= 1 and _short(b.get('text'), 8),
        build=lambda b, v, at: {'layout': 'matteband', 'variant': v, 'srcs': b['srcs'], 'text': b['text'], 'sub': b.get('sub'), 'tag': b.get('tag')},
        sound=lambda st, b, at: [{'type': 'swell', 'at': 0.0}],
        demo={'beat': 'topic', 'srcs': ['@photo', '@rec', '@shot'], 'text': '信息差', 'tag': '效率工具'},
        demo_v={'tech': {'text': 'AI 剪辑'}},
    ),
    'paper_layer_collage': dict(
        beats={'demo': 3, 'concept': 3, 'chapter': 4, 'story': 3}, style=['web'], intensity=3, max_n=1,
        ok=lambda b: len(b.get('srcs') or []) >= 2,
        build=lambda b, v, at: {'layout': 'papercollage', 'srcs': b['srcs'], 'text': b.get('text'), 'stickers': b.get('stickers')},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0.1 + 0.12 * j} for j in range(3)] + [{'type': 'whoosh', 'at': 0.45}],
        demo={'beat': 'story', 'srcs': ['@shot', '@photo', '@rec'], 'text': '手作拼贴感'},
    ),
    'topic_figure_dim_cutout': dict(
        beats={'story': 1, 'concept': 3, 'hook': 3}, style=['premium'], intensity=2,
        ok=lambda b: bool(b.get('figure')) and _short(b.get('text'), 10),
        build=lambda b, v, at: {'layout': 'figure', 'src': b['figure'], 'text': b['text'], 'sub': b.get('sub')},
        sound=lambda st, b, at: [{'type': 'swell', 'at': 0.0}],
        demo={'beat': 'story', 'figure': None, 'text': '他是谁？', 'sub': '一个改变剪辑行业的人'},
    ),
    'mood_image_word': dict(
        beats={'emotion': 2, 'concept': 3, 'emphasis': 3}, style=['premium'], intensity=2,
        ok=lambda b: bool(b.get('mood')) and _short(b.get('word') or b.get('text'), 2),
        build=lambda b, v, at: {'layout': 'moodword', 'src': b['mood'], 'text': b.get('word') or b['text'], 'color': b.get('color')},
        sound=lambda st, b, at: [{'type': 'thump', 'at': 0.05}],
        demo={'beat': 'emotion', 'mood': '@photo', 'word': '静'},
    ),
    'layer_parallax_drift': dict(
        beats={'chapter': 3, 'number': 3, 'transition_talk': 2}, style=['premium'], intensity=2,
        variants={'ambient': ['premium'], 'shift': ['premium']},
        ok=lambda b: _short(b.get('text'), 8),
        build=lambda b, v, at: {'layout': 'parallax', 'variant': v, 'text': b['text'], 'lines': b.get('lines'), 'icon': b.get('icon'),
                                'bg_src': b.get('bg_src'), 'shift_at': [at(x) for x in b['shift_words']] if b.get('shift_words') else None},
        sound=lambda st, b, at: [{'type': 'swell', 'at': 0.0}],
        demo={'beat': 'transition_talk', 'text': '慢下来', 'lines': ['少即是多', '留白有力']},
        demo_v={'shift': {'shift_words': None}},
    ),
})
VNAMES.update({k: v.split('：')[0] for D in (WINDOW_VARIANTS, BANDS_VARIANTS, MATTEBAND_VARIANTS, PARALLAX_VARIANTS) for k, v in D.items() if k not in VNAMES})
FIELDS.update({
    'freeze_pause': dict(
        where='顶层 "freezes": [{"t0", "t1", "d": 头像大小, "y": 位置}]（1~1.9 秒，全片一次）', style=['premium', 'web'],
        auto='画面停在这一帧并压暗，头像从角落放大到画面中间、带浅金圆环，右侧画暂停图标；配快门声，这几秒配乐静音',
        variants={'freeze': (['premium', 'web'], '定格暂停：长段画中画中间说到有情绪的一句，画面定格、头像跳到正中')},
        demo=lambda A, v: {'freezes': [{'t0': 1.2, 't1': 2.8}]},
    ),
    'bottom_black_badge': dict(
        where='顶层 "badge_bar": {"text": 角标文字, "h": 0.82, "sub_y": 0.70, "ranges": [[t0, t1], ...]}；不写 ranges 就是所有口播全屏的时段',
        style=['premium'],
        auto='口播全屏时段画面底部 18% 盖纯黑，交界线正中骑一枚米白描边小角标；B-roll 和整屏版式时段恢复全屏；字幕整片挪到人物胸前（不放进黑边）',
        variants={'badge': (['premium'], '口播上移底部留黑：人物只占上方八成，下面一条黑，交界线压品牌角标')},
        demo=lambda A, v: {'badge_bar': {'text': '口播剪辑研究所'}},
    ),
    'grain_vignette_bg': dict(
        where='layout 写 {"mode": "bg", "bg": "grain"}（纯文字页底），或抠像换底 {"mode": "matte", "bg": "grain"}', style=['premium'],
        auto='代码画：#4A4A4A 底加细颗粒纸纹，四周重暗角压到约 15% 亮度，最亮在 0.4 高',
        variants={'grain': (['premium'], '深灰纸纹暗角底：纯文字页用，比纯黑有质感')},
        demo=lambda A, v: {'layout': [{'t0': 0.0, 't1': 3.6, 'mode': 'bg', 'bg': 'grain'}],
                           'titles': [{'t0': 0.3, 't1': 3.5, 'layout': 'quote', 'text': '慢一点，才能看清', 'sfx': False}]},
    ),
    'wave_lines_bg': dict(
        where='layout 写 {"mode": "bg", "bg": "waves"}，或抠像换底、素材窗口（example_window 的 thin）的窗外', style=['premium'],
        auto='黑底上 1 像素深灰正弦波浪线，行距 1.2% 画面高，整体每秒上移约 9 像素，像等高线慢慢流动',
        variants={'waves': (['premium'], '黑底动态波浪线：几乎察觉不到地流动，黑底不死板')},
        demo=lambda A, v: {'layout': [{'t0': 0.0, 't1': 3.6, 'mode': 'matte', 'bg': 'waves'}]},
    ),
    'perspective_floor_bg': dict(
        where='layout 写 {"mode": "matte", "bg": "floor:<变体>"} 抠像人站在透视空间里，或 {"mode": "bg", "bg": "floor", "variant": ...}', style=['premium'],
        auto='代码画网格平面，透视成往远处收窄的地面，远端渐隐到黑；地平线在画面中线，字放中间黑带',
        variants={'floor': (['premium'], '透视地面：下半屏白网格地面'), 'tunnel': (['premium'], '上下隧道：上下两片对称、中间留黑带'),
                  'corner': (['premium'], '斜角走廊：两片斜向楔形对称'), 'color': (['premium'], '彩色网格纹理：青色发光方格地面')},
        demo=lambda A, v: {'layout': [{'t0': 0.0, 't1': 3.6, 'mode': 'bg', 'bg': 'floor', 'variant': v}],
                           'titles': [{'t0': 0.3, 't1': 3.5, 'layout': 'quote', 'text': '走进三维空间', 'sfx': False}]},
    ),
    'theme_video_dim_bg': dict(
        where='broll 的 fit 为 double 或 band 时写 "bg": "video", "bg_src": 话题视频（星空、数据流、会议）', style=['premium'],
        auto='话题视频循环铺满做底，压暗约三成、轻虚化、降饱和，一直在微动但不抢卡片',
        variants={'video': (['premium'], '主题视频压暗做底：卡片和截图后面垫一段相关视频')},
        demo=lambda A, v: {'broll': [{'t0': 0.2, 't1': 3.5, 'src': A['shot'], 'fit': 'band', 'bg': 'video', 'bg_src': A['rec']}]},
    ),
})


# ---------------------------------------------------------------- 第 13 批（一星）：文字与排版（wordart.py）
from wordart import PINYIN_VARIANTS, WORDWALL_VARIANTS   # noqa: E402

IMPL.update({
    'grid_2x2_title': dict(
        beats={'topic': 2, 'compare': 3, 'quote': 3}, style=['premium'], intensity=2,
        ok=lambda b: _cjk((b.get('text') or '').replace(' ', ''), 4) and len(b['text'].replace(' ', '')) == 4,
        build=lambda b, v, at: {'layout': 'grid2x2', 'text': b['text'], 'pair': b.get('pair')},
        sound=lambda st, b, at: [{'type': 'thump', 'at': 0.05}],
        demo={'beat': 'topic', 'text': '信息密度', 'pair': '取舍'},
    ),
    'perspective_text_3d': dict(
        beats={'topic': 2, 'chapter': 4}, style=['premium'], intensity=3, max_n=1,
        ok=lambda b: _cjk((b.get('text') or '').replace(' ', ''), 4) and len(b['text'].replace(' ', '')) >= 2,
        build=lambda b, v, at: {'layout': 'persp3d', 'text': b['text']},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.0}, {'type': 'thump', 'at': 0.35}],
        demo={'beat': 'topic', 'text': '先想后做'},
    ),
    'staircase_text': dict(
        beats={'emotion': 2, 'question': 2, 'transition_talk': 2}, style=['web'], intensity=2,
        ok=lambda b: _short((b.get('text') or '').replace(' ', ''), 5) and len(b['text'].replace(' ', '')) >= 3,
        build=lambda b, v, at: {'layout': 'stairs', 'text': b['text']},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0.1 * j} for j in range(min(5, len(b['text'].replace(' ', ''))))],
        demo={'beat': 'emotion', 'text': '简单吗？'},
    ),
    'text_depth_overlap_frame': dict(
        beats={'concept': 2, 'emphasis': 3}, style=['web'], intensity=3, max_n=1,
        ok=lambda b: _items_ok(b, 3, 5, 5),
        build=lambda b, v, at: {'layout': 'overlapframe', 'items': b['items'], 'item_at': [at(x) for x in b['items']], 'cover': True},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0.25 + 0.3 * j} for j in range(len(b['items']))],
        demo={'beat': 'concept', 'items': ['网感', '高级感', '节奏', '留白']},
    ),
    'text_orbit_3d': dict(
        beats={'concept': 2, 'emotion': 3}, style=['web'], intensity=3, max_n=1,
        ok=lambda b: _cjk((b.get('text') or '').replace(' ', ''), 6) and len(b['text'].replace(' ', '')) >= 3,
        build=lambda b, v, at: {'layout': 'orbit', 'text': b['text']},
        sound=lambda st, b, at: [{'type': 'shimmer', 'at': 0.0}],
        demo={'beat': 'concept', 'text': '关键信息'},
    ),
    'word_wall_cloud': dict(
        beats={'emotion': 2, 'negative': 2, 'concept': 3}, style=['premium', 'web'], intensity=2,
        variants={'wall': ['premium', 'web'], 'cloud': ['premium', 'web']},
        variant_ok={'wall': lambda b: _short(b.get('text'), 1), 'cloud': lambda b: _short(b.get('text'), 4)},
        ok=lambda b: _short(b.get('text'), 4),
        build=lambda b, v, at: {'layout': 'wordwall', 'variant': v, 'text': b['text'], 'items': b.get('items')},
        sound=lambda st, b, at: [{'type': 'swell', 'at': 0.0}],
        demo={'beat': 'emotion', 'text': '吵'},
        demo_v={'cloud': {'text': '焦虑', 'items': ['信息', '太多', '噪音', '算法', '推送', '热点', '刷屏']}},
    ),
    'pinyin_note': dict(
        beats={'concept': 2, 'emotion': 3, 'list': 3, 'topic': 3}, style=['web'], intensity=1, max_n=2,
        variants={'above': ['web'], 'pun': ['web'], 'list': ['web']},
        variant_ok={'list': lambda b: len(b.get('items') or []) >= 2},
        ok=lambda b: _cjk(b.get('text'), 6) or len(b.get('items') or []) >= 2,
        build=lambda b, v, at: {'layout': 'pinyin', 'variant': v, 'text': b.get('text'), 'pinyin': b.get('pinyin'), 'items': b.get('items'),
                                'char_at': [at(c) for c in b['text']] if v == 'above' and b.get('text') else None,
                                **({'cover': True} if v == 'list' else {})},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0.25}],
        demo={'beat': 'concept', 'text': '上盘硬菜', 'items': [{'text': '油条', 'pun': 'oil tiao'}, {'text': '豆汁', 'pun': 'dou juice'},
                                                               {'text': '煎饼', 'pun': 'jian bing'}]},
    ),
    'credits_bilingual': dict(
        beats={'cta': 3}, style=['premium'], intensity=2, max_n=1,
        ok=lambda b: 1 <= len(b.get('items') or []) <= 4 and all(isinstance(x, dict) and x.get('role') for x in b['items']),
        build=lambda b, v, at: {'layout': 'credits', 'items': b['items'], 'src': b.get('src'), 'cover': True},
        sound=lambda st, b, at: [{'type': 'swell', 'at': 0.0}],
        demo={'beat': 'cta', 'items': [{'role': '出品', 'en': 'Producer', 'name': '阿木'}, {'role': '剪辑', 'en': 'Editor', 'name': 'AI Agent'},
                                       {'role': '配乐', 'en': 'Music', 'name': 'Mixkit'}]},
    ),
    'ready_go_iris_out': dict(
        beats={'transition_talk': 2, 'chapter': 4}, style=['premium'], intensity=3, max_n=1,
        ok=lambda b: _cjk(b.get('text'), 2) and len(b['text']) == 2,
        build=lambda b, v, at: {'layout': 'readygo', 'text': b['text'], 'en': b.get('en')},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.0}, {'type': 'drop', 'at': max(0.3, b['t1'] - b['t0'] - 0.8)}],
        demo={'beat': 'transition_talk', 'text': '开始', 'en': 'READY GO→'},
    ),
    'darken_blend_text': dict(
        beats={'topic': 3, 'story': 2}, style=['premium'], intensity=1,
        ok=lambda b: _short(b.get('wall') or b.get('text'), 12),
        build=lambda b, v, at: {'layout': 'darkenword', 'text': b.get('wall') or b['text']},
        demo={'beat': 'story', 'wall': '十年剪辑 只做口播'},
    ),
    'hazard_tape_strips': dict(
        beats={'hook': 3, 'topic': 3, 'negative': 3}, style=['web'], intensity=2, max_n=1,
        ok=lambda b: bool(b.get('en')) and b['en'].isascii(),
        build=lambda b, v, at: {'layout': 'tape', 'text': b['en'].upper(), 'text2': (b.get('en2') or b['en']).upper()},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.0}],
        demo={'beat': 'hook', 'en': 'Warning', 'en2': 'Do not skip'},
    ),
    'search_proof_hook': dict(
        beats={'hook': 2, 'evidence': 3}, style=['web'], intensity=3, max_n=1,
        ok=lambda b: bool(b.get('src')) and _short(b.get('text'), 8),
        build=lambda b, v, at: {'layout': 'searchhook', 'src': b['src'], 'src_in': b.get('src_in'), 'text': b['text'], 'items': b.get('items'),
                                'number': b.get('number'), 'clear': b.get('clear'), 'cover': True},
        sound=lambda st, b, at: [{'type': 'thump', 'at': 0.15}, {'type': 'whoosh', 'at': 0.5}],
        demo={'beat': 'hook', 'src': '@rec', 'text': '不会告诉你的', 'items': ['流量', '算法'], 'number': '90%'},
    ),
})
VNAMES.update({k: v.split('：')[0] for D in (WORDWALL_VARIANTS, PINYIN_VARIANTS) for k, v in D.items() if k not in VNAMES})
GLOBAL.update({
    'sub_rolling_two_line': ('sub_look', {'rolling': '双行滚动字幕：左下角两行，上一句变灰退上去（无人出镜的解说）',
                                          'rolling_ink': '双行滚动字幕深色版：浅色纸页底上用'}),
})


# ---------------------------------------------------------------- 第 14 批（一星）：特效与转场（vfx.py）
from vfx import PARTICLE_VARIANTS   # noqa: E402

IMPL.update({
    'match_shape_cut': dict(
        beats={'list': 3, 'hook': 3}, style=['web'], intensity=3, max_n=1,
        ok=lambda b: len(b.get('srcs') or []) >= 3,
        build=lambda b, v, at: {'layout': 'shapecut', 'srcs': b['srcs'], 'circles': b.get('circles'), 'text': b.get('text'), 'every': b.get('every'),
                                'cover': True},
        sound=lambda st, b, at: [{'type': 'tap', 'at': round(0.3 * j, 2)} for j in range(4)],
        demo={'beat': 'list', 'srcs': ['@photo', '@shot', '@rec', '@rec2'], 'text': '形状不变 内容在变'},
    ),
    'radial_blur_feel': dict(
        beats={'negative': 2, 'emotion': 3}, style=['premium'], intensity=3, max_n=1,
        ok=lambda b: _short(b.get('text'), 12) or bool(b.get('lines')),
        build=lambda b, v, at: {'layout': 'radial', 'text': b.get('text'), 'lines': b.get('lines'), 'cover': True},
        sound=lambda st, b, at: [{'type': 'swell', 'at': 0.0}],
        demo={'beat': 'negative', 'lines': ['看 不 清', '好 难 受']},
    ),
    'edge_white_fade': dict(
        beats={'hook': 3, 'topic': 3}, style=['premium'], intensity=1,
        ok=lambda b: True,
        build=lambda b, v, at: {'layout': 'whitefade'},
        demo={'beat': 'topic'},
    ),
    'particle_overlay': dict(
        beats={'cta': 2, 'number': 3}, style=['variety', 'premium', 'web'], intensity=2, max_n=1,
        variants={'starfield': ['variety', 'premium', 'web'], 'money': ['variety', 'web']},
        variant_ok={'starfield': lambda b: b.get('beat') == 'cta', 'money': lambda b: b.get('beat') == 'number' and _short(b.get('text'), 10)},
        ok=lambda b: True,
        build=lambda b, v, at: {'layout': 'particles', 'variant': v, 'text': b.get('text')},
        sound=lambda st, b, at: [{'type': 'shimmer', 'at': 0.1}],
        demo={'beat': 'cta', 'text': '我们下期见'},
        demo_v={'money': {'beat': 'number', 'text': '¥10,000'}},
    ),
    'canvas_feather_extend': dict(
        beats={'topic': 3, 'concept': 3}, style=['premium'], intensity=2,
        ok=lambda b: _short(b.get('text'), 10),
        build=lambda b, v, at: {'layout': 'extend', 'text': b['text'], 'sub': b.get('sub'), 'cover': True},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.0}],
        demo={'beat': 'topic', 'text': '上方留白放标题', 'sub': '画面往下挪，墙面颜色补上去'},
    ),
    'id_watermark_bg': dict(
        beats={'hook': 3, 'chapter': 4, 'cta': 3}, style=['web', 'premium'], intensity=1,
        ok=lambda b: bool(b.get('id')),
        build=lambda b, v, at: {'layout': 'idwall', 'text': b['id']},
        demo={'beat': 'cta', 'id': '@口播剪辑研究所'},
    ),
    'ui_panel_metaphor_bg': dict(
        beats={'negative': 3, 'concept': 4}, style=['premium'], intensity=2, max_n=1,
        ok=lambda b: _short(b.get('giant'), 2),
        build=lambda b, v, at: {'layout': 'panels', 'text': b['giant'], 'items': b.get('items')},
        sound=lambda st, b, at: [{'type': 'thump', 'at': 0.2}],
        demo={'beat': 'negative', 'giant': '模板'},
    ),
    'greenscreen_desaturate': dict(
        beats={'emotion': 4}, style=['premium'], intensity=1,
        ok=lambda b: bool(b.get('overlay')),
        build=lambda b, v, at: {'layout': 'screenblend', 'src': b['overlay'], 'opacity': b.get('opacity'), 'cover': True},
        demo={'beat': 'emotion', 'overlay': '@rec2'},
    ),
    'color_swatch_card': dict(
        beats={'concept': 3, 'number': 3}, style=['premium', 'web'], intensity=2,
        ok=lambda b: len(b.get('colors') or []) >= 2,
        build=lambda b, v, at: {'layout': 'swatch', 'colors': b['colors'], 'text': b.get('text'), 'note': b.get('note_line')},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0.35 + 0.1 * j} for j in range(len(b['colors']))],
        demo={'beat': 'concept', 'colors': ['#F2E9B8', '#F0A21A', '#BFE3F0'], 'text': '≤3 种颜色', 'note_line': '配色越少越高级'},
    ),
    'diagram_glow_callout': dict(
        beats={'concept': 3, 'steps': 3}, style=['premium'], intensity=2,
        ok=lambda b: bool(b.get('src')) and 1 <= len(b.get('stages') or []) <= 4,
        build=lambda b, v, at: {'layout': 'diagram', 'src': b['src'], 'stages': b['stages'],
                                'item_at': [at(x.get('label')) for x in b['stages']], 'cover': True},
        sound=lambda st, b, at: [{'type': 'shimmer', 'at': 0.4}],
        demo={'beat': 'concept', 'src': '@shot', 'stages': [{'poly': [[0.05, 0.05], [0.95, 0.05], [0.95, 0.4], [0.05, 0.4]], 'label': '第一层：占用比例'},
                                                           {'poly': [[0.05, 0.45], [0.95, 0.45], [0.95, 0.85], [0.05, 0.85]], 'label': '第二层：自动压缩'}]},
    ),
})
VNAMES.update({k: v.split('：')[0] for k, v in PARTICLE_VARIANTS.items() if k not in VNAMES})
FIELDS.update({
    'block_wipe': dict(
        where='transitions 写 {"t", "type": "blocks", "variant": random / bars, "colors": [...]}', style=['web'],
        auto='random 橙红、深色矩形碎块 0.2 秒内随机铺满，切点后按随机顺序散掉露出下一段；bars 黑色竖条随机升起盖满再落下；配故障声',
        variants={'random': (['web'], '随机色块铺满：矩形碎块铺满整屏，再散开露出下一画面'), 'bars': (['web'], '黑色竖条擦屏：竖条随机升起擦掉上一画面')},
        demo=lambda A, v: _cut(A, 'blocks', v),
    ),
    'tunnel_zoom': dict(
        where='transitions 写 {"t", "type": "tunnel", "color": "#1E6E8C"}；30 秒内最多一个，适合开场第一下或章节页进正片', style=['web'],
        auto='切点前后中心放射青色光柱往外冲，下一段从画面中心 20% 冲到满屏；配穿梭声',
        variants={'tunnel': (['web'], '隧道穿梭：光柱冲出来，小窗从中心向镜头冲到满屏')},
        demo=lambda A, v: _cut(A, 'tunnel', None),
    ),
    'frame_tilt': dict(
        where='顶层 fx 写 {"t0", "t1", "type": "tilt", "angle": -10, "back": true}', style=['web', 'variety'],
        auto='0.3 秒整屏（连字幕）转到 -10 度并放大到 1.1 倍免得露黑角，back 写了最后 0.3 秒转回来；配一声嗖',
        variants={'tilt': (['web', 'variety'], '画面歪头倾斜：像镜头歪一下头，讲完转回或直接切走')},
        demo=lambda A, v: _fxd(A, 1.0, 2.6, 'tilt', back=True),
    ),
})


# ---------------------------------------------------------------- 第 15 批（一星）：贴纸、动效与其他（props.py）
from props import FRAMESTICKER_VARIANTS, JYTPL_VARIANTS   # noqa: E402

IMPL.update({
    'avatar_motion_trail': dict(
        beats={'steps': 3, 'story': 3}, style=['web'], intensity=2, max_n=1,
        ok=lambda b: True,
        build=lambda b, v, at: {'layout': 'trail', 'path': b.get('path'), 'cover': True},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.1}],
        demo={'beat': 'steps'},
    ),
    'subject_spin_ring': dict(
        beats={'topic': 3, 'chapter': 4}, style=['premium'], intensity=2, max_n=1,
        ok=lambda b: bool(b.get('subject') or b.get('icon')),
        build=lambda b, v, at: {'layout': 'spinring', 'src': b.get('subject'), 'icon': b.get('icon'), 'text': b.get('text')},
        sound=lambda st, b, at: [{'type': 'swell', 'at': 0.0}],
        demo={'beat': 'topic', 'icon': 'Globe showing asia-australia', 'text': '一个产品 三种卖法'},
    ),
    'text_follow_gesture': dict(
        beats={'emphasis': 3, 'emotion': 3, 'demo': 4}, style=['web', 'premium'], intensity=2,
        ok=lambda b: bool(b.get('keys')) and _short(b.get('text'), 6),
        build=lambda b, v, at: {'layout': 'gesturetext', 'text': b['text'], 'keys': b['keys']},
        demo={'beat': 'emphasis', 'text': '放大', 'keys': None},
    ),
    'perspective_paper_panels': dict(
        beats={'list': 3}, style=['premium'], intensity=2,
        ok=lambda b: 2 <= len(b.get('items') or []) <= 3,
        build=lambda b, v, at: {'layout': 'paperpanels', 'items': b['items'],
                                'item_at': [at(x if isinstance(x, str) else x['text']) for x in b['items']]},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.2 + 0.7 * j} for j in range(len(b['items']))],
        demo={'beat': 'list', 'items': [{'text': '表达', 'note': '先把一句话说清楚'}, {'text': '节奏', 'note': '每两秒有变化'},
                                        {'text': '包装', 'note': '重点才加字'}]},
    ),
    'orbit_coverage': dict(
        beats={'concept': 4}, style=['premium'], intensity=3, max_n=1,
        ok=lambda b: bool(b.get('orbit')),
        build=lambda b, v, at: {'layout': 'orbitcover', 'text': b.get('text'), 'cover': True},
        sound=lambda st, b, at: [{'type': 'shimmer', 'at': 0.2}],
        demo={'beat': 'concept', 'orbit': True, 'text': '全球覆盖'},
    ),
    'hand_mask_text_wipe': dict(
        beats={'emotion': 4, 'emphasis': 4}, style=['web', 'premium'], intensity=2, max_n=1,
        ok=lambda b: b.get('wipe_at') is not None and _short(b.get('text'), 6),
        build=lambda b, v, at: {'layout': 'armwipe', 'text': b['text'], 'wipe_at': b['wipe_at'], 'wipe_dur': b.get('wipe_dur'),
                                'reverse': b.get('reverse'), 'x': b.get('x')},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': b['wipe_at']}],
        demo={'beat': 'emotion', 'text': '抹掉焦虑', 'wipe_at': 1.6},
    ),
    'mic_cluster_announce': dict(
        beats={'topic': 3, 'hook': 3}, style=['variety'], intensity=3, max_n=1,
        ok=lambda b: _short(b.get('text'), 6),
        build=lambda b, v, at: {'layout': 'mics', 'text': b['text']},
        sound=lambda st, b, at: [{'type': 'whoosh', 'at': 0.0}, {'type': 'shimmer', 'at': 0.3}],
        demo={'beat': 'topic', 'text': '重磅宣布'},
    ),
    'frame_stickers': dict(
        beats={'story': 3, 'evidence': 4}, style=['web', 'variety'], intensity=2,
        variants={'polaroid': ['web', 'variety'], 'film': ['web', 'variety'], 'cartoon': ['variety', 'web']},
        ok=lambda b: True,
        build=lambda b, v, at: {'layout': 'framesticker', 'variant': v, 'text': b.get('caption'), 'cover': True},
        sound=lambda st, b, at: [{'type': 'snap', 'at': 0.0}],
        demo={'beat': 'story', 'caption': '2026 夏'},
    ),
    'pain_point_opening': dict(
        beats={'hook': 3, 'question': 4}, style=['web', 'variety'], intensity=3, max_n=1,
        ok=lambda b: _items_ok(b, 2, 2, 6) and _short(b.get('text'), 5),
        build=lambda b, v, at: {'layout': 'painpoint', 'text': b['text'], 'items': b['items'], 'ask': b.get('ask'), 'cover': True},
        sound=lambda st, b, at: [{'type': 'pop', 'at': 0.3}, {'type': 'pop', 'at': 0.55}, {'type': 'glitch', 'at': 1.6}],
        demo={'beat': 'hook', 'text': '剪口播', 'items': ['没排版~', '没思路~']},
    ),
    'jy_text_template_variety': dict(
        beats={'emotion': 3, 'negative': 3, 'hook': 4}, style=['variety'], intensity=2, max_n=2,
        variants={'energy': ['variety'], 'warn': ['variety'], 'out': ['variety'], 'aaa': ['variety']},
        variant_ok={'energy': lambda b: b.get('beat') == 'hook', 'warn': lambda b: b.get('beat') == 'negative', 'aaa': lambda b: b.get('beat') == 'emotion'},
        ok=lambda b: True,
        build=lambda b, v, at: {'layout': 'jytpl', 'variant': v, 'text': b.get('tpl_text')},
        sound=lambda st, b, at: [{'type': 'boing' if st.get('variant') == 'aaa' else 'thump', 'at': 0.05}],
        demo={'beat': 'emotion'},
    ),
})
VNAMES.update({k: v.split('：')[0] for D in (FRAMESTICKER_VARIANTS, JYTPL_VARIANTS) for k, v in D.items() if k not in VNAMES})
FIELDS.update({
    'magnifier_zoom': dict(
        where='顶层 fx 写 {"t0", "t1", "type": "magnifier", "variant": "reach", "at": [x, y], "from": [画外起点], "zoom": 1.5, "r": 0.2}', style=['web', 'variety'],
        auto='镜片 0.5 秒从画外沿手柄方向滑到 at，镜片里放大 1.5 倍（裁切位置跟着镜片走、对得齐），长手柄一直伸到画外，最后 0.5 秒移走；配推近声',
        variants={'reach': (['web', 'variety'], '放大镜从画外伸进来：镜片里的脸或关键词放大，随后移开')},
        demo=lambda A, v: _fxd(A, 0.4, 3.4, 'magnifier', 'reach', at=[0.5, 0.3]),
    ),
    'music_humor_sting': dict(
        where='顶层 "stings": [{"t": 梗句开始, "src": 用户准备的喜剧短乐句, "in": 从第几秒截, "dur": 2~4}]；没有短乐句就别写，改用梗音效', style=['web', 'premium'],
        auto='渲染前剪成短片段（前后 0.1 秒淡变）放进音效，这几秒主配乐让开；五分半的片子三四次就够，不是每个梗都要',
        variants={'sting': (['web', 'premium'], '梗句幽默短乐句：调侃、反转那句配乐临时换成两三秒俏皮乐句再回主循环')},
        demo=lambda A, v: {'audio': {'voice': {'lufs': -16}, 'bgm': [{'src': A['bgm'], 't0': 0, 't1': 3.6}]}, 'stings': [{'t': 1.0, 'src': A['hype'], 'in': 20, 'dur': 2.4}],
                           '_wave': True},
    ),
    'ai_micro_animation': dict(
        where='broll 写生成好的片段 {"src": "ai/xxx.mp4", "ai": {"frame_at": 截帧秒数, "prompt": "…"}}；ai 只是记录来源，渲染照普通 B-roll 放', style=['web'],
        auto='流程：截出关键帧 → 用 Renoise 的图生视频生成 2 秒（消耗额度，先给用户看预估花费，用户同意才生成）→ 截 1~1.5 秒当 B-roll；只补画面小片段，配乐不用 AI 生成',
        variants={'ai': (['web'], 'AI 补一两秒小动画：原本要 AE 做的爆炸、变形、转场插画')},
        demo=None,
    ),
    'jianying_layer_tips': dict(
        where='build_draft.py 生成剪映草稿时按这个结构摆轨道，不用手写', style=['premium', 'web'],
        auto='轨道从下到上：主轨口播 → B-roll → 调整图层 → 网点丝印 → 素材带 → 包装（复合片段）→ 头像 → 字幕；剪映里要人压字就开自由层级、'
             '口播复制一层做智能抠像、文字放两层之间；文字转复合片段后才能加特效滤镜蒙版，先定稿再打包',
        variants={'layers': (['premium', 'web'], '剪映图层组织：包装放同一条轨、文字转复合片段、自由层级夹字')},
        demo=None,
    ),
    'teardown_audit': dict(
        where='python scripts/teardown.py 成片.mp4 [--timeline timeline.json] [--music 配乐分轨.wav] [--separate]', style=['premium'],
        auto='场景检测数包装点、给平均间隔；按 timeline 算口播全屏 / 画中画和整屏包装 / 气口留白的占比；配乐每 0.5 秒算响度找停顿和换段（装了 demucs 可先分离人声）',
        variants={'audit': (['premium'], '拉片量化复盘：标记包装点、镜头类型占比、分离人声单听配乐')},
        demo=None,
    ),
})


# 变体名按手法各管各的：不同批次的变体键会重名（wall、paper、film、tab……），全局 VNAMES 只做兜底
_OWN_VN = {'ui_widget_mock': WIDGET_VARIANTS, 'timeline_axis': AXIS_VARIANTS, 'resource_list_page': RESLIST_VARIANTS, 'type_card_row': TYPEROW_VARIANTS,
           'photo_card_stack': PHOTOSTACK_VARIANTS, 'comment_bubbles': COMMENT_VARIANTS, 'person_info_card': PERSON_VARIANTS,
           'example_window': WINDOW_VARIANTS, 'keyword_band_stack': BANDS_VARIANTS, 'matte_band_stack': MATTEBAND_VARIANTS,
           'layer_parallax_drift': PARALLAX_VARIANTS, 'word_wall_cloud': WORDWALL_VARIANTS, 'pinyin_note': PINYIN_VARIANTS,
           'particle_overlay': PARTICLE_VARIANTS, 'frame_stickers': FRAMESTICKER_VARIANTS, 'jy_text_template_variety': JYTPL_VARIANTS}
for _tid, _D in _OWN_VN.items():
    IMPL[_tid]['vnames'] = {k: v.split('：')[0] for k, v in _D.items()}


def vname(tid, v):
    return (IMPL.get(tid, {}).get('vnames') or {}).get(v) or VNAMES.get(v) or v


def catalog():
    return {t['id']: t for t in json.loads(CATALOG.read_text(encoding='utf-8'))['techniques']}


def allowed(tags, style, tone):
    """风格标签能不能在这条片子里用：克制档只用纯高级感，网感档多了网感，综艺感用综艺和网感。"""
    if style == 'variety':
        return bool(set(tags) & {'variety', 'web'})
    return bool(set(tags) & ({'premium'} if tone == 'calm' else {'premium', 'web'}))


def expand_beats(tl, st, base='.'):
    """把 timeline 的 beats 展开成 titles（不改 timeline）。挑法：内容类型匹配、字够用、风格允许的手法里，
    按优先级挑，同一手法 30 秒内不重复、和上一条大字换版式、重手法之间隔 20 秒；变体轮着用。
    例外：章节页全片只用一种载体（第一次按强度档的 chapter_look 挑），数据卡、章节页这类 same_look 手法全片沿用第一次的变体。"""
    beats = sorted(tl.get('beats') or [], key=lambda b: b['t0'])
    if not beats:
        return []
    style = tl.get('style', 'premium')
    tone = st.get('tone', 'web')
    used = [(t['t0'], t.get('tech') or t.get('layout', 'side'), 2) for t in tl.get('titles', [])]
    vcount, out, fixed = {}, [], {}
    chapter_tid = next((CHAPTER_TECH[t['layout']] for t in sorted(tl.get('titles', []), key=lambda t: t['t0']) if t.get('layout') in CHAPTER_TECH), None)
    cards = [(x['t0'], x['t1']) for x in tl.get('broll', []) if x.get('fit', 'cover') != 'cover']
    for b in beats:
        busy = sum(max(0.0, min(b['t1'], c1) - max(b['t0'], c0)) for c0, c1 in cards) / max(0.1, b['t1'] - b['t0'])
        if busy > 0.4 and not b.get('use'):   # 同一时刻只有一个视觉焦点：素材卡片在画面上时不再自动叠大字
            print(f"beats：{b['t0']:.1f} 秒这段有素材卡片在画面上，不自动加大字（要加就写 use 指定手法）")
            continue
        def at(word, b=b):
            if not word:
                return None
            w = word.replace('\\N', '').replace('\n', '')
            t = word_time(w[:4], base, after=b['t0'] - 0.3)
            return None if t is None or t > b['t1'] else round(max(0.0, t - b['t0']), 3)
        if b.get('use'):
            if b['use'] not in IMPL:
                raise SystemExit(f"beats：手法「{b['use']}」还没实现，可用：{'、'.join(IMPL)}")
            tid = b['use']
        else:
            cands = []
            for tid, T in IMPL.items():
                if b['beat'] not in T['beats'] or not allowed(T['style'], style, tone):
                    continue
                if T.get('max_n') and sum(1 for x in out if x.get('tech') == tid) >= T['max_n']:   # 砸屏这类全片限次
                    continue
                try:
                    if not T['ok'](b):
                        continue
                except (KeyError, TypeError, IndexError):
                    continue
                score = T['beats'][b['beat']] * 2
                score += 10 * sum(1 for t0, u, _ in used if u == tid and abs(b['t0'] - t0) < TEMPLATE_GAP)
                near = sorted((abs(b['t0'] - t0), u) for t0, u, _ in used)[:1]   # 时间上挨着的那条大字
                score += 3 if near and near[0][1] == tid else 0
                if T['intensity'] == 3:
                    score += 6 * sum(1 for t0, _, i in used if i == 3 and abs(b['t0'] - t0) < HEAVY_GAP)
                cands.append((score, list(IMPL).index(tid), tid))
            if not cands:
                print(f"beats：{b['t0']:.1f} 秒的「{b['beat']}」没有合适的已实现手法（字不够或风格不允许），跳过")
                continue
            tid = min(cands)[2]
            if b['beat'] == 'chapter':   # 全片一种章节载体：沿用第一个，第一个按强度档的 chapter_look 挑
                ids = {c[2] for c in cands}
                keep = chapter_tid if chapter_tid in ids else CHAPTER_TECH.get(st.get('chapter_look'))
                tid = keep if keep in ids else tid
        if b['beat'] == 'chapter' and chapter_tid is None and tid in CHAPTER_TECH.values():
            chapter_tid = tid
        T = IMPL[tid]
        vs = [v for v, tags in (T.get('variants') or {}).items() if allowed(tags, style, tone) and T.get('variant_ok', {}).get(v, lambda b: True)(b)]
        if T.get('same_look') and fixed.get(tid) in vs:   # 同一种卡片、章节页全片用同一个样子，只换内容
            v = b.get('variant') or fixed[tid]
        else:
            v = b.get('variant') or (min(vs, key=lambda v: (vcount.get((tid, v), 0), list(T['variants']).index(v))) if vs else None)
        if T.get('same_look') and v:
            fixed.setdefault(tid, v)
        vcount[(tid, v)] = vcount.get((tid, v), 0) + 1
        title = {'t0': b['t0'], 't1': b['t1'], **{k: x for k, x in T['build'](b, v, at).items() if x is not None}, 'tech': tid,
                 **({'variant': v} if v else {})}
        for k in ('y', 'side', 'sfx', 'anim', 'dim_after'):   # beats 上也能写大字的入场动画、读完压暗
            if k in b and k not in title:
                title[k] = b[k]
        snd = T.get('sound')
        if snd and 'sound' not in b and b.get('sfx') is not False:
            s = snd({**st, 'tone': tone, 'variant': v}, b, at)
            if s:
                title['sound'] = s
                title['sound_auto'] = True   # 手法自带的声音按密度上限取舍，不像手写的 sound 必留
                if T['intensity'] >= 3 or title.get('layout') in HIT_LAYOUTS:
                    title['sound_hit'] = True   # 整屏冲击的大包装：画面砸下来必须有声，密度上限只砍小提示音
        out.append(title)
        used.append((b['t0'], tid, T['intensity']))
        if b.get('note'):   # 主标题旁小补充（title_aside_note）：主标题出来 0.3 秒后弹到它右上角
            x, y = _note_anchor(title, st, tl)
            out.append({'t0': b['t0'] + 0.3, 't1': b['t1'], 'layout': 'note', 'variant': b.get('note_look', 'tag'), 'text': b['note'],
                        'x': x, 'y': y, 'tech': 'title_aside_note', 'sound': [{'type': 'pop', 'at': 0}], 'sound_auto': True})
    return out


def _note_anchor(title, st, tl):
    """小补充贴在主标题右上角：ASS 排的大字按排版结果量外框，逐帧画的版式按它的默认位置估。"""
    from typeset import layout_title, text_w
    from kvlib import GRAPHIC_LAYOUTS
    cv = tl.get('canvas', {'w': 1080, 'h': 1920})
    W, H = cv['w'], cv['h']
    if title.get('layout') not in GRAPHIC_LAYOUTS:
        boxes = []
        for it in layout_title(title, st, W, H):
            if it.get('kind') or not it.get('text'):
                continue
            lines = it['text'].replace('\\N', '\n').split('\n')
            w = max(text_w(l, it['size'], it.get('condense', 100)) for l in lines)
            x0 = it['x'] if it['an'] == 7 else it['x'] - w if it['an'] == 9 else it['x'] - w / 2
            boxes.append((x0, it['y'], x0 + w))
        if boxes:
            right, top = max(b[2] for b in boxes), min(b[1] for b in boxes)
            return round(min(0.86, right / W + 0.02), 3), round(max(0.08, top / H - 0.02), 3)
    return 0.78, round(title.get('y', 0.62) - 0.08, 3)


# ---------------------------------------------------------------- 命令行
def cmd_menu(a):
    cat = catalog()
    tl = {'style': a.style, 'tone': a.tone}
    print(f"已实现、{a.style}{'·' + a.tone if a.style == 'premium' else ''} 能用的手法（beats 自动挑，也可 use 指定）：")
    for tid, T in IMPL.items():
        if a.beat and a.beat not in T['beats']:
            continue
        if not allowed(T['style'], tl['style'], tl['tone']):
            continue
        c = cat.get(tid, {})
        vs = [v for v, tags in (T.get('variants') or {}).items() if allowed(tags, a.style, a.tone)]
        print(f"  {tid:22} {c.get('name') or T.get('name', ''):10} 适合：{'、'.join(BEATS[x] for x in sorted(T['beats'], key=T['beats'].get))}"
              + (f"  变体：{'/'.join(vs)}" if vs else ''))
    print('全片一次选定：' + '；'.join(f"{key}={'/'.join(opts)}" for key, opts in GLOBAL.values()))
    print('写在 timeline 字段里的（画面与镜头、版式、素材卡、开场）：')
    for tid, F in FIELDS.items():
        if allowed(F['style'], a.style, a.tone):
            print(f"  {tid:22} {cat.get(tid, {}).get('name', ''):10} {F['where'].split('：')[0]}"
                  + (f"  变体：{'/'.join(v for v, (tags, _) in F['variants'].items() if allowed(tags, a.style, a.tone))}" if F['variants'] else ''))


def cmd_show(a):
    t = catalog().get(a.id)
    if not t:
        raise SystemExit(f'手法库里没有 {a.id}')
    print(json.dumps({**t, 'implemented': a.id in IMPL or a.id in GLOBAL or a.id in FIELDS}, ensure_ascii=False, indent=1))
    if a.id in FIELDS:
        F = FIELDS[a.id]
        print(f"怎么写：{F['where']}" + (f"\n自动：{F['auto']}" if F.get('auto') else ''))


def cmd_arrange(a):
    p = Path(a.timeline).resolve()
    tl = load_json(p)
    st = style_preset(tl)
    got = expand_beats(tl, st, p.parent)
    for t in got:
        print(f"{t['t0']:6.1f}~{t['t1']:5.1f}  {t['tech']:22} {t.get('variant') or '':10} {t.get('text') or t.get('left') or t.get('items') or t.get('value') or ''}")
    if a.write:
        tl['titles'] = tl.get('titles', []) + got
        tl.pop('beats', None)
        save_json(p, tl)
        print(f'已写回 {p.name}：beats 展开成 {len(got)} 条 titles')


class _DocA(dict):
    """生成文档时示例里的素材路径写成 A['名字']。"""
    def __missing__(self, k):
        return f"A['{k}']"


def cmd_docs(a):
    cat = json.loads(CATALOG.read_text(encoding='utf-8'))
    T = {t['id']: t for t in cat['techniques']}
    L = ['# 手法库', '', '本文件由 `scripts/library.py docs` 从手法登记表生成，不要手改。',
         f"手法库共 {len(T)} 条手法（17 类），来自 26 个抖音口播剪辑教程和 10 个剪映草稿；"
         + (f"已全部实现（{len(IMPL)} 条按内容搭配、{len(GLOBAL)} 组全片一次选定、{len(FIELDS)} 条写在 timeline 字段里，有几条是同一手法的不同写法）。"
            if not set(T) - set(IMPL) - set(GLOBAL) - set(FIELDS) else
            f"已实现 {len(set(T) & (set(IMPL) | set(GLOBAL) | set(FIELDS)))} 条，其余按批次补。"),
         '', '## 怎么用', '',
         '在 timeline.json 里写 `beats`：每段话标一个内容类型、给出要上屏的字，渲染时代码自动挑手法和变体、对齐口播时刻。',
         '想指定手法写 `"use": "<id>"`，指定变体写 `"variant"`。挑的结果用 `python scripts/library.py arrange timeline.json` 查看。', '',
         '| 内容类型 beat | 意思 |', '|---|---|'] + [f'| `{k}` | {v} |' for k, v in BEATS.items()] + ['', '## 已实现：按内容搭配的手法', '']
    for tid, I in IMPL.items():
        t = T.get(tid, {})
        need = I['demo']
        L += [f"### `{tid}` {t.get('name') or I.get('name', '')}", '', t.get('summary', '') or '（已有版式，见 timeline.md 的 titles）', '',
              f"- 适合：{'、'.join(f'`{x}`' for x in sorted(I['beats'], key=I['beats'].get))}；风格：{'、'.join(I['style'])}；轻重：{I['intensity']}",
              ]
        if I.get('variants'):
            vl = {v.get('key'): v.get('name') for v in t.get('variants', [])}
            L.append('- 变体：' + '；'.join(f"`{v}` {vname(tid, v)}（{'、'.join(tags)}）" for v, tags in I['variants'].items()))
        L += [f"- 示例：`{json.dumps(need, ensure_ascii=False)}`", '']
    L += ['## 已实现：全片一次选定', '']
    for tid, (key, opts) in GLOBAL.items():
        L.append(f"- `{key}`（{T.get(tid, {}).get('name', tid)}）：" + '；'.join(f'`{k}` {v}' for k, v in opts.items()))
    L += ['', '## 已实现：写在 timeline 字段里的手法', '',
          '版式、背景、镜头运动、素材卡样式、开场这类手法不跟一段话的内容走，由 Agent 按画面节奏写进 layout、broll、zoom 或顶层字段；字段细节见 `timeline.md`。'
          '每条的示例是样本册用的时间线片段（0~3.6 秒，`A[...]` 是素材路径）。', '']
    for tid, F in FIELDS.items():
        t = T.get(tid, {})
        L += [f"### `{tid}` {t.get('name', '')}", '', t.get('summary', ''), '', f"- 怎么写：{F['where']}", f"- 风格：{'、'.join(F['style'])}"]
        if F.get('auto'):
            L.append(f"- 自动：{F['auto']}")
        if F['variants']:
            L.append('- 变体：' + '；'.join(f"`{v}` {d}（{'、'.join(tags)}）" for v, (tags, d) in F['variants'].items()))
        if F['demo']:
            demo = F['demo'](_DocA(), next(iter(F['variants']), None))
            demo = {k: v for k, v in demo.items() if not k.startswith('_') and k != 'dur'}
            L += [f"- 示例：`{json.dumps(demo, ensure_ascii=False)}`"]
        L.append('')
    L += ['## 还没实现', '', '按落地批次陆续补齐；没实现的手法不要在 timeline 里写，也不要用别的手法冒充。', '']
    for lib, zh in LIBS.items():
        names = [t['name'] for t in cat['techniques'] if t['library'] == lib and t['id'] not in IMPL and t['id'] not in GLOBAL
                 and t['id'] not in FIELDS and t['tier'] != 'have']
        if names:
            L.append(f'- {zh}：' + '、'.join(names))
    out = HERE.parent / 'references' / 'library.md'
    out.write_text('\n'.join(L) + '\n', encoding='utf-8')
    print(f'已生成 {out}')


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    m = sp.add_parser('menu')
    m.add_argument('--beat')
    m.add_argument('--style', default='premium')
    m.add_argument('--tone', default='web')
    s = sp.add_parser('show')
    s.add_argument('id')
    r = sp.add_parser('arrange')
    r.add_argument('timeline')
    r.add_argument('--write', action='store_true')
    sp.add_parser('docs')
    a = ap.parse_args()
    {'menu': cmd_menu, 'show': cmd_show, 'arrange': cmd_arrange, 'docs': cmd_docs}[a.cmd](a)


if __name__ == '__main__':
    main()
