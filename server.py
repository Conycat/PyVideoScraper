import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, Dict

from utils.config import settings
from utils.logger import log_dir
from core.monitor import MediaMonitor

# 初始化 FastAPI
app = FastAPI(title="PyVideoScraper API", version="1.0.0")

# 全局 Monitor 实例 (单例模式)
# 注意：这里需要先读取配置来初始化，或者提供一个接口让前端传入路径初始化
# 为简化演示，我们这里读取默认配置
scan_path = Path(settings.get("General", "scan_path"))
lib_folder = settings.get("Output", "library_folder", fallback="Anime_Library")
library_path = scan_path / lib_folder

monitor = MediaMonitor(scan_path, library_path)

# --- 数据模型 (Pydantic Models) ---
class ConfigUpdate(BaseModel):
    section: str
    key: str
    value: str

class ScanOptions(BaseModel):
    interval: Optional[int] = 300

# --- 1. 配置接口 ---

@app.get("/api/config")
def get_config():
    """读取 config.ini 的所有内容"""
    # configparser 对象不能直接转 JSON，需要手动转换
    conf_dict = {}
    for section in settings.config.sections():
        conf_dict[section] = dict(settings.config[section])
    return conf_dict

@app.post("/api/config")
def update_config(data: ConfigUpdate):
    """修改配置"""
    try:
        # 修改内存中的配置
        settings.config.set(data.section, data.key, data.value)
        # 写入文件
        with open(settings.config_path, 'w', encoding='utf-8') as f:
            settings.config.write(f)
        return {"status": "success", "message": f"Updated {data.section}.{data.key}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- 2. 控制接口 ---

@app.get("/api/status")
def get_status():
    """获取当前是否在运行"""
    return {
        "running": monitor._running,
        "scan_path": str(monitor.scan_root),
        "library_path": str(monitor.library_root)
    }

@app.post("/api/scan/start")
def start_scan(opts: ScanOptions):
    """启动后台监控"""
    if monitor._running:
        return {"status": "warning", "message": "Already running"}
    
    monitor.start_background_loop(opts.interval)
    return {"status": "success", "message": "Monitor started"}

@app.post("/api/scan/stop")
def stop_scan():
    """停止后台监控"""
    monitor.stop()
    return {"status": "success", "message": "Monitor stopping..."}

@app.post("/api/scan/once")
def run_once(background_tasks: BackgroundTasks):
    """触发单次扫描 (异步执行)"""
    if monitor._running:
        raise HTTPException(status_code=400, detail="Monitor is already running. Please stop it first.")
    
    # 使用 FastAPI 的后台任务，立即返回响应，然后在后台跑
    background_tasks.add_task(monitor.run_once)
    return {"status": "success", "message": "One-time scan triggered"}

# --- 3. 日志接口 ---

@app.get("/api/logs")
def get_logs(lines: int = 50):
    """读取日志文件的最后 N 行"""
    log_file = log_dir / "scraper.log"
    if not log_file.exists():
        return {"logs": []}
    
    try:
        # 简单的读取最后 N 行的逻辑
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return {"logs": all_lines[-lines:]}
    except Exception as e:
        return {"logs": [f"Error reading logs: {e}"]}

if __name__ == "__main__":
    # 启动 API 服务，默认端口 8000
    # 前端访问 http://localhost:8000/docs 可以看到自动生成的接口文档
    uvicorn.run(app, host="0.0.0.0", port=8000)