import json
from pathlib import Path
from typing import Dict, Optional, Union, TypedDict
from utils.logger import logger

class MappingData(TypedDict, total=False):
    id: int
    season: int
    episode: int  # [新增] 集数

class MappingManager:
    def __init__(self, mapping_file="custom_mapping.json"):
        self.mapping_file = Path(mapping_file)
        self.mappings: Dict[str, Union[int, MappingData]] = {}
        self._load()

    def _load(self):
        if self.mapping_file.exists():
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    self.mappings = json.load(f)
            except Exception as e:
                logger.error(f"加载映射失败: {e}")
                self.mappings = {}

    def save(self):
        try:
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.mappings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存映射失败: {e}")

    def get_data(self, filename: str) -> MappingData:
        """获取映射数据，统一返回字典格式"""
        raw = self.mappings.get(filename)
        if raw is None:
            return {}
        # 兼容旧版
        if isinstance(raw, int):
            return {"id": raw}
        return raw

    def update(self, filename: str, tmdb_id: int = None, season: int = None, episode: int = None):
        """更新映射"""
        current = self.get_data(filename)
        
        if tmdb_id is not None:
            current["id"] = tmdb_id
        if season is not None:
            current["season"] = season
        if episode is not None:
            current["episode"] = episode  # [新增]
            
        self.mappings[filename] = current
        self.save()
        logger.info(f"[Mapping] 更新映射: {filename} -> {current}")