import math

import pygame

disp = pygame.display.set_mode((512, 512))
clock = pygame.time.Clock()
running = True


while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

    disp.fill(0x0)

    pygame.draw.line(disp, (255, 0, 0), (100, 100), (300, 300), width=30)

    pygame.display.update()
    clock.tick()
