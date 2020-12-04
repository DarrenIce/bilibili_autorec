# bilibili_autorec  哔哩哔哩自动录播机

## README正在施工中...

## 功能

* 监测是否开播，开播后自动录制
* 自动合并可能出现的多片flv并转码，可根据需要选择是否遮挡画面
* 自动上传录播
* 实时监控输出

## 如何使用

考虑把魔改过的包放在utils下
1. 
```python
pip install bilibili_api
pip install rich
```
2. 下载[ffmpeg](https://www.gyan.dev/ffmpeg/builds/)，下载ffmpeg-release-full版本，解压后重命名为ffmpeg，放在utils路径下
3. 新建log文件夹和log.log文件
4. 从[rich](https://github.com/willmcgugan/rich)的master分支下载最新代码，覆盖之前pip下载的rich


## 用到的开源项目

* [bilibili_api](https://github.com/Passkou/bilibili_api)
* [rich](https://github.com/willmcgugan/rich)
* [FFmpeg](https://github.com/FFmpeg/FFmpeg)
* [Bilibili-Toolkit](https://github.com/Hsury/Bilibili-Toolkit)
* [streamlink](https://github.com/streamlink/streamlink)