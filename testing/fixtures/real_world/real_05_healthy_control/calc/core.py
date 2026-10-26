from calc.helpers import square, cube

def evaluate_powers(val: float) -> dict:
    return {
        "square": square(val),
        "cube": cube(val)
    }
