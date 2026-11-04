from __future__ import annotations

import pygame

from . import settings as cfg
from .physics import Ball, draw_ball


class Simulation:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(cfg.TITLE)
        self.screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 20)
        self.small_font = pygame.font.SysFont("consolas", 15)
        self.ball = Ball()
        self.dragging = False
        self.mouse_position = (0, 0)
        self.elapsed = 0.0
        self.reward_total = 0
        self.score_counted = False
        self.running = True

    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(cfg.FPS) / 1000.0, 1 / 30)
            self.elapsed += dt
            self._handle_events()
            self.ball.update(dt, self.elapsed)
            if self.ball.scored and not self.score_counted:
                self.reward_total += self.ball.score_value
                self.score_counted = True
            self._draw()
        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    self.ball.reset()
                    self.dragging = False
                    self.score_counted = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self.ball.active:
                    mx, my = event.pos
                    distance = ((mx - self.ball.x) ** 2 + (my - self.ball.y) ** 2) ** 0.5
                    if distance <= 2 * cfg.BALL_RADIUS:
                        self.dragging = True
                        self.mouse_position = event.pos

            elif event.type == pygame.MOUSEMOTION and self.dragging:
                self.mouse_position = event.pos

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.dragging:
                    self.ball.launch(*event.pos)
                    self.dragging = False

    def _draw_court(self, hoop_x: float | None = None, hoop_y: float | None = None) -> None:
        self.screen.fill((21, 27, 38))
        hoop_x = cfg.HOOP_CENTER_X if hoop_x is None else hoop_x
        hoop_y = cfg.HOOP_Y if hoop_y is None else hoop_y
        hoop_left_x = hoop_x - (cfg.HOOP_RIGHT_X - cfg.HOOP_LEFT_X) / 2
        hoop_right_x = hoop_x + (cfg.HOOP_RIGHT_X - cfg.HOOP_LEFT_X) / 2
        backboard_x = hoop_x + (cfg.BACKBOARD_X - cfg.HOOP_CENTER_X)
        backboard_top = hoop_y + (cfg.BACKBOARD_TOP - cfg.HOOP_Y)
        backboard_bottom = hoop_y + (cfg.BACKBOARD_BOTTOM - cfg.HOOP_Y)

        # Linhas discretas de referência.
        for x in range(0, cfg.SCREEN_WIDTH, 50):
            pygame.draw.line(self.screen, (29, 37, 50), (x, 0), (x, cfg.FLOOR_Y), 1)
        for y in range(0, cfg.FLOOR_Y, 50):
            pygame.draw.line(self.screen, (29, 37, 50), (0, y), (cfg.SCREEN_WIDTH, y), 1)

        # Chão e linha da quadra.
        pygame.draw.line(self.screen, (220, 226, 235),
                         (0, cfg.FLOOR_Y), (cfg.SCREEN_WIDTH, cfg.FLOOR_Y), 4)

        # Suporte e tabela.
        pygame.draw.line(self.screen, (135, 151, 173),
                         (backboard_x + 35, backboard_top - 20),
                         (backboard_x + 35, backboard_bottom + 80), 7)
        pygame.draw.line(self.screen, (230, 235, 242),
                         (backboard_x, backboard_top),
                         (backboard_x, backboard_bottom), 7)

        # Aro: na visão lateral, as duas bordas do aro são representadas
        # por dois pequenos círculos, deixando a abertura entre elas.
        pygame.draw.line(self.screen, (238, 105, 65),
                         (hoop_left_x, hoop_y),
                         (hoop_right_x, hoop_y), 2)
        pygame.draw.circle(self.screen, (255, 119, 75),
                           (round(hoop_left_x), round(hoop_y)), 6)
        pygame.draw.circle(self.screen, (255, 119, 75),
                           (round(hoop_right_x), round(hoop_y)), 6)

        # Rede simplificada.
        net_color = (155, 170, 190)
        for i in range(5):
            x_top = hoop_left_x + 8 + i * 13
            x_bottom = x_top + (i - 2) * 3
            pygame.draw.line(self.screen, net_color,
                             (round(x_top), round(hoop_y + 5)),
                             (round(x_bottom), round(hoop_y + 48)), 1)
        pygame.draw.line(self.screen, net_color,
                         (hoop_left_x + 8, hoop_y + 48),
                         (hoop_right_x - 8, hoop_y + 48), 1)

    def _draw(self) -> None:
        self._draw_court(self.ball.hoop_x, self.ball.hoop_y)

        # Ponto de partida.
        pygame.draw.circle(self.screen, (100, 190, 255),
                           tuple(map(round, cfg.BALL_START)), 3)

        if self.dragging:
            pygame.draw.line(self.screen, (100, 220, 160),
                             (round(self.ball.x), round(self.ball.y)),
                             self.mouse_position, 3)
            pygame.draw.circle(self.screen, (100, 220, 160),
                               self.mouse_position, 5)

        draw_ball(self.screen, self.ball)

        title = self.font.render("NEUROBASKET", True, (238, 243, 250))
        self.screen.blit(title, (24, 20))
        score_text = self.small_font.render(
            f"Recompensa acumulada: {self.reward_total}", True, (238, 243, 250)
        )
        self.screen.blit(score_text, (250, 26))

        instructions = [
            "Clique na bola, arraste na direcao desejada e solte para arremessar.",
            "R: reiniciar tentativa    ESC: sair",
            "Recompensa: aro +1    tabela +2    sem toque +3",
        ]
        for index, line in enumerate(instructions):
            text = self.small_font.render(line, True, (170, 184, 204))
            self.screen.blit(text, (24, 55 + index * 23))

        if self.ball.scored:
            message = self.font.render(
                f"CESTA! +{self.ball.score_value} recompensa.",
                True,
                (120, 235, 160),
            )
            self.screen.blit(message, (24, 115))
        elif not self.ball.active:
            message = self.small_font.render("Aguardando arremesso...", True, (170, 184, 204))
            self.screen.blit(message, (24, 115))

        pygame.display.flip()
