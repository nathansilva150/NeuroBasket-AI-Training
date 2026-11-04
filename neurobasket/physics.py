from __future__ import annotations

import math
import pygame

from . import settings as cfg


class Ball:
    """Bola com integração semi-implícita e colisões 2D simples."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.x, self.y = cfg.BALL_START
        self.vx = 0.0
        self.vy = 0.0
        self.active = False
        self.scored = False
        self.rim_touched = False
        self.backboard_touched = False
        self.score_value = 0
        self.last_score_time = 0.0
        self._set_hoop_position(0.0)

    def _set_hoop_position(self, elapsed: float) -> None:
        self.hoop_x, self.hoop_y = cfg.hoop_position(elapsed)
        self.backboard_x = self.hoop_x + (cfg.BACKBOARD_X - cfg.HOOP_CENTER_X)
        self.backboard_top = self.hoop_y + (cfg.BACKBOARD_TOP - cfg.HOOP_Y)
        self.backboard_bottom = self.hoop_y + (cfg.BACKBOARD_BOTTOM - cfg.HOOP_Y)

    def launch(self, target_x: float, target_y: float) -> None:
        dx = target_x - self.x
        dy = target_y - self.y
        speed = math.hypot(dx, dy) * cfg.LAUNCH_SPEED_PER_PIXEL
        speed = min(speed, cfg.MAX_LAUNCH_SPEED)

        if speed < 30:
            return

        length = math.hypot(dx, dy)
        self.vx = (dx / length) * speed
        self.vy = (dy / length) * speed
        self.active = True
        self.scored = False

    def update(self, dt: float, elapsed: float) -> None:
        previous_x, previous_y = self.x, self.y
        previous_hoop_x, previous_hoop_y = self.hoop_x, self.hoop_y
        self._set_hoop_position(elapsed)
        if not self.active:
            return

        # Subpassos reduzem a chance de a bola atravessar objetos em alta velocidade.
        steps = max(1, math.ceil(dt / (1 / 240)))
        step_dt = dt / steps

        for _ in range(steps):
            self._integrate(step_dt)
            self._collide_with_floor()
            self._collide_with_backboard()
            self._collide_with_rim()

        # Verifica a passagem relativa à cesta, que também está em movimento.
        previous_relative_y = previous_y - previous_hoop_y
        current_relative_y = self.y - self.hoop_y
        relative_y_change = current_relative_y - previous_relative_y
        if (
            not self.scored
            and previous_relative_y < 0 <= current_relative_y
            and relative_y_change > 0
        ):
            crossing_fraction = -previous_relative_y / relative_y_change
            previous_relative_x = previous_x - previous_hoop_x
            current_relative_x = self.x - self.hoop_x
            crossing_relative_x = previous_relative_x + crossing_fraction * (
                current_relative_x - previous_relative_x
            )
            opening_half_width = (
                (cfg.HOOP_RIGHT_X - cfg.HOOP_LEFT_X) / 2 - cfg.BALL_RADIUS
            )
            if abs(crossing_relative_x) < opening_half_width:
                self.scored = True
                if self.rim_touched:
                    self.score_value = 1
                elif self.backboard_touched:
                    self.score_value = 2
                else:
                    self.score_value = 3
                self.last_score_time = elapsed

    def _integrate(self, dt: float) -> None:
        self.vy += cfg.GRAVITY * dt
        # Arrasto do ar aproximado, pequeno e proporcional à velocidade.
        drag = max(0.0, 1.0 - cfg.AIR_DRAG * dt * math.hypot(self.vx, self.vy))
        self.vx *= drag
        self.vy *= drag
        self.x += self.vx * dt
        self.y += self.vy * dt

    def _resolve_circle_collision(self, cx: float, cy: float, radius: float,
                                  restitution: float) -> None:
        dx = self.x - cx
        dy = self.y - cy
        distance = math.hypot(dx, dy)
        min_distance = cfg.BALL_RADIUS + radius

        if distance == 0:
            dx, dy, distance = 1.0, 0.0, 1.0

        if distance < min_distance:
            self.rim_touched = True
            nx, ny = dx / distance, dy / distance
            penetration = min_distance - distance
            self.x += nx * penetration
            self.y += ny * penetration

            velocity_along_normal = self.vx * nx + self.vy * ny
            if velocity_along_normal < 0:
                impulse = (1 + restitution) * velocity_along_normal
                self.vx -= impulse * nx
                self.vy -= impulse * ny
                self.vx *= cfg.COLLISION_FRICTION
                self.vy *= cfg.COLLISION_FRICTION

    def _collide_with_floor(self) -> None:
        if self.y + cfg.BALL_RADIUS > cfg.FLOOR_Y:
            self.y = cfg.FLOOR_Y - cfg.BALL_RADIUS
            if self.vy > 0:
                self.vy *= -cfg.RESTITUTION_FLOOR
                self.vx *= 0.92
                if abs(self.vy) < 35:
                    self.vy = 0.0
                    self.vx *= 0.85

    def _collide_with_backboard(self) -> None:
        # A tabela é um segmento vertical com espessura desprezível.
        if self.backboard_top <= self.y <= self.backboard_bottom:
            if (self.x + cfg.BALL_RADIUS > self.backboard_x
                    and self.x < self.backboard_x):
                self.backboard_touched = True
                self.x = self.backboard_x - cfg.BALL_RADIUS
                if self.vx > 0:
                    self.vx *= -cfg.RESTITUTION_BACKBOARD
                    self.vy *= 0.98

    def _collide_with_rim(self) -> None:
        self._resolve_circle_collision(
            self.hoop_x - (cfg.HOOP_RIGHT_X - cfg.HOOP_LEFT_X) / 2,
            self.hoop_y, cfg.RIM_RADIUS, cfg.RESTITUTION_RIM
        )
        self._resolve_circle_collision(
            self.hoop_x + (cfg.HOOP_RIGHT_X - cfg.HOOP_LEFT_X) / 2,
            self.hoop_y, cfg.RIM_RADIUS, cfg.RESTITUTION_RIM
        )


def draw_ball(surface: pygame.Surface, ball: Ball) -> None:
    center = (round(ball.x), round(ball.y))
    pygame.draw.circle(surface, (225, 119, 48), center, cfg.BALL_RADIUS)
    pygame.draw.circle(surface, (105, 48, 24), center, cfg.BALL_RADIUS, 2)
    # Costuras estilizadas da bola.
    pygame.draw.arc(
        surface, (105, 48, 24),
        pygame.Rect(ball.x - 8, ball.y - 11, 16, 22),
        math.radians(270), math.radians(90), 2
    )
    pygame.draw.line(
        surface, (105, 48, 24),
        (round(ball.x - 10), round(ball.y)),
        (round(ball.x + 10), round(ball.y)), 2
    )
