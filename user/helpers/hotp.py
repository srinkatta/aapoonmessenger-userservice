#!/usr/bin/env python
"""
OATH HOTP + TOTP Implementation in python.
Based on http://tools.ietf.org/html/rfc4226
         http://tools.ietf.org/html/rfc6238
Parameter and function names kept inline with the RFC
(e.g. HOTP, Truncate, K, C etc)
"""

import hmac
import hashlib
import struct
import time
import unittest


def HOTP(K, C, digits=6, digestmod=hashlib.sha1):
    """
    HOTP accepts key K and counter C
    optional digits parameter can control the response length
    returns the OATH integer code with {digits} length
    """
    C_bytes = struct.pack(b"!Q", C)
    K_bytes = bytes(K, encoding="utf-8")
    hmac_digest = hmac.new(key=K_bytes, msg=C_bytes, digestmod=digestmod).hexdigest()
    return Truncate(hmac_digest)[-digits:]


def TOTP(K, digits=6, window=30, clock=None, digestmod=hashlib.sha1):
    """
    TOTP is a time-based variant of HOTP.
    It accepts only key K, since the counter is derived from the current time
    optional digits parameter can control the response length
    optional window parameter controls the time window in seconds
    returns the OATH integer code with {digits} length
    """
    if clock is None:
        clock = time.time()
    C = int(clock / window)
    return HOTP(K, C, digits=digits, digestmod=digestmod)


def Truncate(hmac_digest):
    """
    Truncate represents the function that converts an HMAC
    value into an HOTP value as defined in Section 5.3.
    http://tools.ietf.org/html/rfc4226#section-5.3
    """
    offset = int(hmac_digest[-1], 16)
    binary = int(hmac_digest[(offset * 2) : ((offset * 2) + 8)], 16) & 0x7FFFFFFF
    return str(binary)
