"""Unit tests for world_model utilities."""
import unittest

from inference.utils.world_model import (
    SimFrame,
    compare_grids,
    check_sim,
    search,
    extract_grid,
    _cell_equal,
)


class MockTransition:
    def __init__(self, action, before_frame, after_frame, result=None):
        self.action = action
        self.before_frame = before_frame
        self.after_frame = after_frame
        self.result = result or {}


class TestWorldModelUtils(unittest.TestCase):
    def test_sim_frame(self):
        grid = [[0, 1], [8, 9]]  # W, w, R, b
        frame = SimFrame(grid, step=1, level=2)
        self.assertEqual(frame.shape, (2, 2))
        self.assertEqual(frame.get(0, 0), 0)
        self.assertEqual(frame.get(1, 0), 8)
        self.assertIsNone(frame.get(2, 2))
        self.assertEqual(frame.ascii, "Ww\nRb")
        clone = frame.copy()
        self.assertEqual(clone.grid, frame.grid)
        self.assertEqual(clone.step, 1)

    def test_cell_equal(self):
        self.assertTrue(_cell_equal(0, "W"))
        self.assertTrue(_cell_equal("W", 0))
        self.assertTrue(_cell_equal(8, "R"))
        self.assertTrue(_cell_equal("R", 8))
        self.assertTrue(_cell_equal("W", "W"))
        self.assertTrue(_cell_equal(5, 5))
        self.assertFalse(_cell_equal(0, "R"))
        self.assertFalse(_cell_equal(1, "W"))

    def test_compare_grids_identical(self):
        # 10x10 grid with border=2
        grid1 = [[0] * 10 for _ in range(10)]
        grid2 = [["W"] * 10 for _ in range(10)]
        res = compare_grids(grid1, grid2, border=2)
        self.assertTrue(res["match"])
        self.assertEqual(res["diff_count"], 0)

    def test_compare_grids_border_ignored(self):
        # Difference only on the outer border (row 0)
        grid1 = [[0] * 10 for _ in range(10)]
        grid2 = [[0] * 10 for _ in range(10)]
        grid2[0][0] = 5  # Border cell
        res = compare_grids(grid1, grid2, border=2)
        self.assertTrue(res["match"])
        self.assertEqual(res["diff_count"], 0)

    def test_compare_grids_interior_diff(self):
        grid1 = [[0] * 10 for _ in range(10)]
        grid2 = [[0] * 10 for _ in range(10)]
        grid2[4][4] = 8  # Interior cell
        res = compare_grids(grid1, grid2, border=2)
        self.assertFalse(res["match"])
        self.assertEqual(res["diff_count"], 1)
        self.assertEqual(len(res["sample_diffs"]), 1)
        self.assertEqual(res["sample_diffs"][0]["pos"], [4, 4])

    def test_compare_grids_sparse_dict(self):
        grid1 = [[0] * 10 for _ in range(10)]
        # Predicted is sparse diff
        pred_diff = {(4, 4): 8}
        actual = [[0] * 10 for _ in range(10)]
        actual[4][4] = 8
        res = compare_grids(actual, pred_diff, border=2, base_frame=grid1)
        self.assertTrue(res["match"])
        self.assertEqual(res["diff_count"], 0)

    def test_check_sim(self):
        # Mock transitions
        f0 = SimFrame([[0] * 10 for _ in range(10)], step=0, level=1)
        f1 = SimFrame([[0] * 10 for _ in range(10)], step=1, level=1)
        f1.grid[4][4] = 8  # step 1: cell (4,4) changed to 8 on "RIGHT"
        f2 = SimFrame([[0] * 10 for _ in range(10)], step=2, level=1)
        f2.grid[4][4] = 8
        f2.grid[4][5] = 8  # step 2: cell (4,5) changed to 8 on "RIGHT"

        transitions = [
            MockTransition("RIGHT", f0, f1),
            MockTransition("RIGHT", f1, f2),
            MockTransition("RESET", f2, f0),  # should be skipped
        ]

        # Perfect simulator
        def perfect_sim(frame, action):
            new_f = frame.copy()
            if action == "RIGHT":
                if new_f.get(4, 4) == 0:
                    new_f.grid[4][4] = 8
                elif new_f.get(4, 5) == 0:
                    new_f.grid[4][5] = 8
            return new_f

        res = check_sim(perfect_sim, transitions, border=2)
        self.assertEqual(res["checked"], 2)
        self.assertEqual(res["matches"], 2)
        self.assertEqual(res["accuracy"], 1.0)
        self.assertEqual(len(res["mismatches"]), 0)

        # Flawed simulator
        def flawed_sim(frame, action):
            return frame.copy()  # changes nothing

        res_flawed = check_sim(flawed_sim, transitions, border=2)
        self.assertEqual(res_flawed["checked"], 2)
        self.assertEqual(res_flawed["matches"], 0)
        self.assertEqual(res_flawed["accuracy"], 0.0)
        self.assertEqual(len(res_flawed["mismatches"]), 2)

    def test_search_bfs(self):
        # 5x5 grid with player at (1,1), target at (1,3), wall at (1,2)
        # 0 = empty, 1 = player, 2 = target, 9 = wall
        grid = [
            [9, 9, 9, 9, 9],
            [9, 1, 9, 2, 9],
            [9, 0, 0, 0, 9],
            [9, 9, 9, 9, 9],
            [9, 9, 9, 9, 9],
        ]
        start = SimFrame(grid)

        def sim_move(frame, action):
            # Find player
            pr, pc = None, None
            for r in range(5):
                for c in range(5):
                    if frame.get(r, c) == 1:
                        pr, pc = r, c
                        break
            if pr is None:
                return frame
            nr, nc = pr, pc
            if action == "UP":
                nr -= 1
            elif action == "DOWN":
                nr += 1
            elif action == "LEFT":
                nc -= 1
            elif action == "RIGHT":
                nc += 1
            if frame.get(nr, nc) in (0, 2):
                new_f = frame.copy()
                new_f.grid[pr][pc] = 0
                new_f.grid[nr][nc] = 1
                return new_f
            return frame  # hit wall

        def is_goal(frame):
            return frame.get(1, 3) == 1

        res = search(start, sim_move, is_goal, valid_actions=["UP", "DOWN", "LEFT", "RIGHT"], border=0)
        self.assertTrue(res["found"])
        # Should go DOWN, RIGHT, RIGHT, UP
        self.assertEqual(res["actions"], ["DOWN", "RIGHT", "RIGHT", "UP"])
        self.assertEqual(res["depth"], 4)


if __name__ == "__main__":
    unittest.main()
