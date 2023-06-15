import random
import socket
import threading
import time


CLIENT_PING_TIME = 5
SERVER_PORT = 16324


class Game:
    def __init__(self, server):
        self.current_word = "tits"
        self.server = server
        self.game_is_running = False

    def load_random_word(self):
        with open("WordList.txt") as file:
            words = file.read().split("\n")

        words = [_.strip() for _ in words]
        word = random.choice(words)
        self.current_word = word
        print(f" [ \033[35m GAME \033[0m ] Chosen the word '{word}'")

    def start_game(self):
        self.load_random_word()
        self.game_is_running = True
        self.server.send_word_refresh()

    def check_word(self, guess, player):
        if not self.game_is_running:
            return player.send_chat_message(
                "You cant guess yet! The game isn't running!"
            )

        guess.replace("_", " ")

        if self.current_word == guess:
            player.send_chat_message(f"_WON {player.name}: {guess}")
            self.server.send_message_to_all(
                f"_LOST {player.name}: {guess}", except_=player
            )

        else:
            self.server.send_message_to_all(f"{player.name}: {guess}")


class Server:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("", SERVER_PORT))
        self.running = True
        self.clients: list[Client] = []

        self.self_ip = socket.gethostbyname(socket.gethostname())
        print(" [ \033[32mMS    \033[0m ] Discovered my ip.", self.self_ip)

        self.game = Game(self)

    def send_message_to_all(self, message, except_=None):
        for client in self.clients:
            if client == except_:
                pass

            client.send_chat_message(message)

    def run(self):
        print(" [ \033[32mMS    \033[0m ] Starting server on port", SERVER_PORT)
        self.sock.listen(1)

        while self.running:
            client, address = self.sock.accept()
            print(f" [ \033[32mMS    \033[0m ] New connection from {address}")
            port = f"{str(address[1]):5s}"

            client = Client(self, client, port)
            client.start()
            self.clients.append(client)


class Client(threading.Thread):
    def __init__(self, master, client, port):
        super(Client, self).__init__()

        self._server: Server = master
        self._socket: socket.socket = client
        self._running = True
        self._last_ping_time = time.time()
        self._port = port
        self._name = b"N00B"

    def process_packet(self, packet):
        if packet == b"PONG":
            self._last_ping_time = time.time()

        elif packet == b"WORD":
            word = self._read_string_secure()
            self._server.game.check_word(word, self)

        elif packet == b"JOIN":
            name = self._read_string_secure()
            self._name = name
            print(f" [ \033[34mC{self._port}\033[0m ] Has named themselves {name}")

        else:
            print("WHAT THE FUUUUUUUUUUCK")
            print(f"Client {self._port} did a dumb and sent", packet)

    def send_ping(self):
        self._socket.send(b"PING")

    def send_chat_message(self, message):
        self._socket.send(b"CHAT")
        self._send_string_secure(message)

    # def send_lobby_update(self):
    #     clients = self._server.clients YO
    #
    #     self._socket.send(b"LOBY")
    #     self._send_int_secure(len(clients))
    #
    #     for client in clients:
    #         self._send_string_secure(client.name)

    def death_spiral(self):
        self._running = False
        self._socket.close()
        self._server.clients.remove(self)
        print(f" \033[31m[ \033[34mC{self._port}\033[0m \033[31m]\33[0m Closing thread")

    def _send_string_secure(self, string: str):
        self._socket.send(len(string).to_bytes(2, "big"))
        self._socket.send(string.encode())

    def _read_string_secure(self):
        length = self._socket.recv(2)
        length = int.from_bytes(length, "big")

        data = self._socket.recv(length)
        return data.decode()

    def _send_int_secure(self, number: int):
        self._socket.send(number.to_bytes(4, "big"))

    def _read_int_secure(self):
        data = self._socket.recv(4)
        data = int.from_bytes(data, "big")
        return data

    def run(self) -> None:
        while self._running:
            self._socket.settimeout(0.2)

            try:
                data = self._socket.recv(4)
            except socket.timeout:
                ...
            except ConnectionResetError:
                print(f" [ \033[34mC{self._port}\033[0m ] Connection reset.")
                return self.death_spiral()
            except ConnectionAbortedError:
                print(f" [ \033[34mC{self._port}\033[0m ] Connection aborted.")
                return self.death_spiral()
            else:
                self._socket.settimeout(None)
                if data:
                    self.process_packet(data)

            t = time.time()
            if t > self._last_ping_time + CLIENT_PING_TIME:
                self.send_ping()


if __name__ == "__main__":
    ms = Server()
    ms.run()
