from pathlib import Path
from typing import List, Generator, Set
from .types import VideoFile

class VideoScanner:
    '''
    VideoScanner 的 Docstring
    这是一个用于扫描指定目录下视频文件的类，旨在识别符合条件的动漫视频文件并封装为 VideoFile 对象。
    主要功能包括：
    1. 支持多种视频文件后缀的过滤。
    2. 基于文件大小的过滤，排除过小的无效文件。
    3. 文件锁定检查，避免处理正在被下载或占用的文件。
    4. 使用生成器模式，逐个返回符合条件的 VideoFile 对象，提高内存效率。
    该类适用于需要批量处理视频文件的场景，能够有效提升文件扫描的效率和准确性。
    '''
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
            
            # 简单的文件锁定检查：尝试以追加模式打开
            # 如果文件被 BT 软件独占锁定，这一步会抛出 PermissionError
            with open(file_path, 'a'):
                pass

            return VideoFile(
                path=file_path,
                filename=file_path.stem, #  .stem提取不包含扩展名（后缀名）的文件名部分
                extension=file_path.suffix.lower(), # 包含点号的后缀名，如 '.mp4'
                size_mb=round(size_mb, 2) # 保留两位小数
            )
        except OSError:
            # 处理权限不足或文件被占用等异常
            return None
        except IOError:
            # logger.debug(f"文件可能正在被使用/下载中，跳过: {file_path.name}")
            return None