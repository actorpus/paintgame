import json
import os
import warnings


def split_by_max_length(inp: str, length: int, split_by_spaces=True) -> list[str]:
    """
    Splits a string into a list of strings based on a maximum length
    :param inp: input string
    :param length: maximum length of output strings
    :param split_by_spaces: attempts to dynamically split the string based on the location of spaces
    :return: the output list of strings, note: these are not of the length 'length'
             they are of the maximum length 'length'
    """

    remainder = []

    if len(inp) <= length:
        # string fits in width by default
        remainder.append(inp)
        return remainder

    last_space = -1

    if split_by_spaces:
        temp_part = inp[:length]
        last_space = temp_part.rfind(" ")

    if last_space == -1:
        # there are no spaces in the maximum string length
        part, inp = inp[:length], inp[length:]

        remainder.append(part)
        remainder.extend(
            split_by_max_length(inp, length, split_by_spaces=split_by_spaces)
        )

        return remainder

    part, inp = inp[:last_space], inp[last_space + 1:]

    remainder.append(part)
    remainder.extend(split_by_max_length(inp, length, split_by_spaces=split_by_spaces))

    return remainder


def stringpop(i, string):
    """
    remove character from string at index i
    :return: amended string
    """
    if i != -1:
        return string[:i] + string[i + 1:]
    else:
        return string[:i]


def stringadd(string2, string1, i):
    """
    add A to B at index i
    :return: amended string
    """
    if i != -1:
        return string1[: i + 1] + string2 + string1[i + 1:]
    else:
        return string1 + string2


def interpolate(
        a: tuple[int, int], b: tuple[int, int], i: float = 0.5
) -> tuple[int, int]:
    """
    Linearly interpolates between two 2 dimensional position vectors
    """
    return int((a[0] * i) + (b[0] * (1 - i))), int((a[1] * i) + (b[1] * (1 - i)))



# def compress_surface(surf: pygame.Surface):
#     return zlib.compress(bytes(numpy.packbits(pygame.surfarray.array3d(surf))))
#


class _Settings:
    def _create_default(self):
        file = open(self._file, "w")
        file.write(json.dumps({
            "ServerAddress": "0.0.0.0",
            "Port": 16324,
            "Name": "N00B",
            "MouseSnap": False,
        }))
        file.close()

    def __init__(self, *, file="settings.json"):
        self._file = file
        self._is_template = False

        # if settings.json does not exist create it and populate with defaults
        if not os.path.exists(self._file):
            warnings.warn(f"File {self._file} does not exist, creating default template now.")
            self._create_default()
            self._is_template = True

        with open(self._file, "r") as file:
            _settings: dict = json.load(file)

        self._settings = {
            "ServerAddress": _settings.get("ServerAddress", "0.0.0.0"),
            "Name": _settings.get("Name", "N00B"),
            "Port": _settings.get("Port", 16324),
            "MouseSnap": _settings.get("MouseSnap", False)
        }

    @property
    def default(self) -> bool:
        return self._is_template

    def __getitem__(self, item):
        if item in self._settings:
            return self._settings[item]

        warnings.warn(f"Unknown setting {item}, returning empty string.")
        return ""

    def _save_to_file(self):
        with open(self._file, "w") as file:
            json.dump(self._settings, file)

    def __setitem__(self, key, value) -> None:
        if key in self._settings:
            self._settings[key] = value
            self._save_to_file()
            return

        warnings.warn(f"Unknown setting {key}, not changing anything.")


settings = Settings = _Settings()
