import socket
import time
import pygame
from pygame.locals import *
from functools import lru_cache
import threading
import traceback
import hashlib
import sys
import math

RED = (255, 0, 0)
BLUE = (0, 0, 255)
GRAY, SLIGHTLY_DARKER_GRAY, SLIGHTLY_DARKER_DARKER_GRAY = (
    (200, 200, 200),
    (190, 190, 190),
    (180, 180, 180),
)
BLACK = (0, 0, 0)
SERVER_PORT = 16324
INTERPOLATE_STEP = 20
WELCOME_MESSAGE = "Welcome to the game"

entryboxes = []


def interpolate(a, b, i):
    return int((a[0] * i) + (b[0] * (1 - i))), int((a[1] * i) + (b[1] * (1 - i)))


def draw_line_interpolated_1(points, screen, rgb, line_width):
    true = (
        (points[-1][0] - points[-2][0]) ** 2 + (points[-1][1] - points[-2][1]) ** 2
    ) ** 0.5
    projected = (
        (points[-2][0] - points[-3][0]) ** 2 + (points[-2][1] - points[-3][1]) ** 2
    ) ** 0.5
    final = min(projected, true * 0.3)

    projection = (
        int(points[-2][0] - ((final / projected) * (points[-3][0] - points[-2][0]))),
        int(points[-2][1] - ((final / projected) * (points[-3][1] - points[-2][1]))),
    )

    interpolate_points = points[-2:]

    interpolate_points.insert(1, projection)

    prev = (
        interpolate(
            interpolate(interpolate_points[0], interpolate_points[1], 0),
            interpolate(interpolate_points[1], interpolate_points[2], 0),
            0,
        ),
    )

    for i in range(INTERPOLATE_STEP):
        new = (
            interpolate(
                interpolate(
                    interpolate_points[0], interpolate_points[1], (i / INTERPOLATE_STEP)
                ),
                interpolate(
                    interpolate_points[1], interpolate_points[2], (i / INTERPOLATE_STEP)
                ),
                (i / INTERPOLATE_STEP),
            ),
        )

        pygame.draw.line(screen, rgb, prev, new, line_width)
        pygame.draw.circle(screen, rgb, prev, line_width // 2)
        pygame.draw.circle(screen, rgb, new, line_width // 2)

        prev = new

    pygame.draw.line(screen, rgb, points[-2], prev, line_width)
    pygame.draw.circle(screen, rgb, prev, line_width // 2)


class BadConfig(Exception):
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

    def process_packet(self, packet):
        if packet == b"PING":
            self._socket.send(b"PONG")

        elif packet == b"LOBY":
            len_clients = self._read_int_secure()

        elif packet == b"CHAT":
            message = self._read_string_secure()
            self._chat.append(message.strip())

        elif packet == b"UPDT":
            le = self._read_string_secure()

        else:
            print(f" [ \033[34mClient\033[0m ] Bad packet received", packet)

    def close(self):
        self._running = False

    def send_message(self, word):
        self._socket.send(b"WORD")
        self._send_string_secure(word)

        print("send init", word)

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
            raise BadConfig("Bad name length")

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


class Renderer:
    def __init__(self, client):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Drawing fun paint")
        self.server = client
        self.screen = pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN)
        self.font = pygame.font.SysFont(pygame.font.get_default_font(), 25)
        self.__running = True
        self.__is_drawing = True
        self.__is_guessing = False
        self.__is_spectating = False
        # List of tools 'Drawing', 'Rubber', 'Fill' and more to come :)
        self.__current_tool = "Drawing"
        self.__past_drawing_points = []
        self.__current_tool_active = False
        self.__pen_size = 5
        self.__current_RGB = (0, 0, 0)
        self.__last_draw_pos = (0, 0)
        self.__canvas = pygame.Surface((1920, 1080))
        self.__canvas.fill(GRAY)
        self.clock = pygame.time.Clock()
        self.__options_menu_open = False
        self.__settings_pos = (0, 0)
        self.__round_end = time.time() + 120
        self.__skip_current_word = pygame.Surface((100, 50), pygame.SRCALPHA)
        self.__skip_current_word.fill((0, 0, 0, 0))
        self.__editing_text = False
        pygame.draw.rect(
            self.__skip_current_word, (*BLUE, 255), (0, 0, 100, 50), border_radius=25
        )

        self.__images = {}
        for image in ["add", "minus"]:
            i = pygame.image.load("images/" + image + ".png")
            i = pygame.transform.scale(i, (32, 32))
            self.__images[image] = i

    def render_loop(self):
        while self.__running:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.__running = False
                # Event checks:
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_j:
                        how_long = time.time()
                        self.filler(mouse_pos)
                        print('How long ali ' + str(time.time()-how_long))

                    if event.key == pygame.K_k:
                        threading.Thread(target=lambda: self.alex_filler(mouse_pos)).start()

                    if event.key == pygame.K_h:
                        pygame.draw.rect(self.__canvas, self.__current_RGB, (100, 100, 100, 100), 4)
                        pygame.draw.rect(self.__canvas, self.__current_RGB, (250, 100, 100, 100), 4)
                        pygame.draw.rect(self.__canvas, self.__current_RGB, (100, 250, 100, 100), 4)
                        pygame.draw.rect(self.__canvas, self.__current_RGB, (250, 250, 100, 100), 4)
                        pygame.draw.rect(self.__canvas, self.__current_RGB, (500, 100, 100, 100), 4)
                        pygame.draw.rect(self.__canvas, self.__current_RGB, (650, 100, 100, 100), 4)
                        pygame.draw.rect(self.__canvas, self.__current_RGB, (500, 250, 100, 100), 4)
                        pygame.draw.rect(self.__canvas, self.__current_RGB, (650, 250, 100, 100), 4)
                        pygame.draw.rect(self.__canvas, self.__current_RGB, (100, 500, 100, 100), 4)
                        pygame.draw.rect(self.__canvas, self.__current_RGB, (250, 500, 100, 100), 4)
                        pygame.draw.rect(self.__canvas, self.__current_RGB, (100, 650, 100, 100), 4)
                        pygame.draw.rect(self.__canvas, self.__current_RGB, (250, 650, 100, 100), 4)
                        pygame.draw.rect(self.__canvas, self.__current_RGB, (500, 500, 100, 100), 4)
                        pygame.draw.rect(self.__canvas, self.__current_RGB, (650, 500, 100, 100), 4)
                        pygame.draw.rect(self.__canvas, self.__current_RGB, (500, 650, 100, 100), 4)
                        pygame.draw.rect(self.__canvas, self.__current_RGB, (650, 650, 100, 100), 4)

                    for box in entryboxes:
                        if not event.unicode:
                            continue
                        if box.writing and (
                            (32 <= ord(event.unicode) <= 126)
                            or (event.key == pygame.K_BACKSPACE)
                        ):
                            box.update_string(event)

                elif event.type == MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self._reset_states()
                        for box in entryboxes:
                            if box.rect.collidepoint(pygame.mouse.get_pos()):
                                box.text_box_clicked()
                            else:
                                box.text_box_not_clicked()
                        else:
                            if self.__current_tool == "Drawing":
                                self.__current_tool_active = True
                                self.__last_draw_pos = mouse_pos

                            elif self.__current_tool == "Rubber":
                                self.__current_tool_active = True
                                self.__last_draw_pos = mouse_pos

                            if (
                                960 < mouse_pos[0] < 1060
                                and 100 < mouse_pos[1] < 150
                                and self.__skip_current_word.get_at(
                                    (mouse_pos[0] - 960, mouse_pos[1] - 100)
                                )
                                == (*BLUE, 255)
                            ):
                                print("gimme my new word boi")

                    elif event.button == 3:
                        self.options_menu()
                        self.__settings_pos = (mouse_pos[0] - 200, mouse_pos[1] - 200)
                        self.__options_menu_open = True

                elif event.type == MOUSEBUTTONUP:
                    if event.button == 1:
                        if self.__current_tool_active:
                            self.__current_tool_active = False
                            self.__past_drawing_points = []

                    elif event.button == 3:
                        self.__options_menu_open = False
                        self.options_checker(mouse_pos)

            if self.__current_tool == "Drawing" and self.__current_tool_active:
                self.drawing(mouse_pos, self.__current_RGB)

            if self.__current_tool == "Rubber" and self.__current_tool_active:
                self.drawing(mouse_pos, GRAY)

            self.screen.blit(self.__canvas, (0, 0))
            if self.__options_menu_open:
                self.screen.blit(self.__options_menu, self.__settings_pos)

            self._word_list_renderer()
            self.skip_cur_word_renderer()
            for box in entryboxes:
                box.render()
            self.timer()
            self.clock.tick(60)
            pygame.display.update()

    def _reset_states(self):
        # Careful with what you put in the function, might end up screwing things up later down the line... (tommys predictions)
        self.__options_menu_open = False

    def word_checker(self, input):
        ...

    def render_menu(self):
        ...

    @lru_cache(maxsize=32)
    def _word_list_renderer_part(self, x, temppyyy, i):
        return self.font.render(
            self.server.chat_log[-1 - i][
                len(self.server.chat_log[-1 - i])
                - (x + 1) * temppyyy : len(self.server.chat_log[-1 - i])
                - x * temppyyy
            ],
            True,
            (111, 111, 111),
        )

    def skip_cur_word_renderer(self):
        self.__canvas.blit(self.__skip_current_word, (960, 100))

    def _word_list_renderer(self):
        lines_taken = 0
        pygame.draw.rect(self.screen, (255, 0, 0), (1580, 20, 320, 740), width=1)
        temppyyy = 30
        for i in range(len(self.server.chat_log)):
            tempyyyyyyyy = 0
            for x in range(len(self.server.chat_log[-1 - i]) // temppyyy):
                tempyyyyyyyy += 1
                self.screen.blit(
                    self._word_list_renderer_part(x, temppyyy, i),
                    (1600, 740 - lines_taken * 25),
                )
                lines_taken += 1
                if lines_taken >= 29:
                    break
            if lines_taken >= 29:
                break
            self.screen.blit(
                self.font.render(
                    self.server.chat_log[-1 - i][0 : temppyyy - 2],
                    True,
                    (111, 111, 111),
                ),
                (1600, 740 - lines_taken * 25),
            )
            lines_taken += 1

    def drawing(self, position, RGB):
        # [pos before last pos, last pos, current pos]
        self.__past_drawing_points.append(position)

        if len(self.__past_drawing_points) == 1:
            pygame.draw.circle(
                self.__canvas,
                RGB,
                self.__past_drawing_points[0],
                self.__pen_size // 2,
            )

        elif len(self.__past_drawing_points) == 2:
            pygame.draw.line(
                self.__canvas,
                RGB,
                self.__past_drawing_points[0],
                self.__past_drawing_points[1],
                self.__pen_size,
            )
            pygame.draw.circle(
                self.__canvas,
                self.__current_RGB,
                self.__past_drawing_points[0],
                self.__pen_size // 2,
            )
            pygame.draw.circle(
                self.__canvas,
                self.__current_RGB,
                self.__past_drawing_points[1],
                self.__pen_size // 2,
            )

        else:
            try:
                draw_line_interpolated_1(
                    self.__past_drawing_points, self.__canvas, RGB, self.__pen_size
                )
            except ZeroDivisionError:
                ...

            self.__past_drawing_points.pop(0)

    def options_menu(self):
        self.__options_menu = pygame.Surface((400, 400), pygame.SRCALPHA)
        pygame.draw.circle(self.__options_menu, (0, 0, 0, 255), (200, 200), 200, 2)
        pygame.draw.circle(self.__options_menu, (0, 0, 0, 255), (200, 200), 100, 2)

        # pygame.draw.line(self.__options_menu, (0, 0, 0, 255), (0, 0), (400, 400), width=5)
        # pygame.draw.line(self.__options_menu, (0, 0, 0, 255), (0, 400), (400, 0), width=5)
        # pygame.draw.line(self.__options_menu, (0, 0, 0, 255), (0, 400), (400, 0), width=5)
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 255), (50, 50), (135, 135), width=12
        )
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 0), (50, 50), (135, 135), width=6
        )
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 255), (260, 260), (350, 350), width=12
        )
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 0), (260, 260), (350, 350), width=6
        )
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 255), (200, 0), (200, 100), width=12
        )
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 255), (200, 300), (200, 400), width=12
        )
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 255), (0, 200), (100, 200), width=12
        )
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 255), (300, 200), (400, 200), width=12
        )
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 0), (200, 0), (200, 400), width=8
        )
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 0), (0, 200), (400, 200), width=8
        )

        pygame.draw.circle(self.__options_menu, (0, 0, 0, 0), (200, 200), 220, 20)
        pygame.draw.circle(self.__options_menu, (0, 0, 0, 0), (200, 200), 98, 20)

        self.__options_menu.blit(self.__images["add"], (0, 0))

    def options_checker(self, mouse_pos):
        location_mouse = (
            mouse_pos[0] - self.__settings_pos[0] - 200,
            mouse_pos[1] - self.__settings_pos[1] - 200,
        )
        if 200 > ((location_mouse[0]) ** 2 + (location_mouse[1]) ** 2) ** (1 / 2) > 50:
            try:
                angle = math.atan(location_mouse[1] / location_mouse[0])
                angle += math.pi / 2
                if location_mouse[0] > 0:
                    angle += math.pi

            except ZeroDivisionError:
                return

            #          [pen]          [increase pen size]
            #   [rubber]                            [decrease pen size]
            #   [blank]                             [blank]
            #          [clear screen] [blank]

            if angle < math.pi / 4:
                self.clear_screen()

            elif angle < math.pi / 2:
                print("Option 2")

            elif angle < math.pi * 3 / 4:
                self.set_rubber()

            elif angle < math.pi:
                self.set_drawing()

            elif angle < math.pi * 5 / 4:
                self.pen_size_increase()

            elif angle < math.pi * 3 / 2:
                self.pen_size_decrease()

            elif angle < math.pi * 7 / 4:
                print("Option 7")

            else:
                print("Option 8")

    def pen_size_increase(self):
        self.__pen_size += 2

    def pen_size_decrease(self):
        self.__pen_size -= 2

    def set_rubber(self):
        if self.__current_tool != "Rubber":
            self.__current_tool = "Rubber"
            self.__pen_size += 10

    def set_drawing(self):
        if self.__current_tool == "Rubber":
            self.__pen_size -= 10
        self.__current_tool = "Drawing"

    def set_filler(self):
        self.__current_tool == "Filler"

    def alex_filler(self, mouse_pos):
        how_long = time.time()
        stack = [mouse_pos]

        while stack:
            item = stack.pop(0)

            for offset in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
                question = (
                    item[0] + offset[0],
                    item[1] + offset[1]
                )

                if question in stack:
                    continue

                if self.__canvas.get_at(question) != GRAY:
                    continue

                stack.insert(0, question)

            self.__canvas.set_at(item, self.__current_RGB)
            # self.screen.blit(self.__canvas, (0, 0))
            # pygame.display.update()

        print('How long alex ' + str(time.time() - how_long))

    def filler(self, mouse_pos):
        fill_canvas = pygame.Surface((1920, 1080), pygame.SRCALPHA)
        fill_canvas.fill((0, 0, 0, 0))
        completed_stack = []
        current_stack = [mouse_pos]
        while len(current_stack) > 0:
            if self.__canvas.get_at(current_stack[-1]) == GRAY:
                for y in range(3):
                    for x in range(3):
                        p = (
                            current_stack[-1][0] - 1 + y,
                            current_stack[-1][1] - 1 + x,
                        )
                        if (
                                p not in completed_stack
                                and p not in current_stack
                                and not (y == 1 and x == 1)
                        ):
                            current_stack.append(p)

                completed_stack.append(current_stack.pop(-1))
                fill_canvas.set_at(completed_stack[-1], self.__current_RGB)
            else:
                current_stack.pop(-1)

        self.__canvas.blit(fill_canvas, (0, 0))

    def color_setter(self):
        ...

    def clear_screen(self):
        self.__canvas.fill(GRAY)


class TextEntryBox:
    def __init__(self, renderer, vals, col=SLIGHTLY_DARKER_GRAY):
        self.writing = False
        self._current_string: str = ""
        self.renderer = renderer
        entryboxes.append(self)
        self.col = col
        self.rect: pygame.rect.Rect = pygame.Rect(vals)
        self.__box_surface = pygame.Surface((vals[2], vals[3]))

        self.__font: pygame.font.Font = renderer.font
        self.__cursor_surf = pygame.Surface((4, 30))

    def text_box_clicked(self):
        self.writing = True
        self.col = SLIGHTLY_DARKER_DARKER_GRAY

    def text_box_not_clicked(self):
        self.writing = False
        self.col = SLIGHTLY_DARKER_GRAY

    def update_string(self, event):
        if event.key == K_BACKSPACE and self._current_string != "":
            self._current_string = self._current_string[:-1]

        elif event.key != K_BACKSPACE:
            self._current_string = self._current_string + event.unicode

    def render(self):
        rendered_text = self.__font.render(self._current_string, True, BLACK)
        text_rect = rendered_text.get_rect()
        if (pygame.time.get_ticks() % 1 > 1/2) and self.writing:
            self.__cursor_surf.fill(BLACK)
        else:
            self.__cursor_surf.fill(BLUE)
        self.__box_surface.fill(self.col)
        pygame.draw.rect(self.__box_surface, RED, (0, 0, *self.__box_surface.get_size()), width=3)
        self.__box_surface.blit(rendered_text, (3, 3))
        self.renderer.screen.blit(self.__box_surface, self.rect)


if __name__ == "__main__":
    # Temporary
    url, port = "192.168.56.1", SERVER_PORT
    server = Client((url, port), "Alex")
    server.start()
    server.wait_till_success()

    try:
        # renderer bollocks
        render_me = Renderer(server)

        # Other class instantiations
        new_words_box = TextEntryBox(render_me, (150, 900, 1000, 100))

        render_me.render_loop()
    except Exception:
        print("\033[31m", end="")
        print(traceback.format_exc(), end="\033[0m\n")

    print("Closing server")
    server.close()

# 2
