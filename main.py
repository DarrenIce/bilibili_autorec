from utils.live import Live
import datetime
import os
from rich.console import Console
from bilibili_api import live
console = Console()
def main():
    log_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'log')
    if not os.path.exists(log_path):
        os.mkdir(log_path)
        log_file = os.path.join(log_path,'log.log')
        stream_log_file = os.path.join(log_path,'stream.log')
        with open(log_file,'w',encoding='utf-8') as a:
            pass
        with open(stream_log_file,'w',encoding='utf-8') as a:
            pass
    live = Live()
    live.run()

if __name__ == '__main__':
    main()
    # console.print(live.get_room_info('2603963'))
    # print(os.path.dirname(os.path.realpath(__file__)))
    # print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

# import requests

# headers = {
#     'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36 Edg/86.0.622.69',
#     'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
#     'accept-encoding':'gzip, deflate, br',
#     'accept-language':'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,zh-TW;q=0.5'
# }

# cookies = {
#     'SESSDATA':'d20ece5d%2C1622518849%2Cbfe3e*c1',
#     'bili_jct':'916b94679dccb53f177cd587128f3392'
# }

# r = requests.get('https://api.live.bilibili.com/xlive/web-room/v1/index/getRoomPlayInfo',{'room_id':'2603963'},cookies = cookies, headers = headers)

# print(r.text)