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
'''


class Live():
    def __init__(self):
        self.config = Config()
        self.cookies = login()
        logger.info(self.cookies)
        self.base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                                      self.config.config['output']['path'])
        self.live_infos = {}
        self.display = Display()
        self.decoder = Decoder()
        self.upload = Upload()
        logger.info('基路径:%s' % (self.base_path))
        self.load_room_info()
        self.get_live_url()
        logger.info('初始化完成')

    def create_duration(self, start_time, end_time):
        t = datetime.datetime.now()
        tt = datetime.datetime.now().strftime('%Y%m%d %H%M%S')
        tmp = datetime.datetime.strptime(tt.split(' ')[0] + ' 000000', '%Y%m%d %H%M%S')
        if tmp < t:
            base_time1 = tt.split(' ')[0]
            base_time2 = (t + datetime.timedelta(days=1)).strftime('%Y%m%d %H%M%S').split(' ')[0]
        else:
            base_time1 = (t - datetime.timedelta(days=1)).strftime('%Y%m%d %H%M%S').split(' ')[0]
            base_time2 = tt.split(' ')[0]
        if start_time > end_time:
            start_time = '%s %s' % (base_time1, start_time)
            end_time = '%s %s' % (base_time2, end_time)
        else:
            start_time = '%s %s' % (base_time1, start_time)
            end_time = '%s %s' % (base_time1, end_time)
        return '%s-%s' % (start_time, end_time)

    def check_live(self, key):
        duration = self.live_infos[key]['duration']
        lst = duration.split('-')
        now_time = datetime.datetime.now()
        if len(lst) == 2:
            start_time = datetime.datetime.strptime(lst[0], '%Y%m%d %H%M%S')
            end_time = datetime.datetime.strptime(lst[1], '%Y%m%d %H%M%S')
            if now_time > start_time and now_time < end_time:
                return True
            else:
                return False
        else:
            return False

    def load_room_info(self):
        for lst in self.config.config['live']['room_info']:
            if lst[0] not in self.live_infos:
                self.live_infos[lst[0]] = {}
                self.live_infos[lst[0]]['record_start_time'] = ''
            self.live_infos[lst[0]]['need_rec'] = lst[1]
            self.live_infos[lst[0]]['need_mask'] = lst[2]
            self.live_infos[lst[0]]['maxsecond'] = lst[3]
            self.live_infos[lst[0]]['upload'] = lst[4]
            self.live_infos[str(lst[0])]['duration'] = self.create_duration(lst[5], lst[6])
            self.live_infos[lst[0]]['cookies'] = self.cookies
            self.live_infos[lst[0]]['base_path'] = self.base_path

    def load_realtime(self):
        self.config.load_cfg()
        logger.debug(self.config.config)
        room_lst = [i[0] for i in self.config.config['live']['room_info']]
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
            self.live_infos[id]['room_id'] = id
            self.live_infos[id]['real_id'] = info['room_info']['room_id']
            try:
                if self.live_infos[id]['live_status'] != 1 and info['room_info']['live_status'] == 1:
                    logger.info('%s[RoomID:%s]开播了' % (self.live_infos[id]['uname'], id))
                    toaster = ToastNotifier()
                    toaster.show_toast("开播通知",
                                       '%s[RoomID:%s]开播了' % (self.live_infos[id]['uname'], id),
                                       icon_path=None,
                                       duration=3)
            except:
                pass
            self.live_infos[id]['live_status'] = info['room_info']['live_status']
            self.live_infos[id]['uid'] = info['room_info']['uid']
            self.live_infos[id]['uname'] = info['anchor_info']['base_info']['uname']
            self.live_infos[id]['save_name'] = '%s_%s.flv' % (
                self.live_infos[id]['uname'], time.strftime("%Y%m%d%H%M%S", time.localtime()))
            self.live_infos[id]['title'] = info['room_info']['title']
            self.live_infos[id]['live_start_time'] = info['room_info']['live_start_time']
            if 'recording' not in self.live_infos[id]:
                self.live_infos[id]['recording'] = 0
            logger.debug(
                '%s[RoomID:%s]直播状态\t%s' % (self.live_infos[id]['uname'], id, self.live_infos[id]['live_status']))
            self.display.refresh_info(self.live_infos)
            logger.debug(self.live_infos)

    def get_stream(self, key):
        '''
        获取直播流
        :param key:
        :return:
        '''
        if key not in self.live_infos:
            return None
        logger.info('%s[RoomID:%s]获取直播流' % (self.live_infos[key]['uname'], key))
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
            logger.error('%s[RoomID:%s]未获取到直播流，可能是下播或者网络问题' % (self.live_infos[key]['uname'], key))
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

    def unlive(self, key, unlived):
        logger.info('%s[RoomID:%s]似乎下播了' % (self.live_infos[key]['uname'], key))
        self.live_infos[key]['recording'] = 0
        logger.info('%s[RoomID:%s]录制结束，录制了%.2f分钟' % (self.live_infos[key]['uname'], key, (
                datetime.datetime.now() - datetime.datetime.strptime(
            self.live_infos[key]['record_start_time'],
            '%Y-%m-%d %H:%M:%S')).total_seconds() / 60.0))
        self.live_infos[key]['record_start_time'] = ''
        if unlived:
            logger.info('%s[RoomID:%s]确认下播，加入转码上传队列' % (self.live_infos[key]['uname'], key))
            self.decoder.enqueue(self.live_infos[key])
            if self.live_infos[key]['upload'] == '1':
                self.live_infos[key]['filename'] = self.live_infos[key]['uname'] + \
                                                   self.live_infos[key]['duration'].split('-')[0].split(' ')[0]
                self.live_infos[key]['filepath'] = os.path.join(self.base_path, self.live_infos[key]['uname'],
                                                                '%s_%s' % (self.live_infos[key]['uname'],
                                                                           self.live_infos[key]['duration'].split('-')[
                                                                               0].split(' ')[0]))
                if self.live_infos[key]['need_mask'] == '1':
                    self.live_infos[key]['filepath'] += '_mask.mp4'
                else:
                    self.live_infos[key]['filepath'] += '.mp4'
                self.upload.enqueue(self.live_infos[key])

    def download_live(self, key):
        if key not in self.live_infos:
            return

        if self.live_infos[key]['live_status'] != 1:
            self.live_infos[key]['recording'] = 0
            return

        if not self.check_live(key) and self.live_infos[key]['live_status'] == 1:
            self.live_infos[key]['recording'] = 2
            return

        if self.check_live(key) and self.live_infos[key]['live_status'] == 1 and self.live_infos[key][
            'need_rec'] == '0':
            self.live_infos[key]['recording'] = 3
            return

        if self.live_infos[key]['live_status'] == 1 and self.live_infos[key]['need_rec'] == '1':
            save_path = os.path.join(self.base_path, self.live_infos[key]['uname'], 'recording')
            logger.info('%s[RoomID:%s]准备下载直播流,保存在%s' % (self.live_infos[key]['uname'], key, save_path))
            self.live_infos[key]['recording'] = 1
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            stream = self.get_stream(key)
            if stream is None:
                logger.error('%s[RoomID:%s]获取直播流失败' % (self.live_infos[key]['uname'], key))
                self.live_infos[key]['record_start_time'] = ''
                self.live_infos[key]['recording'] = 0
                return
            filename = os.path.join(save_path, self.live_infos[key]['save_name'])
            self.live_infos[key]['record_start_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            fd = stream.open()
            with open(filename, 'wb') as f:
                while key in self.live_infos and self.live_infos[key]['live_status'] == 1 and self.live_infos[key][
                    'need_rec'] == '1' and self.check_live(key):
                    try:
                        data = fd.read(1024 * 8)
                        if len(data) > 0:
                            f.write(data)
                        else:
                            fd.close()
                            logger.warning('%s[RoomID:%s]直播流断开,尝试重连' % (self.live_infos[key]['uname'], key))
                            stream = self.get_stream(key)
                            if stream is None:
                                logger.warning('%s[RoomID:%s]重连失败' % (self.live_infos[key]['uname'], key))
                                self.unlive(key, True)
                                return
                            else:
                                logger.info('%s[RoomID:%s]重连成功' % (self.live_infos[key]['uname'], key))
                                fd = stream.open()
                    except Exception as e:
                        fd.close()
                        logger.critical('%s[RoomID:%s]遇到了什么问题' % (self.live_infos[key]['uname'], key))
                        logger.error(e)
                        raise e
            fd.close()
            self.unlive(key, True)

    def run(self):
        a = threading.Thread(target=self.display.run,daemon=True)
        a.start()
        d = threading.Thread(target=self.decoder.run,daemon=True)
        d.start()
        u = threading.Thread(target=self.upload.run,daemon=True)
        u.start()
        while True:
            time.sleep(1)
            # logger.info(threading.enumerate())
            self.load_realtime()
            self.get_live_url()
            self.upload.remove(self.live_infos)
            for key in self.live_infos:
                if self.live_infos[key]['recording'] != 1:
                    t = threading.Thread(target=self.download_live, args=[key, ],daemon=True)
                    t.start()
                time.sleep(0.2)