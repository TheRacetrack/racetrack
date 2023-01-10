from dashboard.utils import remove_ansi_sequences


def test_remove_ansi_sequences():
    assert remove_ansi_sequences("\033[2m[21:37:00]\033[0m") == "[21:37:00]"
    assert remove_ansi_sequences("[time] \033[0;34mINFO\033[0m message") == "[time] INFO message"
    assert remove_ansi_sequences("\x1b") == "\x1b"
    assert remove_ansi_sequences("\x1b[1;31m") == ""
    assert remove_ansi_sequences("[2m] normal text [0m]") == "[2m] normal text [0m]"
