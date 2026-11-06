"""Partida manual contra a melhor rede do treinamento atual."""

from __future__ import annotations

import math
import random

import pygame

from . import settings as cfg
from .physics import draw_ball
from .simulation import Simulation
from .training import brain_output, shot_inputs

PLAYER_STYLES = {
    "LeBron James": ((92, 55, 145), (125, 78, 53), (30, "gold")),
    "Stephen Curry": ((45, 91, 175), (211, 157, 116), (30, "white")),
    "Jason Tatum": ((35, 125, 82), (151, 99, 69), (0, "white")),
    "Gui Santos": ((37, 95, 164), (187, 129, 91), (15, "white")),
    "Nikola Jokic": ((42, 105, 175), (225, 184, 147), (15, "gold")),
    "Viktor Wembanyama": ((38, 42, 55), (138, 91, 65), (1, "white")),
    "Luka Doncic": ((30, 73, 144), (222, 174, 137), (77, "white")),
}
PLAYER_HEIGHTS = {
    "LeBron James": 2.06,
    "Stephen Curry": 1.88,
    "Jason Tatum": 2.03,
    "Gui Santos": 2.01,
    "Nikola Jokic": 2.11,
    "Viktor Wembanyama": 2.24,
    "Luka Doncic": 2.03,
}
PLAYER_HAIR_STYLES = {
    "LeBron James": "bald",
    "Stephen Curry": "short",
    "Jason Tatum": "curls",
    "Gui Santos": "big_curls",
    "Nikola Jokic": "part",
    "Viktor Wembanyama": "twists",
    "Luka Doncic": "part",
}
PLAYER_HEADBANDS = {"Gui Santos": (238, 242, 247)}
PLAYER_BEARDS = {
    "LeBron James": "full",
    "Stephen Curry": "short",
    "Jason Tatum": "short",
    "Gui Santos": "goatee",
    "Nikola Jokic": "full",
    "Luka Doncic": "short",
}


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
        self.shift_held = False
        self.power_charge = 0.0
        self.elapsed = 0.0
        self.shot_elapsed = 0.0
        self.shot_finished = False
        self.shot_message = ""
        self.running = True
        self.human_player = None
        self.previous_human_player = None
        self.pressed_keys = set()
        self.chord_latched = False
        self.secret_next_basket = False
        self.winner = None
        self.victory_particles = []
        self.jump_elapsed = None
        self.jump_duration = 0.48
        self.bot_pending_velocity = None
        self.bot_aim_elapsed = 0.0
        self.bot_jump_elapsed = None
        self._start_turn()

    def _start_turn(self) -> None:
        self.simulation.ball.reset()
        self.simulation.ball._set_hoop_position(self.elapsed)
        self.dragging = False
        self.shift_held = False
        self.power_charge = 0.0
        self.shot_elapsed = 0.0
        self.shot_finished = False
        self.shot_message = ""
        self.jump_elapsed = None
        self.bot_pending_velocity = None
        self.bot_aim_elapsed = 0.0
        self.bot_jump_elapsed = None
        if self.current_player == "bot":
            outputs = brain_output(
                self.brain,
                shot_inputs(
                    self.simulation.ball.hoop_x,
                    self.simulation.ball.hoop_y,
                    self.elapsed,
                ),
            )
            angle_output, speed_output = outputs[:2]
            boost_output = outputs[2] if len(outputs) > 2 else -1.0
            angle = math.radians(45 + angle_output * 35)
            boost = max(0.0, boost_output) * cfg.MAX_POWER_BOOST
            speed = 800 + speed_output * 500 + boost
            self.bot_pending_velocity = (
                math.cos(angle) * speed,
                -math.sin(angle) * speed,
            )
        else:
            if self.secret_next_basket:
                self.human_player = "LeBron James"
            else:
                candidates = [
                    name for name in PLAYER_STYLES if name != self.previous_human_player
                ]
                self.human_player = random.choice(candidates)
            self.previous_human_player = self.human_player

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
                self.pressed_keys.add(event.key)
                self._check_hidden_chord()
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_F11:
                    self.simulation.toggle_fullscreen()
                    self.screen = self.simulation.screen
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and self.shot_finished:
                    self._next_turn()
                elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self.shift_held = True
            elif event.type == pygame.KEYUP:
                self.pressed_keys.discard(event.key)
                self._check_hidden_chord()
                if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self.shift_held = False
            elif self.current_player == "human" and not self.shot_finished:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not ball.active:
                    mx, my = event.pos
                    if math.hypot(mx - ball.x, my - ball.y) <= 2 * cfg.BALL_RADIUS:
                        self.dragging = True
                        self.mouse_position = event.pos
                elif event.type == pygame.MOUSEMOTION and self.dragging:
                    self.mouse_position = event.pos
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
                    boost = (
                        cfg.MAX_POWER_BOOST
                        * self.power_charge / cfg.POWER_CHARGE_SECONDS
                    )
                    ball.launch(*event.pos, boost=boost)
                    self.dragging = False
                    self.power_charge = 0.0
                    self.jump_elapsed = 0.0

    def _check_hidden_chord(self) -> None:
        ctrl_down = any(key in self.pressed_keys for key in (pygame.K_LCTRL, pygame.K_RCTRL))
        shift_down = any(key in self.pressed_keys for key in (pygame.K_LSHIFT, pygame.K_RSHIFT))
        chord_down = (
            ctrl_down and shift_down
            and pygame.K_l in self.pressed_keys
            and pygame.K_j in self.pressed_keys
        )
        if not chord_down:
            self.chord_latched = False
        elif not self.chord_latched:
            self.chord_latched = True
            if self.current_player == "human" and not self.shot_finished:
                self.secret_next_basket = True
                self.human_player = "LeBron James"
                self.previous_human_player = self.human_player

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
                points = 10 if self.secret_next_basket else ball.score_value
                self.player_score += points
                self.shot_message = f"Cesta! +{points} ponto(s)."
                self.secret_next_basket = False
            else:
                self.bot_score += ball.score_value
                self.shot_message = f"O bot marcou +{ball.score_value} ponto(s)."
            self.shot_finished = True
            if self.player_score >= self.TARGET_SCORE:
                self._start_victory_effect("human")
            elif self.bot_score >= self.TARGET_SCORE:
                self._start_victory_effect("bot")
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
        if self.current_player == "human":
            self._draw_human_player(self.human_player)
            character_label = f"Jogador deste arremesso: {self.human_player}"
        else:
            self._draw_robot()
            character_label = "Bot: Robo generico"
        if self.dragging:
            pygame.draw.line(self.screen, (100, 220, 160),
                             (round(ball.x), round(ball.y)), self.mouse_position, 3)
            pygame.draw.circle(self.screen, (100, 220, 160), self.mouse_position, 5)
        draw_ball(self.screen, ball)
        if self.winner:
            self._draw_victory_effects()
        if self.current_player == "human" and not self.shot_finished:
            self.simulation.draw_power_bar(self.power_charge, y=190)

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
            "Aro: 1, 3, 5...  |  tabela +2  |  sem toque +3",
            True, (170, 190, 215)), (24, 108))
        self.screen.blit(self.small_font.render(
            character_label, True, (190, 210, 235)), (320, 162))

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
                "Arraste para mirar; SHIFT: forca (1,5s); F11: tela cheia; ESC: voltar",
                True, (170, 184, 204)), (24, 138))

        pygame.display.flip()

    def _start_victory_effect(self, winner: str) -> None:
        self.winner = winner
        count = 110 if winner == "human" else 26
        self.victory_particles = []
        for _ in range(count):
            if winner == "human":
                self.victory_particles.append({
                    "x": random.uniform(0, cfg.SCREEN_WIDTH),
                    "y": random.uniform(-cfg.SCREEN_HEIGHT, cfg.SCREEN_HEIGHT),
                    "vx": random.uniform(-70, 70),
                    "vy": random.uniform(45, 190),
                    "size": random.uniform(4, 9),
                    "angle": random.uniform(0, math.tau),
                    "spin": random.uniform(-5, 5),
                    "color": random.choice((
                        (255, 91, 104), (255, 207, 75), (87, 221, 152),
                        (86, 173, 255), (203, 126, 255), (255, 255, 255),
                    )),
                })
            else:
                self.victory_particles.append({
                    "x": random.uniform(20, cfg.SCREEN_WIDTH - 20),
                    "y": random.uniform(-cfg.SCREEN_HEIGHT, -10),
                    "vx": random.uniform(-100, 100),
                    "vy": random.uniform(90, 240),
                    "radius": random.randint(9, 15),
                })

    def _draw_victory_effects(self) -> None:
        for particle in self.victory_particles:
            x, y = round(particle["x"]), round(particle["y"])
            if self.winner == "human":
                size = particle["size"]
                half_w, half_h = size, size * 0.45
                angle = particle["angle"]
                cos_a, sin_a = math.cos(angle), math.sin(angle)
                corners = []
                for px, py in ((-half_w, -half_h), (half_w, -half_h),
                               (half_w, half_h), (-half_w, half_h)):
                    corners.append((
                        round(x + px * cos_a - py * sin_a),
                        round(y + px * sin_a + py * cos_a),
                    ))
                pygame.draw.polygon(self.screen, particle["color"], corners)
            else:
                radius = particle["radius"]
                pygame.draw.circle(self.screen, (194, 38, 48), (x, y), radius)
                pygame.draw.circle(self.screen, (239, 79, 69),
                                   (x - radius // 3, y - radius // 3), max(2, radius // 3))
                pygame.draw.polygon(self.screen, (64, 145, 65), (
                    (x, y - radius + 2),
                    (x - radius // 2, y - radius - 4),
                    (x - 1, y - radius - 2),
                    (x + radius // 2, y - radius - 5),
                    (x + radius // 3, y - radius + 3),
                ))

    def _update_victory_effects(self, dt: float) -> None:
        for particle in self.victory_particles:
            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt
            if self.winner == "human":
                particle["vy"] += 100 * dt
                particle["angle"] += particle["spin"] * dt
                if particle["y"] > cfg.SCREEN_HEIGHT + 10:
                    particle["y"] = random.uniform(-100, -10)
                    particle["x"] = random.uniform(0, cfg.SCREEN_WIDTH)
            else:
                particle["vy"] += 120 * dt
                if particle["y"] > cfg.SCREEN_HEIGHT + particle["radius"]:
                    particle["y"] = random.uniform(-160, -20)
                    particle["x"] = random.uniform(20, cfg.SCREEN_WIDTH - 20)

    def _draw_human_player(self, name: str | None) -> None:
        if name is None:
            return
        jersey, skin, (number, trim) = PLAYER_STYLES[name]
        center_x, ground_y = 32, 88
        avatar = pygame.Surface((64, 88), pygame.SRCALPHA)
        trim_color = (245, 199, 74) if trim == "gold" else (238, 242, 247)
        powered = self.secret_next_basket and name == "LeBron James"
        if powered:
            pulse = round(3 * math.sin(self.elapsed * 9))
            pygame.draw.ellipse(
                avatar, (54, 172, 255),
                (center_x - 27 - pulse, 6 - pulse, 54 + 2 * pulse, 78 + 2 * pulse), 3,
            )
            pygame.draw.ellipse(
                avatar, (255, 211, 66),
                (center_x - 22 + pulse, 11 + pulse, 44 - 2 * pulse, 69 - 2 * pulse), 2,
            )
        pygame.draw.ellipse(avatar, (9, 13, 20), (center_x - 17, ground_y - 3, 34, 7))
        pygame.draw.line(avatar, skin, (center_x - 7, ground_y - 20),
                         (center_x - 11, ground_y - 4), 5)
        pygame.draw.line(avatar, skin, (center_x + 7, ground_y - 20),
                         (center_x + 11, ground_y - 4), 5)
        pygame.draw.line(avatar, (238, 239, 242), (center_x - 11, ground_y - 4),
                         (center_x - 17, ground_y - 3), 4)
        pygame.draw.line(avatar, (238, 239, 242), (center_x + 11, ground_y - 4),
                         (center_x + 17, ground_y - 3), 4)
        pygame.draw.rect(avatar, jersey,
                         (center_x - 12, ground_y - 44, 24, 25), border_radius=4)
        pygame.draw.line(avatar, trim_color, (center_x - 8, ground_y - 43),
                         (center_x - 8, ground_y - 21), 2)
        pygame.draw.line(avatar, trim_color, (center_x + 8, ground_y - 43),
                         (center_x + 8, ground_y - 21), 2)
        number_text = self.small_font.render(str(number), True, trim_color)
        avatar.blit(number_text, number_text.get_rect(center=(center_x, ground_y - 33)))
        if self.dragging:
            pygame.draw.line(avatar, skin, (center_x - 10, ground_y - 40),
                             (center_x - 20, ground_y - 30), 5)
            pygame.draw.line(avatar, skin, (center_x + 10, ground_y - 40),
                             (center_x + 21, ground_y - 34), 5)
        elif self.jump_elapsed is not None:
            pygame.draw.line(avatar, skin, (center_x - 10, ground_y - 40),
                             (center_x - 19, ground_y - 61), 5)
            pygame.draw.line(avatar, skin, (center_x + 10, ground_y - 40),
                             (center_x + 19, ground_y - 61), 5)
        else:
            pygame.draw.line(avatar, skin, (center_x - 10, ground_y - 40),
                             (center_x - 20, ground_y - 24), 5)
            pygame.draw.line(avatar, skin, (center_x + 10, ground_y - 40),
                             (center_x + 20, ground_y - 24), 5)
        pygame.draw.circle(avatar, skin, (center_x, ground_y - 54), 10)
        head_y = ground_y - 54
        self._draw_player_hair(avatar, name, center_x, head_y)
        self._draw_player_headband(avatar, name, center_x, head_y)
        self._draw_player_beard(avatar, name, center_x, head_y)
        if powered:
            crown_y = ground_y - 77
            pygame.draw.polygon(avatar, (255, 205, 48), (
                (center_x - 11, crown_y + 8),
                (center_x - 13, crown_y - 4),
                (center_x - 5, crown_y + 2),
                (center_x, crown_y - 8),
                (center_x + 5, crown_y + 2),
                (center_x + 13, crown_y - 4),
                (center_x + 11, crown_y + 8),
            ))
            pygame.draw.rect(avatar, (255, 226, 91),
                             (center_x - 11, crown_y + 7, 22, 4), border_radius=2)
        pygame.draw.rect(avatar, trim_color,
                         (center_x - 13, ground_y - 20, 26, 3), border_radius=2)
        scale = PLAYER_HEIGHTS[name] / 1.88 * 1.08
        height_scale = 0.78 if self.dragging else 1.0
        jump_height = 0.0
        if self.jump_elapsed is not None:
            progress = min(1.0, self.jump_elapsed / self.jump_duration)
            jump_height = 48 * math.sin(math.pi * progress)
        target_size = (
            max(1, round(64 * scale)),
            max(1, round(88 * scale * height_scale)),
        )
        avatar = pygame.transform.smoothscale(avatar, target_size)
        ground = round(634 - jump_height)
        self.screen.blit(avatar, (66 - target_size[0] // 2, ground - target_size[1]))

    @staticmethod
    def _draw_player_hair(avatar: pygame.Surface, name: str,
                          center_x: int, head_y: int) -> None:
        hair = (35, 27, 25)
        style = PLAYER_HAIR_STYLES[name]
        if style == "bald":
            return
        pygame.draw.ellipse(avatar, hair,
                            (center_x - 10, head_y - 10, 20, 11))
        if style == "curls":
            for offset, rise in ((-8, 5), (-5, 8), (-1, 9), (3, 8), (7, 6)):
                pygame.draw.circle(avatar, hair,
                                   (center_x + offset, head_y - rise), 3)
        elif style == "big_curls":
            for offset, rise, radius in (
                (-10, 8, 4), (-7, 13, 4), (-3, 16, 4), (2, 17, 4),
                (7, 14, 4), (10, 9, 4), (-11, 3, 3), (11, 4, 3),
            ):
                pygame.draw.circle(avatar, hair,
                                   (center_x + offset, head_y - rise), radius)
        elif style == "twists":
            for offset, rise in ((-8, 7), (-4, 10), (0, 11), (4, 9), (8, 7)):
                pygame.draw.line(avatar, hair,
                                 (center_x + offset, head_y - rise + 4),
                                 (center_x + offset, head_y - rise), 3)
        elif style == "part":
            pygame.draw.ellipse(avatar, (68, 48, 38),
                                (center_x + 1, head_y - 9, 8, 6))
            pygame.draw.line(avatar, (20, 18, 17),
                             (center_x + 1, head_y - 9),
                             (center_x - 1, head_y - 4), 1)
        else:
            pygame.draw.line(avatar, (20, 18, 17),
                             (center_x - 8, head_y - 4),
                             (center_x + 8, head_y - 4), 2)
        pygame.draw.rect(avatar, hair,
                         (center_x - 10, head_y - 3, 3, 7), border_radius=1)
        pygame.draw.rect(avatar, hair,
                         (center_x + 7, head_y - 3, 3, 7), border_radius=1)

    @staticmethod
    def _draw_player_headband(avatar: pygame.Surface, name: str,
                              center_x: int, head_y: int) -> None:
        color = PLAYER_HEADBANDS.get(name)
        if color is None:
            return
        pygame.draw.rect(avatar, color,
                         (center_x - 10, head_y - 3, 20, 4), border_radius=2)

    @staticmethod
    def _draw_player_beard(avatar: pygame.Surface, name: str,
                           center_x: int, head_y: int) -> None:
        style = PLAYER_BEARDS.get(name)
        if style is None:
            return
        color = (37, 29, 27)
        if name == "Nikola Jokic":
            color = (92, 68, 51)
        pygame.draw.ellipse(avatar, color,
                            (center_x - 6, head_y + 2, 12, 4))
        if style == "full":
            pygame.draw.polygon(avatar, color, (
                (center_x - 8, head_y + 1),
                (center_x - 7, head_y + 7),
                (center_x - 3, head_y + 10),
                (center_x, head_y + 11),
                (center_x + 4, head_y + 9),
                (center_x + 7, head_y + 5),
                (center_x + 8, head_y + 1),
                (center_x + 4, head_y + 4),
                (center_x, head_y + 5),
                (center_x - 4, head_y + 4),
            ))
        elif style == "goatee":
            pygame.draw.polygon(avatar, color, (
                (center_x - 3, head_y + 3),
                (center_x + 3, head_y + 3),
                (center_x + 2, head_y + 8),
                (center_x, head_y + 10),
                (center_x - 2, head_y + 8),
            ))
        else:
            pygame.draw.arc(avatar, color,
                            (center_x - 8, head_y - 1, 16, 12),
                            math.pi, math.tau, 3)

    def _draw_robot(self) -> None:
        center_x, ground_y = 32, 88
        metal, glow = (117, 143, 169), (96, 225, 255)
        robot = pygame.Surface((64, 88), pygame.SRCALPHA)
        aiming = self.bot_pending_velocity is not None
        pygame.draw.ellipse(robot, (9, 13, 20), (center_x - 19, ground_y - 3, 38, 7))
        pygame.draw.line(robot, metal, (center_x - 8, ground_y - 20),
                         (center_x - 10, ground_y - 4), 6)
        pygame.draw.line(robot, metal, (center_x + 8, ground_y - 20),
                         (center_x + 10, ground_y - 4), 6)
        pygame.draw.rect(robot, (77, 97, 119),
                         (center_x - 16, ground_y - 46, 32, 27), border_radius=5)
        if aiming:
            arm_ends = ((center_x - 22, ground_y - 31),
                        (center_x + 22, ground_y - 31))
        elif self.bot_jump_elapsed is not None:
            arm_ends = ((center_x - 21, ground_y - 64),
                        (center_x + 21, ground_y - 64))
        else:
            arm_ends = ((center_x - 22, ground_y - 25),
                        (center_x + 22, ground_y - 25))
        pygame.draw.line(robot, metal, (center_x - 14, ground_y - 41), arm_ends[0], 6)
        pygame.draw.line(robot, metal, (center_x + 14, ground_y - 41), arm_ends[1], 6)
        pygame.draw.rect(robot, metal,
                         (center_x - 13, ground_y - 68, 26, 20), border_radius=5)
        pygame.draw.line(robot, glow, (center_x, ground_y - 68),
                         (center_x, ground_y - 76), 2)
        pygame.draw.circle(robot, glow, (center_x, ground_y - 78), 3)
        pygame.draw.circle(robot, glow, (center_x - 6, ground_y - 59), 3)
        pygame.draw.circle(robot, glow, (center_x + 6, ground_y - 59), 3)
        pygame.draw.line(robot, (207, 221, 234), (center_x - 13, ground_y - 20),
                         (center_x + 13, ground_y - 20), 3)
        height_scale = 0.80 if aiming else 1.0
        jump_height = 0.0
        if self.bot_jump_elapsed is not None:
            progress = min(1.0, self.bot_jump_elapsed / self.jump_duration)
            jump_height = 42 * math.sin(math.pi * progress)
        target_size = (69, max(1, round(95 * height_scale)))
        robot = pygame.transform.smoothscale(robot, target_size)
        ground = round(634 - jump_height)
        self.screen.blit(robot, (66 - target_size[0] // 2, ground - target_size[1]))

    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(cfg.FPS) / 1000.0, 1 / 30)
            self.elapsed += dt
            self._handle_events()
            if self.bot_pending_velocity is not None:
                self.bot_aim_elapsed += dt
                if self.bot_aim_elapsed >= 0.24:
                    self.simulation.ball.vx, self.simulation.ball.vy = self.bot_pending_velocity
                    self.simulation.ball.active = True
                    self.bot_pending_velocity = None
                    self.bot_jump_elapsed = 0.0
            if self.shift_held and self.current_player == "human" and not self.simulation.ball.active:
                self.power_charge = min(
                    cfg.POWER_CHARGE_SECONDS, self.power_charge + dt
                )
            self._update(dt)
            if self.jump_elapsed is not None:
                self.jump_elapsed += dt
                if self.jump_elapsed >= self.jump_duration:
                    self.jump_elapsed = None
            if self.bot_jump_elapsed is not None:
                self.bot_jump_elapsed += dt
                if self.bot_jump_elapsed >= self.jump_duration:
                    self.bot_jump_elapsed = None
            if self.winner:
                self._update_victory_effects(dt)
            self._draw()
        pygame.quit()
