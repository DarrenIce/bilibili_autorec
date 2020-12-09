import os
import time
import datetime
import threading
import streamlink
from utils.log import Log
from utils.upload import Upload
from utils.tools import login
from utils.rich.console import Console
from utils.display import Display
from utils.load_conf import Config
from utils.decoder import Decoder
from utils.infos import Infos
from utils.bilibili_api import live
from win10toast import ToastNotifier

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
√   合并完成后删除ts中间项                        
√   合并完成后给视频增加黑色遮挡，上传遮挡版本      
√   可以在配置中选择是否加黑色遮挡                 
√   输出优化                                    
√   增加日志输出                                 
可以判断是否开始录播
√   配置选择是否录制                             
√   显示录制时长                                
√   为了避免anchor的网络过差引起的下载流中断，需要重写下载逻辑，增强连接稳定性      
√   声音压得有点厉害，需要调一下参数            
√   实时监测cfg                            
√   优化日志逻辑        
√   去掉starttime这个key，改成每个主播的直播时长 maxsecond      
√   确认真正下播逻辑，然后再执行转码，不然CPU扛不住了   --  限制了下播逻辑，正在确认准确性        
√   或者设置一个转码队列，按顺序进行转码      
√   live_info加一个key,base_path = self.base_path，可以一直更新       
√   live_info加一个key,cookies     
√   转码队列可以去掉uname和filename相同的过早项        
√   可以设置录制的起始和结束时间，为了避免录到录播的办法
√   修改上传逻辑，维护一个上传队列，每一个加进去会有3600的EXPIRE，退到0时退出队列开始上传，如果EXPIRE期间有同名加入，则重新开始
当前都是以uname作为重复判断条件，如果有问题再说
√   卡死问题需要解决，昨晚应该是死锁导致，目前已解决
√   输出频闪问题，是因为decoder线程的while循环没有sleep，一直在占用CPU，影响了rich的输出。
√   设置log level、expire等参数为配置文件，部分可以作为动态调整参数。记得提醒user根据自己电脑配置设置expire,或者每次上传前先os检测一下，没有就放回队列
√   加一个CPU、内存、网络占用显示
√   singleton queue 消息队列
'''


class Live():
    def __init__(self):
        self.config = Config()
        self.cookies = login()
        logger.info(self.cookies)
        self.base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                                      self.config.config['output']['path'])
        self.live_infos = Infos()
        self.display = Display()
        self.decoder = Decoder()
        self.uploader = Upload()
        logger.info('基路径:%s' % (self.base_path))
        self.load_room_info()
        self.get_live_url()
        logger.info('初始化完成')

    def create_duration(self, start_time, end_time):
        t = datetime.datetime.now()
        tt = t.strftime('%Y%m%d %H%M%S')
        if start_time == end_time == '0':
            return '0'
        tmp = datetime.datetime.strptime(tt.split(' ')[0] + ' %s' % start_time, '%Y%m%d %H%M%S')
        if t > tmp:
            base_time1 = tt.split(' ')[0]
            base_time2 = (t + datetime.timedelta(days=1)).strftime('%Y%m%d %H%M%S').split(' ')[0]
        else:
            base_time1 = (t - datetime.timedelta(days=1)).strftime('%Y%m%d %H%M%S').split(' ')[0]
            base_time2 = tt.split(' ')[0]
        if start_time > end_time:
            start_time = '%s %s' % (base_time1, start_time)
            end_time = '%s %s' % (base_time2, end_time)
        else:
            start_time = '%s %s' % (tt.split(' ')[0], start_time)
            end_time = '%s %s' % (tt.split(' ')[0], end_time)
        return '%s-%s' % (start_time, end_time)

    def check_live(self, key):
        duration = self.live_infos.get(key)['duration']
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
                logger.debug('%s[RoomID:%s]不在直播时间段' % (self.live_infos.get(key)['uname'], key))
                return False
        else:
            return False

    def load_room_info(self):
        live_infos = self.live_infos.copy()
        for lst in self.config.config['live']['room_info']:
            if lst[0] not in live_infos:
                live_info = {}
                live_info['record_start_time'] = ''
            else:
                live_info = live_infos[lst[0]]
            live_info['need_rec'] = lst[1]
            live_info['need_mask'] = lst[2]
            live_info['maxsecond'] = lst[3]
            live_info['need_upload'] = lst[4]
            live_info['duration'] = self.create_duration(lst[5], lst[6])
            live_info['cookies'] = self.cookies
            live_info['base_path'] = self.base_path
            self.live_infos.update(lst[0],live_info)

    def load_realtime(self):
        '''
        实时加载配置，更新房间信息
        '''
        self.config.load_cfg()
        # logger.info(self.config.config)
        room_lst = [i[0] for i in self.config.config['live']['room_info']]
        del_lst = []
        for key in self.live_infos.copy():
            if key not in room_lst:
                del_lst.append(key)
        for key in del_lst:
            self.live_infos.delete(key)
        self.load_room_info()

    def judge_in(self, key):
        room_lst = [i[0] for i in self.config.config['live']['room_info']]
        if key not in room_lst:
            return False
        return True

    def get_live_url(self):
        '''
        获取所有监听直播间的信息
        '''
        room_lst = [i[0] for i in self.config.config['live']['room_info']]
        for id in room_lst:
            info = None
            while info is None:
                try:
                    info = live.get_room_info(id, cookies=self.cookies)
                    time.sleep(0.3)
                except:
                    logger.error('[RoomID:%s]获取信息失败，重新尝试' % (id))
                    continue
            live_info = self.live_infos.copy()[id]
            live_info['room_id'] = id
            live_info['real_id'] = info['room_info']['room_id']
            try:
                if live_info['live_status'] != 1 and info['room_info']['live_status'] == 1:
                    logger.info('%s[RoomID:%s]开播了' % (live_info['uname'], id))
                    toaster = ToastNotifier()
                    toaster.show_toast("开播通知",
                                       '%s[RoomID:%s]开播了' % (live_info['uname'], id),
                                       icon_path=None,
                                       duration=3)
            except:
                pass
            try:
                live_info['live_status'] = info['room_info']['live_status']
                live_info['uid'] = info['room_info']['uid']
                live_info['uname'] = info['anchor_info']['base_info']['uname']
                live_info['save_name'] = '%s_%s.flv' % (
                    live_info['uname'], time.strftime("%Y%m%d%H%M%S", time.localtime()))
                live_info['title'] = info['room_info']['title']
                live_info['live_start_time'] = info['room_info']['live_start_time']
                if 'recording' not in live_info:
                    live_info['recording'] = 0
                self.live_infos.update(id,live_info)
                logger.debug(
                    '%s[RoomID:%s]直播状态\t%s' % (live_info['uname'], id, live_info['live_status']))
            except Exception as e:
                logger.critical(e)
                logger.error('[RoomID:%s]房间信息更新失败' % (id))
        # logger.info(self.live_infos.copy())

    def get_stream(self, key):
        '''
        获取直播流
        :param key: 房间显示id
        :return: stream
        '''
        if not self.judge_in(key):
            return None
        live_info = self.live_infos.copy()[key]
        logger.info('%s[RoomID:%s]获取直播流' % (live_info['uname'], key))
        session = streamlink.Streamlink()
        session.set_option("http-cookies", self.cookies)
        session.set_option("http-headers", headers)
        log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'log', 'stream.log')
        session.set_loglevel("debug")
        session.set_logoutput(open(log_path, 'a',encoding='utf-8'))
        streams = None
        while streams is None:
            try:
                streams = session.streams('https://live.bilibili.com/%s' % key)
            except:
                logger.warning('%s[RoomID:%s]获取直播流失败，正在重试' % (live_info['uname'], key))
                time.sleep(1)
        if streams == {}:
            logger.error('%s[RoomID:%s]未获取到直播流，可能是下播或者网络问题' % (live_info['uname'], key))
            return None
        if 'best' in streams:
            logger.info('%s[RoomID:%s]获取到best直播流' % (live_info['uname'], key))
            return streams['best']
        elif 'source' in streams:
            logger.info('%s[RoomID:%s]获取到source直播流' % (live_info['uname'], key))
            return streams['source']
        elif 'worst' in streams:
            logger.info('%s[RoomID:%s]获取到worst直播流' % (live_info['uname'], key))
            return streams['worst']
        else:
            logger.info('%s[RoomID:%s]未获取到直播流' % (live_info['uname'], key))
            return None

    def unlive(self, key, unlived):
        if not self.judge_in(key):
            return None
        live_info = self.live_infos.copy()[key]
        logger.info('%s[RoomID:%s]似乎下播了' % (live_info['uname'], key))
        live_info['recording'] = 0
        logger.info('%s[RoomID:%s]录制结束，录制了%.2f分钟' % (live_info['uname'], key, (
                datetime.datetime.now() - datetime.datetime.strptime(
            live_info['record_start_time'],
            '%Y-%m-%d %H:%M:%S')).total_seconds() / 60.0))
        live_info['record_start_time'] = ''
        if unlived:
            logger.info('%s[RoomID:%s]确认下播，加入转码上传队列' % (live_info['uname'], key))
            if live_info['need_upload'] == '1':
                live_info['filename'] = live_info['uname'] + live_info['duration'].split('-')[0].split(' ')[0]
                live_info['filepath'] = os.path.join(self.base_path, live_info['uname'], '%s_%s' % (live_info['uname'], live_info['duration'].split('-')[0].split(' ')[0]))
                if live_info['need_mask'] == '1':
                    live_info['filepath'] += '_mask.mp4'
                else:
                    live_info['filepath'] += '.mp4'
            self.decoder.enqueue(key)
        self.live_infos.update(key,live_info)    

    def download_live(self, key):
        if not self.judge_in(key):
            return None

        if self.live_infos.get(key)['live_status'] != 1:
            self.live_infos.get(key)['recording'] = 0
            return

        if not self.check_live(key) and self.live_infos.get(key)['live_status'] == 1:
            self.live_infos.get(key)['recording'] = 2
            return

        if self.check_live(key) and self.live_infos.get(key)['live_status'] == 1 and self.live_infos.get(key)['need_rec'] == '0':
            self.live_infos.get(key)['recording'] = 3
            return

        if self.live_infos.get(key)['live_status'] == 1 and self.live_infos.get(key)['need_rec'] == '1':
            save_path = os.path.join(self.base_path, self.live_infos.get(key)['uname'], 'recording')
            logger.info('%s[RoomID:%s]准备下载直播流,保存在%s' % (self.live_infos.get(key)['uname'], key, save_path))
            self.live_infos.get(key)['recording'] = 1
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            stream = self.get_stream(key)
            if stream is None:
                logger.error('%s[RoomID:%s]获取直播流失败' % (self.live_infos.get(key)['uname'], key))
                self.live_infos.get(key)['record_start_time'] = ''
                self.live_infos.get(key)['recording'] = 0
                return
            filename = os.path.join(save_path, self.live_infos.get(key)['save_name'])
            self.live_infos.get(key)['record_start_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            fd = stream.open()
            with open(filename, 'wb') as f:
                while self.judge_in(key) and self.live_infos.get(key)['live_status'] == 1 and self.live_infos.get(key)[
                    'need_rec'] == '1' and self.check_live(key):
                    try:
                        data = fd.read(1024 * 8)
                        if len(data) > 0:
                            f.write(data)
                        else:
                            fd.close()
                            logger.warning('%s[RoomID:%s]直播流断开,尝试重连' % (self.live_infos.get(key)['uname'], key))
                            stream = self.get_stream(key)
                            if stream is None:
                                logger.warning('%s[RoomID:%s]重连失败' % (self.live_infos.get(key)['uname'], key))
                                self.unlive(key, True)
                                return
                            else:
                                logger.info('%s[RoomID:%s]重连成功' % (self.live_infos.get(key)['uname'], key))
                                fd = stream.open()
                    except Exception as e:
                        fd.close()
                        logger.critical('%s[RoomID:%s]遇到了什么问题' % (self.live_infos.get(key)['uname'], key))
                        logger.error(e)
                        raise e
            fd.close()
            self.unlive(key, True)

    def run(self):
        threading.Thread(target=self.display.run,daemon=True).start()
        threading.Thread(target=self.decoder.run,daemon=True).start()
        threading.Thread(target=self.decoder.heartbeat,daemon=True).start()
        threading.Thread(target=self.uploader.run,daemon=True).start()
        threading.Thread(target=self.uploader.heartbeat,daemon=True).start()
        while True:
            time.sleep(1)
            self.load_realtime()
            self.get_live_url()
            live_infos = self.live_infos.copy()
            for key in live_infos:
                if live_infos[key]['recording'] != 1:
                    threading.Thread(target=self.download_live, args=[key, ],daemon=True).start()
                time.sleep(0.2)