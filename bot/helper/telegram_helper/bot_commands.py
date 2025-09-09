from ...core.config_manager import Config
from ...core.plugin_manager import get_plugin_manager


class BotCommands:
    StartCommand = "start"
    LoginCommand = "login"

    _static_commands = {
        "Mirror": ["mirrorx", "mx"],
        "QbMirror": ["qbmirrorx", "qmx"],
        "JdMirror": ["jdmirrorx", "jmx"],
        "Ytdl": ["ytdlx", "yx"],
        "NzbMirror": ["nzbmirrorx", "nmx"],
        "Leech": ["leechx", "lx"],
        "QbLeech": ["qbleechx", "qlx"],
        "JdLeech": ["jdleechx", "jlx"],
        "YtdlLeech": ["ytdlleechx", "ylx"],
        "NzbLeech": ["nzbleechx", "nlx"],
        "Clone": ["clone", "cl"],
        "Count": "count",
        "Delete": "del",
        "List": "list",
        "Search": "searchx",
        "Users": "users",
        "CancelTask": ["cancel", "c"],
        "CancelAll": ["cancelall", "call"],
        "ForceStart": ["forcestart", "fs"],
        "Status": ["statusx", "s", "statusall"],
        "MediaInfo": ["mediainfo", "mi"],
        "Ping": "pingx",
        "Restart": ["restartx", "r", "restartall"],
        "RestartSessions": ["restartses", "rses"],
        "Broadcast": ["broadcast", "bc"],
        "Stats": ["statsx", "st"],
        "Help": ["helpx", "h"],
        "Log": "log",
        "Shell": "shell",
        "AExec": "aexec",
        "Exec": "exec",
        "ClearLocals": "clearlocals",
        "IMDB": "imdb",
        "Rss": "rss",
        "Authorize": ["authorize", "a"],
        "UnAuthorize": ["unauthorize", "ua"],
        "AddSudo": ["addsudo", "as"],
        "RmSudo": ["rmsudo", "rs"],
        "BotSet": ["bsettingx", "bs"],
        "UserSet": ["usettingx", "us"],
        "Select": ["select", "sel"],
        "NzbSearch": "nzbsearch",
        "Plugins": "plugins",
    }

    @classmethod
    def get_commands(cls):
        commands = cls._static_commands.copy()

        plugin_manager = get_plugin_manager()
        if plugin_manager:
            for plugin_info in plugin_manager.list_plugins():
                if plugin_info.enabled and plugin_info.commands:
                    for cmd in plugin_info.commands:
                        if cmd == "speedtest":
                            commands["SpeedTest"] = ["speedtest", "stest"]
                        elif cmd == "stest":
                            if "SpeedTest" not in commands:
                                commands["SpeedTest"] = ["speedtest", "stest"]
                            elif "stest" not in commands["SpeedTest"]:
                                commands["SpeedTest"].append("stest")

        return commands

    @classmethod
    def _build_command_vars(cls):
        commands = cls.get_commands()

        for key, cmds in commands.items():
            setattr(
                cls,
                f"{key}Command",
                (
                    [
                        (
                            f"{cmd}{Config.CMD_SUFFIX}"
                            if cmd not in ["restartall", "statusall"]
                            else cmd
                        )
                        for cmd in cmds
                    ]
                    if isinstance(cmds, list)
                    else f"{cmds}{Config.CMD_SUFFIX}"
                ),
            )

    @classmethod
    def refresh_commands(cls):
        cls._build_command_vars()


BotCommands._build_command_vars()
