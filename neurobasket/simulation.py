from __future__ import annotations

import pygame

from . import settings as cfg
from .physics import Ball, draw_ball


class Simulation:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(cfg.TITLE)
        self.fullscreen = False
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
        self.shift_held = False
        self.power_charge = 0.0
        self.running = True

    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(cfg.FPS) / 1000.0, 1 / 30)
            self.elapsed += dt
            self._handle_events()
            if self.shift_held and not self.ball.active:
                self.power_charge = min(
                    cfg.POWER_CHARGE_SECONDS, self.power_charge + dt
                )
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
                elif event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.key == pygame.K_r:
                    self.ball.reset()
                    self.dragging = False
                    self.score_counted = False
                    self.shift_held = False
                    self.power_charge = 0.0
                elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self.shift_held = True
            elif event.type == pygame.KEYUP and event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                self.shift_held = False
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
                    boost = (
                        cfg.MAX_POWER_BOOST
                        * self.power_charge / cfg.POWER_CHARGE_SECONDS
                    )
                    self.ball.launch(*event.pos, boost=boost)
                    self.dragging = False
                    self.power_charge = 0.0

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        flags = pygame.FULLSCREEN if self.fullscreen else 0
        self.screen = pygame.display.set_mode(
            (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), flags
        )

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
            "SHIFT: forca extra (3s)  |  F11: tela cheia  |  R: reiniciar  |  ESC: sair",
            "Aro: 1, 3, 5...    tabela +2    sem toque +3",
        ]
        for index, line in enumerate(instructions):
            text = self.small_font.render(line, True, (170, 184, 204))
            self.screen.blit(text, (24, 55 + index * 23))

        self.draw_power_bar(self.power_charge)

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

    def draw_power_bar(self, charge: float, y: int = 143) -> None:
        bar_x, bar_y, bar_width, bar_height = 24, y, 240, 14
        fraction = max(0.0, min(1.0, charge / cfg.POWER_CHARGE_SECONDS))
        pygame.draw.rect(self.screen, (52, 62, 78),
                         (bar_x, bar_y, bar_width, bar_height), border_radius=5)
        if fraction:
            color = (95, 220, 150) if fraction < 1 else (255, 195, 85)
            pygame.draw.rect(self.screen, color,
                             (bar_x, bar_y, round(bar_width * fraction), bar_height),
                             border_radius=5)
        label = self.small_font.render(
            f"FORCA EXTRA (SHIFT): {round(fraction * 100)}%",
            True, (190, 205, 225),
        )
        self.screen.blit(label, (bar_x, bar_y + 19))
