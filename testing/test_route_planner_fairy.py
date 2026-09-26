import unittest

import route_planner as rp


def _zero_legs(nodes):
    table = {a: {b: 0.0 for b in nodes} for a in nodes}
    return {"base": table, "raft": table, "ladder": table}


class RoutePlannerFairyTests(unittest.TestCase):
    def test_fairy_errand_has_its_own_cost_and_sets_heal_flag(self):
        seq = list(rp.CURRENT)
        seq.insert(1, "fairy_2C")  # after L3, while bombs are available
        nodes = {"start", "h_2C", *seq, *rp.CURRENT}
        L = _zero_legs(nodes)

        base = rp.evaluate(rp.CURRENT, L)
        with_fairy, lines = rp.evaluate(seq, L, explain=True)

        self.assertEqual(with_fairy - base, rp.FAIRY_STOP)
        fairy_line = next(line for line in lines if "fairy_2C" in line)
        self.assertIn("heal yes", fairy_line)


if __name__ == "__main__":
    unittest.main()
