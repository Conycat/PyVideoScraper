import time
import gc
import threading
from pathlib import Path
from typing import List, Dict, Optional

from utils.logger import logger
from utils.config import settings
from core.scanner import VideoScanner
from core.parser import AnimeParser
from core.scraper import TMDBScraper
from core.saver import DataSaver
from core.linker import FileLinker
from core.mapping import MappingManager
from core.seasonal import SeasonalManager

class MediaMonitor:
    def __init__(self, scan_root: Path, library_root: Path):
        self.scan_root = scan_root
        self.library_root = library_root
        
        # 读取配置
        extensions = settings.get_list("Scanner", "video_extensions")
        min_size = settings.get_int("Scanner", "min_file_size")
        dl_img = settings.get_boolean("Output", "download_images")
        gen_nfo = settings.get_boolean("Output", "generate_nfo")
        do_link = settings.get_boolean("Output", "create_hardlink")

        # 初始化各组件
        self.scanner = VideoScanner(extensions, min_size)
        self.parser = AnimeParser()
        self.scraper = TMDBScraper()
        self.saver = DataSaver(download_images=dl_img, generate_nfo=gen_nfo)
        self.linker = FileLinker(target_root=library_root, enabled=do_link)
        self.mapping_manager = MappingManager()
        self.seasonal_manager = SeasonalManager(self.scraper)
        
        # 运行状态控制
        self._running = False
        self._thread = None
        
        # 运行时缓存
        self.processed_shows = set()
        
        # [核心修复] 这里必须初始化未识别列表，否则后面 clear() 会报错
        # 格式: {"filename": "video", "path": "...", "parsed_title": "...", "reason": "..."}
        self.unidentified_files: List[Dict] = []

    def run_once(self):
        """执行一次完整的扫描流程"""
        logger.info(f"--- 开始新一轮扫描: {self.scan_root} ---")
        
        # 每次扫描前清空列表，重新评估
        self.unidentified_files.clear()
        
        count = 0
        try:
            for video in self.scanner.scan(self.scan_root):
                try:
                    self._process_single_video(video)
                    count += 1
                except Exception as e:
                    logger.error(f"处理文件出错 {video.filename}: {e}", exc_info=True)
                    # 显式释放对象
                    del video 
        finally:
            self._cleanup_memory()
        
        logger.info(f"--- 扫描结束，处理: {count}，未识别: {len(self.unidentified_files)} ---")

    def _process_single_video(self, video):
        """处理单个视频的核心逻辑"""
        meta = self.parser.parse(video.filename)
        if not meta:
            return

        tv_id = None
        official_name = None
        
        # [核心修改] 获取手动映射数据
        map_data = self.mapping_manager.get_data(video.filename)
        manual_id = map_data.get("id")
        manual_season = map_data.get("season")
        manual_episode = map_data.get("episode") # [新增]

        # 1. 确定季数和集数 (优先使用手动值)
        target_season = manual_season if manual_season is not None else meta.season
        target_episode = manual_episode if manual_episode is not None else meta.episode
        
        if manual_season is not None or manual_episode is not None:
            logger.info(f"    [Map] 强制覆写: S{target_season}E{target_episode}")

        # 2. 确定 TV ID
        if manual_id:
            logger.info(f"    [Map] 命中手动ID: {manual_id}")
            tv_id = manual_id
            show_details = self.scraper.get_show_details(tv_id)
            if show_details:
                official_name = show_details.get("name")
        else:
            # 自动搜索
            tmdb_info = self.scraper.search_tv_show(meta.title)
            if tmdb_info:
                tv_id = tmdb_info['id']
                official_name = tmdb_info['name']

        if not tv_id:
            logger.warning(f"未找到剧集: {meta.title}")
            self._add_to_unidentified(video, meta.title, "剧集未找到 (Series Not Found)")
            return

        # 3. 整理 (Linker)
        # 临时修改 meta 对象以便生成正确的文件名
        meta.season = target_season
        meta.episode = target_episode # [新增]
        
        video = self.linker.run(video, meta, official_name)

        # 4. 剧集元数据
        if tv_id not in self.processed_shows:
            show_save_path = video.path.parent.parent if self.linker.enabled else video.path.parent
            show_data = self.scraper.get_show_details(tv_id)
            if show_data:
                self.saver.save_show_metadata(show_save_path, show_data)
                self.processed_shows.add(tv_id)

        # 5. 单集数据 (使用 target_season 和 target_episode)
        ep_data = self.scraper.get_episode_details(tv_id, target_season, target_episode)
        
        if not ep_data:
            logger.warning(f"单集缺失: {official_name} S{target_season}E{target_episode}")
            self._add_to_unidentified(video, meta.title, f"单集缺失 (S{target_season}E{target_episode} Missing)")
            return

        self.saver.save(video, meta, ep_data)

    def _add_to_unidentified(self, video, parsed_title, reason):
        """封装添加未识别列表的逻辑"""
        # 避免重复添加
        for f in self.unidentified_files:
            if f['filename'] == video.filename:
                return
        
        self.unidentified_files.append({
            "filename": video.filename,
            "full_name": f"{video.filename}{video.extension}",
            "path": str(video.path),
            "parsed_title": parsed_title,
            "reason": reason
        })

    def manual_identify(self, filename: str, keyword: str = None, season: int = None, episode: int = None) -> bool:
        """
        处理用户手动识别请求
        """
        logger.info(f"[API] 手动修正: {filename} -> ID:{keyword}, S{season}E{episode}")
        
        final_id = None
        
        # 如果用户输入了 keyword
        if keyword:
            if str(keyword).isdigit():
                final_id = int(keyword)
            else:
                search_res = self.scraper.search_tv_show(keyword)
                if search_res:
                    final_id = search_res['id']
                else:
                    return False 

        # 更新映射
        self.mapping_manager.update(filename, tmdb_id=final_id, season=season, episode=episode)
        
        # UI 反馈
        self.unidentified_files = [f for f in self.unidentified_files if f['filename'] != filename]
        
        return True
    
    def _cleanup_memory(self):
        """执行内存清理"""
        logger.info("[System] 正在执行内存回收...")
        self.processed_shows.clear()
        self.scraper.clear_cache()
        self.saver.close()
        gc_count = gc.collect()
        logger.info(f"[System] 内存回收完成，回收对象数: {gc_count}")

    # --- 后台线程控制 ---

    def start_background_loop(self, interval: int):
        """在后台线程启动监控"""
        if self._running:
            return False
        
        self._running = True
        self._thread = threading.Thread(target=self._loop_logic, args=(interval,), daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """停止监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _loop_logic(self, interval: int):
        """内部循环逻辑"""
        logger.info(f"启动监控模式，扫描间隔: {interval} 秒")
        while self._running:
            self.run_once()
            
            # 分段休眠，以便能快速响应 stop 指令
            for _ in range(interval):
                if not self._running: break
                time.sleep(1)