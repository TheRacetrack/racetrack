import random
import subprocess
import time
from pathlib import Path

command_delay_before: float = 0.6
command_delay_after: float = 0.3
ESCAPE = '\x1B'


def type_text(txt: str, key_delay: float = 0.2):
    for character in txt:
        character = character.replace('\\', '\\\\')
        character = character.replace('"', '\\"')
        if character == '\n':
            shell('xdotool key Return')
        elif character == ESCAPE:
            shell('xdotool key Escape')
        else:
            shell(f'xdotool key type "{character}"')
        time.sleep(key_delay * random.uniform(0.5, 1))


def type_file(filepath: str):
    type_text(Path(filepath).read_text())


def type_command(line: str, key_delay: float = 0.2):
    type_text(line, key_delay)
    time.sleep(command_delay_before)
    type_text('\n', key_delay)
    time.sleep(command_delay_after)


def countdown():
    for i in range(3, 0, -1):
        print(f'Starting in {i}...')
        time.sleep(1)
    print('Action!')


def shell(cmd: str):
    subprocess.Popen(cmd, shell=True).wait()


