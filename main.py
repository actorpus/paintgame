import pygame
from pygame.locals import *
import traceback
import sys
import math
from utilities import *
from client import *
import io

RED = (255, 0, 0)
BLUE = (0, 0, 255)
CANVAS_BACKGROUND = (232, 252, 255)
GRAY, SLIGHTLY_DARKER_GRAY, SLIGHTLY_DARKER_DARKER_GRAY = (
    (200, 200, 200),
    (190, 190, 190),
    (180, 180, 180),
)
BLACK = (0, 0, 0)
INTERPOLATE_STEP = 20

entryboxes = []
important_keys = [K_RETURN, K_KP_ENTER, K_BACKSPACE, K_LEFT, K_RIGHT]
arrow_keys = [K_LEFT, K_RIGHT]


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


class Renderer:
    def __init__(self, client):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Drawing fun paint")
        self.server: Client = client
        self.screen = pygame.display.set_mode((1920, 1080))
        self.font = pygame.font.FontType("resources/consola.ttf", 18)
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
        self.__canvas.fill(CANVAS_BACKGROUND)
        self.clock = pygame.time.Clock()
        self.__options_menu_open = False
        self.__settings_pos = (0, 0)
        self.__round_end = time.time() + 120
        self.__skip_current_word = pygame.Surface((100, 50), pygame.SRCALPHA)
        self.__skip_current_word.fill((0, 0, 0, 0))
        self.__editing_text = False
        self.__options_menu = pygame.Surface((400, 400), pygame.SRCALPHA)
        pygame.draw.rect(
            self.__skip_current_word, (*BLUE, 255), (0, 0, 100, 50), border_radius=25
        )

        self.images = {}
        for image in ["add", "minus"]:
            i = pygame.image.load("resources/" + image + ".png")
            i = pygame.transform.scale(i, (32, 32))
            self.images[image] = i

    def render_loop(self):
        while self.__running:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.__running = False
                # Event checks:
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_h:
                        pygame.draw.rect(
                            self.__canvas, self.__current_RGB, (100, 100, 100, 100), 4
                        )

                    for box in entryboxes:
                        if box.writing:
                            if event.key in important_keys:
                                box.update_string(event)
                                break
                            elif not event.unicode:
                                continue
                            if box.writing and (32 <= ord(event.unicode) <= 126):
                                box.update_string(event)

                elif event.type == MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self._reset_states()
                        for box in entryboxes:
                            if box.rect.collidepoint(pygame.mouse.get_pos()):
                                box.text_box_clicked()
                            elif box.has_button:
                                if box.button_rect.collidepoint(pygame.mouse.get_pos()):
                                    box.on_button_press()
                                else:
                                    self._reset_states(box)
                            else:
                                self._reset_states(box)
                        else:
                            if (
                                960 < mouse_pos[0] < 1060
                                and 100 < mouse_pos[1] < 150
                                and self.__skip_current_word.get_at(
                                    (mouse_pos[0] - 960, mouse_pos[1] - 100)
                                )
                                == (*BLUE, 255)
                            ):
                                self.server.request_word_skip()
                                
                            elif 1700 < mouse_pos[0] < 1800 and 850 < mouse_pos[1] < 900 and self.__skip_current_word.get_at((mouse_pos[0]-1700, mouse_pos[1]-850)) == (*BLUE, 255):
                                self.server.request_game_start()
                                
                            elif self.__current_tool == "Drawing":
                                self.__current_tool_active = True
                                self.__last_draw_pos = mouse_pos

                            elif self.__current_tool == "Rubber":
                                self.__current_tool_active = True
                                self.__last_draw_pos = mouse_pos

                            
                            
                            

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
                self.drawing(mouse_pos, CANVAS_BACKGROUND)

            self.screen.blit(self.__canvas, (0, 0))
            if self.__options_menu_open:
                self.screen.blit(self.__options_menu, self.__settings_pos)

            self._word_list_renderer()
            self.skip_cur_word_renderer()
            if self.server.word_pattern == 'loading...':
                self.start_new_game_renderer()

            for box in entryboxes:
                box.render()
            self.timer()
            self.clock.tick(60)
            pygame.display.update()

    def _reset_states(self, box=None):
        # Careful with what you put in the function, might end up screwing things up later down the line... (tommys predictions)
        self.__options_menu_open = False
        if box is not None:
            box.writing = False
            box.col = SLIGHTLY_DARKER_GRAY
            box.reset_strings(True)

    def word_checker(self, input):
        ...

    def render_menu(self):
        ...
    
    def start_new_game_renderer(self):
        self.screen.blit(self.__skip_current_word, (1700, 850))
       
    def skip_cur_word_renderer(self):
        self.screen.blit(self.__skip_current_word, (960, 100))

    def _word_list_renderer(self):
        pygame.draw.rect(self.screen, (255, 0, 0), (1580, 20, 320, 740), width=1)
        lines_taken = 0
        max_lines = 27
        max_length = 30
        for i in self.server.chat_log[:-max_lines:-1]:
            temp_lines_taken = 0
            broken_message = split_by_max_length(i, max_length)
            for x in broken_message[::-1]:
                self.screen.blit(
                self.font.render(
                    x,
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
                RGB,
                self.__past_drawing_points[0],
                self.__pen_size // 2,
            )
            pygame.draw.circle(
                self.__canvas,
                RGB,
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

    def timer(self):
        self.screen.blit(
            self.font.render(str(int(self.__round_end - time.time())), True, BLACK),
            (800, 500),
        )

    def options_menu(self):
        # self.__options_menu = pygame.Surface((400, 400), pygame.SRCALPHA)
        pygame.draw.circle(self.__options_menu, (*GRAY, 255), (200, 200), 200)
        pygame.draw.circle(self.__options_menu, (0, 0, 0, 0), (200, 200), 95)
        pygame.draw.circle(self.__options_menu, (0, 0, 0, 255), (200, 200), 200, 2)
        pygame.draw.circle(self.__options_menu, (0, 0, 0, 255), (200, 200), 100, 2)

        # angled lines
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 255), (50, 50), (135, 135), width=16
        )
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 0), (50, 50), (135, 135), width=10
        )
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 255), (50, 350), (135, 265), width=16
        )
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 0), (50, 350), (135, 265), width=10
        )
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 255), (260, 260), (350, 350), width=16
        )
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 0), (260, 260), (350, 350), width=10
        )
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 255), (260, 135), (350, 50), width=16
        )
        pygame.draw.line(
            self.__options_menu, (0, 0, 0, 0), (260, 135), (350, 50), width=10
        )
        # straight lines
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

        self.__options_menu.blit(self.images["add"], (0, 0))

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
            #   [fill section]                      [blank]
            #          [clear screen] [blank]

            if angle < math.pi / 4:
                self.clear_screen()

            elif angle < math.pi / 2:
                threading.Thread(
                    target=lambda: self.filler(
                        (self.__settings_pos[0] + 200, self.__settings_pos[1] + 200)
                    ),
                    daemon=True,
                ).start()

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

        if settings["MouseSnap"]:
            pygame.mouse.set_pos(
                (self.__settings_pos[0] + 200, self.__settings_pos[1] + 200)
            )

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
        self.__current_tool = "Filler"

    def filler(self, mouse_pos):
        stack = [mouse_pos]

        while stack:
            item = stack.pop()

            for offset in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
                question = (item[0] + offset[0], item[1] + offset[1])

                if (
                    question[0] < 0
                    or question[0] > 1919
                    or question[1] < 0
                    or question[1] > 1079
                ):
                    continue

                if question in stack:
                    continue

                if self.__canvas.get_at(question) != CANVAS_BACKGROUND:
                    continue

                stack.insert(0, question)

            self.__canvas.set_at(item, self.__current_RGB)

    def color_setter(self):
        ...

    def clear_screen(self):
        self.__canvas.fill(CANVAS_BACKGROUND)


class TextEntryBox:
    def __init__(
        self,
        renderer,
        vals,
        default="",
        col=SLIGHTLY_DARKER_GRAY,
        on_enter=None,
        blur=False,
        button=False,
    ):
        # Private
        self.__default = default
        self.__current_string: str = default
        self.__display_string: str = default
        self.__on_enter = on_enter
        self.__blur = blur
        self.__pointer = -1
        # Public
        entryboxes.append(self)
        self.writing = False
        self.col = col
        self.renderer = renderer
        self.rect: pygame.rect.Rect = pygame.Rect(vals)
        # Setup
        self.__box_surface = pygame.Surface((vals[2], vals[3]), pygame.SRCALPHA)
        self.__font: pygame.font.Font = renderer.font
        self.__cursor_surf = pygame.Surface((2, self.__font.get_height() - 4))
        self.has_button = button

        if self.has_button:
            self.__icon = pygame.image.load("resources/tick.png")
            self.__button_surface = pygame.Surface((40, vals[3]))
            self.__button_surface.fill(self.col)
            self.__button_surface.blit(self.__icon, (-5, 5))
            self.button_rect = pygame.Rect(
                vals[0] - self.__button_surface.get_width() - 10, vals[1], 50, 20
            )

    def text_box_clicked(self):
        # Click response
        self.writing = True
        self.reset_strings()
        self.col = GRAY

    def reset_strings(self, default=False):
        if not default:
            self.__display_string = ""
        else:
            self.__display_string = self.__default
        self.__current_string = ""
        self.__pointer = -1

    def on_button_press(self):
        if self.__current_string != "":
            self.__on_enter(self.__current_string)

    def update_string(self, event):
        # Keyboard handler
        if event.key in important_keys:
            if self.__current_string != "":
                if event.key == K_BACKSPACE:
                    self.__current_string = stringpop(
                        self.__pointer, self.__current_string
                    )
                elif event.key == (K_RETURN or K_KP_ENTER):
                    print(
                        f" [ \033[35mTextBx\033[0m ] Sending String '{self.__display_string}' to function. "
                    )
                    self.__on_enter(self.__current_string)
                    self.reset_strings()
                elif event.key == K_LEFT:
                    self.__pointer -= 1
                elif event.key == K_RIGHT and self.__pointer != -1:
                    self.__pointer += 1

        elif len(self.__current_string) <= 32:
            self.__current_string = stringadd(
                event.unicode, self.__current_string, self.__pointer
            )
        self.__display_string = self.__current_string

    def render(self):
        # Drawing surfaces and blinking cursor
        if self.__blur and self.__display_string != self.__default:
            self.__display_string = "".join("*" * len(self.__current_string))
        rendered_text = self.__font.render(self.__display_string, True, BLACK)
        text_rect = rendered_text.get_rect()

        if (time.time() % 1 > 0.5) and self.writing:
            self.__cursor_surf.fill(BLACK)
        else:
            self.__cursor_surf.fill(self.col)

        pygame.draw.rect(
            self.__box_surface,
            self.col,
            (0, 0, *self.__box_surface.get_size()),
            border_radius=4,
        )
        pygame.draw.rect(
            self.__box_surface,
            BLACK,
            (0, 0, *self.__box_surface.get_size()),
            width=2,
            border_radius=4,
        )
        self.__box_surface.blit(rendered_text, (3, 3))
        self.__box_surface.blit(
            self.__cursor_surf,
            (
                text_rect.right + 2 + ((self.__pointer + 1) * 10),
                text_rect.bottom - self.renderer.font.get_height() + 5,
            ),
        )
        if self.has_button:
            self.renderer.screen.blit(self.__button_surface, self.button_rect)
        self.renderer.screen.blit(self.__box_surface, self.rect)


if __name__ == "__main__":
    if settings.default:
        print("Default settings created, please configure now")
        sys.exit(0)

    # Temporary
    url, port = settings["ServerAddress"], settings["Port"]

    server = Client((url, port), settings["Name"])
    server.start()
    server.wait_till_success()

    # renderer bollocks
    render_me = Renderer(server)

    # Other class instantiations
    guesses = TextEntryBox(
        render_me,
        (1575, 765, 325, render_me.font.get_height() + 10),
        on_enter=server.send_message,
        default="Guess a word...",
    )
    password_box = TextEntryBox(
        render_me,
        (
            1575,
            765 + render_me.font.get_height() + 20,
            325,
            render_me.font.get_height() + 10,
        ),
        on_enter=server.send_message,
        blur=True,
        default="Password",
        button=True,
    )

    render_me.render_loop()

    server.close()
