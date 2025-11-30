import os
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict
from .types import VideoFile, AnimeMeta

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
            print(f"    [Save] NFO 已生成: {nfo_path.name}")
        except Exception as e:
            print(f"    [!] NFO 生成失败: {e}")

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
                print(f"    [Save] 封面已下载: {image_path.name}")
        except Exception as e:
            print(f"    [!] 图片下载失败: {e}")