<div align="right">
  <strong>Languages:</strong>
  <a href="#english-version">English</a> |
  <a href="#简体中文版本">简体中文</a>
</div>


<h2 id="english-version">dyDouYinDownloadConvertMp3 (English) </h2>

A lightweight Douyin (TikTok China) video/audio parsing and downloading tool with a graphical user interface (GUI).
**Core Highlight: No Cookie configuration required, no yt-dlp needed, supports direct MP3 extraction or original video download.**

### ✨ Features
* **Zero-config parsing:** Direct paste Douyin share link/text, automatically extracts watermark-free resources.
* **Visual operation:** Simple UI built with `Tkinter`, featuring intuitive progress bars and status prompts.
* **Online preview:** Built-in `pygame` player, allows online playback and seeking before downloading.
* **Smart format handling:** * If the original video has a standalone audio track, directly downloads MP3.
  * If the video has mixed audio, automatically calls `ffmpeg` to extract audio (requires local FFmpeg installation).
* **Auto-dependency installation:** First run auto-detects and installs missing Python libraries.

### 🛠️ Prerequisites
* **Python:** 3.x and above.
* **FFmpeg (Optional):** Required only if you need to force extract MP3 from MP4 video streams. Ensure `ffmpeg` is added to your system environment variables.

### 🚀 Quick Start
1. **Clone the repository:**
   ```bash
   git clone [https://github.com/teosam89/dyDouYinDownloadConvertMp3.git](https://github.com/teosam89/dyDouYinDownloadConvertMp3.git)
   cd dyDouYinDownloadConvertMp3

2. **Bash**

   python douyin_mp3.py

4. **Usage**

   Paste the Douyin share link, click "🔍 侦测资源" (Detect Resource). Once parsed, you can preview or download the MP3.

# Disclaimer
This project is for educational and personal research purposes only. Please do not use it for commercial purposes. The copyright of the downloaded media belongs to the original platform and authors.

# License
This project is licensed under the MIT License.

<h2 id="简体中文版本">dyDouYinDownloadConvertMp3 (简体中文) </h2>
一个轻量级的抖音视频/音频解析与下载工具，带可视化图形界面（GUI）。

**核心亮点：无需配置 Cookie、无需 yt-dlp，支持直接提取 MP3 或下载原视频。**

## 核心特性
* **零配置解析：** 直接粘贴抖音分享链接或文本，自动提取并解析无水印资源。
* **可视化操作：** 基于 `Tkinter` 构建的简洁 UI，支持直观的进度条和状态提示。
* **在线试听：** 内置 `pygame` 播放器，下载前可直接在线播放和拖动进度条。
* **智能格式处理：** * 如果原视频有独立原生音频，直接极速下载 MP3。
    * 如果是视频混合原声，支持自动调用 `ffmpeg` 提取音频（需本地已安装 FFmpeg）。
* **自动依赖安装：** 首次运行会自动检测并补充缺失的 Python 库。

## 运行环境与依赖
* **Python:** 3.x 及以上版本
* **FFmpeg (可选):** 如果需要从 MP4 视频流中强制提取 MP3，系统需配置好 `ffmpeg` 环境变量。

## 快速开始
1. **克隆仓库到本地：**
   ```bash
   git clone [https://github.com/teosam89/dyDouYinDownloadConvertMp3.git](https://github.com/teosam89/dyDouYinDownloadConvertMp3.git)
   cd dyDouYinDownloadConvertMp3

2. **Bash**

   python douyin_mp3.py

4. **使用说明：**

   在输入框粘贴抖音分享链接（例如：https://v.douyin.com/xxxx/）。

   点击 “侦测资源”。
   
   解析成功后，可点击 “▶ 在线试听” 或 “⬇ 立即下载 MP3”，文件默认将保存至系统的 Downloads 文件夹。

# 免责声明
本项目仅供学习编程技术及个人研究使用，请勿用于任何商业用途。下载的音视频版权归原平台及原作者所有。请合理、合法地使用本工具，因滥用导致的任何责任由使用者自行承担。

# 许可证
本项目采用 MIT License 开源协议。
