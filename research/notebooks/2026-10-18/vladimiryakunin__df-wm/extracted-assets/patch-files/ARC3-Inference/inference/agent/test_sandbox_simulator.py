"""Integration tests for world model simulator inside python_tool_sandbox."""
import unittest

from inference.agent.python_tool_sandbox import run_sandboxed_python


class TestSandboxSimulator(unittest.TestCase):
    def setUp(self):
        # 10x10 board with initial zeros
        self.initial_grid = [[0] * 10 for _ in range(10)]
        self.initial_state = {
            "current_frame": {
                "ascii": "W" * 10 + ("\n" + "W" * 10) * 9,
                "step": 2,
                "level": 1,
                "shape": [10, 10],
                "grid": self.initial_grid,
            },
            "history": [
                {
                    "action": "RIGHT",
                    "frame": {
                        "ascii": "W" * 10 + ("\n" + "W" * 10) * 9,
                        "step": 1,
                        "level": 1,
                        "shape": [10, 10],
                        "grid": self.initial_grid,
                    },
                    "result": {"executed": True, "gameplay_changed": True},
                },
                {
                    "action": "RIGHT",
                    "frame": {
                        "ascii": "W" * 10 + ("\n" + "W" * 10) * 9,
                        "step": 2,
                        "level": 1,
                        "shape": [10, 10],
                        "grid": self.initial_grid,
                    },
                    "result": {"executed": True, "gameplay_changed": True},
                },
            ],
            "valid_actions": ["UP", "DOWN", "LEFT", "RIGHT", "SPACE"],
        }

    def test_check_sim_and_retention(self):
        code = """
def simulate(frame, action):
    # Perfect no-op simulator for this empty board
    return frame.copy()

res = check_sim()
result = res
"""
        executed_actions = []

        def mock_action_handler(actions, stale_after=None):
            executed_actions.append(actions)
            return {"action_result": {"executed": True}}

        res = run_sandboxed_python(
            code=code,
            timeout_seconds=5,
            initial_state=self.initial_state,
            action_handler=mock_action_handler,
            kept_functions=[],
        )

        self.assertFalse(res.get("error"), f"Unexpected error: {res.get('error')}")
        sim_res = res.get("result")
        self.assertIsInstance(sim_res, dict)
        self.assertEqual(sim_res.get("checked"), 1)
        self.assertEqual(sim_res.get("matches"), 1)
        self.assertEqual(sim_res.get("accuracy"), 1.0)

        # Verify retention detected simulate function
        kept = res.get("keepable_functions") or []
        kept_names = [f["name"] for f in kept]
        self.assertIn("simulate", kept_names)

    def test_search_in_sandbox(self):
        code = """
def simulate(frame, action):
    f = frame.copy()
    if action == 'RIGHT':
        f.grid[5][5] = 'R'
    return f

def is_goal(frame):
    return frame.get(5, 5) == 'R'

result = search(current_frame, simulate, is_goal, valid_actions=['UP', 'RIGHT'], border=2)
"""
        res = run_sandboxed_python(
            code=code,
            timeout_seconds=5,
            initial_state=self.initial_state,
            action_handler=lambda actions, stale_after=None: {},
            kept_functions=[],
        )
        self.assertFalse(res.get("error"), f"Unexpected error: {res.get('error')}")
        search_res = res.get("result")
        self.assertTrue(search_res.get("found"))
        self.assertEqual(search_res.get("actions"), ["RIGHT"])

    def test_act_checked_stops_on_divergence(self):
        # Simulator predicts cell (5,5) becomes 'R' (Red)
        # But real environment sets it to 5 ('B' = Black)
        code = """
def simulate(frame, action):
    f = frame.copy()
    f.grid[5][5] = 'R'
    return f

# Try to run 3 actions with act_checked
act_checked(['RIGHT', 'RIGHT', 'RIGHT'], border=2)
"""
        executed_actions = []

        def mock_action_handler(actions, stale_after=None):
            executed_actions.extend(actions)
            # Board actually changes cell (5, 5) to 5 ('B')
            new_grid = [list(r) for r in self.initial_grid]
            new_grid[5][5] = 5
            return {
                "action_result": {
                    "executed": True,
                    "gameplay_changed": True,
                    "action_name": "RIGHT",
                },
                "state": {
                    "current_frame": {
                        "ascii": "W" * 10 + ("\n" + "W" * 10) * 9,
                        "step": len(executed_actions),
                        "level": 1,
                        "shape": [10, 10],
                        "grid": new_grid,
                    },
                    "history": [],
                    "valid_actions": ["RIGHT"],
                },
            }

        res = run_sandboxed_python(
            code=code,
            timeout_seconds=5,
            initial_state=self.initial_state,
            action_handler=mock_action_handler,
            kept_functions=[],
        )

        # Mismatch error should be raised and caught
        err = res.get("error", "")
        self.assertTrue(err, "Expected error but none occurred.")
        self.assertIn("PredictionMismatchError", err)
        self.assertIn("SIMULATOR DIVERGENCE", err)
        # Exactly 1 action executed, remaining 2 actions were stopped!
        self.assertEqual(len(executed_actions), 1)


if __name__ == "__main__":
    unittest.main()
