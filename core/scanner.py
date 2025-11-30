from pathlib import Path
from typing import List, Generator, Set
from .types import VideoFile

class VideoScanner:
    def __init__(self, extensions: List[str], min_size_mb: int):
        """
        初始化扫描器
        :param extensions: 允许的后缀列表，如 ['.mp4', '.mkv']
        :param min_size_mb: 最小文件大小过滤
        """
        # 转为集合 set，查询速度为 O(1)，比列表更快
        self.allowed_extensions: Set[str] = {ext.lower().strip() for ext in extensions}
        self.min_size_mb = min_size_mb

    def scan(self, root_path: str) -> Generator[VideoFile, None, None]:
        """
        扫描指定目录，yield 返回 VideoFile 对象
        """
        root = Path(root_path)
        if not root.exists():
            return

        # rglob('*') 递归查找所有文件
        for file_path in root.rglob("*"):
            if file_path.is_file():
                # 预先检查后缀，不符合的直接跳过，避免不必要的 I/O 操作
                if file_path.suffix.lower() not in self.allowed_extensions:
                    continue
                
                video = self._process_file(file_path)
                if video:
                    yield video

    def _process_file(self, file_path: Path) -> VideoFile | None:
        """验证文件有效性并封装对象"""
        try:
            # 获取文件大小
            size_bytes = file_path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)

            if size_mb < self.min_size_mb:
                return None

            return VideoFile(
                path=file_path,
                filename=file_path.stem,
                extension=file_path.suffix.lower(),
                size_mb=round(size_mb, 2)
            )
        except OSError:
            # 处理权限不足或文件被占用等异常
            return None