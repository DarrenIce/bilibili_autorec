import subprocess
import os
import datetime
from utils.live import Live
from apscheduler.schedulers.blocking import BlockingScheduler
import keyboard
import threading
from utils.log import Log
import time

logger = Log()()



live = Live()
keyboard.add_hotkey(r'ctrl+/', os._exit, args=[0])
def daily_job():
    PCSpath = r'.\utils\BaiduPCS-Go.exe'
    local_base_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'rec')
    pcs_base_path = '/录播/%s'
    live_infos = live.live_infos.copy()
    for key in live_infos:
        name = live_infos[key]['uname']
        base_path = os.path.join(local_base_path,name)
        if os.path.exists(base_path):
            a = subprocess.run([PCSpath,"mkdir",pcs_base_path % name])
            print(a)
            print(base_path)
            for f in os.listdir(base_path):
                if os.path.isfile(os.path.join(base_path,f)):
                    if '_mask' not in f:
                        x = '.'.join(f.split('.')[:-1]).split('_')[-1]
                        print(x)
                        print((datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y%m%d'))
                        if (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y%m%d') == x:
                            # a = subprocess.run([PCSpath,'upload',os.path.join(base_path,f),pcs_base_path % name])
                            print(a)

# def test():
#     logger.info(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

# def scheduler_run():
#     scheduler = BlockingScheduler()
#     scheduler.add_job(test,'cron',day_of_week='0-6',hour=17,minute=10)
#     scheduler.start()

# threading.Thread(target=scheduler_run,daemon=True).start()
# while True:
#     time.sleep(1)
# a = a = subprocess.run([PCSpath,"share","set",'录播'])

daily_job()