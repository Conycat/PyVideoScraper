import re
from typing import Optional
from .types import AnimeMeta

class AnimeParser:
    '''
    AnimeParser 的 Docstring
    这是一个用于解析文件名的类，旨在从复杂多变的命名格式中提取出的标题、季数和集数等关键信息。
    该类采用多种正则表达式策略，逐步尝试匹配不同的命名风格，以提高解析的准确性和鲁棒性。
    主要功能包括：
    1. 预处理文件名，统一括号格式。
    2. 依次应用多种正则表达式策略，提取标题、季数和集数。
    3. 深度清洗标题，去除多余信息，如季数关键词、年份和组名等。
    4. 提供季数补救机制，从标题文本中挖掘季数信息，确保解析的完整性。
    该类适用于各种复杂的文件命名格式，能够有效提升元数据的提取效率和准确性。
    '''

    def __init__(self):
        # --- 预处理正则 ---
        self.re_replace_brackets = re.compile(r'【|】')

        # --- 核心提取策略 ---
        
        # 策略 1: Standard Dash
        self.re_strategy_dash = re.compile(
            r'^.*?\]\s*(?P<title>.+?)\s*(?:-|–)\s*(?:S(?P<season>\d{1,2})\s*(?:-|–)?\s*)?(?P<episode>\d{1,4}(?:\.\d)?)(?:v\d)?(?:\s|\[|\(|$)',
            re.IGNORECASE
        )

        # 策略 2: SxxExx
        self.re_strategy_se = re.compile(
            r'(?P<title>.*?)[\s\.]S(?P<season>\d{1,2})E(?P<episode>\d{1,3})',
            re.IGNORECASE
        )

        # 策略 3: Brackets (优化版)
        # 针对 [Group][Title][Season?][Episode]
        # 现在 season_raw 可以匹配 S2 或 Season 2 或 2nd Season
        self.re_strategy_brackets = re.compile(
            r'^\[(?P<group>[^\]]+)\]\[(?P<title>[^\]]+)\](?:\[(?P<season_raw>S\d+|Season\s*\d+|part\s*\d+|[^\]]*?Season)\])?\[(?P<episode>\d{1,3})\]',
            re.IGNORECASE
        )

        # 策略 4: Simple
        self.re_strategy_simple = re.compile(
            r'(?P<title>.+?)\s+(?P<episode>\d{1,3})(?:v\d)?(?:\.mp4|\.mkv)$',
            re.IGNORECASE
        )
        
        # --- 季数补救正则 ---
        # 用于从标题中提取 "Season 3", "2nd Season", "S3"
        self.re_season_text = re.compile(r'(?i)(?:season|part)\s*(\d{1,2})|S(\d{1,2})\b|(\d{1,2})(?:nd|rd|th)\s+season')

        # --- 清洗正则 ---
        # 清洗标题中的季数关键词，防止干扰 TMDB 搜索
        self.re_clean_season = re.compile(r'(?i)\s+(?:2nd|3rd|4th|final|first)?\s*(?:season|part)\s*\d*|\s+S\d+\b')

    def parse(self, filename: str) -> Optional[AnimeMeta]:
        # 1. 预处理
        filename = self.re_replace_brackets.sub(lambda x: '[' if x.group() == '【' else ']', filename)
        
        # 2. 依次尝试策略
        match = None
        if not match: match = self.re_strategy_dash.search(filename)
        if not match: match = self.re_strategy_se.search(filename)
        if not match: match = self.re_strategy_brackets.search(filename)
        if not match: match = self.re_strategy_simple.search(filename)

        if not match:
            return None

        # 3. 提取基础数据
        data = match.groupdict()
        raw_title = data.get('title', '').strip()
        
        # --- 季数提取逻辑 (核心修复) ---
        season = 1
        
        # A. 优先查看正则是否直接捕获了 season 组
        if data.get('season'):
            season = int(data['season'])
            
        # B. 查看 bracket 策略中的 season_raw (处理 [S2] 或 [Season 2])
        elif data.get('season_raw'):
            s_raw = data['season_raw'].lower()
            # 提取数字
            nums = re.findall(r'\d+', s_raw)
            if nums:
                season = int(nums[0])

        # C. 如果以上都没找到，从标题文本中“深挖”季数
        # 例如: raw_title = "Spy x Family Season 3"
        if season == 1:
            extracted_season = self._extract_season_from_text(raw_title)
            if extracted_season:
                season = extracted_season

        # 处理集数
        episode_val = data.get('episode')
        episode = float(episode_val) if episode_val else 0.0

        # 4. 深度清洗标题
        # 此时已经提取完季数，可以安全地把 "Season 3" 从标题里删掉了
        clean_title = self._clean_title(raw_title)

        return AnimeMeta(
            title=clean_title,
            season=season,
            episode=int(episode),
            raw_filename=filename
        )

    def _extract_season_from_text(self, text: str) -> Optional[int]:
        """从标题文本中识别季数"""
        # 匹配 "Season 3", "Part 2", "2nd Season"
        match = self.re_season_text.search(text)
        if match:
            # re_season_text 有 3 个分组，看哪个命中了
            # 1: season/part (\d)
            # 2: S(\d)
            # 3: (\d)nd season
            for g in match.groups():
                if g:
                    return int(g)
        return None

    def _clean_title(self, text: str) -> str:
        """清洗标题"""
        # 去除首尾方括号部分 (Group Name)
        text = re.sub(r'^\[.*?\]\s*', '', text)
        
        # 去除季数信息
        text = self.re_clean_season.sub('', text)
        
        # 去除年份 (2025)
        text = re.sub(r'\s\(\d{4}\)', '', text)

        # 处理双语标题 (取下划线后半部分，如果是纯英文)
        if '_' in text:
            parts = text.split('_')
            if len(parts) > 1 and all(ord(c) < 128 for c in parts[-1].strip().replace(' ', '')):
                text = parts[-1]
            else:
                text = parts[0]
        
        return text.strip()