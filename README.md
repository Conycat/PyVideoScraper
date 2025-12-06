# PyVideoScraper - 自动化番剧刮削与整理工具

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**PyVideoScraper** 是一个轻量级、模块化且高效的本地视频文件刮削与整理工具。专门针对番剧（Anime）设计，支持从文件名智能解析元数据，自动获取 TMDB 信息，生成 NFO 文件，并通过**硬链接**（Hard Link）构建完美的媒体库目录结构，无缝对接 Emby、Plex、Kodi 等媒体服务器。

---

## ✨ 核心特性

- 🧠 **智能文件名解析**：基于多层级正则策略，精准识别 `[字幕组] 标题 - 集数`、`S01E01` 等多种命名格式。
- 🎬 **TMDB 数据刮削**：自动搜索 TMDB 获取官方中文标题、简介、评分、发行日期等元数据。
- 🖼️ **精美海报墙**：自动下载剧集海报（Poster）、背景图（Fanart）及单集封面（Thumbnail）。
- 📝 **NFO 生成器**：生成标准的 `.nfo` 文件，让媒体服务器秒识别，无需二次刮削。
- 🔗 **硬链接整理 (Hard Link)**：
  - **不占用额外磁盘空间**：整理后的文件只是原文件的别名。
  - **保种友好**：不修改原始文件名，完全不影响 PT/BT 做种。
  - **自动化归档**：自动创建 `媒体库 -> 中文剧集名 -> Season XX` 的标准目录结构。
- 👁️ **持续监控模式**：支持后台驻留，自动检测下载目录的新增文件并实时整理。
- 🚀 **内存优化**：内置自动垃圾回收与缓存清理机制，适合在 NAS 或低配置 VPS 上长期运行。

---

## 🛠️ 安装指南

### 1. 克隆项目
```bash
git clone https://github.com/yourusername/PyVideoScraper.git
cd PyVideoScraper
