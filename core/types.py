from dataclasses import dataclass
from pathlib import Path

@dataclass
class VideoFile:
    """视频文件数据模型，用于在模块间传递标准数据"""
    path: Path          # 完整路径对象
    filename: str       # 文件名 (不含后缀)
    extension: str      # 后缀名
    size_mb: float      # 文件大小 (MB)

    def __repr__(self):
        return f"<Video: {self.filename}{self.extension} ({self.size_mb}MB)>"
    
@dataclass
class AnimeMeta:
    """番剧元数据模型，存放解析后的信息"""
    title: str          # 清洗后的标题
    season: int         # 季号 (默认为1)
    episode: int        # 集号
    raw_filename: str   # 原始文件名 (用于调试)

    def __repr__(self):
        return f"<Anime: {self.title} S{self.season:02d}E{self.episode:02d}>"