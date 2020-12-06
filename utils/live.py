import os
import time
import datetime
import threading
import streamlink
from utils.log import Log
from utils.tools import login
from utils.rich.console import Console
from utils.display import Display
from utils.load_conf import Config
from utils.decoder import Decoder
from utils.bilibili_api import live

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
可以设置录制的起始和结束时间，为了避免录到录播的办法
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
            self.live_infos[str(lst[0])]['maxsecond'] = str(lst[3])
            self.live_infos[str(lst[0])]['upload'] = str(lst[4])
            self.live_infos[str(lst[0])]['cookies'] = self.cookies
            self.live_infos[str(lst[0])]['base_path'] = self.base_path

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
                    info = live.get_room_info(id, cookies=self.cookies)
                    time.sleep(0.3)
                except:
                    logger.error('%s[RoomID:%s]获取信息失败，重新尝试' % (self.live_infos[id]['uname'], id))
                    continue
            self.live_infos[id]['room_id'] = id
            self.live_infos[id]['real_id'] = info['room_info']['room_id']
            try:
                if self.live_infos[id]['live_status'] != 1 and info['room_info']['live_status'] == 1:
                    logger.info('%s[RoomID:%s]开播了' % (self.live_infos[id]['uname'], id))
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

    def unlive(self,key,unlived):
        logger.info('%s[RoomID:%s]似乎下播了' % (self.live_infos[key]['uname'], key))
        self.live_infos[key]['recording'] = False
        logger.info('%s[RoomID:%s]录制结束，录制了%.2f分钟' % (self.live_infos[key]['uname'], key, (
                datetime.datetime.now() - datetime.datetime.strptime(
            self.live_infos[key]['record_start_time'],
            '%Y-%m-%d %H:%M:%S')).total_seconds() / 60.0))
        self.live_infos[key]['record_start_time'] = ''
        if unlived:
            logger.info('%s[RoomID:%s]确认下播，加入转码上传队列' % (self.live_infos[key]['uname'], key))
            self.decoder.enqueue(self.live_infos[key])

    def download_live(self, key):
        if key not in self.live_infos:
            return
        if self.live_infos[key]['live_status'] == 1 and self.live_infos[key]['need_rec'] == '1':
            save_path = os.path.join(self.base_path, self.live_infos[key]['uname'], 'recording')
            logger.info('%s[RoomID:%s]准备下载直播流,保存在%s' % (self.live_infos[key]['uname'], key, save_path))
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
                                logger.warning('%s[RoomID:%s]重连失败' % (self.live_infos[key]['uname'], key))
                                self.unlive(key,False)
                                return
                            else:
                                logger.info('%s[RoomID:%s]重连成功' % (self.live_infos[key]['uname'], key))
                                fd = stream.open()
                    except Exception as e:
                        fd.close()
                        logger.critical('%s[RoomID:%s]遇到了什么问题' % (self.live_infos[key]['uname'], key))
                        self.unlive(key,False)
                        logger.error(e)
                        raise e
            fd.close()
            self.unlive(key,True)

    def run(self):
        a = threading.Thread(target=self.display.run)
        a.setDaemon(True)
        a.start()
        d = threading.Thread(target=self.decoder.run)
        d.setDaemon(True)
        d.start()
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
