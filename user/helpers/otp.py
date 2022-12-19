import secrets


def generate_otp():
    sys_random_obj = secrets.SystemRandom()
    return sys_random_obj.randrange(100000, 999999)
