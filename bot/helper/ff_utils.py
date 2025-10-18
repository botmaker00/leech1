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


async def merge_videos(video_paths, output_path):
    """
    Merge multiple videos into one.
    """
    file_list_path = "file_list.txt"
    with open(file_list_path, "w") as f:
        for path in video_paths:
            f.write(f"file '{path}'\n")

    command = [
        "ffmpeg",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        file_list_path,
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
    os.remove(file_list_path)
    if process.returncode != 0:
        return False, stderr.decode("utf-8")
    return True, None


async def merge_video_audio(video_path, audio_path, output_path):
    """
    Merge a video and an audio file.
    """
    command = [
        "ffmpeg",
        "-i",
        video_path,
        "-i",
        audio_path,
        "-c:v",
        "copy",
        "-c:a",
        "aac",
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


async def merge_video_subtitle(video_path, subtitle_path, output_path):
    """
    Merge a video and a subtitle file.
    """
    command = [
        "ffmpeg",
        "-i",
        video_path,
        "-i",
        subtitle_path,
        "-c",
        "copy",
        "-c:s",
        "mov_text",
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


async def hardsub_video(video_path, subtitle_path, output_path):
    """
    Hardcode subtitles into a video.
    """
    command = [
        "ffmpeg",
        "-i",
        video_path,
        "-vf",
        f"subtitles={subtitle_path}",
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


async def extract_stream(video_path, output_path, stream_specifier):
    """
    Extract a specific stream from a video.
    """
    command = [
        "ffmpeg",
        "-i",
        video_path,
        "-map",
        stream_specifier,
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


async def swap_stream(video_path, input_path, output_path, map_video, map_audio):
    """
    Swap streams between two files.
    """
    command = [
        "ffmpeg",
        "-i",
        video_path,
        "-i",
        input_path,
        "-map",
        map_video,
        "-map",
        map_audio,
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


async def remove_stream(video_path, output_path, stream_specifier):
    """
    Remove a specific stream from a video.
    """
    command = [
        "ffmpeg",
        "-i",
        video_path,
        "-map",
        "0",
        "-map",
        f"-{stream_specifier}",
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