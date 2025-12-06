import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logger(name="PyVideoScraper", log_file="scraper.log", level=logging.INFO):
    """
    配置日志系统
    :param log_file: 日志文件路径
    :param level: 日志级别 (INFO, DEBUG, ERROR)
    """
    # 创建 Logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 防止重复添加 Handler
    if logger.handlers:
        return logger

    # 1. 格式化器: [时间] [级别] [模块] 消息
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(module)-10s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 2. 文件处理器 (写入文件，单个最大10MB，保留5个备份)
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # 3. 控制台处理器 (输出到屏幕)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# 初始化一个全局 logger 供其他模块直接导入
# 日志文件保存在项目根目录下的 logs 文件夹
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logger = setup_logger(log_file=log_dir / "scraper.log")