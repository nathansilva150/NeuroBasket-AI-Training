"""Partida manual contra a melhor rede do treinamento atual."""

from __future__ import annotations

import math

import pygame

from . import settings as cfg
from .physics import draw_ball
from .simulation import Simulation
from .training import brain_output, shot_inputs


class MatchSession:
    TARGET_SCORE = 10

    def __init__(self, brain: dict[str, list], generation: int,
                 record_generation: int | None = None) -> None:
        self.brain = brain
        self.generation = generation
        self.record_generation = record_generation or generation
        self.simulation = Simulation()
        self.screen = self.simulation.screen
        self.clock = self.simulation.clock
        self.font = self.simulation.font
        self.small_font = self.simulation.small_font
        self.player_score = 0
        self.bot_score = 0
        self.current_player = "human"
        self.dragging = False
        self.mouse_position = (0, 0)
        self.elapsed = 0.0
        self.shot_elapsed = 0.0
        self.shot_finished = False
        self.shot_message = ""
        self.running = True
        self._start_turn()

    def _start_turn(self) -> None:
        self.simulation.ball.reset()
        self.simulation.ball._set_hoop_position(self.elapsed)
        self.dragging = False
        self.shot_elapsed = 0.0
        self.shot_finished = False
        self.shot_message = ""
        if self.current_player == "bot":
            angle_output, speed_output = brain_output(
                self.brain,
                shot_inputs(
                    self.simulation.ball.hoop_x,
                    self.simulation.ball.hoop_y,
                    self.elapsed,
                ),
            )
            angle = math.radians(45 + angle_output * 35)
            speed = 800 + speed_output * 500
            self.simulation.ball.vx = math.cos(angle) * speed
            self.simulation.ball.vy = -math.sin(angle) * speed
            self.simulation.ball.active = True

    def _next_turn(self) -> None:
        if self.player_score >= self.TARGET_SCORE or self.bot_score >= self.TARGET_SCORE:
            self.running = False
            return
        self.current_player = "bot" if self.current_player == "human" else "human"
        self._start_turn()

    def _handle_events(self) -> None:
        ball = self.simulation.ball
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and self.shot_finished:
                    self._next_turn()
            elif self.current_player == "human" and not self.shot_finished:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not ball.active:
                    mx, my = event.pos
                    if math.hypot(mx - ball.x, my - ball.y) <= 2 * cfg.BALL_RADIUS:
                        self.dragging = True
                        self.mouse_position = event.pos
                elif event.type == pygame.MOUSEMOTION and self.dragging:
                    self.mouse_position = event.pos
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
                    ball.launch(*event.pos)
                    self.dragging = False

    def _update(self, dt: float) -> None:
        if self.shot_finished:
            return
        self.simulation.ball.update(dt, self.elapsed)
        ball = self.simulation.ball
        if not ball.active:
            return
        self.shot_elapsed += dt
        if ball.scored:
            if self.current_player == "human":
                self.player_score += ball.score_value
                self.shot_message = f"Cesta! +{ball.score_value} ponto(s)."
            else:
                self.bot_score += ball.score_value
                self.shot_message = f"O bot marcou +{ball.score_value} ponto(s)."
            self.shot_finished = True
        elif (
            self.shot_elapsed >= 4.0
            or ball.x < -cfg.BALL_RADIUS
            or ball.x > cfg.SCREEN_WIDTH + cfg.BALL_RADIUS
            or (ball.y > cfg.FLOOR_Y + cfg.BALL_RADIUS and ball.vy > 0)
        ):
            self.shot_message = "Sem cesta."
            self.shot_finished = True

    def _draw(self) -> None:
        ball = self.simulation.ball
        self.simulation._draw_court(ball.hoop_x, ball.hoop_y)
        if self.dragging:
            pygame.draw.line(self.screen, (100, 220, 160),
                             (round(ball.x), round(ball.y)), self.mouse_position, 3)
            pygame.draw.circle(self.screen, (100, 220, 160), self.mouse_position, 5)
        draw_ball(self.screen, ball)

        title = self.font.render("PARTIDA CONTRA A IA", True, (238, 243, 250))
        self.screen.blit(title, (24, 20))
        score = self.font.render(
            f"Voce {self.player_score}  x  {self.bot_score} Bot  |  primeiro a 10 PONTOS",
            True,
            (238, 243, 250),
        )
        self.screen.blit(score, (24, 52))
        turn_name = "Sua vez" if self.current_player == "human" else "Vez do bot"
        self.screen.blit(self.small_font.render(
            f"Bot selecionado ate a geracao {self.generation} "
            f"(recorde da {self.record_generation})  |  {turn_name}",
            True, (170, 190, 215)), (24, 82))
        self.screen.blit(self.small_font.render(
            "Pontuacao por cesta: aro +1  |  tabela +2  |  sem toque +3",
            True, (170, 190, 215)), (24, 108))

        if self.shot_finished:
            message = self.shot_message
            if self.player_score >= self.TARGET_SCORE:
                message = "Voce venceu: chegou a 10 pontos!"
            elif self.bot_score >= self.TARGET_SCORE:
                message = "O bot venceu: chegou a 10 pontos."
            color = (120, 235, 160) if self.player_score >= 10 else (255, 210, 120)
            self.screen.blit(self.font.render(message, True, color), (24, 138))
            if self.player_score < self.TARGET_SCORE and self.bot_score < self.TARGET_SCORE:
                self.screen.blit(self.small_font.render(
                    "ENTER ou ESPACO: proximo arremesso", True, (215, 225, 238)), (24, 168))
            else:
                self.screen.blit(self.small_font.render(
                    "Pressione ESC para voltar ao treinamento", True, (215, 225, 238)),
                    (24, 168))
        elif self.current_player == "human":
            self.screen.blit(self.small_font.render(
                "Clique na bola, arraste para mirar e solte. ESC: voltar ao treinamento",
                True, (170, 184, 204)), (24, 138))

        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(cfg.FPS) / 1000.0, 1 / 30)
            self.elapsed += dt
            self._handle_events()
            self._update(dt)
            self._draw()
        pygame.quit()
