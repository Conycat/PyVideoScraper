import json
import time
from pathlib import Path
from typing import Dict, List
from utils.logger import logger
from core.scraper import TMDBScraper

class SeasonalManager:
    def __init__(self, scraper: TMDBScraper):
        self.scraper = scraper
        self.cache_file = Path("seasonal_cache.json")
        self.cache_data = {"updated_at": 0, "list": []}
        self._load()

    def _load(self):
        """加载本地缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache_data = json.load(f)
            except Exception as e:
                logger.error(f"加载新番缓存失败: {e}")

    def save(self):
        """保存缓存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存新番缓存失败: {e}")

    def refresh(self):
        """强制从 TMDB 获取最新数据 (获取前2页，约40部热门)"""
        logger.info("[Seasonal] 开始刷新当季新番列表...")
        all_results = []
        
        # 获取第 1 页
        data1 = self.scraper.get_current_season_anime(page=1)
        if data1 and 'results' in data1:
            all_results.extend(data1['results'])
        
        # 获取第 2 页 (可选，为了数据更多)
        if data1.get('total_pages', 0) > 1:
            time.sleep(0.5) # 礼貌延时
            data2 = self.scraper.get_current_season_anime(page=2)
            if data2 and 'results' in data2:
                all_results.extend(data2['results'])

        # 简化数据结构，只存需要的字段
        simplified_list = []
        for item in all_results:
            simplified_list.append({
                "id": item.get('id'),
                "name": item.get('name'),
                "original_name": item.get('original_name'),
                "overview": item.get('overview'),
                "poster_path": item.get('poster_path'),
                "backdrop_path": item.get('backdrop_path'),
                "first_air_date": item.get('first_air_date'),
                "vote_average": item.get('vote_average')
            })

        self.cache_data = {
            "updated_at": time.time(),
            "list": simplified_list
        }
        self.save()
        logger.info(f"[Seasonal] 刷新完成，共获取 {len(simplified_list)} 部番剧")
        return self.cache_data

    def get_data(self):
        """获取数据 (如果缓存不存在则自动刷新)"""
        if not self.cache_data.get("list"):
            return self.refresh()
        return self.cache_data