import os
import sys
import configparser

# 定义默认配置字典，用于初始化
DEFAULT_CONFIG = {
    "General": {
        "scan_path": "./downloads",
        "log_level": "INFO"
    },
    "Network": {
        "timeout": "30",
        "retry_count": "3",
        "proxy": ""
    },
    "Scanner": {
        "video_extensions": ".mp4, .mkv, .avi, .wmv, .iso",
        "min_file_size": "50"
    },
    "Scraper": {
        "source": "tmdb",
        "language": "zh-CN",
        "api_key": ""
    },
    "Output": {
        "download_images": "True",
        "generate_nfo": "True",
        "create_hardlink": "True",
        "library_folder": "Anime_Library",
        "link_path": ""
    },
    "Monitor": {
        "enable_monitor": "False",
        "interval": "300"
    }
}

class ConfigManager:
    '''
    ConfigManager 的 Docstring
    这是一个用于管理应用程序配置的类，旨在简化配置文件的读取和写入操作。
    主要功能包括：
    1. 自动检测配置文件路径，支持打包后的可执行文件和脚本运行环境。
    2. 加载配置文件，如果文件不存在则创建一个包含默认设置的配置文件。
    3. 提供便捷的方法获取不同类型的配置值（字符串、整数、布尔值和列表）。
    4. 支持 UTF-8 编码，确保配置文件中的中文字符正确显示。
    该类通过灵活的设计，方便其他模块轻松访问和管理应用程序的配置选项。
    '''
    def __init__(self, config_filename='config.ini'):
        # [修改] 判断是否是打包后的环境 (Frozen)
        if getattr(sys, 'frozen', False):
            # 如果是 EXE，配置文件路径 = EXE 所在目录
            base_path = os.path.dirname(sys.executable)
        else:
            # 如果是脚本，配置文件路径 = 项目根目录
            # (假设 config.py 在 utils 下，根目录是 utils 的上一级)
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.config_path = os.path.join(base_path, config_filename)
        self.config = configparser.ConfigParser()
        self._load_config()

    def _load_config(self):
        """加载配置，如果文件不存在则创建默认配置"""
        if not os.path.exists(self.config_path):
            print(f"[提示] 配置文件 {self.config_path} 不存在，正在创建默认配置...")
            self._create_default_config()
        
        # 读取文件，支持 UTF-8
        self.config.read(self.config_path, encoding='utf-8')

    def _create_default_config(self):
        """生成默认的 .ini 文件"""
        for section, options in DEFAULT_CONFIG.items():
            self.config[section] = options
        
        with open(self.config_path, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def get(self, section, option, fallback=None):
        """获取字符串类型的配置"""
        return self.config.get(section, option, fallback=fallback)

    def get_int(self, section, option, fallback=0):
        """获取整数类型的配置"""
        return self.config.getint(section, option, fallback=fallback)

    def get_boolean(self, section, option, fallback=False):
        """获取布尔类型的配置"""
        return self.config.getboolean(section, option, fallback=fallback)

    def get_list(self, section, option, delimiter=','):
        """获取列表类型配置 (自动分割字符串)"""
        val = self.config.get(section, option, fallback="")
        return [x.strip() for x in val.split(delimiter) if x.strip()]

# 创建一个单例实例，方便在其他文件中直接导入使用
settings = ConfigManager()