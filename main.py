"""
shogun-voice main.py
Phase 2a: マイク → Deepgram Nova-3 → コンソール出力
Phase 2b: + 確定テキストをアクティブウィンドウにキーストローク送信
Phase 3:  + コールバック対応（floating_window.py から呼ばれる）

Windows+Hの精度に絶望した将軍が作った
"""

import os
import sys
import asyncio
import time as _time
import threading
import requests
import sounddevice as sd
from dotenv import load_dotenv
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)


class Microphone:
    """sounddevice ベースのマイク入力クラス（pyaudio 代替）"""
    RATE = 16000
    CHUNK = 8000

    def __init__(self, send_fn):
        self._send = send_fn
        self._thread = None
        self._stop = threading.Event()

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._stream, daemon=True)
        self._thread.start()

    def _stream(self):
        with sd.RawInputStream(
            samplerate=self.RATE,
            channels=1,
            dtype="int16",
            blocksize=self.CHUNK,
        ) as stream:
            while not self._stop.is_set():
                data, _ = stream.read(self.CHUNK)
                self._send(bytes(data))

    def finish(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

# キーストローク送信（Phase 2b）
# WSL2からWindowsウィンドウへの直接キーストローク送信は制約あり
# Windows上でPythonを直接実行する場合は pynput が動作する
KEYSTROKE_AVAILABLE = False
keyboard_controller = None

try:
    # Windows環境ではpynputが動作する
    from pynput.keyboard import Controller
    keyboard_controller = Controller()
    KEYSTROKE_AVAILABLE = True
    print("[INFO] pynput キーストローク送信: 有効")
except ImportError:
    print("[INFO] pynput 未インストール。キーストローク送信: 無効")
except Exception as e:
    # WSL2環境ではX11/Win32アクセスができないためエラーになる
    print(f"[INFO] キーストローク送信初期化失敗 (WSL2環境では正常): {e}")
    print("[INFO] キーストローク送信: 無効 - Windows上でPythonを直接実行する必要あり")


def send_keystrokes(text: str) -> None:
    """確定テキストをアクティブウィンドウに送信する（Phase 2b）"""
    if not KEYSTROKE_AVAILABLE or keyboard_controller is None:
        return
    try:
        keyboard_controller.type(text)
    except Exception as e:
        print(f"[WARN] キーストローク送信失敗: {e}")


def _load_keyterms() -> list[str]:
    """DEEPGRAM_KEYTERMS環境変数からカンマ区切りの辞書用語を読み込む"""
    raw = os.getenv("DEEPGRAM_KEYTERMS", "")
    if not raw.strip():
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def _load_env() -> None:
    """Windowsでも .env を UTF-8 として安定して読み込む。"""
    load_dotenv(encoding="utf-8")


# 音声認識中フラグ（tray.pyから制御するためグローバル）
is_running = True


async def run_transcription() -> None:
    """Deepgram Nova-3でマイク音声をリアルタイム文字起こしする"""
    _load_env()
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        print("[ERROR] DEEPGRAM_API_KEY が設定されていません。")
        print("  .env ファイルを作成して DEEPGRAM_API_KEY=your_key_here を設定してください。")
        print("  APIキーは https://console.deepgram.com で取得できます（$200無料クレジット）。")
        sys.exit(1)

    config = DeepgramClientOptions(options={"keepalive": "true"})
    client = DeepgramClient(api_key, config)

    connection = client.listen.asyncwebsocket.v("1")

    _connection_dead = False

    async def on_message(self, result, **kwargs):
        """Deepgramからの文字起こし結果を処理する"""
        sentence = result.channel.alternatives[0].transcript
        if not sentence:
            return

        if result.is_final:
            # 確定結果: 改行して表示 + キーストローク送信
            print(f"\n[確定] {sentence}")
            send_keystrokes(sentence)
        else:
            # 部分認識結果: 同一行にインライン表示
            print(f"\r[認識中] {sentence}    ", end="", flush=True)

    async def on_utterance_end(self, utterance_end, **kwargs):
        print()  # 発話終了時に改行

    async def on_speech_started(self, speech_started, **kwargs):
        print("\r[音声検出]          ", end="", flush=True)

    async def on_error(self, error, **kwargs):
        nonlocal _connection_dead
        error_str = str(error)
        if "SSL" in error_str or "ConnectionClosed" in error_str or "invalid state" in error_str:
            if not _connection_dead:
                print(f"\n[ERROR] 接続が切断されました: {error_str[:80]}")
                _connection_dead = True
        else:
            print(f"\n[ERROR] {error}")

    connection.on(LiveTranscriptionEvents.Transcript, on_message)
    connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
    connection.on(LiveTranscriptionEvents.SpeechStarted, on_speech_started)
    connection.on(LiveTranscriptionEvents.Error, on_error)

    options = LiveOptions(
        model="nova-3",
        language="ja",
        encoding="linear16",
        sample_rate=16000,
        channels=1,
        interim_results=True,
        utterance_end_ms=1000,
        vad_events=True,
        endpointing=300,
        punctuate=True,
        smart_format=True,
        numerals=True,
        keyterm=_load_keyterms(),
    )

    print("Deepgram Nova-3 接続中...")
    try:
        connected = await connection.start(options)
    except Exception as e:
        print(f"[ERROR] Deepgramへの接続に失敗しました: {e}")
        sys.exit(1)

    if not connected:
        print("[ERROR] Deepgramへの接続に失敗しました。APIキーを確認してください。")
        sys.exit(1)

    microphone = Microphone(connection.send)

    print("マイク入力中... Ctrl+Cで停止")
    print("-" * 40)

    microphone.start()

    global is_running
    try:
        while is_running:
            if _connection_dead:
                print("[INFO] 接続切断を検知。音声認識を停止します。")
                break
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass
    finally:
        try:
            microphone.finish()
        except Exception:
            pass
        try:
            await asyncio.wait_for(connection.finish(), timeout=2.0)
        except (asyncio.TimeoutError, Exception):
            pass
        print("\n停止しました。")


async def run_transcription_with_callbacks(
    on_interim=None,
    on_final=None,
    should_stop=None,
) -> None:
    """コールバック対応版 Deepgram 文字起こし（Phase 3 / floating_window.py 用）

    Args:
        on_interim: 中間認識テキストを受け取るコールバック (text: str) -> None
        on_final:   確定テキストを受け取るコールバック (text: str) -> None
        should_stop: True を返すと認識を停止するコールバック () -> bool
    """
    _load_env()
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        print("[ERROR] DEEPGRAM_API_KEY が設定されていません。")
        return

    config = DeepgramClientOptions(options={"keepalive": "true"})
    client = DeepgramClient(api_key, config)
    connection = client.listen.asyncwebsocket.v("1")

    # 接続エラー検知フラグ — エラー時にマイクループを即座に抜ける
    _connection_dead = False
    # ウォッチドッグ: 最後にDeepgramからイベントを受信した時刻
    _last_event_time = _time.monotonic()
    _WATCHDOG_TIMEOUT = 30  # 30秒無応答で接続死亡とみなす

    async def on_message(self, result, **kwargs):
        nonlocal _last_event_time
        _last_event_time = _time.monotonic()
        sentence = result.channel.alternatives[0].transcript
        if not sentence:
            return
        if result.is_final:
            if on_final:
                on_final(sentence)
            else:
                print(f"\n[確定] {sentence}")
        else:
            if on_interim:
                on_interim(sentence)
            else:
                print(f"\r[認識中] {sentence}    ", end="", flush=True)

    async def on_utterance_end(self, utterance_end, **kwargs):
        nonlocal _last_event_time
        _last_event_time = _time.monotonic()
        if not on_interim:
            print()

    async def on_speech_started(self, speech_started, **kwargs):
        nonlocal _last_event_time
        _last_event_time = _time.monotonic()
        if not on_interim:
            print("\r[音声検出]          ", end="", flush=True)

    async def on_error(self, error, **kwargs):
        nonlocal _connection_dead, _last_event_time
        _last_event_time = _time.monotonic()
        error_str = str(error)
        # SSL/WebSocket切断エラーは1回だけログして接続死亡フラグを立てる
        if "SSL" in error_str or "ConnectionClosed" in error_str or "invalid state" in error_str:
            if not _connection_dead:
                print(f"\n[ERROR] 接続が切断されました: {error_str[:80]}")
                _connection_dead = True
        else:
            print(f"\n[ERROR] {error}")

    connection.on(LiveTranscriptionEvents.Transcript, on_message)
    connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
    connection.on(LiveTranscriptionEvents.SpeechStarted, on_speech_started)
    connection.on(LiveTranscriptionEvents.Error, on_error)

    options = LiveOptions(
        model="nova-3",
        language="ja",
        encoding="linear16",
        sample_rate=16000,
        channels=1,
        interim_results=True,
        utterance_end_ms=1000,
        vad_events=True,
        endpointing=300,
        punctuate=True,
        smart_format=True,
        numerals=True,
        keyterm=_load_keyterms(),
    )

    try:
        connected = await connection.start(options)
    except Exception as e:
        print(f"[ERROR] Deepgramへの接続に失敗しました: {e}")
        return

    if not connected:
        print("[ERROR] Deepgramへの接続に失敗しました。APIキーを確認してください。")
        return

    microphone = Microphone(connection.send)
    microphone.start()

    _KEEPALIVE_INTERVAL = 8  # 8秒ごとにkeepalive ping
    _last_keepalive = _time.monotonic()

    try:
        while True:
            if _connection_dead:
                print("[INFO] 接続切断を検知。音声認識を停止します。")
                break
            # ウォッチドッグ: 30秒間Deepgramから何も来なければ接続死亡
            if _time.monotonic() - _last_event_time > _WATCHDOG_TIMEOUT:
                print("[INFO] 30秒間応答なし。接続が死んでいると判断します。")
                break
            # Keepalive ping: 接続維持のため定期的に送信
            if _time.monotonic() - _last_keepalive > _KEEPALIVE_INTERVAL:
                try:
                    await connection.keep_alive()
                    _last_keepalive = _time.monotonic()
                except Exception:
                    print("[INFO] keepalive送信失敗。接続が切れています。")
                    break
            if should_stop and should_stop():
                break
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass
    finally:
        try:
            microphone.finish()
        except Exception:
            pass
        try:
            await asyncio.wait_for(connection.finish(), timeout=2.0)
        except (asyncio.TimeoutError, Exception):
            pass
        print("[INFO] STT接続を終了しました。")


def check_balance() -> str | None:
    """Deepgramの残高を取得して表示用文字列を返す"""
    _load_env()
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        return None
    try:
        resp = requests.get(
            "https://api.deepgram.com/v1/projects",
            headers={"Authorization": f"Token {api_key}"},
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        projects = resp.json().get("projects", [])
        if not projects:
            return None
        project_id = projects[0]["project_id"]
        resp = requests.get(
            f"https://api.deepgram.com/v1/projects/{project_id}/balances",
            headers={"Authorization": f"Token {api_key}"},
            timeout=5,
        )
        if resp.status_code != 200:
            return "[Credit] N/A (billing:read required)"
        balances = resp.json().get("balances", [])
        if not balances:
            return "[Credit] N/A"
        amount = balances[0].get("amount", 0)
        return f"[Credit] ${amount:.2f}"
    except Exception:
        return None


def main() -> None:
    """エントリーポイント"""
    print("=" * 40)
    print("  shogun-voice - Deepgram Nova-3 STT")
    print("  Windows+Hの精度に絶望した将軍が作った")
    print("=" * 40)

    balance = check_balance()
    if balance:
        print(f"  {balance}")

    if KEYSTROKE_AVAILABLE:
        print("[Phase 2b] キーストローク送信: 有効")
    else:
        print("[Phase 2a] コンソール出力のみ（キーストローク送信: 無効）")
        print("  ※ Windows上でPythonを直接実行するとキーストローク送信が有効になります")

    print()

    try:
        asyncio.run(run_transcription())
    except KeyboardInterrupt:
        print("\n終了します。")


if __name__ == "__main__":
    main()
