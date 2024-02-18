import secrets


def generate_otp():
    """
    Generate a random six-digit OTP (One-Time Password).

    This function generates a random six-digit OTP using the `secrets.SystemRandom` module.

    Returns:
        int: A random six-digit OTP.
    """
    sys_random_obj = secrets.SystemRandom()
    return sys_random_obj.randrange(100000, 999999)
