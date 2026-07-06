"""AI-assisted command input helper."""

import sys
import uselect


stdin_poll = uselect.poll()
stdin_poll.register(sys.stdin, uselect.POLLIN)


def read_command():
    if not stdin_poll.poll(10):
        return None
    return sys.stdin.readline().strip().lower()
