import datetime
import os
from pathlib import Path
from timeit import default_timer as timer
import inspect
import logging
import sys


class MessageLog:
    """
    Provides utility functions to print for the message log.
    """

    _starting_time = timer()
    _session_log_path = None
    _file_handler = None

    enable_inspect_caller = False

    logging.basicConfig(format='%(message)s', level=logging.INFO, stream=sys.stdout)

    @staticmethod
    def initialize_session_log() -> str:
        """Create a durable session log shared by the supervisor and bot process.

        The desktop frontend historically writes its log only after Python exits.  Keeping a
        backend-side streaming log means diagnostics survive a forced GUI/process-tree stop.
        """
        env_name = "GRANBLUE_AUTOMATION_LOG_PATH"
        log_path = os.environ.get(env_name)
        if not log_path:
            project_root = Path(__file__).resolve().parents[2]
            log_dir = project_root / "logs"
            log_dir.mkdir(parents = True, exist_ok = True)
            stamp = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
            log_path = str(log_dir / f"backend-live {stamp}.txt")
            os.environ[env_name] = log_path

        MessageLog._session_log_path = log_path
        MessageLog._ensure_file_handler()
        return log_path

    @staticmethod
    def _ensure_file_handler():
        if MessageLog._file_handler is not None:
            return

        log_path = MessageLog._session_log_path or os.environ.get("GRANBLUE_AUTOMATION_LOG_PATH")
        if not log_path:
            return

        MessageLog._session_log_path = log_path
        handler = logging.FileHandler(log_path, mode = "a", encoding = "utf-8")
        handler.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(handler)
        MessageLog._file_handler = handler

    @staticmethod
    def shutdown_logging():
        """Flush and close the per-process file handler."""
        handler = MessageLog._file_handler
        if handler is not None:
            handler.flush()
            handler.close()
            logging.getLogger().removeHandler(handler)
            MessageLog._file_handler = None

    @staticmethod
    def _print_time():
        """Formats the time since the bot started into a readable, printable HH:MM:SS format using timedelta.

        Returns:
            str: A formatted string that displays the elapsed time since the bot started.
        """
        return str(datetime.timedelta(seconds = (timer() - MessageLog._starting_time))).split('.')[0]

    @staticmethod
    def print_message(message: str):
        """Listen for and format messages before printing it to console.

        Returns:
            None
        """
        # Loop until the status flag has been set to 1.
        if message.startswith("\n"):
            if MessageLog.enable_inspect_caller:
                new_message = "\n" + MessageLog._print_time() + " " + f"[{inspect.stack()[1][3]}]" + message[len("\n"):]
            else:
                new_message = "\n" + MessageLog._print_time() + " " + message[len("\n"):]
        else:
            if MessageLog.enable_inspect_caller:
                new_message = MessageLog._print_time() + " " + f"[{inspect.stack()[1][3]}]" + message
            else:
                new_message = MessageLog._print_time() + " " + message

        MessageLog._ensure_file_handler()
        try:
            logging.info(new_message)
        except UnicodeEncodeError:
            # Clean out any non UTF-8 characters before printing.
            new_message_decoded = new_message.encode("utf-8", "ignore")
            logging.info(new_message_decoded)

        return None
