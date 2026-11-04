"""Treinamento evolutivo de arremessos para o NeuroBasket."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from datetime import datetime
from pathlib import Path

from . import settings as cfg
from .physics import Ball
from .training_view import TrainingView

INPUTS = 5
HIDDEN = 8
OUTPUTS = 2
DT = 1 / 120
MAX_STEPS = 600
EVALUATION_PHASES = 8


def new_brain(rng: random.Random) -> dict[str, list]:
    return {
        "w1": [[rng.uniform(-1, 1) for _ in range(HIDDEN)] for _ in range(INPUTS)],
        "b1": [rng.uniform(-1, 1) for _ in range(HIDDEN)],
        "w2": [[rng.uniform(-1, 1) for _ in range(OUTPUTS)] for _ in range(HIDDEN)],
        "b2": [rng.uniform(-1, 1) for _ in range(OUTPUTS)],
    }


def brain_output(brain: dict[str, list], inputs: list[float]) -> list[float]:
    hidden = [
        math.tanh(brain["b1"][j] + sum(inputs[i] * brain["w1"][i][j] for i in range(INPUTS)))
        for j in range(HIDDEN)
    ]
    return [
        math.tanh(brain["b2"][k] + sum(hidden[j] * brain["w2"][j][k] for j in range(HIDDEN)))
        for k in range(OUTPUTS)
    ]


def shot_inputs(hoop_x: float | None = None, hoop_y: float | None = None,
                elapsed: float = 0.0) -> list[float]:
    if hoop_x is None or hoop_y is None:
        hoop_x, hoop_y = cfg.hoop_position(elapsed)
    hoop_vx, hoop_vy = cfg.hoop_velocity(elapsed)
    return [
        (hoop_x - cfg.BALL_START[0]) / cfg.SCREEN_WIDTH,
        (cfg.BALL_START[1] - hoop_y) / cfg.SCREEN_HEIGHT,
        hoop_vx / (cfg.HOOP_MOTION_RADIUS_X * 2 * math.pi / cfg.HOOP_MOTION_PERIOD),
        hoop_vy / (cfg.HOOP_MOTION_RADIUS_Y * 2 * math.pi / cfg.HOOP_MOTION_PERIOD),
        1.0,
    ]


def evaluate_one(brain: dict[str, list], start_time: float) -> tuple:
    initial_hoop_x, initial_hoop_y = cfg.hoop_position(start_time)
    angle_output, speed_output = brain_output(
        brain, shot_inputs(initial_hoop_x, initial_hoop_y, start_time)
    )
    angle_degrees = 45 + angle_output * 35
    speed = 800 + speed_output * 500
    angle = math.radians(angle_degrees)

    ball = Ball()
    ball._set_hoop_position(start_time)
    ball.vx = math.cos(angle) * speed
    ball.vy = -math.sin(angle) * speed
    ball.active = True
    trajectory = [(ball.x, ball.y)]
    hoop_trajectory = [(ball.hoop_x, ball.hoop_y)]

    closest_distance = float("inf")
    for step in range(MAX_STEPS):
        ball.update(DT, start_time + (step + 1) * DT)
        if step % 3 == 0 or ball.scored:
            trajectory.append((ball.x, ball.y))
            hoop_trajectory.append((ball.hoop_x, ball.hoop_y))
        closest_distance = min(
            closest_distance,
            math.hypot(ball.x - ball.hoop_x, ball.y - ball.hoop_y),
        )
        if ball.scored:
            return (100 + ball.score_value, ball.score_value, angle_degrees, speed,
                    trajectory, hoop_trajectory)
        if ball.x > cfg.SCREEN_WIDTH + cfg.BALL_RADIUS or (
            ball.y > cfg.FLOOR_Y + cfg.BALL_RADIUS and ball.vy > 0
        ):
            break

    # Recompensa gradual: aproximações ao aro já ajudam a seleção a evoluir.
    fitness = 20 / (1 + closest_distance / 100)
    return fitness, 0, angle_degrees, speed, trajectory, hoop_trajectory


def evaluate(brain: dict[str, list], start_times: list[float]) -> tuple:
    outcomes = [evaluate_one(brain, start_time) for start_time in start_times]
    average_fitness = sum(outcome[0] for outcome in outcomes) / len(outcomes)
    total_reward = sum(outcome[1] for outcome in outcomes)
    basket_count = sum(outcome[1] > 0 for outcome in outcomes)
    reward_counts = tuple(sum(outcome[1] == value for outcome in outcomes) for value in (1, 2, 3))
    representative = max(outcomes, key=lambda outcome: (outcome[1], outcome[0]))
    return (
        average_fitness,
        total_reward,
        representative[2],
        representative[3],
        representative[4],
        representative[5],
        basket_count,
        reward_counts,
        representative[1],
    )


def mutate(brain: dict[str, list], rng: random.Random, rate: float = 0.12) -> None:
    for matrix in (brain["w1"], brain["w2"]):
        for row in matrix:
            for index in range(len(row)):
                if rng.random() < rate:
                    row[index] += rng.gauss(0, 0.25)
    for vector in (brain["b1"], brain["b2"]):
        for index in range(len(vector)):
            if rng.random() < rate:
                vector[index] += rng.gauss(0, 0.25)


def crossover(first: dict[str, list], second: dict[str, list], rng: random.Random) -> dict[str, list]:
    child = new_brain(rng)
    for key in ("w1", "w2"):
        for row_index, row in enumerate(child[key]):
            for col_index in range(len(row)):
                parent = first if rng.random() < 0.5 else second
                row[col_index] = parent[key][row_index][col_index]
    for key in ("b1", "b2"):
        for index in range(len(child[key])):
            parent = first if rng.random() < 0.5 else second
            child[key][index] = parent[key][index]
    return child


def tournament(ranked: list[tuple], rng: random.Random):
    candidates = rng.sample(ranked[: max(2, len(ranked) // 2)], k=3)
    return max(candidates, key=lambda entry: entry[0])[1]


def train(generations: int, population_size: int, output_dir: Path, seed: int | None,
          visualize: bool = True, generation_delay_ms: int = 500) -> None:
    rng = random.Random(seed)
    population = [new_brain(rng) for _ in range(population_size)]
    output_dir.mkdir(parents=True, exist_ok=True)
    history_path = output_dir / "training_history.csv"
    best_path = output_dir / "best_brain.json"
    global_best_key = (-float("inf"), -1, -1)
    global_best_brain = None
    global_best_generation = 0
    elite_count = max(2, population_size // 20)
    view = TrainingView() if visualize else None

    with history_path.open("w", newline="", encoding="utf-8") as history_file:
        writer = csv.writer(history_file)
        writer.writerow((
            "generation", "best_fitness", "average_fitness", "baskets",
            "attempts", "best_total_reward",
        ))

        for generation in range(1, generations + 1):
            ranked = []
            baskets = 0
            start_times = [
                index * cfg.HOOP_MOTION_PERIOD / EVALUATION_PHASES
                for index in range(EVALUATION_PHASES)
            ]
            for brain in population:
                (fitness, total_reward, angle, speed, trajectory, hoop_trajectory,
                 basket_count, reward_counts, representative_reward) = evaluate(brain, start_times)
                baskets += basket_count
                ranked.append((
                    fitness, brain, total_reward, angle, speed, trajectory,
                    hoop_trajectory, basket_count, reward_counts, representative_reward,
                ))
            ranked.sort(key=lambda entry: (entry[0], entry[7], entry[2]), reverse=True)

            best = ranked[0]
            average = sum(entry[0] for entry in ranked) / population_size
            attempt_count = population_size * EVALUATION_PHASES
            writer.writerow((
                generation, f"{best[0]:.4f}", f"{average:.4f}", baskets,
                attempt_count, best[2],
            ))
            history_file.flush()
            best_key = (best[0], best[7], best[2])
            if best_key > global_best_key:
                global_best_key = best_key
                global_best_brain = best[1]
                global_best_generation = generation
                best_path.write_text(
                    json.dumps(
                        {
                            "architecture": [INPUTS, HIDDEN, OUTPUTS],
                            "brain": best[1],
                            "fitness": best[0],
                            "reward": best[2],
                            "baskets": best[7],
                            "evaluation_phases": EVALUATION_PHASES,
                            "angle_degrees": best[3],
                            "speed": best[4],
                            "generation": generation,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )

            print(
                f"Geracao {generation:>4}/{generations} | "
                f"melhor fitness: {best[0]:7.2f} | cestas: {baskets:>3}/{attempt_count} | "
                f"recompensa melhor: {best[2]:>2} | angulo: {best[3]:.1f} graus | "
                f"velocidade: {best[4]:.0f}"
            )

            if view and not view.update(
                generation, generations, ranked, average, population_size,
                generation_delay_ms, EVALUATION_PHASES,
            ):
                break
            if view and view.consume_match_request():
                view.close()
                from .match import MatchSession

                MatchSession(
                    global_best_brain,
                    generation,
                    global_best_generation,
                ).run()
                view = TrainingView()

            next_population = [entry[1] for entry in ranked[:elite_count]]
            while len(next_population) < population_size:
                child = crossover(tournament(ranked, rng), tournament(ranked, rng), rng)
                mutate(child, rng)
                next_population.append(child)
            population = next_population

    if view:
        view.close()

    print(f"Treinamento encerrado. Melhor rede salva em: {best_path}")
    print(f"Historico salvo em: {history_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Treina a IA do NeuroBasket por evolucao genetica.")
    parser.add_argument("--generations", type=int, default=100)
    parser.add_argument("--population", type=int, default=50)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=None, help="Semente opcional para repetir o treino.")
    parser.add_argument(
        "--generation-delay", type=int, default=500,
        help="Tempo em milissegundos para visualizar cada geracao (padrao: 500).",
    )
    parser.add_argument("--headless", action="store_true", help="Treina sem abrir o painel visual.")
    args = parser.parse_args()
    if args.generations < 1 or args.population < 4 or args.generation_delay < 0:
        parser.error("use pelo menos 1 geracao, populacao de 4 e atraso nao negativo")
    output_dir = args.output or Path("training_runs") / datetime.now().strftime("run_%Y%m%d_%H%M%S")
    train(
        args.generations,
        args.population,
        output_dir,
        args.seed,
        visualize=not args.headless,
        generation_delay_ms=args.generation_delay,
    )


if __name__ == "__main__":
    main()
