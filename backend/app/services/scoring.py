"""Lead score from the pack's scoring table: points per collected field plus a bonus for finishing."""


def score(pack: dict, collected: dict, completed: bool) -> int:
    rules = pack.get("scoring", {})
    total = sum(points for name, points in rules.get("fields", {}).items() if collected.get(name))
    if completed:
        total += rules.get("complete", 0)
    return max(0, min(100, int(total)))


def label(value: int) -> str:
    return "hot" if value >= 70 else "warm" if value >= 40 else "cold"
