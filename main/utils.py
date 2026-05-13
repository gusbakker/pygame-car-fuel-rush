Color = tuple[int, int, int]


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def lerp(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount


def mix_color(first: Color, second: Color, amount: float) -> Color:
    return (
        int(lerp(first[0], second[0], amount)),
        int(lerp(first[1], second[1], amount)),
        int(lerp(first[2], second[2], amount)),
    )
