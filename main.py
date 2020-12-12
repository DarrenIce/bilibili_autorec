from utils.live import Live
import os
import subprocess
import threading
from apscheduler.schedulers.blocking import BlockingScheduler
import datetime 
import keyboard
from utils.threadRecoder import threadRecorder

log_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'log')
keyboard.add_hotkey('ctrl+alt+;', os._exit, args=[0])
if not os.path.exists(log_path):
    os.mkdir(log_path)
log_file = os.path.join(log_path, 'log.log')
stream_log_file = os.path.join(log_path, 'stream.log')
ffmpeg_log_file = os.path.join(log_path, 'ffmpeg.log')
if not os.path.exists(log_file):
    with open(log_file, 'w', encoding='utf-8') as a:
        pass
if not os.path.exists(stream_log_file):
    with open(stream_log_file, 'w', encoding='utf-8') as a:
        pass
if not os.path.exists(ffmpeg_log_file):
    with open(ffmpeg_log_file, 'w', encoding='utf-8') as a:
        pass

live = Live()
threadRecorder = threadRecorder()

def main():
    threading.Thread(target=threadRecorder.heartbeat).start()
    threadRecorder.add('daily_job',scheduler_run,None,False)
    live.start()
    

def daily_job():
    PCSpath = r'.\utils\BaiduPCS-Go.exe'
    local_base_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'rec')
    pcs_base_path = '录播/%s'
    live_infos = live.live_infos.copy()
    for key in live_infos:
        name = live_infos[key]['uname']
        base_path = os.path.join(local_base_path,name)
        if os.path.exists(base_path):
            a = subprocess.run([PCSpath,"mkdir",pcs_base_path % name])
            print(a)
            for f in os.listdir(base_path):
                if os.path.isfile(os.path.join(base_path,f)):
                    if '_mask' not in f:
                        x = f.rstrip('.mp4').lstrip(name+'_')
                        if (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y%m%d') == x:
                            a = subprocess.run([PCSpath,'upload',os.path.join(base_path,f),pcs_base_path % name])
                            print(a)

def scheduler_run():
    scheduler = BlockingScheduler()
    scheduler.add_job(daily_job,'cron',day_of_week='0-6',hour=7,minute=1)
    scheduler.start()

if __name__ == '__main__':
    main()
