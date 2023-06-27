import threading
import socket
import time


WELCOME_MESSAGE = "Welcome to the game! Have fun!"


class BadClientConfig(Exception):
    ...


class Client(threading.Thread):
    def __init__(self, address: tuple[str, int], name: str, frame_func = None):
        super(Client, self).__init__()
        self._running = True
        self._operable = False

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect(address)

        self._frame_func = frame_func
        self._name = name
        self._chat = [WELCOME_MESSAGE]
        self._lobby_clients = []

        self._word_pattern = None
        self._time_since_last_frame = time.time()
        self._frame_sending_signaling = 0

    def request_word_skip(self):
        self._socket.send(b"SKIP")

    def request_game_start(self):
        self._socket.send(b"STRT")

    @property
    def word_pattern(self):
        if self._word_pattern is None:
            return "loading..."

        return self._word_pattern

    @property
    def chat_log(self):
        return self._chat

    @property
    def in_lobby(self):
        return self._lobby_clients

    def process_packet(self, packet):
        if packet == b"PING":
            self._socket.send(b"PONG")

        elif packet == b"LOBY":
            len_clients = self._read_int_secure()
            clients = []

            for _ in range(len_clients):
                clients.append(self._read_string_secure())

            self._lobby_clients = clients

        elif packet == b"CHAT":
            message = self._read_string_secure()
            print(f" [ \033[34mClient\033[0m ] Received chat message '{message}'")

            self._chat.append(message.strip())
            print(f" [ \033[34mClient\033[0m ] Chat log '{self._chat}'")

        elif packet == b"WORD":
            self._word_pattern = self._read_string_secure()

        else:
            print(f" [ \033[34mClient\033[0m ] Bad packet received", packet)

    def close(self):
        self._running = False
        print(f" [ \033[34mClient\033[0m ] Closing server")

    def send_message(self, word):
        print(f" [ \033[34mClient\033[0m ] Sending chat message '{word}'")

        self._socket.send(b"WORD")
        self._send_string_secure(word)

    def wait_till_success(self, query_time=0.5):
        while not self._operable:
            time.sleep(query_time)

    def _send_string_secure(self, string: str):
        self._socket.send(len(string).to_bytes(2, "big"))
        self._socket.send(string.encode())

    def _read_string_secure(self):
        length = self._socket.recv(2)
        length = int.from_bytes(length, "big")

        data = self._socket.recv(length)
        return data.decode()

    def send_initial(self):
        if not (4 <= len(self.name) <= 10):
            raise BadClientConfig("Bad name length")

        self._socket.send(b"JOIN")
        self._send_string_secure(self.name)

    def _send_int_secure(self, number: int):
        self._socket.send(number.to_bytes(4, "big"))

    def _read_int_secure(self):
        data = self._socket.recv(4)
        data = int.from_bytes(data, "big")
        return data

    def _send_frame(self):
        self._socket.send(b"FRME")


    def _frame_send_check(self):
        current_time = time.time()

        if self._frame_sending_signaling < current_time:
            return

        if self._time_since_last_frame + 1 / 24 > current_time:
            return

        if self._frame_func is None:
            print(f" [ \033[34mClient\033[0m ] ERROR: Tried to get frame, no function was registered")
            return

        self._time_since_last_frame = current_time
        frame = self._frame_func()

        self._socket.send(len(frame).to_bytes(2, "big"))
        self._socket.send(frame)

    def run(self) -> None:
        self.send_initial()
        self._operable = True

        while self._running:
            self._socket.settimeout(1/24)

            try:
                data = self._socket.recv(4)
            except socket.timeout:
                ...
            else:
                self._socket.settimeout(None)
                self.process_packet(data)
            finally:
                self._socket.settimeout(None)

            self._frame_send_check()