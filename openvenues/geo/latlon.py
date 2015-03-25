def degrees_to_decimal(degrees, minutes=0, seconds=0):
    return (float(degrees) + float(minutes) / 60 + float(seconds) / 3600)


def direction_sign(direction=None):
    sign = -1 if direction and direction.lower() in ('s', 'w') else 1
    return sign
