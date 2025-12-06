import os
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict
from .types import VideoFile, AnimeMeta
from utils.logger import logger

class DataSaver:
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w780"

    def __init__(self, download_images: bool = True, generate_nfo: bool = True):
        self.download_images = download_images
        self.generate_nfo = generate_nfo

    def save(self, video: VideoFile, meta: AnimeMeta, tmdb_data: Dict):
        """主保存入口"""
        # 基础路径: /downloads/video.mkv -> /downloads/video
        base_path = video.path.parent / video.path.stem

        if self.generate_nfo:
            self._save_nfo(base_path, meta, tmdb_data)
        
        if self.download_images and tmdb_data.get('still_path'):
            self._save_image(base_path, tmdb_data['still_path'])

    def _save_nfo(self, base_path: Path, meta: AnimeMeta, data: Dict):
        """生成 Kodi/Emby 兼容的 .nfo XML 文件"""
        nfo_path = base_path.with_suffix(".nfo")
        
        root = ET.Element("episodedetails")
        
        # 构建 XML 结构
        ET.SubElement(root, "title").text = data.get('name', meta.title)
        ET.SubElement(root, "showtitle").text = meta.title
        ET.SubElement(root, "season").text = str(meta.season)
        ET.SubElement(root, "episode").text = str(meta.episode)
        ET.SubElement(root, "plot").text = data.get('overview', '')
        ET.SubElement(root, "aired").text = data.get('air_date', '')
        ET.SubElement(root, "rating").text = str(data.get('vote_average', 0))
        
        # 写入文件
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0) # 美化 XML 格式 (Python 3.9+)
        try:
            tree.write(nfo_path, encoding="utf-8", xml_declaration=True)
            logger.info(f"    [Save] NFO 已生成: {nfo_path.name}")
        except Exception as e:
            logger.error(f"    [!] NFO 生成失败: {e}")

    def _save_image(self, base_path: Path, still_path: str):
        """下载单集封面"""
        # 命名规则: 视频名-thumb.jpg (Emby/Kodi 标准)
        image_path = base_path.parent / (base_path.name + "-thumb.jpg")
        
        if image_path.exists():
            return # 已存在则跳过

        url = self.IMAGE_BASE_URL + still_path
        try:
            # 简单下载逻辑
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                with open(image_path, 'wb') as f:
                    f.write(resp.content)
                logger.info(f"    [Save] 封面已下载: {image_path.name}")
        except Exception as e:
            logger.error(f"    [!] 图片下载失败: {e}")

    def save_show_metadata(self, folder_path: Path, show_data: Dict):
        """
        保存剧集层面的元数据 (仅当文件不存在时保存)
        生成: tvshow.nfo, poster.jpg, fanart.jpg
        """
        if not folder_path.is_dir():
            return

        # 1. 保存 tvshow.nfo
        nfo_path = folder_path / "tvshow.nfo"
        if not nfo_path.exists() and self.generate_nfo:
            self._create_tvshow_nfo(nfo_path, show_data)

        # 2. 保存海报 (poster.jpg)
        if self.download_images and show_data.get("poster_path"):
            self._download_asset(folder_path / "poster.jpg", show_data["poster_path"])

        # 3. 保存背景图 (fanart.jpg)
        if self.download_images and show_data.get("backdrop_path"):
            self._download_asset(folder_path / "fanart.jpg", show_data["backdrop_path"])

    def _create_tvshow_nfo(self, path: Path, data: Dict):
        """生成剧集总简介 XML"""
        root = ET.Element("tvshow")
        ET.SubElement(root, "title").text = data.get("name", "")
        ET.SubElement(root, "originaltitle").text = data.get("original_name", "")
        ET.SubElement(root, "plot").text = data.get("overview", "")
        ET.SubElement(root, "premiered").text = data.get("first_air_date", "")
        ET.SubElement(root, "rating").text = str(data.get("vote_average", 0))
        # 这里可以继续加 actor, genre 等信息
        
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        try:
            tree.write(path, encoding="utf-8", xml_declaration=True)
            logger.info(f"    [Series] tvshow.nfo 已生成")
        except Exception as e:
            logger.error(f"    [!] tvshow.nfo 生成失败: {e}")

    def _download_asset(self, save_path: Path, url_suffix: str):
        """通用下载辅助方法"""
        if save_path.exists():
            return # 既然存在就不重复下载了，节省流量
        
        url = self.IMAGE_BASE_URL + url_suffix
        try:
            with self.session.get(url, stream=True, timeout=(5, 30)) as r:
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            logger.info(f"    [Series] 图片已下载: {save_path.name}")
        except Exception:
            pass # 剧集图片下载失败不影响流程，静默失败即可

    def close(self):
        """关闭下载会话，释放资源"""
        try:
            self.session.close()
        except Exception:
            pass
        # 重新初始化 Session 以便下次使用
        self.__init__(self.download_images, self.generate_nfo)