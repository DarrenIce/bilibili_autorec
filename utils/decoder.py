import subprocess
from utils.log import Log
import threading
import os
import re
import datetime

logger = Log()()


class Decoder():
    def __init__(self):
        self._lock = threading.Lock()
        self._lock2 = threading.Lock()
        self.decode_queue = []

    def decode(self, live_info):
        '''
        当前逻辑是
        从最近的一个flv文件向前数12小时，合并所有录播
        先把每个flv转ts，再ts合MP4
        最后给视频加黑色遮挡
        '''
        save_path = os.path.join(live_info['base_path'], live_info['uname'])
        time_lst = []
        flst = []
        for f in os.listdir(os.path.join(save_path, 'recording')):
            if 'flv' in f:
                flst.append(f)
        flst = sorted(flst, key=lambda x: x.split('_')[-1].split('.')[0])
        for f in flst:
            time_lst.append(datetime.datetime.fromtimestamp(os.stat(os.path.join(save_path, 'recording', f)).st_mtime))
        latest_time = time_lst[-1]
        input_file = []
        for f, t in zip(flst, time_lst):
            if (latest_time - t).total_seconds() < int(live_info['maxsecond']):
                input_file.append(f)

        output_file = re.search(r'.*?_\d{8}', input_file[0]).group() + '.mp4'
        filename = ''.join(output_file.replace('.mp4', '').split('_'))

        logger.info(
            '%s[RoomID:%s]本次录制文件:%s\t最终上传:%s' % (
                live_info['uname'], live_info['room_id'], ' '.join(input_file), filename))

        output_lst = []
        for i in input_file:
            output_lst.append(os.path.join(save_path, 'recording', i.replace('.flv', '.ts')))

        for i in range(len(input_file)):
            input_file[i] = '-i ' + os.path.join(save_path, 'recording', input_file[i])

        output_file = os.path.join(save_path, output_file)
        ffmpeg_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ffmpeg', 'bin', 'ffmpeg.exe')
        ffmpeg_log = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'log', 'ffmpeg.log')

        for i, o in zip(input_file, output_lst):
            command = [
                ffmpeg_path,
                i,
                '-c', 'copy',
                '-bsf:v', 'h264_mp4toannexb',
                '-f', 'mpegts',
                '-y',
                o
            ]
            # print(' '.join(command))
            subprocess.call(' '.join(command), stdout=open(ffmpeg_log, 'a'), stderr=open(ffmpeg_log, 'a'))

        op_cmd = '\"%s\"' % ('concat:' + '|'.join(output_lst))

        command = [
            ffmpeg_path,
            '-i', op_cmd,
            '-c', 'copy',
            '-bsf:a', 'aac_adtstoasc',
            '-movflags', '+faststart',
            '-y',
            output_file
        ]
        subprocess.call(' '.join(command), stdout=open(ffmpeg_log, 'a'), stderr=open(ffmpeg_log, 'a'))

        for tsop in output_lst:
            os.remove(tsop)
            logger.info('%s has been removed.' % tsop)

        if live_info['need_mask'] == '1':
            mask_path = os.path.join(live_info['base_path'], 'mask.jpg')
            output_file2 = output_file.replace('.mp4', '') + '_mask.mp4'
            command = [
                ffmpeg_path,
                '-i', output_file,
                '-i', mask_path,
                '-filter_complex', 'overlay',
                '-ac', '2',
                '-ab', '300000',
                '-y',
                output_file2
            ]
            subprocess.call(' '.join(command), stdout=open(ffmpeg_log, 'a'), stderr=open(ffmpeg_log, 'a'))
            logger.info('%s[RoomID:%s]转码完成' % (live_info['uname'], live_info['room_id']))
            return output_file2, filename

        logger.info('%s[RoomID:%s]转码完成' % (live_info['uname'], live_info['room_id']))
        return output_file, filename

    def decodeAndupload(self, live_info):
        logger.info('%s 等待转码上传' % (live_info['uname']))
        with self._lock2:
            logger.info('%s 开始转码' % (live_info['uname']))
            # 这两个参数存到live_info里
            live_info['filepath'], live_info['filename'] = self.decode(live_info)


    def enqueue(self, live_info):
        with self._lock:
            unames = {}
            for i in range(len(self.decode_queue)):
                unames[self.decode_queue[i]['uname']] = i
            if live_info['uname'] not in unames:
                self.decode_queue.append(live_info)
                logger.info('%s 进入转码等待队列' % live_info['uname'])
            else:
                del self.decode_queue[unames[live_info['uname']]]
                self.decode_queue.append(live_info)
                logger.info('%s 在转码等待队列中的状态更新了' % live_info['uname'])
            unames = [i['uname'] for i in self.decode_queue]
            logger.info('当前转码队列情况: %s' % (' '.join(unames)))

    def dequeue(self):
        with self._lock:
            with self._lock2:
                if len(self.decode_queue) > 0:
                    live_info = self.decode_queue[0]
                    del self.decode_queue[0]
                    logger.info('%s 退出转码等待队列' % live_info['uname'])
                    unames = [i['uname'] for i in self.decode_queue]
                    logger.info('当前转码队列情况: %s' % (' '.join(unames)))
                    return live_info
                else:
                    return None

    def run(self):
        while True:
            if len(self.decode_queue) > 0:
                live_info = self.dequeue()
                t = threading.Thread(target=self.decodeAndupload, args=[live_info, ])
                t.setDaemon(True)
                t.start()
