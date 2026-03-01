"""
shogun-voice floating_window.py
Phase 3: フローティングUI + Ctrl+Space ホットキー

使い方:
  python floating_window.py

  Ctrl+Space  → 小窓を表示して即座に音声認識開始
  Ctrl+Space  → もう一度押すと停止 & 非表示
  Esc         → 停止 & 非表示
  Ctrl+C      → 完全終了

Windows+Hの精度に絶望した将軍が作った
"""

import sys
import threading
import asyncio
import time
import tkinter as tk

# クリップボード経由テキスト送信
try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False
    print("[WARN] pyperclip 未インストール。クリップボード送信が無効です: pip install pyperclip")

# pynput (グローバルホットキー + Ctrl+V 送信)
try:
    from pynput import keyboard as pynput_kb
    from pynput.keyboard import Controller as KeyController, Key
    PYNPUT_AVAILABLE = True
    _key_ctrl = KeyController()
except ImportError:
    PYNPUT_AVAILABLE = False
    _key_ctrl = None
    print("[WARN] pynput 未インストール。ホットキー・貼り付けが無効です: pip install pynput")
except Exception as e:
    PYNPUT_AVAILABLE = False
    _key_ctrl = None
    print(f"[WARN] pynput 初期化失敗（WSL2環境では正常）: {e}")


# ── テキスト送信 ─────────────────────────────────────────────────

def clipboard_paste(text: str) -> None:
    """クリップボード経由でテキストをアクティブウィンドウに貼り付ける。

    IME対応のため keyboard.type() ではなくクリップボード経由を使用する。
    """
    if not text:
        return
    if CLIPBOARD_AVAILABLE and PYNPUT_AVAILABLE and _key_ctrl is not None:
        try:
            pyperclip.copy(text)
            time.sleep(0.05)  # クリップボード反映待ち
            _key_ctrl.press(Key.ctrl)
            _key_ctrl.press('v')
            _key_ctrl.release('v')
            _key_ctrl.release(Key.ctrl)
        except Exception as e:
            print(f"[WARN] テキスト貼り付け失敗: {e}")
    else:
        # フォールバック: コンソール出力のみ
        print(f"[OUTPUT] {text}")


# ── フローティングウィンドウ ──────────────────────────────────────

class FloatingWindow:
    """音声認識インジケータ付きフローティングウィンドウ。

    Ctrl+Space でトグル表示。表示中は常時音声認識を継続する。
    """

    WIN_W = 300
    WIN_H = 100
    HOTKEY = "<ctrl>+<space>"

    def __init__(self) -> None:
        self._active = False          # ウィンドウ表示 & 認識中フラグ
        self._stt_running = False     # STTスレッド停止シグナル
        self._stt_thread: threading.Thread | None = None
        self._root: tk.Tk | None = None
        self._interim_var: tk.StringVar | None = None
        self._drag_offset: tuple[int, int] = (0, 0)

    # ── UI ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """tkinter ウィンドウを構築する（メインスレッドで呼ぶこと）"""
        r = tk.Tk()
        self._root = r

        # -- 将軍カラーパレット --
        BG = '#0d0d1a'          # 漆黒
        ACCENT = '#c4a35a'      # 金箔
        RED = '#b33a3a'         # 朱色
        ORANGE = '#d4893a'      # 橙
        TEXT = '#e8dcc8'        # 和紙色
        DIM = '#5a5a6a'         # 墨色

        r.overrideredirect(True)       # タイトルバーなし
        r.attributes('-topmost', True) # 常に最前面
        r.attributes('-alpha', 0.93)   # 軽く透過
        r.configure(bg=BG)

        # 画面右下に初期配置
        sw = r.winfo_screenwidth()
        sh = r.winfo_screenheight()
        r.geometry(f"{self.WIN_W}x{self.WIN_H}+{sw - self.WIN_W - 20}+{sh - self.WIN_H - 60}")

        # 外枠（金箔の細い枠線）
        outer = tk.Frame(r, bg=ACCENT, padx=1, pady=1)
        outer.pack(fill=tk.BOTH, expand=True)

        # メインフレーム
        frame = tk.Frame(outer, bg=BG, cursor='fleur')
        frame.pack(fill=tk.BOTH, expand=True)

        # タイトル行: 将軍 + 残高
        title_bar = tk.Frame(frame, bg=BG)
        title_bar.pack(fill=tk.X, pady=(6, 0), padx=10)

        tk.Label(
            title_bar,
            text="⚔ SHOGUN",
            fg=ACCENT,
            bg=BG,
            font=('Yu Gothic', 9, 'bold'),
        ).pack(side=tk.LEFT)

        # 残高ラベル（右寄せ）
        from main import check_balance
        balance = check_balance()
        if balance:
            tk.Label(
                title_bar,
                text=balance,
                fg=DIM,
                bg=BG,
                font=('Consolas', 8),
            ).pack(side=tk.RIGHT)

        # ステータス行
        self._status_var = tk.StringVar(value="● 全集中聴中 (Listening)")
        self._status_label = tk.Label(
            frame,
            textvariable=self._status_var,
            fg=RED,
            bg=BG,
            font=('Yu Gothic', 12, 'bold'),
        )
        self._status_label.pack(pady=(2, 0))

        # 中間認識テキスト
        self._interim_var = tk.StringVar(value="")
        tk.Label(
            frame,
            textvariable=self._interim_var,
            fg=TEXT,
            bg=BG,
            font=('Yu Gothic', 10),
            wraplength=270,
        ).pack(pady=(2, 8))

        # ドラッグ移動をフレームと子ウィジェット全体に適用
        for w in [r, frame] + frame.winfo_children():
            w.bind('<Button-1>', self._drag_start)
            w.bind('<B1-Motion>', self._drag_move)

        # Esc で非表示
        r.bind('<Escape>', lambda _e: self.hide())

        # 初期状態は非表示
        r.withdraw()

    def _drag_start(self, event) -> None:
        self._drag_offset = (
            event.x_root - self._root.winfo_x(),
            event.y_root - self._root.winfo_y(),
        )

    def _drag_move(self, event) -> None:
        ox, oy = self._drag_offset
        self._root.geometry(f"+{event.x_root - ox}+{event.y_root - oy}")

    def _set_interim(self, text: str) -> None:
        """STTスレッドから中間テキストを更新する（スレッドセーフ）"""
        if self._root is None or self._interim_var is None:
            return
        display = text[:36] + "…" if len(text) > 36 else text
        self._root.after(0, lambda: self._interim_var.set(display))

    def _clear_interim(self) -> None:
        if self._root is not None and self._interim_var is not None:
            self._root.after(0, lambda: self._interim_var.set(""))

    # ── STT 管理 ──────────────────────────────────────────────────

    def _set_status(self, text: str, color: str = '#b33a3a') -> None:
        """ステータス表示を更新する（スレッドセーフ）"""
        if self._root is None:
            return
        self._root.after(0, lambda: (
            self._status_var.set(text),
            self._status_label.config(fg=color),
        ))

    def _start_stt(self) -> None:
        """音声認識をバックグラウンドスレッドで開始する"""
        if self._stt_running:
            return
        self._stt_running = True
        self._set_status("● 全集中聴中 (Listening)", '#b33a3a')
        ref = self

        def _on_interim(text: str) -> None:
            ref._set_interim(text)

        def _on_final(text: str) -> None:
            ref._clear_interim()
            clipboard_paste(text)

        def _should_stop() -> bool:
            return not ref._stt_running

        def run() -> None:
            import main as voice_main
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    voice_main.run_transcription_with_callbacks(
                        on_interim=_on_interim,
                        on_final=_on_final,
                        should_stop=_should_stop,
                    )
                )
            except Exception as e:
                print(f"[ERROR] STT: {e}")
            finally:
                loop.close()
                was_active = ref._active
                ref._stt_running = False
                if was_active:
                    # 接続が切れたが、ユーザーは停止してない → 自動再接続
                    ref._set_status("● 再起奮迅中 (Reconnecting)", '#d4893a')
                    print("[INFO] STT接続切断 → 2秒後に再接続")
                    time.sleep(2)
                    if ref._active:
                        ref._root.after(0, ref._start_stt)

        self._stt_thread = threading.Thread(target=run, daemon=True)
        self._stt_thread.start()
        print("[INFO] 音声認識 開始")

    def _stop_stt(self) -> None:
        """音声認識を停止する（ノンブロッキング）"""
        self._stt_running = False
        self._clear_interim()
        print("[INFO] 音声認識 停止")

    # ── 表示制御（メインスレッドから呼ぶこと）───────────────────────

    def show(self) -> None:
        """ウィンドウを表示して音声認識を開始する"""
        if self._active:
            return
        self._active = True
        self._root.deiconify()
        self._start_stt()

    def hide(self) -> None:
        """音声認識を停止してウィンドウを非表示にする"""
        if not self._active:
            return
        self._active = False
        self._stop_stt()
        self._root.withdraw()

    def toggle(self) -> None:
        """表示/非表示をトグルする"""
        if self._active:
            self.hide()
        else:
            self.show()

    # ── ホットキー ──────────────────────────────────────────────

    def _setup_hotkeys(self) -> None:
        """グローバルホットキーを登録する（Ctrl+Space）"""
        if not PYNPUT_AVAILABLE:
            print("[WARN] ホットキー無効 — pynput が必要です: pip install pynput")
            return

        ref = self

        def _hotkey_callback() -> None:
            # ホットキーは別スレッドから呼ばれるので after() 経由でUIスレッドに渡す
            if ref._root is not None:
                ref._root.after(0, ref.toggle)

        hotkeys = pynput_kb.GlobalHotKeys({self.HOTKEY: _hotkey_callback})
        hotkeys.daemon = True
        hotkeys.start()
        print(f"[INFO] ホットキー登録: {self.HOTKEY} で認識ON/OFF")

    # ── エントリーポイント ─────────────────────────────────────────

    def run(self) -> None:
        """アプリを起動してメインループを開始する"""
        self._build_ui()
        self._setup_hotkeys()

        from main import check_balance

        print("=" * 48)
        print("  shogun-voice Phase 3 — フローティングUI")
        balance = check_balance()
        if balance:
            print(f"  {balance}")
        print(f"  {self.HOTKEY}: 認識ON/OFF")
        print("  Esc: ウィンドウを閉じる")
        print("  Ctrl+C: 完全終了")
        print("=" * 48)
        print("準備完了。Ctrl+Space を押すと認識開始します。")

        import signal
        self._shutdown = False

        def _on_sigint(*_):
            self._shutdown = True

        signal.signal(signal.SIGINT, _on_sigint)

        def _check_quit():
            if self._shutdown:
                self._stop_stt()
                self._root.destroy()
                return
            self._root.after(200, _check_quit)

        self._root.after(200, _check_quit)

        try:
            self._root.mainloop()
        except KeyboardInterrupt:
            pass
        print("\n終了します。")


def main() -> None:
    app = FloatingWindow()
    app.run()


if __name__ == "__main__":
    main()
