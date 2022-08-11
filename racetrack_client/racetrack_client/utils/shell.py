import io
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional, Callable

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


def shell(
    cmd: str, 
    workdir: Optional[Path] = None,
    print_stdout: bool = True,
    read_bytes: bool = False,
    output_filename: Optional[str] = None,
):
    """
    Run system shell command.
    Print live stdout as it comes (line by line) and capture entire output in case of errors.
    :param cmd: shell command to run
    :param workdir: working directory for the command
    :param print_stdout: whether to print stdout from a subprocess to the main process stdout
    :param output_filename: file to write the output in real time
    :raises:
        CommandError: in case of non-zero command exit code.
    """
    _run_shell_command(cmd, workdir, print_stdout, output_filename, read_bytes)


def shell_output(
    cmd: str, 
    workdir: Optional[Path] = None, 
    print_stdout: bool = False,
    read_bytes: bool = False,
    output_filename: Optional[str] = None,
) -> str:
    """
    Run system shell command and return its output.
    Print live stdout as it comes (line by line) and capture entire output in case of errors.
    :param cmd: shell command to run
    :param workdir: working directory for the command
    :param print_stdout: whether to print stdout from a subprocess to the main process stdout
    :param output_filename: file to write the output in real time
    """
    captured_stream = _run_shell_command(cmd, workdir, print_stdout, output_filename, read_bytes)
    return captured_stream.getvalue()


def _run_shell_command(
    cmd: str, 
    workdir: Optional[Path] = None, 
    print_stdout: bool = True,
    output_filename: Optional[str] = None,
    read_bytes: bool = False,
) -> io.StringIO:
    logger.debug(f'Command: {cmd}')
    if len(cmd) > 4096:  # see https://github.com/torvalds/linux/blob/v5.11/drivers/tty/n_tty.c#L1681
        raise RuntimeError('maximum tty line length has been exceeded')
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=workdir)
    output_file = open(output_filename, 'a') if output_filename else None
    try:
        # fork command output to stdout, captured buffer and output file
        captured_stream = io.StringIO()

        if read_bytes:
            while True:
                chunk: bytes = process.stdout.read(1)
                if chunk == b'':
                    break
                chunk_str = chunk.decode()

                if print_stdout:
                    sys.stdout.write(chunk_str)
                    sys.stdout.flush()
                if output_file is not None:
                    output_file.write(chunk_str)
                captured_stream.write(chunk_str)

        else:
            for line in iter(process.stdout.readline, b''):
                line_str = line.decode()

                if print_stdout:
                    sys.stdout.write(line_str)
                    sys.stdout.flush()
                if output_file is not None:
                    output_file.write(line_str)
                captured_stream.write(line_str)

        process.wait()
        if output_file is not None:
            output_file.close()
        if process.returncode != 0:
            stdout = captured_stream.getvalue()
            raise CommandError(cmd, stdout, process.returncode)
        return captured_stream
    except KeyboardInterrupt:
        logger.warning('killing subprocess')
        process.kill()
        raise


class CommandOutputStream:
    def __init__(self,
                 cmd: str,
                 on_next_line: Callable[[str], None],
                 on_error: Callable[['CommandError'], None] = None,
                 workdir: Optional[Path] = None,
                 print_stdout: bool = False):
        """
        Manager of a shell command process running in background,
        monitoring stdout lines coming from it and streaming them.
        :param cmd: shell command
        :param on_next_line: callback function called whenever the new stdout line appears
        :param on_error: callback function called when process ends with non-zero return code
        :param workdir: working directory to call command with
        :param print_stdout: whether to write output also to stdout
        """
        self.stop = False
        logger.debug(f'Command: {cmd}')
        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=workdir)

        def monitor_output(stream):
            captured_stream = io.StringIO()
            for line in iter(stream.process.stdout.readline, b''):
                if stream.stop:
                    break
                line_str = line.decode()
                if print_stdout:
                    sys.stdout.write(line_str)
                    sys.stdout.flush()
                on_next_line(line_str)
                captured_stream.write(line_str)

            stream.process.wait()
            if stream.process.returncode != 0 and on_error is not None:
                stdout = captured_stream.getvalue()
                on_error(CommandError(cmd, stdout, stream.process.returncode))

        self.thread = threading.Thread(
            target=monitor_output,
            args=(self,),
            daemon=True,
        )
        self.thread.start()

    def interrupt(self):
        self.stop = True
        self.process.terminate()


class CommandError(RuntimeError):
    def __init__(self, cmd: str, stdout: str, returncode: int):
        super().__init__()
        self.cmd = cmd
        self.stdout = stdout
        self.returncode = returncode

    def __str__(self):
        return f'command failed: {self.cmd}: {self.stdout}'
