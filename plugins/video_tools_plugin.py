from pyrogram import Client
from pyrogram.types import Message

from bot.core.plugin_manager import PluginBase, PluginInfo


user_settings_editor = {}


class VideoToolsPlugin(PluginBase):
    PLUGIN_INFO = PluginInfo(
        name="video_tools",
        version="1.0.0",
        author="Jules",
        description="A plugin to add video manipulation tools.",
        enabled=True,
        commands=[
            "video_encode",
            "video_convert",
            "video_trim",
            "video_watermark",
            "video_audio_merge",
            "video_subtitle_merge",
            "video_hardsub",
            "video_merge",
            "stream_extract",
            "stream_swap",
            "stream_remove",
            "intro_subtitle",
            "video_settings",
        ],
        dependencies=[],
    )

    async def on_load(self) -> bool:
        from bot import LOGGER
        from pyrogram.handlers import CallbackQueryHandler, MessageHandler

        self.PLUGIN_INFO.handlers.clear()
        load_video_settings()
        self.PLUGIN_INFO.handlers.append(
            CallbackQueryHandler(
                settings_callback, filters=lambda _, cb: cb.data.startswith("settings_")
            )
        )
        self.PLUGIN_INFO.handlers.append(
            MessageHandler(
                update_setting,
                filters=lambda _, m: m.from_user.id in user_settings_editor,
            )
        )
        LOGGER.info("Video Tools plugin loaded")
        return True

    async def on_unload(self) -> bool:
        from bot import LOGGER

        LOGGER.info("Video Tools plugin unloaded")
        return True


from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.helper.ff_utils import (
    add_watermark,
    convert_video,
    extract_stream,
    hardsub_video,
    merge_video_audio,
    merge_video_subtitle,
    merge_videos,
    remove_stream,
    trim_video,
)
import json
from config import (
    VIDEO_CRF,
    VIDEO_ENCODE_PRESET,
    WATERMARK_FONT_SIZE,
    WATERMARK_OPACITY,
    WATERMARK_POSITION,
    WATERMARK_TEXT,
)

VIDEO_SETTINGS_FILE = "plugins/video_settings.json"
VIDEO_SETTINGS = {}


def load_video_settings():
    global VIDEO_SETTINGS
    defaults = {
        "VIDEO_ENCODE_PRESET": VIDEO_ENCODE_PRESET,
        "VIDEO_CRF": VIDEO_CRF,
        "WATERMARK_TEXT": WATERMARK_TEXT,
        "WATERMARK_POSITION": WATERMARK_POSITION,
        "WATERMARK_OPACITY": WATERMARK_OPACITY,
        "WATERMARK_FONT_SIZE": WATERMARK_FONT_SIZE,
    }
    try:
        with open(VIDEO_SETTINGS_FILE, "r") as f:
            VIDEO_SETTINGS = json.load(f)
        for key, value in defaults.items():
            if key not in VIDEO_SETTINGS:
                VIDEO_SETTINGS[key] = value
    except (FileNotFoundError, json.JSONDecodeError):
        VIDEO_SETTINGS = defaults
    save_video_settings()


def save_video_settings():
    with open(VIDEO_SETTINGS_FILE, "w") as f:
        json.dump(VIDEO_SETTINGS, f, indent=4)


async def video_encode_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply_text("Reply to a video to use this command.")
        return

    video_message = message.reply_to_message
    args = message.text.split(maxsplit=1)
    preset = VIDEO_SETTINGS["VIDEO_ENCODE_PRESET"]
    crf = VIDEO_SETTINGS["VIDEO_CRF"]

    if len(args) > 1:
        options = args[1].split()
        for option in options:
            if option.startswith("preset="):
                preset = option.split("=")[1]
            elif option.startswith("crf="):
                crf = int(option.split("=")[1])

    await message.reply_text("Encoding video...")
    video_path = await video_message.download()
    output_path = f"encoded_{video_message.video.file_name}"

    success, error = await convert_video(video_path, output_path, preset, crf)
    if success:
        await message.reply_video(output_path, caption="Video encoded successfully.")
    else:
        await message.reply_text(f"Error encoding video: {error}")


async def video_convert_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply_text("Reply to a video to use this command.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text("Usage: /video_convert <format (e.g., mkv)>")
        return

    video_message = message.reply_to_message
    output_format = args[1]
    video_path = await video_message.download()
    output_path = f"converted_{video_message.video.file_name.split('.')[0]}.{output_format}"

    success, error = await convert_video(video_path, output_path)
    if success:
        await message.reply_video(output_path, caption=f"Video converted to {output_format}.")
    else:
        await message.reply_text(f"Error converting video: {error}")


async def video_trim_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply_text("Reply to a video to use this command.")
        return

    args = message.text.split()
    if len(args) < 3:
        await message.reply_text("Usage: /video_trim <start_time> <end_time>")
        return

    start_time, end_time = args[1], args[2]
    video_path = await message.reply_to_message.download()
    output_path = f"trimmed_{message.reply_to_message.video.file_name}"

    success, error = await trim_video(video_path, output_path, start_time, end_time)
    if success:
        await message.reply_video(output_path, caption="Video trimmed successfully.")
    else:
        await message.reply_text(f"Error trimming video: {error}")


async def video_watermark_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply_text("Reply to a video to use this command.")
        return

    args = message.text.split(maxsplit=1)
    watermark_text = VIDEO_SETTINGS["WATERMARK_TEXT"]
    if len(args) > 1:
        watermark_text = args[1]

    video_path = await message.reply_to_message.download()
    output_path = f"watermarked_{message.reply_to_message.video.file_name}"

    success, error = await add_watermark(
        video_path,
        output_path,
        watermark_text,
        position=VIDEO_SETTINGS["WATERMARK_POSITION"],
        opacity=VIDEO_SETTINGS["WATERMARK_OPACITY"],
        font_size=VIDEO_SETTINGS["WATERMARK_FONT_SIZE"],
    )
    if success:
        await message.reply_video(
            output_path, caption="Watermark added successfully."
        )
    else:
        await message.reply_text(f"Error adding watermark: {error}")


async def video_audio_merge_command(client: Client, message: Message):
    if (
        not message.reply_to_message
        or not message.reply_to_message.reply_to_message
    ):
        await message.reply_text(
            "Reply to an audio file which is a reply to a video file."
        )
        return

    audio_message = message.reply_to_message
    video_message = message.reply_to_message.reply_to_message

    if not audio_message.audio:
        await message.reply_text("The first replied message must be an audio file.")
        return

    if not video_message.video:
        await message.reply_text("The second replied message must be a video file.")
        return

    await message.reply_text("Downloading video and audio...")
    video_path = await video_message.download()
    audio_path = await audio_message.download()
    output_path = f"merged_{video_message.video.file_name}"

    success, error = await merge_video_audio(video_path, audio_path, output_path)
    if success:
        await message.reply_video(output_path, caption="Video and audio merged.")
    else:
        await message.reply_text(f"Error merging files: {error}")


async def video_subtitle_merge_command(client: Client, message: Message):
    if (
        not message.reply_to_message
        or not message.reply_to_message.reply_to_message
    ):
        await message.reply_text(
            "Reply to a subtitle file which is a reply to a video file."
        )
        return

    subtitle_message = message.reply_to_message
    video_message = message.reply_to_message.reply_to_message

    if not subtitle_message.document:
        await message.reply_text(
            "The first replied message must be a subtitle file."
        )
        return

    if not video_message.video:
        await message.reply_text("The second replied message must be a video file.")
        return

    await message.reply_text("Downloading video and subtitle...")
    video_path = await video_message.download()
    subtitle_path = await subtitle_message.download()
    output_path = f"subtitled_{video_message.video.file_name}"

    success, error = await merge_video_subtitle(
        video_path, subtitle_path, output_path
    )
    if success:
        await message.reply_video(output_path, caption="Video and subtitle merged.")
    else:
        await message.reply_text(f"Error merging files: {error}")


async def video_hardsub_command(client: Client, message: Message):
    if (
        not message.reply_to_message
        or not message.reply_to_message.reply_to_message
    ):
        await message.reply_text(
            "Reply to a subtitle file which is a reply to a video file."
        )
        return

    subtitle_message = message.reply_to_message
    video_message = message.reply_to_message.reply_to_message

    if not subtitle_message.document:
        await message.reply_text(
            "The first replied message must be a subtitle file."
        )
        return

    if not video_message.video:
        await message.reply_text("The second replied message must be a video file.")
        return

    await message.reply_text("Downloading video and subtitle...")
    video_path = await video_message.download()
    subtitle_path = await subtitle_message.download()
    output_path = f"hardsubbed_{video_message.video.file_name}"

    success, error = await hardsub_video(video_path, subtitle_path, output_path)
    if success:
        await message.reply_video(output_path, caption="Hardsubbed video created.")
    else:
        await message.reply_text(f"Error hardsubbing video: {error}")


async def video_merge_command(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("Reply to at least one video to start merging.")
        return

    video_messages = []
    current_message = message.reply_to_message
    while current_message:
        if current_message.video:
            video_messages.append(current_message)
        current_message = current_message.reply_to_message

    if len(video_messages) < 2:
        await message.reply_text("Reply to at least two videos to merge.")
        return

    await message.reply_text(f"Found {len(video_messages)} videos. Downloading...")
    video_paths = [await msg.download() for msg in reversed(video_messages)]
    output_path = "merged_video.mp4"

    success, error = await merge_videos(video_paths, output_path)
    if success:
        await message.reply_video(output_path, caption="Videos merged successfully.")
    else:
        await message.reply_text(f"Error merging videos: {error}")


async def stream_extract_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply_text("Reply to a video to use this command.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("Usage: /stream_extract <stream_specifier>")
        return

    stream_specifier = args[1]
    video_path = await message.reply_to_message.download()
    output_path = f"extracted_{stream_specifier}_{message.reply_to_message.video.file_name}"

    success, error = await extract_stream(
        video_path, output_path, stream_specifier
    )
    if success:
        await message.reply_document(output_path, caption="Stream extracted.")
    else:
        await message.reply_text(f"Error extracting stream: {error}")


async def stream_swap_command(client: Client, message: Message):
    if (
        not message.reply_to_message
        or not message.reply_to_message.reply_to_message
    ):
        await message.reply_text("Reply to a file which is a reply to another file.")
        return

    args = message.text.split()
    if len(args) < 3:
        await message.reply_text(
            "Usage: /stream_swap <map_video (e.g., 0:v)> <map_audio (e.g., 1:a)>"
        )
        return

    map_video, map_audio = args[1], args[2]
    file1_message = message.reply_to_message
    file2_message = message.reply_to_message.reply_to_message

    if not (file1_message.video or file1_message.document) or not (
        file2_message.video or file2_message.document
    ):
        await message.reply_text("Both replied messages must be video files.")
        return

    await message.reply_text("Downloading files...")
    file1_path = await file1_message.download()
    file2_path = await file2_message.download()
    output_path = "swapped_video.mp4"

    success, error = await swap_stream(
        file1_path, file2_path, output_path, map_video, map_audio
    )
    if success:
        await message.reply_video(output_path, caption="Streams swapped successfully.")
    else:
        await message.reply_text(f"Error swapping streams: {error}")


async def stream_remove_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply_text("Reply to a video to use this command.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("Usage: /stream_remove <stream_specifier>")
        return

    stream_specifier = args[1]
    video_path = await message.reply_to_message.download()
    output_path = (
        f"removed_{stream_specifier}_{message.reply_to_message.video.file_name}"
    )

    success, error = await remove_stream(
        video_path, output_path, stream_specifier
    )
    if success:
        await message.reply_video(output_path, caption="Stream removed.")
    else:
        await message.reply_text(f"Error removing stream: {error}")


from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


import os


async def intro_subtitle_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.video:
        await message.reply_text("Reply to a video to use this command.")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply_text("Usage: /intro_subtitle <duration> <text>")
        return

    duration, text = args[1], args[2]
    video_path = await message.reply_to_message.download()
    subtitle_path = "intro.srt"
    output_path = f"intro_{message.reply_to_message.video.file_name}"

    with open(subtitle_path, "w") as f:
        f.write(f"1\n00:00:00,000 --> 00:00:{duration},000\n{text}\n")

    try:
        success, error = await hardsub_video(video_path, subtitle_path, output_path)
        if success:
            await message.reply_video(output_path, caption="Intro subtitle added.")
        else:
            await message.reply_text(f"Error adding intro subtitle: {error}")
    finally:
        if os.path.exists(subtitle_path):
            os.remove(subtitle_path)


async def video_settings_command(client: Client, message: Message):
    buttons = [
        [
            InlineKeyboardButton(
                "Encode Preset", callback_data="settings_VIDEO_ENCODE_PRESET"
            ),
            InlineKeyboardButton(
                f'{VIDEO_SETTINGS["VIDEO_ENCODE_PRESET"]}', callback_data="ignore"
            ),
        ],
        [
            InlineKeyboardButton("CRF", callback_data="settings_VIDEO_CRF"),
            InlineKeyboardButton(f'{VIDEO_SETTINGS["VIDEO_CRF"]}', callback_data="ignore"),
        ],
        [
            InlineKeyboardButton(
                "Watermark Text", callback_data="settings_WATERMARK_TEXT"
            ),
            InlineKeyboardButton(
                f'{VIDEO_SETTINGS["WATERMARK_TEXT"]}', callback_data="ignore"
            ),
        ],
        [
            InlineKeyboardButton(
                "Watermark Position", callback_data="settings_WATERMARK_POSITION"
            ),
            InlineKeyboardButton(
                f'{VIDEO_SETTINGS["WATERMARK_POSITION"]}', callback_data="ignore"
            ),
        ],
    ]
    await message.reply_text(
        "Video Settings", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def settings_callback(client: Client, callback_query):
    query = callback_query.data
    setting_name = query.split("_", 1)[1]
    user_id = callback_query.from_user.id
    user_settings_editor[user_id] = setting_name
    await callback_query.message.edit_text(f"Send the new value for {setting_name}.")


async def update_setting(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_settings_editor:
        return

    setting_name = user_settings_editor.pop(user_id)
    new_value = message.text

    if setting_name in ["VIDEO_CRF", "WATERMARK_FONT_SIZE"]:
        try:
            new_value = int(new_value)
        except ValueError:
            await message.reply_text("Value must be an integer.")
            return
    elif setting_name == "WATERMARK_OPACITY":
        try:
            new_value = float(new_value)
        except ValueError:
            await message.reply_text("Value must be a float.")
            return

    VIDEO_SETTINGS[setting_name] = new_value
    save_video_settings()
    await message.reply_text(f"{setting_name} updated to {new_value}.")