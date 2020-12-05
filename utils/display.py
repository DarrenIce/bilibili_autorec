import time
import datetime
from utils.rich.live import Live
from utils.rich.table import Table
from utils.rich.console import Console
from typing_extensions import Literal
from dataclasses import dataclass

@dataclass
class Info:
    row_id: int
    room_id: str
    anchor: str
    title: str
    live_status: Literal['[greed]直播中','[yellow]录播中','[red]未开播','[blue]轮播中']
    record_status: Literal['[green]录制中','[red]未录制']
    start_time: str
    record_start_time: str
    # live_url: str

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
        if self.record_status:
            return '[green]录制中'
        else:
            return '[red]未录制'

    @property
    def record_time(self) -> str:
        if self.record_start_time != '':
            return str(datetime.datetime.now() - datetime.datetime.strptime(self.record_start_time,'%Y-%m-%d %H:%M:%S'))
        else:
            return '0s'

class Display():
    def __init__(self):
        self.console = Console(force_terminal=True,color_system='truecolor')
        self.console._environ['TERM'] = 'SMART'     

    def generate_info(self,row_id: int,live_info: dict) -> Info:
        return Info(
            row_id = row_id,
            room_id = live_info['room_id'],
            anchor = live_info['uname'],
            title = live_info['title'],
            live_status = live_info['live_status'],
            record_status = live_info['recording'],
            start_time = datetime.datetime.fromtimestamp(live_info['live_start_time']).strftime('%Y-%m-%d %H:%M:%S'),
            record_start_time = live_info['record_start_time'],
            # live_url = live_info['live_url']
        )

    def create_info_table(self,live_infos):
        dct = {0:0,1:100,2:50}
        infos = sorted(
            [self.generate_info(rid,live_infos[key]) for key,rid in zip(live_infos.keys(),range(len(live_infos)))],
            key = lambda i: dct[i.live_status] + 30 * i.record_status - i.row_id,
            reverse=True
        )
        table = Table(
            "行号","房间ID","主播","直播标题","直播状态","录制状态","开播时间","录制时长",title="监控面板 %s" % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

        for info in infos:
            table.add_row(
                str(info.row_id),
                info.room_id,
                info.anchor,
                info.title,
                info.live_status_map,
                info.record_status_map,
                info.start_time,
                info.record_time,
                # info.live_url
            )
        return table

    def run(self):
        with Live(console=self.console, transient=True, auto_refresh=False) as live:
            while True:
                live.update(self.create_info_table(self.live_infos), refresh=True)
                time.sleep(1)

    def refresh_info(self,live_infos):
        self.live_infos = live_infos