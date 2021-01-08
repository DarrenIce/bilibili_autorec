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
        self.base_num = 1000

    def check_live(self, key):
        duration = self.infos.get(key)['duration']
        if duration == '0':
            return True
        lst = duration.split('-')
        now_time = datetime.datetime.now()
        if len(lst) == 2:
            start_time = datetime.datetime.strptime(lst[0], '%Y%m%d %H%M%S')
            end_time = datetime.datetime.strptime(lst[1], '%Y%m%d %H%M%S')
            if now_time > start_time and now_time < end_time:
                return True
            else:
                logger.debug('%s[RoomID:%s]不在直播时间段' % (self.infos.get(key)['uname'], key))
                return False
        else:
            return False

    def decode(self, key):
        '''
        当前逻辑是
        从最近的一个flv文件向前数12小时，合并所有录播
        先把每个flv转ts，再ts合MP4
        最后给视频加黑色遮挡
        '''
        max_time = 120
        try_time = 0
        room_lst = [i[0] for i in self.config.config['live']['room_info']]
        if key not in room_lst:
            return None

        while try_time < max_time:
            live_info = self.infos.copy()[key]
            if live_info['live_status'] == 1 and self.check_live(key):
                try_time += 1
                time.sleep(5)
            else:
                break
        
        if try_time >= max_time:
            logger.info('%s[RoomID:%s]直播中，暂不转码' % (live_info['uname'], live_info['room_id']))
            live_info['queue_status'] = 0
            self.infos.update(key,live_info)
            return None

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

        file_time = datetime.datetime.fromtimestamp(os.stat(os.path.join(save_path, 'recording', input_file[0])).st_ctime)
        if file_time < datetime.datetime.strptime(datetime.datetime.now().strftime('%Y%m%d %H%M%S').split(' ')[0] + ' 030000', '%Y%m%d %H%M%S'):
            ftime = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y%m%d %H%M%S').split(' ')[0]
        else:
            ftime = datetime.datetime.now().strftime('%Y%m%d %H%M%S').split(' ')[0]

        # output_file = re.search(r'.*?_\d{8}', input_file[0]).group() + '.mp4'
        # filename = ''.join(output_file.replace('.mp4', '').split('_'))
        filename = '%s%s' % (live_info['uname'],ftime)
        output_file = '%s_%s.mp4' % (live_info['uname'],ftime)
        output_file = os.path.join(save_path, output_file)
        live_info['filename'] = filename
        live_info['filepath'] = output_file
        if live_info['need_mask'] == '1':
            live_info['filepath'] = live_info['filepath'].replace('.mp4','_mask.mp4')

        logger.info(
            '%s[RoomID:%s]本次录制文件:%s\t最终上传:%s' % (
                live_info['uname'], live_info['room_id'], ' '.join(input_file), filename))

        output_lst = []
        for i in input_file:
            output_lst.append(os.path.join(save_path, 'recording', i.replace('.flv', '.ts')))

        for i in range(len(input_file)):
            input_file[i] = os.path.join(save_path, 'recording', input_file[i])

        ffmpeg_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ffmpeg', 'bin', 'ffmpeg.exe')
        ffmpeg_log = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'log', 'ffmpeg.log')
        file_path = os.path.join(save_path, 'recording', 'concat.txt')

        with open(file_path,'w',encoding='utf-8') as a:
            for line in output_lst:
                a.write('file \'%s\'\n' % line)

        for i, o in zip(input_file, output_lst):
            command = [
                ffmpeg_path,
                '-i', i,
                '-c', 'copy',
                '-y', o
            ]
            # print(' '.join(command))
            message = subprocess.run(command, stdout=open(ffmpeg_log, 'w'), stderr=open(ffmpeg_log, 'a'))
            logger.info(message)

        flag = False
        for o in output_lst:
            if json.loads(MediaInfo.parse(o).to_json())['tracks'][0]['overall_bit_rate'] > 4000000:
                flag = True

        if flag:
            command = [
                ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', file_path,
                '-c:v', 'libx264',
                '-c:a', 'copy',
                '-crf', '17',
                '-maxrate', '4M',
                '-bufsize', '4M',
                '-preset','fast',
                '-y', output_file
            ]
        else:
            command = [
                ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', file_path,
                '-c', 'copy',
                '-y', output_file
            ]
        message = subprocess.run(command, stdout=open(ffmpeg_log, 'w'), stderr=open(ffmpeg_log, 'a'))
        logger.info(message)

        command = [
            ffmpeg_path,
            '-f', 'concat',
            '-safe', '0',
            '-i', file_path, 
            '-vn',
            '-acodec', 'copy',
            '-y', output_file.replace('.mp4', '.m4a')
        ]
        message = subprocess.run(command)

        for tsop in output_lst:
            try:
                os.remove(tsop)
                logger.info('%s has been removed.' % tsop)
            except:
                logger.error('%s removed error.' % tsop)

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
            message = subprocess.run(command, stdout=open(ffmpeg_log, 'w'), stderr=open(ffmpeg_log, 'a'),timeout=3600)
            logger.info(message)
        if os.path.exists(output_file):
            logger.info('%s[RoomID:%s]转码完成' % (live_info['uname'], live_info['room_id']))
        else:
            logger.error('%s[RoomID:%s]转码失败' % (live_info['uname'], live_info['room_id']))
        self.infos.update(key,live_info)
        # if live_info['need_upload'] == '1':
        #     dura = json.loads(MediaInfo.parse(output_file).to_json())['tracks'][0]['duration']
        #     if dura >= 7200000:
        #         self.uploader.enqueue(key)
        #     else:
        #         logger.error('%s[RoomID:%s]录制时长不足' % (live_info['uname'], live_info['room_id']))
