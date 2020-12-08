import subprocess
import os
import datetime
from utils.live import Live

PCSpath = r'.\utils\BaiduPCS-Go.exe'
local_base_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'rec')
pcs_base_path = '录播/%s'
live = Live()

for key in live.live_infos:
    name = live.live_infos[key]['uname']
    a = subprocess.run([PCSpath,"mkdir",pcs_base_path % name])
    print(a)
    base_path = os.path.join(local_base_path,name)
    if os.path.exists(base_path):
        for f in os.listdir(base_path):
            if os.path.isfile(os.path.join(base_path,f)):
                if '_mask' not in f:
                    x = f.rstrip('.mp4').lstrip(name+'_')
                    if (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y%m%d') == x:
                        a = subprocess.run([PCSpath,'upload',os.path.join(base_path,f),pcs_base_path % name])
                        print(a)

a = a = subprocess.run([PCSpath,"share","set",'录播'])