import random
import socket
import threading
import time


CLIENT_PING_TIME = 5
SERVER_PORT = 16324


class Game:
    def __init__(self, server):
        self.current_word = ""
        self.server: Server = server
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
        self.server.send_word_refresh("lm_ w__n yo_ __e t__s")

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


class ServerTimeouts(threading.Thread):
    def __init__(self, server):
        super(ServerTimeouts, self).__init__()
        self.server: Server = server

        self.lobby_update_time = time.time()

    def run(self) -> None:
        while True:
            time.sleep(1)
            t = time.time()

            if self.lobby_update_time + 60 > t:
                print(" [ \033[32mMStime\033[0m ] Sending lobby info")
                self.server.update_all_clients()
                self.lobby_update_time = t


class Server:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("", SERVER_PORT))
        self.running = True
        self.clients: list[Client] = []

        self.self_ip = socket.gethostbyname(socket.gethostname())
        print(" [ \033[32mMS    \033[0m ] Discovered my ip.", self.self_ip)

        self.game = Game(self)
        self.frame = None

    def send_message_to_all(self, message, except_=None):
        for client in self.clients:
            print(client, type(client), except_, type(except_))
            if client == except_:
                pass

            client.send_chat_message(message)

    def send_word_refresh(self, word):
        for client in self.clients:
            client.send_word_refresh(word)

    def update_all_clients(self):
        for client in self.clients:
            client.send_lobby_update()

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
        self._name = "N00B"

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

        elif packet == b"STRT":
            self._server.game.start_game()

        elif packet == b"SKIP":
            self._server.game.load_random_word()

        elif packet == b"FRME":
            length = self._socket.recv(2)
            length = int.from_bytes(length, "big")

            frame = self._socket.recv(length)
            self._server.frame = frame

        else:
            print("WHAT THE FUUUUUUUUUUCK")
            print(f"Client {self._port} did a dumb and sent", packet)

    def send_word_refresh(self, word):
        self._socket.send(b"WORD")
        self._send_string_secure(word)

    def send_ping(self):
        self._socket.send(b"PING")

    def send_chat_message(self, message):
        self._socket.send(b"CHAT")
        self._send_string_secure(message)

    def send_lobby_update(self):
        clients = self._server.clients

        self._socket.send(b"LOBY")
        self._send_int_secure(len(clients))

        for client in clients:
            self._send_string_secure(client.name)

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
        self._server.update_all_clients()

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
