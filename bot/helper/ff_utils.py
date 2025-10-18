import asyncio
import json
import subprocess


async def get_video_info(video_path: str):
    """
    Get video information using ffprobe.
    """
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,size,bit_rate",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        return None, stderr.decode().strip()
    output = stdout.decode().strip().split("\n")
    return {
        "duration": float(output[0]),
        "size": int(output[1]),
        "bit_rate": int(output[2]),
    }, None


async def get_media_info(path):
    """
    Get media information using ffprobe.
    """
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        path,
    ]
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        return None, stderr.decode("utf-8")
    return json.loads(stdout), None


async def convert_video(video_path, output_path, preset="medium", crf=23):
    """
    Convert video to a different format or encoding.
    """
    command = [
        "ffmpeg",
        "-i",
        video_path,
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-c:a",
        "copy",
        output_path,
    ]
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        return False, stderr.decode("utf-8")
    return True, None




import os




async def trim_video(video_path, output_path, start_time, end_time):
    """
    Trim a video to a specific duration.
    """
    command = [
        "ffmpeg",
        "-i",
        video_path,
        "-ss",
        str(start_time),
        "-to",
        str(end_time),
        "-c",
        "copy",
        output_path,
    ]
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        return False, stderr.decode("utf-8")
    return True, None


async def add_watermark(
    video_path,
    output_path,
    watermark_text,
    position="bottom_right",
    opacity=0.8,
    font_size=24,
):
    """
    Add a text watermark to a video.
    """
    if position == "top_left":
        x, y = "10", "10"
    elif position == "top_right":
        x, y = "w-text_w-10", "10"
    elif position == "bottom_left":
        x, y = "10", "h-text_h-10"
    else:  # bottom_right
        x, y = "w-text_w-10", "h-text_h-10"

    command = [
        "ffmpeg",
        "-i",
        video_path,
        "-vf",
        f"drawtext=text='{watermark_text}':x={x}:y={y}:fontsize={font_size}:fontcolor=white@0.8",
        output_path,
    ]
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        return False, stderr.decode("utf-8")
    return True, None