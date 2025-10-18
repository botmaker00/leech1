import json
import os

from pyrogram import Client
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.core.plugin_manager import PluginBase, PluginInfo
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
from config import (
    VIDEO_CRF,
    VIDEO_ENCODE_PRESET,
    WATERMARK_FONT_SIZE,
    WATERMARK_OPACITY,
    WATERMARK_POSITION,
    WATERMARK_TEXT,
)

# --- Settings Management ---
VIDEO_SETTINGS_FILE = "plugins/video_settings.json"
VIDEO_SETTINGS = {}

def load_video_settings():
    """Loads video settings from JSON file or defaults."""
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
    """Saves video settings to JSON file."""
    with open(VIDEO_SETTINGS_FILE, "w") as f:
        json.dump(VIDEO_SETTINGS, f, indent=4)

async def get_main_settings_keyboard():
    """Builds the main settings keyboard."""
    buttons = [
        [InlineKeyboardButton(f'Preset: {VIDEO_SETTINGS["VIDEO_ENCODE_PRESET"]}', callback_data="settings_menu_preset")],
        [InlineKeyboardButton(f'CRF: {VIDEO_SETTINGS["VIDEO_CRF"]}', callback_data="settings_menu_crf")],
        [InlineKeyboardButton(f'Watermark: {VIDEO_SETTINGS["WATERMARK_TEXT"]}', callback_data="settings_menu_watermark_text")],
        [InlineKeyboardButton(f'Position: {VIDEO_SETTINGS["WATERMARK_POSITION"]}', callback_data="settings_menu_watermark_position")],
        [InlineKeyboardButton(f'Opacity: {VIDEO_SETTINGS["WATERMARK_OPACITY"]}', callback_data="settings_menu_opacity")],
        [InlineKeyboardButton(f'Font Size: {VIDEO_SETTINGS["WATERMARK_FONT_SIZE"]}', callback_data="settings_menu_font_size")],
        [InlineKeyboardButton("Close", callback_data="settings_close")],
    ]
    return InlineKeyboardMarkup(buttons)

# --- Plugin Class ---
class VideoToolsPlugin(PluginBase):
    PLUGIN_INFO = PluginInfo(
        name="video_tools",
        version="1.0.0",
        author="Jules",
        description="A plugin to add video manipulation tools.",
        enabled=True,
        commands=[
            "video_encode", "video_convert", "video_trim", "video_watermark",
            "video_audio_merge", "video_subtitle_merge", "video_hardsub",
            "video_merge", "stream_extract", "stream_swap", "stream_remove",
            "intro_subtitle", "video_settings",
        ],
    )

    def __init__(self):
        self.user_settings_editor = {}
        super().__init__()

    async def on_load(self, client: Client) -> bool:
        load_video_settings()
        self.PLUGIN_INFO.handlers = [
            CallbackQueryHandler(self.settings_callback, filters=lambda _, cb: cb.data.startswith("settings_")),
            MessageHandler(self.update_setting, filters=lambda _, m: m.from_user.id in self.user_settings_editor)
        ]
        return await super().on_load()

    async def on_unload(self) -> bool:
        self.PLUGIN_INFO.handlers.clear()
        return await super().on_unload()

    async def settings_callback(self, client: Client, callback_query):
        user_id = callback_query.from_user.id
        message = callback_query.message
        query = callback_query.data

        if query == "settings_close":
            await message.delete()
            return

        if query == "settings_back":
            keyboard = await get_main_settings_keyboard()
            await message.edit_text("<b>Video Settings</b>", reply_markup=keyboard)
            return

        menu_map = {
            "preset": self.get_preset_menu,
            "crf": self.get_crf_menu,
            "watermark_text": self.get_watermark_text_menu,
            "watermark_position": self.get_position_menu,
            "opacity": self.get_opacity_menu,
            "font_size": self.get_font_size_menu,
        }

        action = query.split("_", 2)[-1]
        if action in menu_map:
            await menu_map[action](message)
            return

        value_map = {
            "set_preset": "VIDEO_ENCODE_PRESET",
            "set_pos": "WATERMARK_POSITION",
        }

        if "set_" in query:
            action, value = query.split("_", 3)[2:]
            if action in value_map:
                VIDEO_SETTINGS[value_map[action]] = value
                save_video_settings()
                keyboard = await get_main_settings_keyboard()
                await message.edit_text("<b>Video Settings</b>", reply_markup=keyboard)
            return

        inc_dec_map = {
            "crf": "VIDEO_CRF",
            "opacity": "WATERMARK_OPACITY",
            "font_size": "WATERMARK_FONT_SIZE",
        }

        for key, setting in inc_dec_map.items():
            if key in query:
                if "inc" in query:
                    VIDEO_SETTINGS[setting] += 0.1 if key == 'opacity' else 1
                else:
                    VIDEO_SETTINGS[setting] -= 0.1 if key == 'opacity' else 1

                if key == 'opacity':
                    VIDEO_SETTINGS[setting] = round(min(max(VIDEO_SETTINGS[setting], 0.0), 1.0), 1)

                save_video_settings()
                await menu_map[key](message, is_edit=True)
                return

    async def update_setting(self, client: Client, message: Message):
        user_id = message.from_user.id
        if user_id not in self.user_settings_editor:
            return

        setting_name = self.user_settings_editor.pop(user_id)
        VIDEO_SETTINGS[setting_name] = message.text
        save_video_settings()

        await message.delete()
        async for msg in client.get_chat_history(message.chat.id, limit=10):
            if msg.from_user.id == client.me.id and msg.text.startswith("Send the new watermark text"):
                await msg.delete()
                break

        keyboard = await get_main_settings_keyboard()
        await client.send_message(message.chat.id, "<b>Video Settings</b>", reply_markup=keyboard)

    # --- Menu Builders ---
    async def get_preset_menu(self, message, is_edit=False):
        buttons = [
            [InlineKeyboardButton("Fast", callback_data="settings_set_preset_fast"),
             InlineKeyboardButton("Medium", callback_data="settings_set_preset_preset_medium"),
             InlineKeyboardButton("Slow", callback_data="settings_set_preset_slow")],
            [InlineKeyboardButton("Back", callback_data="settings_back")]
        ]
        text = "<b>Select Encode Preset</b>"
        if is_edit:
            await message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    async def get_crf_menu(self, message, is_edit=False):
        buttons = [
            [InlineKeyboardButton("-1", callback_data="settings_dec_crf"),
             InlineKeyboardButton(f'{VIDEO_SETTINGS["VIDEO_CRF"]}', callback_data="ignore"),
             InlineKeyboardButton("+1", callback_data="settings_inc_crf")],
            [InlineKeyboardButton("Back", callback_data="settings_back")]
        ]
        text = "<b>Set CRF Value</b>"
        if is_edit:
            await message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    async def get_watermark_text_menu(self, message, is_edit=False):
        self.user_settings_editor[message.chat.id] = "WATERMARK_TEXT"
        await message.edit_text("Send the new watermark text.")

    async def get_position_menu(self, message, is_edit=False):
        buttons = [
            [InlineKeyboardButton("Top Left", callback_data="settings_set_pos_top_left"),
             InlineKeyboardButton("Top Right", callback_data="settings_set_pos_top_right")],
            [InlineKeyboardButton("Bottom Left", callback_data="settings_set_pos_bottom_left"),
             InlineKeyboardButton("Bottom Right", callback_data="settings_set_pos_bottom_right")],
            [InlineKeyboardButton("Back", callback_data="settings_back")]
        ]
        text = "<b>Select Watermark Position</b>"
        if is_edit:
            await message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    async def get_opacity_menu(self, message, is_edit=False):
        buttons = [
            [InlineKeyboardButton("-0.1", callback_data="settings_dec_opacity"),
             InlineKeyboardButton(f'{VIDEO_SETTINGS["WATERMARK_OPACITY"]:.1f}', callback_data="ignore"),
             InlineKeyboardButton("+0.1", callback_data="settings_inc_opacity")],
            [InlineKeyboardButton("Back", callback_data="settings_back")]
        ]
        text = "<b>Set Watermark Opacity</b>"
        if is_edit:
            await message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    async def get_font_size_menu(self, message, is_edit=False):
        buttons = [
            [InlineKeyboardButton("-1", callback_data="settings_dec_font_size"),
             InlineKeyboardButton(f'{VIDEO_SETTINGS["WATERMARK_FONT_SIZE"]}', callback_data="ignore"),
             InlineKeyboardButton("+1", callback_data="settings_inc_font_size")],
            [InlineKeyboardButton("Back", callback_data="settings_back")]
        ]
        text = "<b>Set Watermark Font Size</b>"
        if is_edit:
            await message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))


# --- Command Functions ---
async def video_settings_command(client: Client, message: Message):
    keyboard = await get_main_settings_keyboard()
    await message.reply_text("<b>Video Settings</b>", reply_markup=keyboard)

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
    if os.path.exists(video_path):
        os.remove(video_path)
    if os.path.exists(output_path):
        os.remove(output_path)

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
    if os.path.exists(video_path):
        os.remove(video_path)
    if os.path.exists(output_path):
        os.remove(output_path)

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
    if os.path.exists(video_path):
        os.remove(video_path)
    if os.path.exists(output_path):
        os.remove(output_path)

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
        await message.reply_video(output_path, caption="Watermark added successfully.")
    else:
        await message.reply_text(f"Error adding watermark: {error}")
    if os.path.exists(video_path):
        os.remove(video_path)
    if os.path.exists(output_path):
        os.remove(output_path)

async def video_audio_merge_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.reply_to_message:
        await message.reply_text("Reply to an audio file which is a reply to a video file.")
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
    if os.path.exists(video_path):
        os.remove(video_path)
    if os.path.exists(audio_path):
        os.remove(audio_path)
    if os.path.exists(output_path):
        os.remove(output_path)

async def video_subtitle_merge_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.reply_to_message:
        await message.reply_text("Reply to a subtitle file which is a reply to a video file.")
        return

    subtitle_message = message.reply_to_message
    video_message = message.reply_to_message.reply_to_message

    if not subtitle_message.document:
        await message.reply_text("The first replied message must be a subtitle file.")
        return
    if not video_message.video:
        await message.reply_text("The second replied message must be a video file.")
        return

    await message.reply_text("Downloading video and subtitle...")
    video_path = await video_message.download()
    subtitle_path = await subtitle_message.download()
    output_path = f"subtitled_{video_message.video.file_name}"

    success, error = await merge_video_subtitle(video_path, subtitle_path, output_path)
    if success:
        await message.reply_video(output_path, caption="Video and subtitle merged.")
    else:
        await message.reply_text(f"Error merging files: {error}")
    if os.path.exists(video_path):
        os.remove(video_path)
    if os.path.exists(subtitle_path):
        os.remove(subtitle_path)
    if os.path.exists(output_path):
        os.remove(output_path)

async def video_hardsub_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.reply_to_message:
        await message.reply_text("Reply to a subtitle file which is a reply to a video file.")
        return

    subtitle_message = message.reply_to_message
    video_message = message.reply_to_message.reply_to_message

    if not subtitle_message.document:
        await message.reply_text("The first replied message must be a subtitle file.")
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
    if os.path.exists(video_path):
        os.remove(video_path)
    if os.path.exists(subtitle_path):
        os.remove(subtitle_path)
    if os.path.exists(output_path):
        os.remove(output_path)

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
    for path in video_paths:
        if os.path.exists(path):
            os.remove(path)
    if os.path.exists(output_path):
        os.remove(output_path)

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

    success, error = await extract_stream(video_path, output_path, stream_specifier)
    if success:
        await message.reply_document(output_path, caption="Stream extracted.")
    else:
        await message.reply_text(f"Error extracting stream: {error}")
    if os.path.exists(video_path):
        os.remove(video_path)
    if os.path.exists(output_path):
        os.remove(output_path)

async def stream_swap_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.reply_to_message:
        await message.reply_text("Reply to a file which is a reply to another file.")
        return

    args = message.text.split()
    if len(args) < 3:
        await message.reply_text("Usage: /stream_swap <map_video (e.g., 0:v)> <map_audio (e.g., 1:a)>")
        return

    map_video, map_audio = args[1], args[2]
    file1_message = message.reply_to_message
    file2_message = message.reply_to_message.reply_to_message

    if not (file1_message.video or file1_message.document) or not (file2_message.video or file2_message.document):
        await message.reply_text("Both replied messages must be video files.")
        return

    await message.reply_text("Downloading files...")
    file1_path = await file1_message.download()
    file2_path = await file2_message.download()
    output_path = "swapped_video.mp4"

    success, error = await swap_stream(file1_path, file2_path, output_path, map_video, map_audio)
    if success:
        await message.reply_video(output_path, caption="Streams swapped successfully.")
    else:
        await message.reply_text(f"Error swapping streams: {error}")
    if os.path.exists(file1_path):
        os.remove(file1_path)
    if os.path.exists(file2_path):
        os.remove(file2_path)
    if os.path.exists(output_path):
        os.remove(output_path)

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
    output_path = f"removed_{stream_specifier}_{message.reply_to_message.video.file_name}"

    success, error = await remove_stream(video_path, output_path, stream_specifier)
    if success:
        await message.reply_video(output_path, caption="Stream removed.")
    else:
        await message.reply_text(f"Error removing stream: {error}")
    if os.path.exists(video_path):
        os.remove(video_path)
    if os.path.exists(output_path):
        os.remove(output_path)

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
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(output_path):
            os.remove(output_path)