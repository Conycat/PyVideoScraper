import requests
import datetime

from urllib.parse import quote
from typing import Optional, Dict, Any

from utils.config import settings
from utils.logger import logger

class TMDBScraper:
    '''
    TMDBScraper 的 Docstring
    这是一个用于与 TMDB (The Movie Database) API 交互的类，旨在为动漫视频文件获取准确的元数据。
    主要功能包括：
    1. 搜索番剧，返回对应的 TMDB ID 和官方名称。
    2. 获取单集详情，包括标题、简介和剧照路径。
    3. 获取剧集层面的详情，用于生成 tvshow.nfo 和下载总海报。
    4. 内存缓存机制，减少重复的网络请求，提高效率。
    5. 错误处理和日志记录，确保在网络请求失败时提供有用的信息。
    该类通过灵活的配置选项，允许用户设置 API Key、语言和代理，以满足不同的使用需求。
    '''
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
            logger.error("[!] 警告: config.ini 中未配置 TMDB API Key，网络刮削将无法工作！")
        
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
            logger.error(f"[!] 网络请求失败: {e}")
            return None

    def search_tv_show(self, query_title: str) -> Optional[Dict]:
        """
        搜索番剧，返回 ID 和 官方名称
        返回: {'id': 12345, 'name': '间谍过家家'}
        """
        # 1. 查缓存 (缓存存的是完整的 dict info)
        if query_title in self._id_cache:
            return self._id_cache[query_title]

        endpoint = "/search/tv"
        params = {"query": query_title}
        
        data = self._get(endpoint, params)
        if data and data.get("results"):
            first_result = data["results"][0]
            
            result_info = {
                'id': first_result['id'],
                'name': first_result.get('name') # 这里获取到的就是根据 language=zh-CN 设置的中文名
            }
            
            # 2. 写入缓存
            self._id_cache[query_title] = result_info
            
            logger.info(f"    [Net] 搜索成功: {query_title} -> {result_info['name']} (ID: {result_info['id']})")
            return result_info
        
        logger.info(f"    [Net] 未找到匹配结果: {query_title}")
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
    
    def get_show_details(self, tv_id: int) -> Optional[Dict]:
        """
        获取剧集层面的详情 (用于生成 tvshow.nfo 和下载总海报)
        """
        endpoint = f"/tv/{tv_id}"
        # append_to_response=images 可以一次性把图片地址也拿回来
        params = {"append_to_response": "images"} 
        
        data = self._get(endpoint, params)
        if not data:
            return None

        # 提取海报和背景图
        poster_path = data.get("poster_path")
        backdrop_path = data.get("backdrop_path")
        
        # 也可以从 images 字段里找评分最高的图片，这里简单起见直接用默认的
        return {
            "name": data.get("name"),
            "original_name": data.get("original_name"),
            "overview": data.get("overview"),
            "first_air_date": data.get("first_air_date"),
            "vote_average": data.get("vote_average"),
            "poster_path": poster_path,
            "backdrop_path": backdrop_path,
            "id": data.get("id")
        }
    
    def clear_cache(self):
        """
        [内存优化] 清理内部缓存，重置网络会话
        """
        # 1. 清空 ID 搜索缓存 (防止无限增长)
        cache_size = len(self._id_cache)
        self._id_cache.clear()
        
        # 2. 关闭旧的 Session (释放底层连接池占用的 socket 资源)
        try:
            self.session.close()
        except Exception:
            pass

        # 3. 重建一个新的 Session (保持配置不变)
        self.session = requests.Session()
        if self.proxy_str:
            self.session.proxies = {
                "http": self.proxy_str,
                "https": self.proxy_str
            }
        # 重新应用之前的 Session 设置 (如下载图片时的 verify=False 等)
        # 注意：如果你在 Saver 里也用了 Session，Saver 也需要类似的逻辑
        
        logger.info(f"    [System] 内存释放: 已清理 {cache_size} 条缓存并重置网络连接")

    def get_current_season_anime(self, page: int = 1) -> Dict:
        """
        获取当季新番列表
        返回 TMDB API 的原始响应数据
        参考: https://developers.themoviedb.org/3/discover/tv-discover
        逻辑: 根据当前日期计算季度起止日期，筛选出首播日期在该范围内的动画番剧
        过滤条件:
        - 类型: 动画 (with_genres=16)
        - 语言: 日语 (with_original_language=ja)
        - 排序: 按热度排序 (sort_by=popularity.desc)
        - 分页: 支持分页查询 (page 参数)
        备注: 该方法适用于获取当前季度的热门新番列表，方便用户了解最新的动漫作品。
        """
        today = datetime.date.today()
        year = today.year
        month = today.month

        # 1. 计算当前季度的起止日期
        # Q1: 1-3月, Q2: 4-6月, Q3: 7-9月, Q4: 10-12月
        if 1 <= month <= 3:
            start_date = f"{year}-01-01"
            end_date = f"{year}-03-31"
        elif 4 <= month <= 6:
            start_date = f"{year}-04-01"
            end_date = f"{year}-06-30"
        elif 7 <= month <= 9:
            start_date = f"{year}-07-01"
            end_date = f"{year}-09-30"
        else:
            start_date = f"{year}-10-01"
            end_date = f"{year}-12-31"

        endpoint = "/discover/tv"
        params = {
            "api_key": self.api_key,
            "language": self.language,
            "sort_by": "popularity.desc",       # 按热度排序
            "first_air_date.gte": start_date,   # 首播日期 >= 季度开始
            "first_air_date.lte": end_date,     # 首播日期 <= 季度结束
            "with_genres": "16",                # 16 = 动画 (Animation)
            "with_original_language": "ja",     # 原声语言 = 日语 (过滤掉欧美动画)
            "page": page,
            "include_null_first_air_dates": "false"
        }

        data = self._get(endpoint, params)
        if data:
            print(f"    [Net] 获取当季新番成功: {start_date} ~ {end_date}")
            return data
        return {"results": []}