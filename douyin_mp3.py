import sys, os, re, threading, shutil, tempfile, subprocess, json, urllib.parse

for _pkg, _mod in [("requests","requests"), ("pygame","pygame")]:
    try:
        __import__(_mod)
    except ImportError:
        subprocess.check_call(
            [sys.executable,"-m","pip","install",_pkg,"-q","--break-system-packages"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

import tkinter as tk
from tkinter import ttk, filedialog
import requests, pygame

try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
except Exception:
    pass

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.0 Mobile/15E148 Safari/604.1"
    ),
    "Referer": "https://www.douyin.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

def extract_short_url(text):
    for pat in [
        r'https?://v\.douyin\.com/[A-Za-z0-9/_?=&%.+\-]+',
        r'https?://www\.douyin\.com/video/\d+',
        r'https?://vm\.tiktok\.com/[A-Za-z0-9]+',
    ]:
        m = re.search(pat, text)
        if m:
            return m.group(0).rstrip('.,!?，。！？ ')
    return None


def resolve_video_id(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        all_urls = ([r.headers.get("Location", "") for r in resp.history]
                    + [resp.url])
        print("[DEBUG] 重定向链:", all_urls)
        for u in all_urls:
            m = re.search(r'/video/(\d{10,})', u)
            if m:
                print("[DEBUG] 视频ID:", m.group(1))
                return m.group(1)
    except Exception as e:
        print("[DEBUG] resolve_video_id 异常:", e)
    return None


def _find_nested(obj, keys):
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and obj[k]:
                return obj[k]
        for v in obj.values():
            r = _find_nested(v, keys)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_nested(v, keys)
            if r is not None:
                return r
    return None


def fetch_douyin_info(video_id):
    api_attempts = [
        (
            "https://www.iesdouyin.com/aweme/v1/web/aweme/detail/"
            "?aweme_id={}&aid=1128&version_name=23.5.0&device_platform=android".format(video_id),
            lambda d: d.get("aweme_detail")
        ),
        (
            "https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/"
            "?reflow_source=reflow_page&item_ids={}".format(video_id),
            lambda d: (d.get("item_list") or [None])[0]
        ),
        (
            "https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/"
            "?item_ids={}".format(video_id),
            lambda d: (d.get("item_list") or [None])[0]
        ),
    ]
    for api_url, extractor in api_attempts:
        try:
            print("[DEBUG] 尝试 API:", api_url[:80])
            resp = requests.get(api_url, headers=HEADERS, timeout=12)
            if resp.text.strip():
                data = resp.json()
                print("[DEBUG] 返回 keys:", list(data.keys()) if isinstance(data, dict) else type(data))
                item = extractor(data)
                if item and isinstance(item, dict) and item.get("aweme_id"):
                    print("[DEBUG] API 成功:", item.get("aweme_id"))
                    return item
                else:
                    print("[DEBUG] 无有效数据:", str(data)[:200])
        except Exception as e:
            print("[DEBUG] API 异常:", e)

    try:
        share_url = "https://www.iesdouyin.com/share/video/{}/".format(video_id)
        print("[DEBUG] 请求 HTML:", share_url)
        resp = requests.get(share_url, headers=HEADERS, timeout=15)
        html = resp.text
        print("[DEBUG] HTML 长度: {} bytes".format(len(html)))

        m = re.search(r'window\._ROUTER_DATA\s*=\s*(\{.+?\})\s*(?:;|</script>)',
                      html, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                result = _find_nested(data, ["aweme_detail", "item_list"])
                if isinstance(result, list) and result:
                    result = result[0]
                if result and isinstance(result, dict) and result.get("aweme_id"):
                    print("[DEBUG] _ROUTER_DATA 解析成功:", result.get("aweme_id"))
                    return result
            except Exception as e2:
                print("[DEBUG] _ROUTER_DATA 解析失败:", e2)

        m = re.search(r'window\._SSR_DATA\s*=\s*(\{.+?\})\s*(?:;|</script>)',
                      html, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                result = _find_nested(data, ["aweme_detail", "item_list"])
                if isinstance(result, list) and result:
                    result = result[0]
                if result and isinstance(result, dict) and result.get("aweme_id"):
                    print("[DEBUG] _SSR_DATA 解析成功")
                    return result
            except Exception as e2:
                print("[DEBUG] _SSR_DATA 解析失败:", e2)

        for i, m in enumerate(re.finditer(r'<script([^>]*)>(.*?)</script>', html, re.S)):
            attrs, body = m.group(1).strip(), m.group(2).strip()
            if body and len(body) > 50:
                print("[DEBUG] script[{}] attrs={!r} len={} head={!r}".format(
                    i, attrs[:50], len(body), body[:80]))

        m = re.search(r'id=["\']RENDER_DATA["\'][^>]*>(.+?)</script>', html, re.S)
        if m:
            raw = m.group(1).strip()
            print("[DEBUG] RENDER_DATA ({}b): {!r}".format(len(raw), raw[:100]))
            for transform in [
                lambda s: urllib.parse.unquote(s),
                lambda s: urllib.parse.unquote(s.strip('"')),
                lambda s: s,
            ]:
                try:
                    data = json.loads(transform(raw))
                    result = _find_nested(data, ["aweme_detail", "item_list"])
                    if isinstance(result, list) and result:
                        result = result[0]
                    if result and isinstance(result, dict) and result.get("aweme_id"):
                        print("[DEBUG] RENDER_DATA 成功")
                        return result
                except Exception:
                    pass

        m = re.search(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.+?)</script>',
                      html, re.S)
        if m:
            raw = m.group(1).strip()
            print("[DEBUG] __NEXT_DATA__ len={} head={!r}".format(len(raw), raw[:80]))
            try:
                data = json.loads(raw)
                result = _find_nested(data, ["aweme_detail", "item_list"])
                if isinstance(result, list) and result:
                    result = result[0]
                if result and isinstance(result, dict) and result.get("aweme_id"):
                    print("[DEBUG] __NEXT_DATA__ 成功")
                    return result
            except Exception as e2:
                print("[DEBUG] __NEXT_DATA__ 失败:", e2)

        big_scripts = sorted(
            re.findall(r'<script[^>]*>(.{500,}?)</script>', html, re.S),
            key=len, reverse=True
        )
        for sc in big_scripts[:3]:
            for attempt in [sc.strip(), urllib.parse.unquote(sc.strip())]:
                try:
                    idx = attempt.find('{')
                    if idx >= 0:
                        data = json.loads(attempt[idx:])
                        result = _find_nested(data, ["aweme_detail", "item_list"])
                        if isinstance(result, list) and result:
                            result = result[0]
                        if result and isinstance(result, dict) and result.get("aweme_id"):
                            print("[DEBUG] 大script块成功")
                            return result
                except Exception:
                    pass

        print("[DEBUG] 直接 regex 找音乐 URL")

        mu = re.search(
            r'"play_url"\s*:\s*\{[^{}]*?"url_list"\s*:\s*\["(https://[^"]+)"',
            html, re.S)
        if not mu:
            for cdn in ["douyinvod.com", "byteimg.com", "snssdk.com",
                        "tosv.boe", "v3-dy", "v26-dy", "v9-dy"]:
                mu = re.search(r'"(https://[^"]*' + re.escape(cdn) + r'[^"]*)"', html)
                if mu:
                    break
        if mu:
            music_url = mu.group(1).replace('\\u002F', '/').replace('\\/', '/')
            print("[DEBUG] 直接找到 URL:", music_url[:80])
            title_m  = re.search(r'"title"\s*:\s*"([^"]{2,80})"', html)
            author_m = re.search(r'"author"\s*:\s*"([^"]{1,40})"', html)
            return {
                "aweme_id": video_id,
                "music": {
                    "title":    title_m.group(1)  if title_m  else "未知曲目",
                    "author":   author_m.group(1) if author_m else "",
                    "play_url": {"url_list": [music_url]},
                    "duration": 0,
                },
                "desc": "",
            }

        idx = html.find(video_id)
        if idx != -1:
            print("[DEBUG] video_id 附近内容:",
                  repr(html[max(0, idx-100):idx+400]))

    except Exception as e:
        print("[DEBUG] HTML 解析异常:", e)

    return None


def get_music_info(item):
    """
    从 item 提取 (audio_url, 标题, 作者, is_video)
    优先级：music.play_url > video.play_addr (MP4，需要后续提取音频)
    """
    print("[DEBUG] item keys:", list(item.keys())[:20])
    music = item.get("music") or {}
    print("[DEBUG] music keys:", list(music.keys()) if music else "无 music 字段")

    title  = music.get("title") or (item.get("desc") or "未知曲目")
    author = (music.get("author") or
              (item.get("author") or {}).get("nickname", ""))

    urls = (music.get("play_url") or {}).get("url_list") or []
    if urls:
        print("[DEBUG] 音乐URL (music):", urls[0][:80])
        return urls[0], title[:60], author, False

    pu = music.get("play_url")
    if isinstance(pu, str) and pu.startswith("http"):
        print("[DEBUG] 音乐URL (str):", pu[:80])
        return pu, title[:60], author, False

    video = item.get("video") or {}
    print("[DEBUG] video keys:", list(video.keys()) if video else "无 video 字段")
    pa = video.get("play_addr") or {}
    vurls = pa.get("url_list") or []
    if vurls:
        mp4 = next((u for u in vurls if "mp4" in u.lower()), vurls[0])
        mp4 = mp4.replace("playwm", "play")
        print("[DEBUG] 视频URL (MP4):", mp4[:80])
        return mp4, title[:60], author, True

    return None, title[:60], author, False


def _has_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def fmt_time(s):
    try:
        m, sec = divmod(max(0, int(s)), 60)
        return "{:02d}:{:02d}".format(m, sec)
    except Exception:
        return "00:00"

class SeekBar(tk.Canvas):
    TRACK_H = 4
    THUMB_R = 7

    def __init__(self, parent, on_seek=None, **kw):
        kw.setdefault("height", 20)
        kw.setdefault("highlightthickness", 0)
        kw.setdefault("bd", 0)
        super().__init__(parent, **kw)
        self._frac    = 0.0
        self._active  = False
        self._on_seek = on_seek
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>",  self._click)
        self.bind("<B1-Motion>", self._click)

    def set_fraction(self, f):
        self._frac = max(0.0, min(1.0, f))
        self._draw()

    def set_active(self, v):
        self._active = v
        self.configure(cursor="hand2" if v else "arrow")

    def _draw(self):
        self.delete("all")
        W, H = self.winfo_width(), self.winfo_height()
        if W < 2: return
        cy, r, th = H // 2, self.THUMB_R, self.TRACK_H
        self.create_rectangle(0, cy-th//2, W, cy+th//2+1, fill="#c8c8c8", outline="")
        fx = int(W * self._frac)
        if fx > 0:
            self.create_rectangle(0, cy-th//2, fx, cy+th//2+1, fill="#0078d4", outline="")
        tx = max(r, min(W-r, fx))
        self.create_oval(tx-r, cy-r, tx+r, cy+r, fill="#0078d4", outline="#005ca3", width=1.5)

    def _click(self, event):
        if not self._active: return
        frac = max(0.0, min(1.0, event.x / max(1, self.winfo_width())))
        self.set_fraction(frac)
        if self._on_seek:
            self._on_seek(frac)


class DouyinApp:
    BG    = "#f0f0f0"; PANEL = "#ffffff"; PAN2 = "#e8e8e8"
    BLUE  = "#0078d4"; BLUA  = "#005a9e"
    GBTN  = "#d4d4d4"; GBTA  = "#c0c0c0"
    TEXT  = "#1a1a1a"; MUTED = "#666666"; BORD = "#b4b4b4"
    OK    = "#107c10"; ERR   = "#c42b1c"; WARN = "#ca5010"; INFO = "#0050a0"

    S_IDLE       = "idle"
    S_DETECTING  = "detecting"
    S_PREVIEW_DL = "preview_dl"
    S_PLAYING    = "playing"
    S_PAUSED     = "paused"
    S_ENDED      = "ended"

    def __init__(self, root):
        self.root = root
        self.root.title("抖音 MP3 下载器")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)

        self._state        = self.S_IDLE
        self._item         = None
        self._music_url    = None
        self._music_title  = ""
        self._music_author = ""
        self._is_video     = False
        self._tmpdir       = tempfile.mkdtemp()
        self._tmp_mp3      = os.path.join(self._tmpdir, "preview.mp3")
        self._duration     = 0.0
        self._seek_offset  = 0.0
        self._save_dir     = os.path.expanduser("~/Downloads")

        self._build_ui()
        self._poll()

    def _build_ui(self):
        root = self.root

        tk.Label(root, text="抖音音乐下载  &  试听",
                 font=("Microsoft YaHei UI", 15, "bold"),
                 bg=self.BG, fg=self.TEXT).pack(pady=(18, 14))

        r1 = tk.Frame(root, bg=self.BG)
        r1.pack(fill="x", padx=24, pady=(0, 4))
        tk.Label(r1, text="歌曲链接：",
                 font=("Microsoft YaHei UI", 10),
                 bg=self.BG, fg=self.TEXT).pack(side="left")
        self._url_var = tk.StringVar()
        e = tk.Entry(r1, textvariable=self._url_var, font=("Consolas", 10),
                     bg=self.PANEL, fg=self.TEXT, insertbackground=self.TEXT,
                     relief="solid", bd=1, width=44)
        e.pack(side="left", padx=(4, 8), ipady=4)
        e.bind("<Return>", lambda _: self._detect())
        self._detect_btn = self._mkbtn(r1, "🔍  侦测资源",
                                        self.BLUE, "white", self.BLUA, self._detect)
        self._detect_btn.pack(side="left")

        tk.Label(root, text="✅ 无需 Cookie / 无需登录 — 直接粘贴分享文字或链接",
                 font=("Microsoft YaHei UI", 8), bg=self.BG, fg=self.OK
                 ).pack(anchor="w", padx=28, pady=(0, 8))

        panel = tk.Frame(root, bg=self.PAN2,
                         highlightthickness=1, highlightbackground=self.BORD)
        panel.pack(fill="x", padx=24)

        self._track_var = tk.StringVar(value="等待输入链接...")
        tk.Label(panel, textvariable=self._track_var,
                 font=("Microsoft YaHei UI", 10),
                 bg=self.PAN2, fg=self.TEXT, anchor="w"
                 ).pack(fill="x", padx=16, pady=(12, 8))

        bar_row = tk.Frame(panel, bg=self.PAN2)
        bar_row.pack(fill="x", padx=16, pady=(0, 14))
        self._seekbar = SeekBar(bar_row, on_seek=self._on_seek, bg=self.PAN2)
        self._seekbar.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._time_var = tk.StringVar(value="00:00 / 00:00")
        tk.Label(bar_row, textvariable=self._time_var,
                 font=("Courier New", 9), bg=self.PAN2, fg=self.MUTED,
                 width=12, anchor="e").pack(side="left")

        btn_row = tk.Frame(root, bg=self.BG)
        btn_row.pack(pady=(14, 0))
        self._play_btn = self._mkbtn(btn_row, "▶  在线试听", self.GBTN, self.TEXT,
                                      self.GBTA, self._toggle_play, state="disabled",
                                      padx=30, pady=10, font=("Microsoft YaHei UI", 11))
        self._play_btn.pack(side="left", padx=(0, 10))
        self._dl_btn = self._mkbtn(btn_row, "⬇  立即下载 MP3", self.GBTN, self.TEXT,
                                    self.GBTA, self._download, state="disabled",
                                    padx=30, pady=10, font=("Microsoft YaHei UI", 11))
        self._dl_btn.pack(side="left")

        self._status_var = tk.StringVar(value="")
        self._status_lbl = tk.Label(root, textvariable=self._status_var,
                                     font=("Microsoft YaHei UI", 8),
                                     bg=self.BG, fg=self.MUTED,
                                     wraplength=580, justify="left", anchor="w")
        self._status_lbl.pack(fill="x", padx=24, pady=(10, 16))

    def _mkbtn(self, parent, text, bg, fg, abg, cmd,
               state="normal", padx=14, pady=5,
               font=("Microsoft YaHei UI", 10)):
        return tk.Button(parent, text=text, font=font,
                         bg=bg, fg=fg, activebackground=abg, activeforeground=fg,
                         relief="flat", padx=padx, pady=pady,
                         cursor="hand2", bd=0, state=state, command=cmd)

    def _status(self, msg, kind="normal"):
        colors = {"ok": self.OK, "error": self.ERR,
                  "warn": self.WARN, "info": self.INFO, "normal": self.MUTED}
        self._status_var.set(msg)
        self._status_lbl.configure(fg=colors.get(kind, self.MUTED))

    def _detect(self):
        raw = self._url_var.get().strip()
        url = extract_short_url(raw)
        if not url:
            self._status("❌ 未识别到有效的抖音链接", "error")
            return
        self._stop_playback()
        self._item = None; self._music_url = None
        self._set_state(self.S_DETECTING)
        self._track_var.set("🔄 正在解析...")
        self._time_var.set("00:00 / 00:00")
        self._seekbar.set_fraction(0)
        self._status("正在解析（无需 Cookie）...", "info")
        threading.Thread(target=self._detect_worker, args=(url,), daemon=True).start()

    def _detect_worker(self, url):
        try:
            vid = resolve_video_id(url)
            if not vid:
                self.root.after(0, lambda: self._detect_err("无法解析视频 ID，请检查链接"))
                return
            item = fetch_douyin_info(vid)
            if not item:
                self.root.after(0, lambda: self._detect_err(
                    "所有解析方式均失败，详情见终端 [DEBUG] 输出"))
                return
            music_url, title, author, is_video = get_music_info(item)
            if not music_url:
                self.root.after(0, lambda: self._detect_err(
                    "该视频既无背景音乐也无可提取的视频地址"))
                return
            result = {"item": item, "music_url": music_url,
                      "title": title, "author": author,
                      "is_video": is_video}
            self.root.after(0, lambda: self._detect_done(result))
        except Exception as exc:
            err = str(exc)
            self.root.after(0, lambda: self._detect_err(err))

    def _detect_done(self, result):
        self._item        = result["item"]
        self._music_url   = result["music_url"]
        self._music_title = result["title"]
        self._music_author= result["author"]
        self._is_video    = result.get("is_video", False)

        label = self._music_title
        if self._music_author:
            label = "{}  —  {}".format(self._music_title, self._music_author)
        prefix = "🎬 " if self._is_video else "🎵 "
        self._track_var.set(prefix + label)

        try:
            if self._is_video:
                dur = self._item.get("duration", 0) or 0
                if not dur:
                    dur = (self._item.get("video") or {}).get("duration", 0) or 0
                dur = dur / 1000 if dur > 1000 else dur
            else:
                dur = (self._item.get("music") or {}).get("duration", 0) or 0
            self._duration = float(dur)
        except Exception:
            self._duration = 0.0
        self._time_var.set("00:00 / " + fmt_time(self._duration))

        self._set_state(self.S_IDLE)
        if self._is_video:
            self._status(
                "⚠ 该视频无独立音乐轨道，将下载视频 MP4。"
                "保存时会自动调用 ffmpeg 抽取音频为 MP3（如未安装 ffmpeg 则保留 MP4）",
                "warn"
            )
        else:
            self._status("✅ 解析成功！可试听或下载 MP3（无需 ffmpeg）", "ok")

    def _detect_err(self, err):
        self._set_state(self.S_IDLE)
        self._track_var.set("等待输入链接...")
        if "timeout" in err.lower() or "connect" in err.lower():
            self._status("❌ 网络超时，请检查网络后重试", "error")
        else:
            self._status("❌ 解析失败：" + err[:120], "error")

    def _toggle_play(self):
        if self._state == self.S_PLAYING:
            pygame.mixer.music.pause()
            self._set_state(self.S_PAUSED)
            return
        if self._state == self.S_PAUSED:
            pygame.mixer.music.unpause()
            self._set_state(self.S_PLAYING)
            return
        if self._state == self.S_ENDED:
            self._play_from(0.0); return
        if os.path.exists(self._tmp_mp3):
            self._play_from(0.0)
        elif self._music_url:
            self._start_preview_dl()

    def _play_from(self, pos):
        try:
            pygame.mixer.music.load(self._tmp_mp3)
            pygame.mixer.music.play(start=pos)
            self._seek_offset = pos
            self._set_state(self.S_PLAYING)
            self._status("▶  正在播放，可拖动进度条跳转", "ok")
        except Exception as exc:
            self._status("❌ 播放失败：" + str(exc), "error")

    def _stop_playback(self):
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        except Exception: pass
        self._seek_offset = 0.0
        self._seekbar.set_fraction(0)
        self._seekbar.set_active(False)
        if os.path.exists(self._tmp_mp3):
            try: os.remove(self._tmp_mp3)
            except Exception: pass

    def _start_preview_dl(self):
        self._set_state(self.S_PREVIEW_DL)
        self._status("正在下载音频（直接 MP3，无需转换）...", "info")
        threading.Thread(target=self._preview_dl_worker, daemon=True).start()

    def _preview_dl_worker(self):
        try:
            resp = requests.get(self._music_url, headers=HEADERS,
                                timeout=30, stream=True)
            resp.raise_for_status()
            with open(self._tmp_mp3, "wb") as f:
                for chunk in resp.iter_content(65536):
                    if chunk: f.write(chunk)
            self.root.after(0, self._preview_ready)
        except Exception as exc:
            err = str(exc)
            self.root.after(0, lambda: self._preview_err(err))

    def _preview_ready(self):
        self._seekbar.set_active(True)
        self._play_from(0.0)

    def _preview_err(self, err):
        self._set_state(self.S_IDLE)
        self._status("❌ 下载失败：" + err[:120], "error")

    def _on_seek(self, frac):
        if self._state not in (self.S_PLAYING, self.S_PAUSED, self.S_ENDED):
            return
        if self._duration <= 0 or not os.path.exists(self._tmp_mp3): return
        target = frac * self._duration
        was_playing = (self._state == self.S_PLAYING)
        try:
            pygame.mixer.music.play(start=target)
            self._seek_offset = target
            if not was_playing:
                pygame.mixer.music.pause()
                self._set_state(self.S_PAUSED)
            else:
                self._set_state(self.S_PLAYING)
        except Exception as exc:
            self._status("跳转出错：" + str(exc), "warn")

    def _poll(self):
        if self._state == self.S_PLAYING:
            try:
                raw = pygame.mixer.music.get_pos()
                if raw < 0 or not pygame.mixer.music.get_busy():
                    self._set_state(self.S_ENDED)
                    pos = self._duration
                else:
                    pos = self._seek_offset + raw / 1000.0
                    pos = min(pos, self._duration) if self._duration > 0 else pos
                frac = (pos / self._duration) if self._duration > 0 else 0
                self._seekbar.set_fraction(frac)
                self._time_var.set("{} / {}".format(fmt_time(pos), fmt_time(self._duration)))
            except Exception: pass
        self.root.after(200, self._poll)

    def _set_state(self, state):
        self._state = state
        has_info = self._music_url is not None
        d, n = "disabled", "normal"
        det_st = d if state in (self.S_DETECTING, self.S_PREVIEW_DL) else n
        self._detect_btn.configure(state=det_st)

        if state == self.S_IDLE:
            self._play_btn.configure(text="▶  在线试听", state=n if has_info else d,
                                      bg=self.GBTN, fg=self.TEXT)
            self._dl_btn.configure(state=n if has_info else d)
        elif state == self.S_DETECTING:
            self._play_btn.configure(state=d, text="▶  在线试听", bg=self.GBTN, fg=self.TEXT)
            self._dl_btn.configure(state=d)
        elif state == self.S_PREVIEW_DL:
            self._play_btn.configure(state=d, text="⬇  下载中...", bg=self.GBTN, fg=self.MUTED)
            self._dl_btn.configure(state=d)
        elif state == self.S_PLAYING:
            self._play_btn.configure(state=n, text="⏸  暂停", bg=self.GBTN, fg=self.TEXT)
            self._dl_btn.configure(state=n)
            self._seekbar.set_active(True)
        elif state == self.S_PAUSED:
            self._play_btn.configure(state=n, text="▶  继续播放", bg=self.GBTN, fg=self.TEXT)
            self._dl_btn.configure(state=n)
        elif state == self.S_ENDED:
            self._seekbar.set_fraction(1.0)
            self._time_var.set("{} / {}".format(fmt_time(self._duration), fmt_time(self._duration)))
            self._play_btn.configure(state=n, text="▶  重新播放", bg=self.GBTN, fg=self.TEXT)
            self._dl_btn.configure(state=n)
            self._status("播放完毕", "ok")

    def _download(self):
        if not self._music_url: return
        save_dir = filedialog.askdirectory(initialdir=self._save_dir,
                                            title="选择 MP3 保存位置")
        if not save_dir: return
        self._save_dir = save_dir

        if os.path.exists(self._tmp_mp3):
            safe = re.sub(r'[\\/:*?"<>|]', "_", self._music_title)[:80] or "audio"
            dest = os.path.join(save_dir, safe + ".mp3")
            try:
                shutil.copy2(self._tmp_mp3, dest)
                self._status("✅ 已保存：" + dest, "ok")
                self._open_folder(save_dir)
                return
            except Exception as exc:
                self._status("复制失败，将重新下载：" + str(exc), "warn")

        self._dl_btn.configure(state="disabled")
        self._play_btn.configure(state="disabled")
        self._status("正在下载 MP3...", "info")
        threading.Thread(target=self._dl_worker, args=(save_dir,), daemon=True).start()

    def _dl_worker(self, save_dir):
        os.makedirs(save_dir, exist_ok=True)
        safe = re.sub(r'[\\/:*?"<>|]', "_", self._music_title)[:80] or "audio"
        if self._is_video:
            tmp_mp4 = os.path.join(save_dir, safe + ".mp4")
            final_mp3 = os.path.join(save_dir, safe + ".mp3")
            try:
                resp = requests.get(self._music_url, headers=HEADERS,
                                    timeout=60, stream=True)
                resp.raise_for_status()
                with open(tmp_mp4, "wb") as f:
                    for chunk in resp.iter_content(65536):
                        if chunk: f.write(chunk)
                if _has_ffmpeg():
                    print("[DEBUG] ffmpeg 提取音频:", tmp_mp4, "->", final_mp3)
                    r = subprocess.run(
                        ["ffmpeg", "-y", "-i", tmp_mp4, "-vn",
                         "-acodec", "libmp3lame", "-q:a", "2", final_mp3],
                        capture_output=True
                    )
                    if r.returncode == 0 and os.path.exists(final_mp3):
                        try: os.remove(tmp_mp4)
                        except Exception: pass
                        self.root.after(0, lambda: self._dl_done(final_mp3, save_dir))
                        return
                    else:
                        print("[DEBUG] ffmpeg 错误:", r.stderr.decode("utf-8", errors="ignore")[:200])
                self.root.after(0, lambda: self._dl_done(tmp_mp4, save_dir))
            except Exception as exc:
                err = str(exc)
                self.root.after(0, lambda: self._dl_err(err))
            return

        dest = os.path.join(save_dir, safe + ".mp3")
        try:
            resp = requests.get(self._music_url, headers=HEADERS,
                                timeout=30, stream=True)
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(65536):
                    if chunk: f.write(chunk)
            self.root.after(0, lambda: self._dl_done(dest, save_dir))
        except Exception as exc:
            err = str(exc)
            self.root.after(0, lambda: self._dl_err(err))

    def _dl_done(self, dest, save_dir):
        self._dl_btn.configure(state="normal")
        self._play_btn.configure(state="normal")
        self._status("✅ 下载完成：" + dest, "ok")
        self._open_folder(save_dir)

    def _dl_err(self, err):
        self._dl_btn.configure(state="normal")
        self._play_btn.configure(state="normal")
        self._status("❌ 下载失败：" + err[:120], "error")

    def _open_folder(self, path):
        try:
            if sys.platform == "win32": os.startfile(path)
            elif sys.platform == "darwin": subprocess.Popen(["open", path])
            else: subprocess.Popen(["xdg-open", path])
        except Exception: pass

    def on_close(self):
        self._stop_playback()
        try: pygame.mixer.quit()
        except Exception: pass
        try: shutil.rmtree(self._tmpdir, ignore_errors=True)
        except Exception: pass
        self.root.destroy()


def main():
    root = tk.Tk()
    root.update_idletasks()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    w, h = 660, 370
    root.geometry("{}x{}+{}+{}".format(w, h, (sw-w)//2, (sh-h)//2))
    app = DouyinApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main()
