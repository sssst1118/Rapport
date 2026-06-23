"""常驻 always-on 后台录音子包。

把「分段决策逻辑」与「真实麦克风/线程」彻底分开：
- segmenter：纯逻辑，对音频帧/RMS 能量做静音切分，零硬件依赖、可纯单测。
- daywav：按天滚动 WAV 的增量追加 + 头长度字段更新，可被 Range 流式播放。
- status：录制状态文件的原子读写，供 /api/status 读。
- engine：常驻引擎，串起采集→切句→转写→分离→续写当天 conversation→落 day-WAV。
"""

from __future__ import annotations
