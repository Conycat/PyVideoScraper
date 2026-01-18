import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, Dict

from utils.config import settings
from utils.logger import log_dir, logger  # [新增] 引入 logger 用于打印启动模式
from core.monitor import MediaMonitor

# 初始化 FastAPI
app = FastAPI(title="PyVideoScraper API", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    # 返回 index.html
    return FileResponse('static/index.html')

# --- [核心修复] 初始化逻辑 ---

# 1. 获取扫描路径 (增加容错，防止 NoneType 错误)
scan_path_str = settings.get("General", "scan_path", fallback="/data")
# 如果配置文件里的 key 存在但值为空字符串，强制设为 /data
if not scan_path_str:
    scan_path_str = "/data"
scan_path = Path(scan_path_str)

# 2. [新增] 获取硬链接路径逻辑 (同步 main.py 的逻辑)
link_str = settings.get("Output", "link_path", fallback="")
lib_folder = settings.get("Output", "library_folder", fallback="Anime_Library")

if link_str:
    # 如果配置了 link_path，使用独立路径
    library_path = Path(link_str)
    logger.info(f"[Server] Mode: 使用独立硬链接目录 -> {library_path}")
else:
    # 否则回退到旧逻辑：在扫描目录下创建子文件夹
    library_path = scan_path / lib_folder
    logger.info(f"[Server] Mode: 使用默认子目录 -> {library_path}")

# 3. 初始化 Monitor
# 这一步非常关键，Monitor 会将正确的 library_path 传给 Linker
monitor = MediaMonitor(scan_path, library_path)


# --- 数据模型 (Pydantic Models) ---
class ConfigUpdate(BaseModel):
    section: str
    key: str
    value: str

class ScanOptions(BaseModel):
    interval: Optional[int] = 300


class IdentifyRequest(BaseModel):
    filename: str
    keyword: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
# --- 1. 配置接口 ---

@app.get("/api/config")
def get_config():
    """读取 config.ini 的所有内容"""
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
        # 可以在这里验证路径是否正确
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
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return {"logs": all_lines[-lines:]}
    except Exception as e:
        return {"logs": [f"Error reading logs: {e}"]}
@app.get("/api/unidentified")
def get_unidentified_files():
    """获取当前未识别的视频文件列表"""
    return {
        "count": len(monitor.unidentified_files),
        "files": monitor.unidentified_files
    }

@app.post("/api/identify")
def manual_identify(req: IdentifyRequest):
    """提交手动识别信息"""
    # 至少要有一个参数被提供
    if not req.keyword and req.season is None and req.episode is None:
         raise HTTPException(status_code=400, detail="未提供任何修正信息")

    success = monitor.manual_identify(req.filename, req.keyword, req.season, req.episode)
    
    if success:
        return {"status": "success", "message": "已保存修正信息"}
    else:
        raise HTTPException(status_code=404, detail=f"无法找到 '{req.keyword}'")
    
# [新增] 获取当季新番
@app.get("/api/seasonal")
def get_seasonal_anime():
    data = monitor.seasonal_manager.get_data()
    return data

# [新增] 强制刷新新番
@app.post("/api/seasonal/refresh")
def refresh_seasonal_anime():
    data = monitor.seasonal_manager.refresh()
    return data
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)