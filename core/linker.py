import os
from pathlib import Path

from .types import VideoFile, AnimeMeta
from utils.logger import logger

class FileLinker:
    def __init__(self, target_root: Path, enabled: bool = False):
        self.target_root = target_root
        self.enabled = enabled
        
        if self.enabled and not self.target_root.exists():
            try:
                self.target_root.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass

    def run(self, video: VideoFile, meta: AnimeMeta, tmdb_name: str = None) -> VideoFile:
        """
        创建层级硬链接
        :param tmdb_name: TMDB 返回的官方中文名 (如 "间谍过家家")
        """
        if not self.enabled:
            return video

        # 1. 确定一级目录名 (优先用 TMDB 中文名，否则用解析出的英文/罗马音名)
        series_name_raw = tmdb_name if tmdb_name else meta.title
        
        # 清洗非法字符 (例如 Re:Zero -> Re Zero)
        clean_series_name = self._sanitize(series_name_raw)
        
        # 2. 确定二级目录名
        season_folder_name = f"Season {meta.season:02d}"
        
        # 3. 确定新文件名 (为了保持整洁，这里还是保留英文名或者用官方名看个人喜好)
        # 方案 A: 文件名保留原始解析标题 (Spy x Family - S01E01.mp4) -> 推荐，兼容性好
        # 方案 B: 文件名也改成中文 (间谍过家家 - S01E01.mp4) -> 如果你想要，就把 meta.title 换成 tmdb_name
        
        # 这里仅修改文件夹名为中文，文件名保持标准格式，方便字幕插件匹配
        new_filename = f"{meta.title} - S{meta.season:02d}E{meta.episode:02d}{video.extension}"
        new_filename = self._sanitize(new_filename)

        # 4. 组合路径
        # Anime_Library / 间谍过家家 / Season 01 / Spy x Family - S01E01.mp4
        series_dir = self.target_root / clean_series_name
        season_dir = series_dir / season_folder_name
        target_path = season_dir / new_filename

        # 5. 创建目录
        if not season_dir.exists():
            try:
                season_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.info(f"    [Link] 创建目录失败: {e}")
                return video

        # 6. 执行硬链接
        if target_path.exists():
            video.path = target_path
            video.filename = target_path.stem
            return video

        try:
            os.link(video.path, target_path)
            logger.info(f"    [Link] 整理成功: {clean_series_name}/{season_folder_name}/{new_filename}")
            
            video.path = target_path
            video.filename = target_path.stem
            return video
            
        except OSError as e:
            logger.error(f"    [Link] 失败: {e}")
            return video

    def _sanitize(self, filename: str) -> str:
        return filename.replace(":", " ").replace("/", " ").replace("\\", " ").replace("?", "").replace('"', "").replace("*", "").replace("<", "").replace(">", "").replace("|", "").strip()