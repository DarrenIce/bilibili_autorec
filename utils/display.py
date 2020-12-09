import time
import datetime
from utils.rich.live import Live
from utils.rich.table import Table
from utils.rich.console import Console
from utils.rich import box
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
    live_status: str
    record_status: str
    start_time: str
    record_start_time: str

    @property
    def live_status_map(self) -> str:
        if self.live_status == 1:
            return '[green]直播中'
        elif self.live_status == 2:
            return '[blue]轮播中'
        else:
            return '[red]未开播'

    @property
    def record_status_map(self) -> str:
        if self.record_status == 1:
            return '[green]录制中'
        elif self.record_status == 0:
            return '[red]未开播'
        elif self.record_status == 2:
            return '[blue]不在直播期间'
        elif self.record_status == 3:
            return '[yellow]不录制该房间'

    @property
    def record_time(self) -> str:
        if self.record_start_time != '':
            return str((datetime.datetime.now() - datetime.datetime.strptime(self.record_start_time,'%Y-%m-%d %H:%M:%S')))
        else:
            return '0s'

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
                info = Info(
                    row_id=row_id,
                    room_id=live_info['room_id'],
                    anchor=live_info['uname'],
                    title=live_info['title'],
                    live_status=live_info['live_status'],
                    record_status=live_info['recording'],
                    start_time=datetime.datetime.fromtimestamp(live_info['live_start_time']).strftime(
                        '%Y-%m-%d %H:%M:%S'),
                    record_start_time=live_info['record_start_time']
                )
            except Exception as e:
                continue
        return info

    def create_info_table(self, live_infos):
        dct = {0: 0, 1: 100, 2: 50}
        dct2 = {0: 0, 1: 100, 2: 50, 3: 30}
        infos = sorted(
            [self.generate_info(rid, live_infos[key]) for key, rid in
                zip(live_infos.keys(), range(len(live_infos)))],
            key=lambda i: dct[i.live_status] + 30 * dct2[i.record_status] - i.row_id,
            reverse=True
        )
        table1 = Table(
            "行号", "房间ID", "主播", "直播标题", "直播状态", "录制状态", "开播时间", "录制时长",
            title="%s" % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            box=box.SIMPLE
        )

        for info in infos:
            table1.add_row(
                str(info.row_id),
                info.room_id,
                info.anchor,
                info.title,
                info.live_status_map,
                info.record_status_map,
                info.start_time,
                info.record_time,
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
                live.update(self.create_info_table(self.live_infos.copy()), refresh=True)
                time.sleep(1)

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