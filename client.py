import threading
import socket
import time


WELCOME_MESSAGE = "Welcome to the game! Have fun!"


class BadClientConfig(Exception):
    ...


class Client(threading.Thread):
    def __init__(self, address: tuple[str, int], name: str):
        super(Client, self).__init__()
        self._running = True
        self._operable = False

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect(address)

        self._name = name
        self._chat = [WELCOME_MESSAGE]
        self._lobby_clients = []

        self._word_pattern = None

    def request_word_skip(self):
        self._socket.send("SKIP")

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

        elif packet == b"UPDT":
            le = self._read_string_secure()

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

    def run(self) -> None:
        self.send_initial()
        self._operable = True

        while self._running:
            self._socket.settimeout(0.2)

            try:
                data = self._socket.recv(4)
            except socket.timeout:
                ...
            else:
                self._socket.settimeout(None)
                self.process_packet(data)
            finally:
                self._socket.settimeout(None)
