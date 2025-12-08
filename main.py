import os
import sys
from pathlib import Path
from utils.config import settings
from utils.logger import logger
from core.monitor import MediaMonitor

def main():
    # 读取基础配置
    scan_str = settings.get("General", "scan_path")
    
    # 读取硬链接目标路径
    link_str = settings.get("Output", "link_path", fallback="")
    lib_name = settings.get("Output", "library_folder", fallback="Anime_Library")
    
    monitor_mode = settings.get_boolean("Monitor", "enable_monitor", fallback=False)
    interval = settings.get_int("Monitor", "interval", fallback=300)

    # 确定扫描路径 (Input)
    target_folder = scan_str
    if not target_folder:
         target_folder = input(f"请输入扫描目录: ").strip()
    
    scan_root = Path(target_folder)
    if not scan_root.exists():
        logger.error(f"扫描路径不存在: {scan_root}")
        sys.exit(1)

    # 确定硬链接路径 (Output)
    if link_str:
        # 如果用户指定了绝对路径，直接使用
        library_root = Path(link_str)
        print('1')
    else:
        # 如果没指定，回退到旧逻辑：在扫描目录下创建子文件夹
        library_root = scan_root / lib_name
        print('2')

    logger.info(f"[*] 扫描来源: {scan_root}")
    logger.info(f"[*] 整理目标: {library_root}")

    # 检查是否跨设备 (Cross-Device Check)
    try:
        if not library_root.exists():
            library_root.mkdir(parents=True, exist_ok=True)
            
        # 获取设备 ID
        dev_scan = os.stat(scan_root).st_dev
        dev_lib = os.stat(library_root).st_dev
        
        if dev_scan != dev_lib:
            logger.error("Stop: 扫描目录和硬链接目录不在同一个文件系统/分区！")
            logger.error(f"Scan Dev: {dev_scan}, Link Dev: {dev_lib}")
            logger.error("请调整 Docker 挂载方式，确保它们属于同一个 Volume。")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"路径检查失败: {e}")
        sys.exit(1)

    # 初始化核心控制器
    monitor = MediaMonitor(scan_root, library_root)

    # 根据模式运行
    if monitor_mode:
        monitor.start_loop(interval)
    else:
        monitor.run_once()
        logger.info("单次任务完成")

if __name__ == "__main__":
    main()