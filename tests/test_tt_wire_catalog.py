import unittest
from tt_wire_catalog import build


def track(name, revision="a"):
    return dict(id="ct."+name, revision=revision*64, directory=name, name=name)


class WireCatalogTests(unittest.TestCase):
    def test_ids_survive_cup_reordering_removal_and_new_tracks(self):
        first = build(dict(tracks=[track("z"), track("b")]))
        changed = build(dict(tracks=[track("a"), track("z")]), first)
        self.assertEqual(changed["tracks"][:2], first["tracks"])
        self.assertEqual(changed["tracks"][2]["base_slot"], 136)

    def test_revision_change_gets_new_boards(self):
        first = build(dict(tracks=[track("a")]))
        changed = build(dict(tracks=[track("a", "b")]), first)
        self.assertEqual([r["base_slot"] for r in changed["tracks"]], [128, 132])

    def test_exhaustion_and_duplicate_are_errors(self):
        with self.assertRaises(ValueError):
            build(dict(tracks=[track("a"), track("a")]))
        with self.assertRaises(ValueError):
            build(dict(tracks=[track(str(n)) for n in range(225)]))


if __name__ == "__main__":
    unittest.main()
