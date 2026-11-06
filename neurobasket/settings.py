# Configurações gerais do NeuroBasket

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
FPS = 60
TITLE = "NeuroBasket | Simulador"

# Mundo físico: pixels e segundos
import math

GRAVITY = 980.0
BALL_RADIUS = 12
BALL_MASS = 0.62  # kg (referência; a gravidade já determina a aceleração)
AIR_DRAG = 0.0008

# Colisões
RESTITUTION_FLOOR = 0.72
RESTITUTION_RIM = 0.78
RESTITUTION_BACKBOARD = 0.68
COLLISION_FRICTION = 0.985

# Geometria do cenário
FLOOR_Y = 640
BALL_START = (130.0, 560.0)

HOOP_LEFT_X = 690.0
HOOP_RIGHT_X = 760.0
HOOP_Y = 330.0
RIM_RADIUS = 5.0

# A cesta percorre uma elipse estreita na horizontal e alta na vertical.
HOOP_CENTER_X = (HOOP_LEFT_X + HOOP_RIGHT_X) / 2
HOOP_MOTION_RADIUS_X = 22.0
HOOP_MOTION_RADIUS_Y = 110.0
HOOP_MOTION_PERIOD = 12.0


def hoop_position(elapsed: float) -> tuple[float, float]:
    """Posição da cesta ao longo de uma elipse; começa no ponto mais baixo."""
    phase = -math.pi / 2 + (elapsed / HOOP_MOTION_PERIOD) * 2 * math.pi
    x = HOOP_CENTER_X + HOOP_MOTION_RADIUS_X * math.cos(phase)
    y = HOOP_Y - HOOP_MOTION_RADIUS_Y * math.sin(phase)
    return x, y


def hoop_velocity(elapsed: float) -> tuple[float, float]:
    """Velocidade horizontal e vertical da cesta no instante informado."""
    angular_speed = 2 * math.pi / HOOP_MOTION_PERIOD
    phase = -math.pi / 2 + elapsed * angular_speed
    vx = -HOOP_MOTION_RADIUS_X * angular_speed * math.sin(phase)
    vy = -HOOP_MOTION_RADIUS_Y * angular_speed * math.cos(phase)
    return vx, vy

BACKBOARD_X = 785.0
BACKBOARD_TOP = 205.0
BACKBOARD_BOTTOM = 345.0

# Controle manual para testar a física
LAUNCH_SPEED_PER_PIXEL = 5.0
MAX_LAUNCH_SPEED = 1300.0
MAX_POWER_BOOST = 150.0
POWER_CHARGE_SECONDS = 1.5
