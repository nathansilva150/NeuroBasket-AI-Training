"""Painel visual do treinamento evolutivo."""

from __future__ import annotations

import pygame

from . import settings as cfg


class TrainingView:
    def __init__(self) -> None:
        pygame.init()
        self.width = 1280
        self.height = 820
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("NeuroBasket | Painel de treinamento")
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.SysFont("consolas", 25, bold=True)
        self.section_font = pygame.font.SysFont("consolas", 18, bold=True)
        self.font = pygame.font.SysFont("consolas", 15)
        self.small_font = pygame.font.SysFont("consolas", 12)
        self.running = True
        self.match_requested = False
        self.match_button = pygame.Rect(900, 15, 354, 40)
        self.background = (17, 23, 33)
        self.panel = (27, 36, 50)

    def _text(self, value: str, x: int, y: int, color=(225, 233, 244), font=None) -> None:
        surface = (font or self.font).render(value, True, color)
        self.screen.blit(surface, (x, y))

    def _draw_court(self, rect: pygame.Rect, hoop_x: float | None = None,
                    hoop_y: float | None = None) -> None:
        pygame.draw.rect(self.screen, (20, 28, 40), rect, border_radius=5)
        sx = rect.width / cfg.SCREEN_WIDTH
        sy = rect.height / cfg.SCREEN_HEIGHT
        hoop_x = cfg.HOOP_CENTER_X if hoop_x is None else hoop_x
        hoop_y = cfg.HOOP_Y if hoop_y is None else hoop_y
        ellipse = pygame.Rect(
            rect.x + round((cfg.HOOP_CENTER_X - cfg.HOOP_MOTION_RADIUS_X) * sx),
            rect.y + round((cfg.HOOP_Y - cfg.HOOP_MOTION_RADIUS_Y) * sy),
            round(2 * cfg.HOOP_MOTION_RADIUS_X * sx),
            round(2 * cfg.HOOP_MOTION_RADIUS_Y * sy),
        )
        pygame.draw.ellipse(self.screen, (55, 78, 105), ellipse, max(1, round(sx)))
        floor_y = rect.y + round(cfg.FLOOR_Y * sy)
        pygame.draw.line(self.screen, (205, 216, 231), (rect.x, floor_y),
                         (rect.right, floor_y), max(1, round(3 * sy)))
        backboard_x = hoop_x + (cfg.BACKBOARD_X - cfg.HOOP_CENTER_X)
        backboard_top = hoop_y + (cfg.BACKBOARD_TOP - cfg.HOOP_Y)
        backboard_bottom = hoop_y + (cfg.BACKBOARD_BOTTOM - cfg.HOOP_Y)
        pygame.draw.line(self.screen, (230, 235, 242),
                         (rect.x + round(backboard_x * sx), rect.y + round(backboard_top * sy)),
                         (rect.x + round(backboard_x * sx), rect.y + round(backboard_bottom * sy)),
                         max(1, round(5 * sx)))
        half_width = (cfg.HOOP_RIGHT_X - cfg.HOOP_LEFT_X) / 2
        left = (rect.x + round((hoop_x - half_width) * sx), rect.y + round(hoop_y * sy))
        right = (rect.x + round((hoop_x + half_width) * sx), rect.y + round(hoop_y * sy))
        pygame.draw.line(self.screen, (235, 107, 70), left, right, max(1, round(2 * sx)))
        rim_radius = max(2, round(6 * sx))
        pygame.draw.circle(self.screen, (255, 125, 82), left, rim_radius)
        pygame.draw.circle(self.screen, (255, 125, 82), right, rim_radius)

    @staticmethod
    def _map_point(point: tuple[float, float], rect: pygame.Rect) -> tuple[int, int]:
        return (
            rect.x + round(point[0] * rect.width / cfg.SCREEN_WIDTH),
            rect.y + round(point[1] * rect.height / cfg.SCREEN_HEIGHT),
        )

    def _draw_trace(self, target: pygame.Surface, path: list[tuple[float, float]],
                    rect: pygame.Rect, color: tuple[int, int, int], width: int = 2) -> None:
        if len(path) < 2:
            return
        points = [self._map_point(point, rect) for point in path]
        pygame.draw.lines(target, color, False, points, width)

    def _draw_all_traces(self, rect: pygame.Rect, ranked: list[tuple]) -> None:
        trace_layer = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for entry in ranked:
            reward, path = entry[9], entry[5]
            if reward == 3:
                color = (85, 245, 155, 95)
            elif reward == 2:
                color = (85, 175, 255, 105)
            elif reward == 1:
                color = (255, 205, 85, 105)
            else:
                color = (255, 105, 100, 48)
            self._draw_trace(trace_layer, path, rect, color, 1)
        self.screen.blit(trace_layer, (0, 0))

    def update(self, generation: int, generations: int, ranked: list[tuple],
               average_fitness: float, population_size: int,
               generation_delay_ms: int = 500,
               evaluation_phases: int = 8) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q)
            ):
                self.running = False
            elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                  and self.match_button.collidepoint(event.pos)):
                self.match_requested = True
        if not self.running:
            return False

        best = ranked[0]
        baskets = sum(entry[7] for entry in ranked)
        counts = {1: 0, 2: 0, 3: 0}
        for entry in ranked:
            for reward, count in zip((1, 2, 3), entry[8]):
                counts[reward] += count

        self.screen.fill(self.background)
        self._text("NEUROBASKET | PAINEL DE TREINAMENTO", 24, 18,
                   (240, 245, 252), self.title_font)
        self._text(f"GERACAO {generation}/{generations}", 26, 58,
                   (112, 202, 255), self.section_font)
        self._text("ESC ou Q: encerrar treinamento", 950, 62, (160, 176, 196), self.small_font)
        pygame.draw.rect(self.screen, (43, 115, 82), self.match_button, border_radius=8)
        pygame.draw.rect(self.screen, (102, 221, 160), self.match_button, 2, border_radius=8)
        button_text = self.section_font.render("DISPUTAR COM MELHOR BOT", True, (238, 255, 246))
        self.screen.blit(button_text, button_text.get_rect(center=self.match_button.center))

        left_panel = pygame.Rect(20, 96, 735, 704)
        right_panel = pygame.Rect(775, 96, 485, 704)
        pygame.draw.rect(self.screen, self.panel, left_panel, border_radius=10)
        pygame.draw.rect(self.screen, self.panel, right_panel, border_radius=10)
        self._text("MELHOR ARREMESSO DA GERACAO", 38, 110,
                   (240, 245, 252), self.section_font)
        self._text("POPULACAO COMPLETA | TODAS AS TRAJETORIAS", 792, 110,
                   (240, 245, 252), self.section_font)

        best_rect = pygame.Rect(38, 150, 699, 490)
        all_rect = pygame.Rect(794, 150, 447, 313)
        self._draw_court(best_rect, *best[6][0])
        self._draw_court(all_rect)
        self._draw_trace(self.screen, best[5], best_rect, (105, 255, 170), 4)
        self._draw_trace(self.screen, best[6], best_rect, (100, 170, 255), 2)
        if best[5]:
            pygame.draw.circle(self.screen, (255, 153, 75),
                               self._map_point(best[5][0], best_rect), 8)
            pygame.draw.circle(self.screen, (105, 255, 170),
                               self._map_point(best[5][-1], best_rect), 6)
        self._draw_all_traces(all_rect, ranked)

        attempts = population_size * evaluation_phases
        self._text(f"Individuos: {population_size}    Cestas: {baskets}/{attempts} arremessos",
                   794, 477, (225, 233, 244))
        self._text(f"Fitness melhor: {best[0]:.2f}    Fitness medio: {average_fitness:.2f}",
                   794, 502, (225, 233, 244))
        self._text(f"Recompensas: aro +1 ({counts[1]})   tabela +2 ({counts[2]})", 794, 527)
        self._text(f"Sem toque +3 ({counts[3]})", 794, 552)
        self._text(f"Melhor rede: {best[2]} pontos em {evaluation_phases} fases", 794, 583,
                   (105, 255, 170))
        self._text(f"Lance mostrado: {best[3]:.1f} graus | {best[4]:.0f} px/s",
                   794, 607, (225, 233, 244))
        self._text("Verde: +3    Azul: +2    Amarelo: +1    Vermelho: sem cesta",
                   794, 638, (175, 190, 210), self.small_font)
        self._text("A rede escolhe angulo e velocidade; a populacao evolui a cada geracao.",
                   38, 666, (175, 190, 210), self.small_font)
        self._text("Amostra visual da trajetoria completa do melhor individuo:",
                   38, 689, (175, 190, 210), self.small_font)
        self._text("Cada linha no painel direito representa um individuo desta geracao.",
                   38, 712, (175, 190, 210), self.small_font)
        self._text("Linha azul no painel esquerdo: movimento da cesta durante o arremesso.",
                   38, 735, (155, 185, 235), self.small_font)

        pygame.display.flip()
        pygame.time.delay(generation_delay_ms)
        return self.running

    def consume_match_request(self) -> bool:
        requested = self.match_requested
        self.match_requested = False
        return requested

    def close(self) -> None:
        pygame.display.quit()
