"""Gradio 界面：上传/录音音频 → 转写 → 显示文本。

gradio 为重依赖，仅在函数内部延迟导入，
保证未安装 gradio 时本模块仍可被导入（便于纯逻辑测试）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import gradio as gr


def _transcribe_path(audio_path: str | None) -> str:
    """转写单个音频文件并返回可读文本。

    供 Gradio 按钮回调使用；空输入时返回提示语。

    Args:
        audio_path: 音频文件路径，未提供音频时为 None。

    Returns:
        转写得到的可读文本，或提示信息。
    """
    from .. import config
    from ..transcribe.text import segments_to_text

    if not audio_path:
        return "请先上传或录制音频。"

    transcriber = config.get_transcriber()
    segments = transcriber.transcribe(audio_path)
    text = segments_to_text(segments)
    return text or "（未识别到文本）"


def build_app() -> "gr.Blocks":
    """构建并返回 Gradio 界面（不启动服务）。

    界面包含：音频输入（上传或麦克风）、转写按钮、结果文本框。

    Returns:
        已组装好的 gr.Blocks 实例。
    """
    import gradio as gr

    with gr.Blocks(title="Rapport") as demo:
        gr.Markdown("# Rapport\n本地优先的对话转写助手。")
        audio_in = gr.Audio(
            sources=["upload", "microphone"],
            type="filepath",
            label="音频",
        )
        transcribe_btn = gr.Button("转写", variant="primary")
        text_out = gr.Textbox(
            label="转写结果",
            lines=10,
        )
        transcribe_btn.click(
            fn=_transcribe_path,
            inputs=audio_in,
            outputs=text_out,
        )
    return demo


def launch(**kwargs: Any) -> None:
    """构建界面并启动 Gradio 服务。

    Args:
        **kwargs: 透传给 gr.Blocks.launch 的关键字参数
            （如 server_name、server_port、share 等）。
    """
    build_app().launch(**kwargs)
