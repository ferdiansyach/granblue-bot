import multiprocessing
import sys
import time

from utils.message_log import MessageLog
from bot.game import Game


class MainDriver:
    """
    This driver class allows the Game class to be run on a separate Thread.
    """

    def __init__(self):
        super().__init__()
        self._game = None
        self._bot_process = None

    def is_running(self) -> bool:
        """Check the status of the bot process.

        Returns:
            (bool): Flag that indicates whether the bot process is still running or not.
        """
        return self._bot_process.is_alive()

    def _run_bot(self):
        """Starts the main bot process on this Thread.

        Returns:
            None
        """
        # Initialize the Game class and start Farming Mode.
        self._game = Game()
        succeeded = self._game.start_farming_mode()
        if not succeeded:
            raise SystemExit(1)
        return True

    def start_bot(self):
        """Starts the bot's Game class on a new Thread.

        Returns:
            None
        """
        # Create a new Process whose target is the MainDriver's run_bot() method.
        self._bot_process = multiprocessing.Process(target = self._run_bot)

        MessageLog.print_message("[STATUS] Starting bot process on a new thread now...")

        # Now start the new Process on a new Thread.
        self._bot_process.start()
        self._bot_process.is_alive()

        return None

    def stop_bot(self):
        """Stops the bot and terminates the Process.

        Returns:
            None
        """
        if self._bot_process is not None and self._bot_process.is_alive():
            MessageLog.print_message("\n[STATUS] Stopping the bot and terminating its Thread.")
            self._bot_process.terminate()
            self._bot_process.join(timeout = 5.0)

        return None


if __name__ == "__main__":
    session_log = MessageLog.initialize_session_log()
    MessageLog.print_message(f"[STATUS] Durable backend log: {session_log}")
    bot_object = MainDriver()
    exit_code = 1
    try:
        bot_object.start_bot()
        bot_object._bot_process.join()
        exit_code = bot_object._bot_process.exitcode
        if exit_code is None:
            exit_code = 1
    except KeyboardInterrupt:
        MessageLog.print_message("\n[STATUS] Interrupt received; stopping bot process...")
        bot_object.stop_bot()
        exit_code = 130
    finally:
        MessageLog.print_message(f"[STATUS] Closing Python process with code {exit_code}...")
        MessageLog.shutdown_logging()

    sys.exit(exit_code)
