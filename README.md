# bilibili_autorec  哔哩哔哩自动录播机

## README基本完工

## 功能

* [x] 监测是否开播，开播后自动录制
* [x] 自动合并可能出现的多片flv并转码，可根据需要选择是否遮挡画面
* [x] 自动上传录播
* [x] 实时监控输出
* [x] 配置文件热更新，无需重启即可监测

## 如何使用

1. 下载[ffmpeg](https://www.gyan.dev/ffmpeg/builds/)，下载ffmpeg-release-full版本，解压后重命名为ffmpeg，放在utils路径下
2. pip install -r requirements.txt
3. 根据提示修改demo配置文件，修改配置文件名为tool.toml
4. python main.py

## 用到的开源项目

* [bilibili_api](https://github.com/Passkou/bilibili_api)
* [rich](https://github.com/willmcgugan/rich)
* [FFmpeg](https://github.com/FFmpeg/FFmpeg)
* [Bilibili-Toolkit](https://github.com/Hsury/Bilibili-Toolkit)
* [streamlink](https://github.com/streamlink/streamlink)
* [keyboard](https://github.com/boppreh/keyboard)
* [Windows-10-Toast-Notifications](https://github.com/jithurjacob/Windows-10-Toast-Notifications)
* [BaiduPCS-Go](https://github.com/qjfoidnh/BaiduPCS-Go)