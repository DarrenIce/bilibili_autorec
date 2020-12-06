from utils.live import Live
import os


def main():
    log_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'log')
    if not os.path.exists(log_path):
        os.mkdir(log_path)
        log_file = os.path.join(log_path, 'log.log')
        stream_log_file = os.path.join(log_path, 'stream.log')
        ffmpeg_log_file = os.path.join(log_path, 'ffmpeg.log')
        with open(log_file, 'w', encoding='utf-8') as a:
            pass
        with open(stream_log_file, 'w', encoding='utf-8') as a:
            pass
        with open(ffmpeg_log_file, 'w', encoding='utf-8') as a:
            pass
    live = Live()
    live.run()


if __name__ == '__main__':
    main()
