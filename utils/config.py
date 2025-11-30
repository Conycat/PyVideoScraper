import os
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
        "rename_files": "False"
    }
}

class ConfigManager:
    def __init__(self, config_path='config.ini'):
        self.config_path = config_path
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