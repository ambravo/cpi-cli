from colorama import Fore, Back


def wrap_with_color(code, background=''):
    def inner(text):
        c = code
        return c + background + text + Fore.RESET + Back.RESET
    return inner


# Color util functions
red = wrap_with_color(Fore.RED)
green = wrap_with_color(Fore.GREEN)
blue = wrap_with_color(Fore.BLUE)
warning = wrap_with_color(Fore.RED, Back.WHITE)
