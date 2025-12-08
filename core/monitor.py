import time
import gc
import threading
from pathlib import Path

from utils.logger import logger
from utils.config import settings
from core.scanner import VideoScanner
from core.parser import AnimeParser
from core.scraper import TMDBScraper
from core.saver import DataSaver
from core.linker import FileLinker

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
        
        # 剧集处理记录 (用于单次循环内去重)
        self.processed_shows = set()

        # [新增] 运行状态标记
        self._running = False
        self._thread = None

    def run_once(self):
        """执行一次完整的扫描流程"""
        logger.info(f"--- 开始新一轮扫描: {self.scan_root} ---")
        
        count = 0
        try:
            # 这里的 generator 会按需读取文件，不会一次性把所有文件加载到内存
            for video in self.scanner.scan(self.scan_root):
                try:
                    self._process_single_video(video)
                    count += 1
                except Exception as e:
                    logger.error(f"处理文件出错 {video.filename}: {e}", exc_info=True)
                    # 遇到错误时，显式删除局部变量，帮助释放
                    del video 
        
        finally:
            # [内存优化核心] 无论扫描是否成功，最后都执行清理
            self._cleanup_memory()
        
        logger.info(f"--- 扫描结束，处理文件数: {count} ---")

    def _process_single_video(self, video):
        """处理单个视频的核心逻辑"""
        # 1. 解析
        meta = self.parser.parse(video.filename)
        if not meta:
            return

        # 2. 搜索 (Scraper 内部有缓存，这里会产生内存占用)
        tmdb_info = self.scraper.search_tv_show(meta.title)
        
        official_name = None
        tv_id = None
        if tmdb_info:
            tv_id = tmdb_info['id']
            official_name = tmdb_info['name']

        # 3. 整理
        video = self.linker.run(video, meta, official_name)

        if not tv_id:
            logger.warning(f"TMDB 未找到: {meta.title}")
            return

        # 4. 剧集元数据
        if tv_id not in self.processed_shows:
            if self.linker.enabled:
                show_save_path = video.path.parent.parent
            else:
                show_save_path = video.path.parent
            
            show_data = self.scraper.get_show_details(tv_id)
            if show_data:
                self.saver.save_show_metadata(show_save_path, show_data)
                self.processed_shows.add(tv_id)

        # 5. 单集数据
        ep_data = self.scraper.get_episode_details(tv_id, meta.season, meta.episode)
        if ep_data:
            self.saver.save(video, meta, ep_data)

    def _cleanup_memory(self):
        """[新增] 执行内存清理"""
        logger.info("[System] 正在执行内存回收...")
        
        # 1. 清空本次循环的去重集合 (防止 set 无限增长)
        self.processed_shows.clear()
        
        # 2. 清理 Scraper 的 ID 缓存和 Session
        self.scraper.clear_cache()
        
        # 3. 重置 Saver 的 Session
        self.saver.close()
        
        # 4. 强制执行 Python 垃圾回收
        # 这会清理循环引用和未被引用的对象
        gc_count = gc.collect()
        
        logger.info(f"[System] 内存回收完成，回收对象数: {gc_count}")

    def start_loop(self, interval: int):
        """开启持续监控循环"""
        logger.info(f"启动监控模式，扫描间隔: {interval} 秒")
        try:
            while True:
                self.run_once()
                
                logger.info(f"休眠 {interval} 秒...")
                
                # 休眠期间也可以再次 gc，确保彻底干净
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("用户停止监控")

    def start_background_loop(self, interval: int):
        """[新增] 在后台线程启动监控"""
        if self._running:
            return False
        
        self._running = True
        self._thread = threading.Thread(target=self._loop_logic, args=(interval,), daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """[新增] 停止监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2) # 等待线程结束
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