from generator import (
    build_auto_generated_puzzle_v4,
    print_goal_board,
    print_puzzle_state,
)

from solver import solve_puzzle, solve_all_puzzles
from validator import explain_meld_assignment



# Parameters

NUM_COLOR_RUNS = 2
MAX_RUN_LENGTH = 4
HAND_SIZE = 3
INCLUDE_SPECIAL_RUN = True
REQUIRE_CHANGED_BOARD = True
PREFER_SPECIAL_TILES = True
RANDOM_SEED = 42



# Generate puzzle

goal_board, state, solvable, changed, hand_tile_uids = build_auto_generated_puzzle_v4(
    num_normal_runs=NUM_COLOR_RUNS,
    num_groups=2,
    num_joker_melds=1,
    num_prism_melds=1,
    num_rk_runs=1,
    normal_run_min_len=3,
    normal_run_max_len=MAX_RUN_LENGTH,
    hand_size=HAND_SIZE,
    require_changed_board=REQUIRE_CHANGED_BOARD,
    prefer_special_tiles=PREFER_SPECIAL_TILES,
    max_run_len=MAX_RUN_LENGTH,
    random_seed=RANDOM_SEED
)



# Print result

print("=== Generator Parameters ===")
print(f"num_color_runs: {NUM_COLOR_RUNS}")
print(f"max_run_length: {MAX_RUN_LENGTH}")
print(f"hand_size: {HAND_SIZE}")
print(f"include_special_run: {INCLUDE_SPECIAL_RUN}")
print(f"require_changed_board: {REQUIRE_CHANGED_BOARD}")
print(f"prefer_special_tiles: {PREFER_SPECIAL_TILES}")
print(f"max_run_len: {MAX_RUN_LENGTH}")
print(f"random_seed: {RANDOM_SEED}")
print()

print_goal_board(goal_board)
print()

print_puzzle_state(state)
print()

print("=== Generation Result ===")
print("Selected hand tile uids:", hand_tile_uids)
print("Generated puzzle solvable?", solvable)
print("Board structure changed?", changed)


# Solve generated puzzle using solve_puzzle

one_success, one_solution = solve_puzzle(
    state,
    max_run_len=MAX_RUN_LENGTH,
)

print()
print("=== Single Solution Result using solve_puzzle ===")
print("Solved?", one_success)

if one_success:
    for m_idx, meld in enumerate(one_solution, start=1):
        print(f"{m_idx}. {meld}")

        explanation = explain_meld_assignment(meld)
        if explanation is not None:
            print("   -> " + ", ".join(explanation))
        else:
            print("   -> [No explanation found]")
else:
    print("No solution found.")


# Solve generated puzzle and print solutions

MAX_SOLUTIONS = 50

solutions = solve_all_puzzles(
    state,
    max_run_len=MAX_RUN_LENGTH,
    max_solutions=MAX_SOLUTIONS,
)

print()
print("=== Solver Result ===")
print(f"Found {len(solutions)} unique solution(s).")
print(f"Max solutions searched: {MAX_SOLUTIONS}")
print()

for s_idx, solution in enumerate(solutions, start=1):
    print(f"--- Solution {s_idx} ---")

    for m_idx, meld in enumerate(solution, start=1):
        print(f"{m_idx}. {meld}")

        explanation = explain_meld_assignment(meld)
        if explanation is not None:
            print("   -> " + ", ".join(explanation))
        else:
            print("   -> [No explanation found]")

    print()