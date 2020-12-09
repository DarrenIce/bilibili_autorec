import subprocess
from pymediainfo import MediaInfo
from utils.log import Log
from utils.queue import Queue
from utils.upload import Upload
import threading
import os
import re
import datetime
import time
import json

logger = Log()()


class Decoder(Queue):
    def __init__(self):
        super().__init__()
        self.qname = '转码'
        self.func = self.decode
        self.uploader = Upload()

    def decode(self, key):
        '''
        当前逻辑是
        从最近的一个flv文件向前数12小时，合并所有录播
        先把每个flv转ts，再ts合MP4
        最后给视频加黑色遮挡
        '''
        room_lst = [i[0] for i in self.config.config['live']['room_info']]
        if key not in room_lst:
            return None
        live_info = self.infos.copy()['key']
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
            width = json.loads(MediaInfo.parse(output_file).to_json())['tracks'][1]['width']
            height = json.loads(MediaInfo.parse(output_file).to_json())['tracks'][1]['height']
            logger.info('%s[RoomID:%s]视频分辨率 %s × %s' % (live_info['uname'], live_info['room_id'],width,height))
            if width == 1920:
                mask_path = os.path.join(live_info['base_path'], 'mask2.jpg')
            else:
                mask_path = os.path.join(live_info['base_path'], 'mask1.jpg')
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
        self.uploader.enqueue(key)
