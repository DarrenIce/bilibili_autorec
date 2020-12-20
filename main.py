import os
import threading
import datetime
import asyncio
import sys
import platform
if sys.platform == 'win32':
    import keyboard
    keyboard.add_hotkey('ctrl+alt+;', os._exit, args=[0])
    
base = os.path.dirname(os.path.realpath(__file__))
log_path = os.path.join(base, 'log')
if not os.path.exists(log_path):
    os.mkdir(log_path)
stream_log_file = os.path.join(log_path, 'stream.log')
ffmpeg_log_file = os.path.join(log_path, 'ffmpeg.log')
if not os.path.exists(stream_log_file):
    with open(stream_log_file, 'w', encoding='utf-8') as a:
        pass
if not os.path.exists(ffmpeg_log_file):
    with open(ffmpeg_log_file, 'w', encoding='utf-8') as a:
        pass

from utils.live import Live
live = Live()

def main():
    live.start()

if __name__ == '__main__':
    main()
