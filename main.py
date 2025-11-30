import os
import sys
import time
from utils.config import settings
from core.scanner import VideoScanner
from core.parser import AnimeParser
from core.scraper import TMDBScraper
from core.saver import DataSaver

def main():
    print("==================================================")
    print("      PyVideoScraper - 自动化番剧刮削工具")
    print("==================================================")

    # 1. 读取配置
    scan_path = settings.get("General", "scan_path")
    extensions = settings.get_list("Scanner", "video_extensions")
    min_size = settings.get_int("Scanner", "min_file_size")
    
    dl_img = settings.get_boolean("Output", "download_images")
    gen_nfo = settings.get_boolean("Output", "generate_nfo")

    # 2. 确认路径
    user_input = input(f"请输入扫描目录 [回车默认: {scan_path}]: ").strip()
    target_folder = user_input if user_input else scan_path

    if not os.path.exists(target_folder):
        print(f"[!] 错误: 路径 '{target_folder}' 不存在")
        sys.exit(1)

    # 3. 初始化各模块
    print("[*] 初始化核心模块...")
    scanner = VideoScanner(extensions, min_size)
    parser = AnimeParser()
    scraper = TMDBScraper()
    saver = DataSaver(download_images=dl_img, generate_nfo=gen_nfo)

    print(f"[*] 开始扫描: {target_folder}")
    print("-" * 50)

    success_count = 0
    fail_count = 0

    # 4. 主循环
    for video in scanner.scan(target_folder):
        print(f"\nProcessing: {video.filename}{video.extension}")
        
        # --- Step 1: 解析文件名 ---
        meta = parser.parse(video.filename)
        if not meta:
            print(f"    [x] Skip: 无法识别文件名格式")
            fail_count += 1
            continue
        
        print(f"    [L] Local: {meta.title} S{meta.season:02d}E{meta.episode:02d}")

        # --- Step 2: 搜索剧集 ID (含缓存) ---
        tv_id = scraper.search_tv_show(meta.title)
        if not tv_id:
            print(f"    [!] Skip: TMDB 未找到剧集 '{meta.title}'")
            fail_count += 1
            continue

        # --- Step 3: 获取单集详情 ---
        ep_data = scraper.get_episode_details(tv_id, meta.season, meta.episode)
        if not ep_data:
            print(f"    [!] Skip: TMDB 未找到 S{meta.season}E{meta.episode} 数据")
            fail_count += 1
            continue

        print(f"    [W] Web: '{ep_data.get('name')}' (Rating: {ep_data.get('vote_average')})")

        # --- Step 4: 保存数据 (NFO & 图片) ---
        saver.save(video, meta, ep_data)
        success_count += 1
        
        # 礼貌性延时，防止 API 限流 (虽然有缓存，但获取单集详情还是会请求网络)
        time.sleep(0.5)

    print("-" * 50)
    print(f"全部完成! 成功: {success_count}, 失败/跳过: {fail_count}")

if __name__ == "__main__":
    main()