from lifecycle.job.ansi import strip_ansi_colors


def test_strip_ansi_colors():
    assert strip_ansi_colors("\033[2m[21:37:00]\033[0m") == "[21:37:00]"
    assert strip_ansi_colors("[time] \033[0;34mINFO\033[0m message") == "[time] INFO message"
    assert strip_ansi_colors("\x1b") == "\x1b"
    assert strip_ansi_colors("\x1b[1;31m") == ""
    assert strip_ansi_colors("[2m] normal text [0m]") == "[2m] normal text [0m]"
