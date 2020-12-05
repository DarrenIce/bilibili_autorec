import os
import re
import time
import datetime
import threading
import subprocess
import streamlink
import utils.bilibili_api
from utils.log import Log
from utils.tools import login
from utils.upload import Upload
from utils.rich.console import Console
from utils.display import Display
from utils.load_conf import Config
from utils.bilibili_api import live, user, Verify

console = Console()
headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36 Edg/86.0.622.69'
}
logger = Log()()

'''
TODO:
合并完成后删除ts中间项                        √
合并完成后给视频增加黑色遮挡，上传遮挡版本      √
可以在配置中选择是否加黑色遮挡                 √
输出优化                                    √
增加日志输出                                 √
可以判断是否开始录播
配置选择是否录制                             √
显示录制时长                                √
为了避免anchor的网络过差引起的下载流中断，需要重写下载逻辑，增强连接稳定性      √
声音压得有点厉害，需要调一下参数            √
实时监测cfg                             √
优化日志逻辑
优化保存路径
'''


class Live():
    def __init__(self):
        self.config = Config()
        self.cookies = login()
        logger.info(self.cookies)
        self.verify = Verify(sessdata=self.cookies['SESSDATA'], csrf=self.cookies['bili_jct'])
        self.base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                                      self.config.config['output']['path'])
        self.live_infos = {}
        self.display = Display()
        logger.info('基路径:%s' % (self.base_path))
        self.load_room_info()
        self.get_live_url()
        logger.info('初始化完成')


    def load_room_info(self):
        for lst in self.config.config['live']['room_info']:
            if str(lst[0]) not in self.live_infos:
                self.live_infos[str(lst[0])] = {}
                self.live_infos[str(lst[0])]['record_start_time'] = ''
            self.live_infos[str(lst[0])]['need_rec'] = str(lst[1])
            self.live_infos[str(lst[0])]['need_mask'] = str(lst[2])
            self.live_infos[str(lst[0])]['starttime'] = str(lst[3])

    def load_realtime(self):
        self.config.load_cfg()
        logger.debug(self.config.config)
        room_lst = [str(i[0]) for i in self.config.config['live']['room_info']]
        tmp_dct = {}
        for key in self.live_infos:
            if key in room_lst:
                tmp_dct[key] = self.live_infos[key]
        self.live_infos = tmp_dct
        self.load_room_info()

    def get_live_url(self):
        '''
        获取所有监听直播间的信息
        '''
        room_lst = [str(i[0]) for i in self.config.config['live']['room_info']]
        for id in room_lst:
            info = None
            while info is None:
                try:
                    info = live.get_room_info(id, verify=self.verify, cookies=self.cookies)
                    time.sleep(0.3)
                except:
                    logger.error('%s[RoomID:%s]获取信息失败，重新尝试' % (self.live_infos[id]['uname'], id))
                    continue
            self.live_infos[id]['room_id'] = id
            self.live_infos[id]['real_id'] = info['room_info']['room_id']
            self.live_infos[id]['live_status'] = info['room_info']['live_status']
            self.live_infos[id]['uid'] = info['room_info']['uid']
            self.live_infos[id]['uname'] = info['anchor_info']['base_info']['uname']
            self.live_infos[id]['save_name'] = '%s_%s.flv' % (
            self.live_infos[id]['uname'], time.strftime("%Y%m%d%H%M%S", time.localtime()))
            self.live_infos[id]['title'] = info['room_info']['title']
            self.live_infos[id]['live_start_time'] = info['room_info']['live_start_time']
            if 'recording' not in self.live_infos[id]:
                self.live_infos[id]['recording'] = False
            logger.debug(
                '%s[RoomID:%s]直播状态\t%s' % (self.live_infos[id]['uname'], id, self.live_infos[id]['live_status']))
            self.display.refresh_info(self.live_infos)

    def get_stream(self, key):
        '''
        获取直播流
        :param key:
        :return:
        '''
        if key not in self.live_infos:
            return None
        session = streamlink.Streamlink()
        session.set_option("http-cookies", self.cookies)
        session.set_option("http-headers", headers)
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'log', 'stream.log')
        session.set_loglevel("debug")
        session.set_logoutput(open(log_path, 'a+'))
        streams = None
        while streams is None:
            try:
                streams = session.streams('https://live.bilibili.com/%s' % key)
            except:
                logger.warning('%s[RoomID:%s]获取直播流失败，正在重试' % (self.live_infos[key]['uname'], key))
                time.sleep(1)
        if streams == {}:
            logger.error('%s[RoomID:%s]下播了' % (self.live_infos[key]['uname'], key))
            return None
        if 'best' in streams:
            logger.info('%s[RoomID:%s]获取到best直播流' % (self.live_infos[key]['uname'], key))
            return streams['best']
        elif 'source' in streams:
            logger.info('%s[RoomID:%s]获取到source直播流' % (self.live_infos[key]['uname'], key))
            return streams['source']
        elif 'worst' in streams:
            logger.info('%s[RoomID:%s]获取到worst直播流' % (self.live_infos[key]['uname'], key))
            return streams['worst']
        else:
            logger.info('%s[RoomID:%s]未获取到直播流' % (self.live_infos[key]['uname'], key))
            return None

    def unlive(self,key):
        logger.info('%s[RoomID:%s]下播了' % (self.live_infos[key]['uname'], key))
        self.live_infos[key]['recording'] = False
        logger.info('%s[RoomID:%s]录制结束，录制了%.2f分钟' % (self.live_infos[key]['uname'], key, (
                datetime.datetime.now() - datetime.datetime.strptime(
            self.live_infos[key]['record_start_time'],
            '%Y-%m-%d %H:%M:%S')).total_seconds() / 60.0))
        self.live_infos[key]['record_start_time'] = ''
        logger.info('%s[RoomID:%s]确认下播，开始转码上传' % (self.live_infos[key]['uname'], key))
        filepath, filename = self.flv2mp4(key)
        # Upload(self.live_infos[key]['uname'],key,filepath,filename,self.verify).upload()

    def download_live(self, key):
        if key not in self.live_infos:
            return
        if self.live_infos[key]['live_status'] == 1 and self.live_infos[key]['need_rec'] == '1':
            save_path = os.path.join(self.base_path, self.live_infos[key]['uname'], 'recording')
            logger.info('%s[RoomID:%s]开播了,准备下载直播流,保存在%s' % (self.live_infos[key]['uname'], key, save_path))
            self.live_infos[key]['recording'] = True
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            stream = self.get_stream(key)
            if stream is None:
                logger.error('%s[RoomID:%s]获取直播流失败' % (self.live_infos[key]['uname'], key))
                self.live_infos[key]['record_start_time'] = ''
                self.live_infos[key]['recording'] = False
                return
            filename = os.path.join(save_path, self.live_infos[key]['save_name'])
            self.live_infos[key]['record_start_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            fd = stream.open()
            with open(filename, 'wb') as f:
                while key in self.live_infos and self.live_infos[key]['live_status'] == 1 and self.live_infos[key]['need_rec'] == '1':
                    try:
                        data = fd.read(1024 * 8)
                        if len(data) == 8192:
                            f.write(data)
                        else:
                            fd.close()
                            logger.warning('%s[RoomID:%s]直播流断开,尝试重连' % (self.live_infos[key]['uname'], key))
                            stream = self.get_stream(key)
                            if stream is None:
                                self.unlive(key)
                                return
                            else:
                                logger.info('%s[RoomID:%s]重连成功' % (self.live_infos[key]['uname'], key))
                                fd = stream.open()
                    except Exception as e:
                        fd.close()
                        logger.info('%s[RoomID:%s]遇到了什么问题' % (self.live_infos[key]['uname'], key))
                        self.unlive(key)
                        logger.error(e)
                        raise e
            fd.close()
            self.unlive(key)

    def run(self):
        a = threading.Thread(target=self.display.run)
        a.setDaemon(True)
        a.start()
        while True:
            self.load_realtime()
            self.get_live_url()
            for key in self.live_infos:
                if not self.live_infos[key]['recording']:
                    t = threading.Thread(target=self.download_live, args=[key, ])
                    t.setDaemon(True)
                    t.start()
                time.sleep(0.2)
            time.sleep(1)

    def flv2mp4(self, key):
        '''
        当前逻辑是
        从最近的一个flv文件向前数12小时，合并所有录播
        先把每个flv转ts，再ts合MP4
        最后给视频加黑色遮挡
        '''
        save_path = os.path.join(self.base_path, self.live_infos[key]['uname'])
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
            if (latest_time - t).total_seconds() < int(self.config.config['live']['maxsecond']):
                input_file.append(f)

        output_file = re.search(r'.*?_\d{8}', input_file[0]).group() + '.mp4'
        filename = ''.join(output_file.replace('.mp4', '').split('_'))

        logger.info(
            '%s[RoomID:%s]本次录制文件:%s\t最终上传:%s' % (self.live_infos[key]['uname'], key, ' '.join(input_file), filename))

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

        if self.live_infos[key]['need_mask'] == '1':
            mask_path = os.path.join(self.base_path, 'mask.jpg')
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
            logger.info('%s[RoomID:%s]转码完成' % (self.live_infos[key]['uname'], key))
            return output_file2, filename

        logger.info('%s[RoomID:%s]转码完成' % (self.live_infos[key]['uname'], key))
        return output_file, filename
        # print(' '.join(command))

# l = Live()
# console.print(bilibili_api.channel.get_channel_info_by_name('生活'))
# Upload(l.live_infos['2603963']['uname'],'2603963',filepath,filename,l.verify).upload()
