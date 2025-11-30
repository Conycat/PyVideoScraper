import requests
from urllib.parse import quote
from typing import Optional, Dict, Any
from utils.config import settings

class TMDBScraper:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self):
        # 从配置中读取参数
        self.api_key = settings.get("Scraper", "api_key")
        self.language = settings.get("Scraper", "language", fallback="zh-CN")
        self.proxy_str = settings.get("Network", "proxy")
        
        # 配置 requests 的 session (连接池)
        self.session = requests.Session()
        if self.proxy_str:
            self.session.proxies = {
                "http": self.proxy_str,
                "https": self.proxy_str
            }
        
        # 验证 API Key 是否存在
        if not self.api_key:
            print("[!] 警告: config.ini 中未配置 TMDB API Key，网络刮削将无法工作！")
        
        # [新增] 内存缓存: { "Clean Title": 12345 }
        self._id_cache = {}

    def _get(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """通用 GET 请求封装"""
        if not self.api_key:
            return None

        url = f"{self.BASE_URL}{endpoint}"
        default_params = {
            "api_key": self.api_key,
            "language": self.language
        }
        if params:
            default_params.update(params)

        try:
            response = self.session.get(url, params=default_params, timeout=10)
            response.raise_for_status() # 如果状态码不是 200，抛出异常
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[!] 网络请求失败: {e}")
            return None

    def search_tv_show(self, query_title: str) -> Optional[int]:
        """
        搜索番剧/剧集，返回 TMDB ID (带缓存)
        """
        # 1. 查缓存
        if query_title in self._id_cache:
            return self._id_cache[query_title]

        endpoint = "/search/tv"
        params = {"query": query_title}
        
        data = self._get(endpoint, params)
        if data and data.get("results"):
            first_result = data["results"][0]
            tmdb_id = first_result['id']
            name = first_result.get('name')
            
            # 2. 写入缓存
            self._id_cache[query_title] = tmdb_id
            
            print(f"    [Net] 搜索成功: {query_title} -> ID {tmdb_id} ({name})")
            return tmdb_id
        
        print(f"    [Net] 未找到匹配结果: {query_title}")
        return None

    def get_episode_details(self, tv_id: int, season: int, episode: int) -> Optional[Dict]:
        """
        获取单集详情 (标题、简介、剧照路径)
        """
        endpoint = f"/tv/{tv_id}/season/{season}/episode/{episode}"
        data = self._get(endpoint)
        
        if data:
            return {
                "name": data.get("name", ""),
                "overview": data.get("overview", ""),
                "still_path": data.get("still_path", ""), # 剧照
                "air_date": data.get("air_date", ""),
                "vote_average": data.get("vote_average", 0)
            }
        return None

    def get_series_details(self, tv_id: int) -> Optional[Dict]:
        """
        获取剧集层面的详情 (用于获取总封面/背景图)
        """
        endpoint = f"/tv/{tv_id}"
        return self._get(endpoint)