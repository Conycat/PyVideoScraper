import sys
from pathlib import Path
from utils.config import settings
from utils.logger import logger
from core.monitor import MediaMonitor

def main():
    # 1. 读取基础配置
    scan_str = settings.get("General", "scan_path")
    lib_name = settings.get("Output", "library_folder", fallback="Anime_Library")
    
    # 读取监控配置
    monitor_mode = settings.get_boolean("Monitor", "enable_monitor", fallback=False)
    interval = settings.get_int("Monitor", "interval", fallback=300)

    # 2. 交互式路径输入 (仅在非监控模式或首次启动时询问)
    # 为了方便自动化部署，如果 scan_path 已经配置且有效，可以跳过输入
    target_folder = scan_str
    if not target_folder or not Path(target_folder).exists():
         user_input = input(f"请输入扫描目录: ").strip()
         target_folder = user_input
    
    scan_root = Path(target_folder)
    if not scan_root.exists():
        logger.error(f"路径不存在: {scan_root}")
        sys.exit(1)

    library_root = scan_root / lib_name

    # 3. 初始化核心控制器
    monitor = MediaMonitor(scan_root, library_root)

    # 4. 根据模式运行
    if monitor_mode:
        # --- 模式 A: 持续监控 ---
        monitor.start_loop(interval)
    else:
        # --- 模式 B: 单次运行 ---
        monitor.run_once()
        logger.info("单次任务完成")

if __name__ == "__main__":
    main()