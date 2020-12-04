import os
import re
import sys
import time
import urllib
import logging
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
from utils.bilibili_api import live,user,Verify

console = Console()
headers = {
    'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding':'gzip, deflate',
    'Accept-Language':'zh-CN,zh;q=0.9,en;q=0.8',
    'Cache-Control':'max-age=0',
    'Connection':'keep-alive',
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36 Edg/86.0.622.69'
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
为了避免anchor的网络过差引起的下载流中断，需要重写下载逻辑，增强连接稳定性
'''

class Live():
    def __init__(self):
        self.config = Config()
        self.cookies = login()
        logger.info(self.cookies)
        self.verify = Verify(sessdata=self.cookies['SESSDATA'], csrf=self.cookies['bili_jct'])
        self.base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),self.config.output.path)
        self.live_infos = {}
        self.display = Display()
        logger.info('基路径:%s' % (self.base_path))
        logger.info('检查帐号状态:%s' % (self.verify.check()))
        if self.verify.check()['code'] != 0:
            logger.info('账号状态异常，请检查配置信息！verify.check = %s' % (self.verify.check()))
            raise RuntimeError('user error')
        self.load_multi_para('starttime',self.config.time.starttime)
        self.load_multi_para('need_mask',self.config.live.need_mask)
        self.load_multi_para('need_rec',self.config.live.need_rec)
        self.get_live_url()

        logger.info('初始化完成')

    def load_multi_para(self,para,conf):
        for id,p in zip(self.config.live.room_ids.split(','),conf.split(',')):
            if id not in self.live_infos:
                self.live_infos[id] = {}
                self.live_infos[id]['record_start_time'] = ''
            self.live_infos[id][para] = p
    
    def get_live_url(self):
        '''
        获取所有监听直播间的信息
        '''
        for id in self.config.live.room_ids.split(','):
            info = live.get_room_info(id,verify=self.verify,cookies=self.cookies)
            time.sleep(1)
            self.live_infos[id]['room_id'] = id
            self.live_infos[id]['real_id'] = info['room_info']['room_id']
            self.live_infos[id]['live_status'] = info['room_info']['live_status']
            # self.live_infos[id]['live_url'] = live.get_room_play_url(info['room_info']['room_id'],verify=self.verify, cookies=self.cookies)['durl'][0]['url']
            # time.sleep(1)
            self.live_infos[id]['uid'] = info['room_info']['uid']
            self.live_infos[id]['uname'] = info['anchor_info']['base_info']['uname']
            self.live_infos[id]['save_name'] = '%s_%s.flv' % (self.live_infos[id]['uname'],time.strftime("%Y%m%d%H%M%S", time.localtime()))
            self.live_infos[id]['title'] = info['room_info']['title']
            self.live_infos[id]['live_start_time'] = info['room_info']['live_start_time']
            if 'recording' not in self.live_infos[id]:
                self.live_infos[id]['recording'] = False
            logger.info('%s[RoomID:%s]直播状态\t%s' % (self.live_infos[id]['uname'],id,self.live_infos[id]['live_status']))
        self.display.refresh_info(self.live_infos)

    def download_live(self,key):
        if self.live_infos[key]['live_status'] == 1 and self.live_infos[key]['need_rec'] == '1':
            save_path = os.path.join(self.base_path,self.live_infos[key]['uname'],'recording')
            logger.info('%s[RoomID:%s]开播了,准备下载直播流,保存在%s' % (self.live_infos[key]['uname'],key,save_path))
            self.live_infos[key]['recording'] = True
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            session = streamlink.Streamlink()
            session.set_option("http-cookies",self.cookies)
            session.set_option("http-headers",headers)
            session.set_loglevel("info")
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),'log','stream.log')
            session.set_loglevel("debug")
            session.set_logoutput(log_path)
            streams = session.streams('https://live.bilibili.com/%s' % key)
            try:
                stream = streams['best']
            except:
                stream = streams['source']
            filename=os.path.join(save_path,self.live_infos[key]['save_name'])
            self.live_infos[key]['record_start_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            fd = stream.open()
            with open(filename,'wb') as f:
                while True:
                    try:
                        data = fd.read(1024)
                        f.write(data)
                    except Exception as e:
                        fd.close()
                        logger.info('%s[RoomID:%s]似乎下播了' % (self.live_infos[key]['uname'],key))
                        self.live_infos[key]['recording'] = False
                        logger.error(e)
                        raise e

    # def download_live(self,key):
    #     '''
    #     直播流下载
    #     '''
    #     if self.live_infos[key]['live_status'] == 1 and self.live_infos[key]['need_rec'] == '1':
    #         save_path = os.path.join(self.base_path,self.live_infos[key]['uname'],'recording')
    #         logger.info('%s[RoomID:%s]开播了,准备下载直播流,保存在%s' % (self.live_infos[key]['uname'],key,save_path))
    #         self.live_infos[key]['recording'] = True
    #         if not os.path.exists(save_path):
    #             os.makedirs(save_path)
            
    #         opener = urllib.request.build_opener()
    #         opener.addheaders = [
    #             ('Accept','text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'),
    #             ('Accept-Encoding','gzip, deflate'),
    #             ('Accept-Language','zh-CN,zh;q=0.9,en;q=0.8'),
    #             ('Cache-Control','max-age=0'),
    #             ('Connection','keep-alive'),
    #             ('User-Agent','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36 Edg/86.0.622.69')
    #             ]
    #         urllib.request.install_opener(opener)
    #         self.live_infos[key]['record_start_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    #         urllib.request.urlretrieve(self.live_infos[key]['live_url'], filename=os.path.join(save_path,self.live_infos[key]['save_name']))
    #         logger.info('%s[RoomID:%s]似乎下播了' % (self.live_infos[key]['uname'],key))
    #         self.live_infos[key]['recording'] = False

    def run(self):
        a = threading.Thread(target=self.display.run)
        a.setDaemon(True)
        a.start()
        while True:
            self.get_live_url()
            for key in self.live_infos:
                if not self.live_infos[key]['recording']:
                    t = threading.Thread(target=self.download_live,args=[key,])
                    t.setDaemon(True)
                    t.start()
                    s = threading.Thread(target=self.detect_live,args=[key,])
                    s.setDaemon(True)
                    s.start()
                time.sleep(0.2)
            time.sleep(1)

    def detect_live(self,key):
        '''
        录播状态直接释放守护线程
        如果复播，则线程释放，由新的守护线程接管
        如果1个小时都还没有复播，那应该是下播了
        '''
        timer = 0
        retry = 0
        living = 0
        while True:
            time.sleep(1)
            if self.live_infos[key]['live_status'] == 2 and living == 0:
                break
            if self.live_infos[key]['live_status'] == 1 and timer > 0:
                retry += 1
                if retry > 10:
                    break
            elif self.live_infos[key]['live_status'] == 1:
                living += 1
            elif not self.live_infos[key]['live_status'] == 1:
                timer += 1
            if (timer >= 3600 or self.live_infos[key]['live_status'] == 2) and living > 0:
                logger.info('%s[RoomID:%s]确认下播，开始转码上传' % (self.live_infos[key]['uname'],key))
                filepath,filename = self.flv2mp4(key)
                # Upload(self.live_infos[key]['uname'],key,filepath,filename,self.verify).upload()
                break

    def flv2mp4(self,key):
        '''
        当前逻辑是
        从最近的一个flv文件向前数12小时，合并所有录播
        先把每个flv转ts，再ts合MP4
        最后给视频加黑色遮挡
        '''        
        save_path = os.path.join(self.base_path,self.live_infos[key]['uname'])
        time_lst = []
        flst = []
        for f in os.listdir(os.path.join(save_path,'recording')):
            if 'flv' in f:
                flst.append(f)
        flst = sorted(flst,key=lambda x:x.split('_')[-1].split('.')[0])
        for f in flst:
            time_lst.append(datetime.datetime.fromtimestamp(os.stat(os.path.join(save_path,'recording',f)).st_mtime))
        latest_time = time_lst[-1]
        input_file = []
        for f,t in zip(flst,time_lst):
            if (latest_time - t).total_seconds() < int(self.config.time.maxsecond):
                input_file.append(f)

        output_file = re.search(r'.*?_\d{8}',input_file[0]).group()+'.mp4'
        filename = output_file.replace('.mp4','')

        logger.info('%s[RoomID:%s]本次录制文件:%s\t最终上传:%s' % (self.live_infos[key]['uname'],key,' '.join(input_file),filename))

        output_lst = []
        for i in input_file:
            output_lst.append(os.path.join(save_path,'recording',i.replace('.flv','.ts')))

        for i in range(len(input_file)):
            input_file[i] = '-i '+os.path.join(save_path,'recording',input_file[i])

        output_file = os.path.join(save_path,output_file)
        ffmpeg_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'ffmpeg','bin','ffmpeg.exe')

        for i,o in zip(input_file,output_lst):
            command = [
                ffmpeg_path,
                i,
                '-c', 'copy',
                '-bsf:v','h264_mp4toannexb',
                '-f','mpegts',
                o
            ]
            # print(' '.join(command))
            subprocess.call(' '.join(command))
        
        op_cmd = '\"%s\"' % ('concat:'+'|'.join(output_lst))

        command = [
            ffmpeg_path,
            '-i',op_cmd,
            '-c', 'copy',
            '-bsf:a', 'aac_adtstoasc',
            '-movflags','+faststart',
            '-y',
            output_file
        ]
        subprocess.call(' '.join(command))

        for tsop in output_lst:
            os.remove(tsop)
            logger.info('%s has been removed.' % tsop)

        logger.info('%s[RoomID:%s]转码完成' % (self.live_infos[key]['uname'],key))

        if self.live_infos[key]['need_mask'] == '1':
            mask_path = os.path.join(self.base_path,'mask.jpg')
            output_file2 = output_file.replace('.mp4','') + '_mask.mp4'
            command = [
                ffmpeg_path,
                '-i', output_file,
                '-i', mask_path,
                '-filter_complex', 'overlay',
                '-y',
                output_file2
            ]
            subprocess.call(' '.join(command))
            return output_file2,filename

        return output_file,filename
        # print(' '.join(command))

# l = Live()
# console.print(bilibili_api.channel.get_channel_info_by_name('生活'))
# l.run()
# while True:
#     l.get_live_url()
# console.print(live.get_room_info('2603963'))
# filepath,filename = l.flv2mp4('2603963')
# print(l.flv2mp4('2603963'))
# Upload(l.live_infos['2603963']['uname'],'2603963',filepath,filename,l.verify).upload()
