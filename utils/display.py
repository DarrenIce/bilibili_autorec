import time
import datetime
from rich.live import Live
from rich.table import Table
from rich.console import Console
from rich import box
from rich.console import RenderGroup
from utils.infos import Infos
from utils.log import Log
from typing_extensions import Literal
from dataclasses import dataclass
import threading
import psutil

logger = Log()()

@dataclass
class Info:
    row_id: int
    room_id: str
    anchor: str
    title: str
    live_status: int
    record_status: int
    start_time: str
    record_start_time: str
    queue_status: int
    finish_time: str

    @property
    def room_id_map(self) -> str:
        return '[cornsilk1]%s' % (self.room_id)

    @property
    def anchor_map(self) -> str:
        return '[wheat1]%s' % (self.anchor)

    @property
    def title_map(self) -> str:
        return '[khaki1]%s' % (self.title)

    @property
    def start_time_map(self) -> str:
        return '[navajo_white1]%s' % (self.start_time)

    @property
    def live_status_map(self) -> str:
        if self.live_status == 1:
            return '[bold spring_green1]直播中'
        elif self.live_status == 2:
            return '[bold sky_blue2]轮播中'
        elif self.live_status == 4:
            return '[indian_red1]封禁中'
        else:
            return '[bold hot_pink3]未开播'

    @property
    def record_status_map(self) -> str:
        if self.record_status == 1:
            return '[bold spring_green1]录制中'
        elif self.record_status == 0:
            return '[bold hot_pink3]未录制'
        elif self.record_status == 2:
            return '[bold salmon1]不在直播期间'
        elif self.record_status == 3:
            return '[bold dark_olive_green1]不录制该房间'

    @property
    def record_time(self) -> str:
        if self.record_start_time != '':
            return '[misty_rose1]%s' % str((datetime.datetime.now() - datetime.datetime.strptime(self.record_start_time,'%Y-%m-%d %H:%M:%S'))).split('.')[0]
        else:
            return '[misty_rose1]0s'

    @property
    def queue_status_map(self) -> str:
        if self.queue_status == 0:
            return '[bold light_steel_blue]不在队列里哦'
        elif self.queue_status >= 1000 and self.queue_status < 2000:
            if self.queue_status == 1000:
                return '[bold spring_green1]正在转码'
            elif self.queue_status == 1500:
                return '[bold cyan]转码完成'
            else:
                return '[bold sky_blue2]等待转码中，目前为第%s个' % (self.queue_status % 1000)
        elif self.queue_status >=2000 and self.queue_status < 3000:
            if self.queue_status == 2000:
                return '[bold spring_green1]正在上传'
            elif self.queue_status == 2500:
                return '[bold medium_orchid3]上传完成'
            else:
                return '[bold sky_blue2]等待上传中，目前为第%s个' % (self.queue_status % 2000)
        else:
            return '[bold light_pink1 blink]收到了奇怪的参数'

    @property
    def finish_time_map(self) -> str:
        return '[thistle1]%s' % (self.finish_time)

class Display():
    def __init__(self):
        self.console = Console(force_terminal=True, color_system='truecolor')
        self.console._environ['TERM'] = 'SMART'
        self._lock = threading.Lock()
        self.live_infos = Infos()
        self.last_time = datetime.datetime.now()
        self.last_net_sent = 0.0
        self.last_net_recv = 0.0

    def generate_info(self, row_id: int, live_info: dict) -> Info:
        info = None
        while info is None:
            try:
                if live_info is not None and 'live_status' in live_info:
                    info = Info(
                        row_id=row_id,
                        room_id=live_info['room_id'],
                        anchor=live_info['uname'],
                        title=live_info['title'],
                        live_status=live_info['live_status'],
                        record_status=live_info['recording'],
                        start_time=datetime.datetime.fromtimestamp(live_info['live_start_time']).strftime(
                            '%Y-%m-%d %H:%M:%S'),
                        record_start_time=live_info['record_start_time'],
                        queue_status=live_info['queue_status'],
                        finish_time = live_info['finish_time']
                    )
                else:
                    break
            except Exception as e:
                continue
        return info

    def create_info_table(self, live_infos):
        dct = {0: 0, 1: 100, 2: 50, 4: 10}
        dct2 = {0: 0, 1: 100, 2: 50, 3: 30}
        infos = sorted(
            [self.generate_info(rid, live_infos[key]) for key, rid in
                zip(live_infos.keys(), range(len(live_infos)))],
            key=lambda i: dct[i.live_status] * 100 + 100 * dct2[i.record_status] - i.row_id + i.queue_status,
            reverse=True
        )
        table1 = Table(
            "行号", "房间ID", "主播", "直播标题", "直播状态", "录制状态", "开播时间", "录制时长","队列情况","完成时间",
            title="%s" % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            box=box.SIMPLE
        )

        for info in infos:
            table1.add_row(
                str(info.row_id),
                info.room_id_map,
                info.anchor_map,
                info.title_map,
                info.live_status_map,
                info.record_status_map,
                info.start_time_map,
                info.record_time,
                info.queue_status_map,
                info.finish_time_map
            )

        table2 = Table(
            "CPU","Memory","NetSent","NetRecv",
            box=box.SIMPLE
        )

        time_now = datetime.datetime.now()
        now_recv = psutil.net_io_counters().bytes_recv
        now_sent = psutil.net_io_counters().bytes_sent

        table2.add_row(
            str(psutil.cpu_percent(None))+'%' + '  %.2fGHz' % (psutil.cpu_freq().current/1000.0),
            str(psutil.virtual_memory().percent)+'%' + '  %s/%s' % (bytes2human(psutil.virtual_memory().used),bytes2human(psutil.virtual_memory().total)),
            bytes2human((now_sent-self.last_net_sent)/(time_now - self.last_time).total_seconds())+'/s',
            bytes2human((now_recv-self.last_net_recv)/(time_now - self.last_time).total_seconds())+'/s'
        )

        self.last_time = time_now
        self.last_net_sent = now_sent
        self.last_net_recv = now_recv

        return RenderGroup(
            table1,table2
        )

    def run(self):
        # self.console.clear()
        with Live(console=self.console, auto_refresh=False) as live:
            while True:
                try:
                    live.update(self.create_info_table(self.live_infos.copy()), refresh=True)
                    time.sleep(1)
                except Exception as e:
                    logger.critical(e)
                    continue

def bytes2human(n):
     symbols = ('K','M','G','T','P','E','Z','Y')
     prefix = {}
     for i,s in enumerate(symbols):
         prefix[s] = 1 << (i + 1) * 10
     for s in reversed(symbols):
         if n >= prefix[s]:
             value = float(n) / prefix[s]
             return '%.1f%s' % (value,s)
     return '%.1fB' % float(n)