"""
shogun-voice tray.py
Phase 2c: タスクトレイ常駐 + グローバルホットキー

Windows+Hの精度に絶望した将軍が作った
"""

import os
import sys
import threading
import asyncio
from PIL import Image, ImageDraw

# タスクトレイ（Windows/macOS）
try:
    import pystray
    PYSTRAY_AVAILABLE = True
except ImportError:
    print("[ERROR] pystray が必要です: pip install pystray")
    sys.exit(1)

# グローバルホットキー
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    print("[WARN] pynput が未インストール。ホットキー機能は無効です: pip install pynput")
    PYNPUT_AVAILABLE = False
except Exception as e:
    print(f"[WARN] pynput 初期化失敗（WSL2環境では正常）: {e}")
    PYNPUT_AVAILABLE = False


# --- アイコン生成 ---

def create_icon(active: bool) -> Image.Image:
    """認識状態に応じたアイコンを動的生成する（画像ファイル不要）"""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if active:
        # 認識中: 赤丸
        color = (220, 50, 50, 255)
    else:
        # 停止中: グレー
        color = (120, 120, 120, 255)

    margin = 4
    draw.ellipse(
        [(margin, margin), (size - margin, size - margin)],
        fill=color,
    )

    # 中央に小さな白丸（マイクを示す）
    center = size // 2
    inner = 10
    draw.ellipse(
        [(center - inner, center - inner), (center + inner, center + inner)],
        fill=(255, 255, 255, 200),
    )

    return img


# --- STT スレッド管理 ---

class ShogunVoiceTray:
    def __init__(self):
        self._active = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stt_task: asyncio.Task | None = None
        self._stt_thread: threading.Thread | None = None
        self._tray: pystray.Icon | None = None

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(
                lambda _: "認識停止" if self._active else "認識開始",
                self._toggle,
                default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("終了", self._quit),
        )

    def _update_icon(self) -> None:
        if self._tray:
            self._tray.icon = create_icon(self._active)
            self._tray.title = "shogun-voice — 認識中" if self._active else "shogun-voice — 停止中"

    def _toggle(self, icon=None, item=None) -> None:
        if self._active:
            self._stop_stt()
        else:
            self._start_stt()
        self._update_icon()

    def _start_stt(self) -> None:
        """STTをバックグラウンドスレッドで起動する"""
        if self._active:
            return

        self._active = True

        def run_loop():
            # main.py の run_transcription を流用
            import main as voice_main
            voice_main.is_running = True
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(voice_main.run_transcription())
            except Exception as e:
                print(f"[ERROR] STT停止: {e}")
            finally:
                self._loop.close()
                self._active = False
                self._update_icon()

        self._stt_thread = threading.Thread(target=run_loop, daemon=True)
        self._stt_thread.start()
        print("[INFO] 音声認識 開始")

    def _stop_stt(self) -> None:
        """STTを停止する"""
        if not self._active:
            return

        import main as voice_main
        voice_main.is_running = False
        self._active = False

        if self._stt_thread and self._stt_thread.is_alive():
            self._stt_thread.join(timeout=3.0)

        print("[INFO] 音声認識 停止")

    def _quit(self, icon=None, item=None) -> None:
        """タスクトレイを終了する"""
        self._stop_stt()
        if self._tray:
            self._tray.stop()

    def _setup_hotkeys(self) -> None:
        """Ctrl+Shift+Space でON/OFF切替するグローバルホットキーを登録する"""
        if not PYNPUT_AVAILABLE:
            return

        hotkeys = keyboard.GlobalHotKeys(
            {"<ctrl>+<shift>+<space>": self._toggle}
        )
        hotkeys.daemon = True
        hotkeys.start()
        print("[INFO] ホットキー登録: Ctrl+Shift+Space で認識ON/OFF")

    def run(self) -> None:
        """タスクトレイを起動する"""
        self._setup_hotkeys()

        icon_img = create_icon(active=False)
        menu = self._build_menu()

        self._tray = pystray.Icon(
            "shogun-voice",
            icon_img,
            "shogun-voice — 停止中",
            menu=menu,
        )

        print("=" * 40)
        print("  shogun-voice タスクトレイ起動")
        print("  Ctrl+Shift+Space: 認識ON/OFF")
        print("  Windows+Hの精度に絶望した将軍が作った")
        print("=" * 40)
        print("タスクトレイアイコンをダブルクリックして認識開始")

        self._tray.run()


def main() -> None:
    app = ShogunVoiceTray()
    app.run()


if __name__ == "__main__":
    main()
