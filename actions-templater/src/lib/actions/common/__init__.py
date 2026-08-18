def ternary(condition, true_val, false_val, quote=True) -> str:
    eval = f"{condition} && {true_val} || {false_val}"
    if quote:
        return "${{ " + eval + " }}"
    return eval
