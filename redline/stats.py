import math

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float] | None:
    """Wilson score interval for k successes out of n."""
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def rate(k: int, n: int) -> dict:
    interval = wilson(k, n)
    return {
        "k": k,
        "n": n,
        "value": k / n if n else None,
        "ci95": list(interval) if interval else None,
    }


def format_rate(r: dict) -> str:
    if not r["n"]:
        return f"{r['k']}/{r['n']} (n/a)"
    lo, hi = r["ci95"]
    return f"{r['k']}/{r['n']} = {r['value']:.2f} [{lo:.2f}, {hi:.2f}]"
