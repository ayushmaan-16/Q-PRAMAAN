"""One-time Toeplitz universal-hash MAC, modeled with pre-shared secret keys.

This demonstrates information-theoretic authentication algebra, not physical key
distribution. OS randomness is used here; ideal uniform secret keys are an assumption.
"""
import json
import secrets
import threading


def canonical(message):
    return json.dumps(message, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def toeplitz_tag(payload, diagonal, pad, bits=128):
    # Prefix length to make the encoded message space unambiguous.
    raw = len(payload).to_bytes(8, "big") + payload
    m = len(raw) * 8
    value, mask = int.from_bytes(raw, "big"), (1 << m) - 1
    tag = 0
    for row in range(bits):
        tag |= ((value & ((diagonal >> row) & mask)).bit_count() & 1) << row
    return tag ^ pad


class OneTimeAuthenticator:
    def __init__(self):
        self._keys = {}
        self._lock = threading.Lock()
        self.key_bits_consumed = 0
        self.messages_issued = 0
        self.attempts = 0

    def issue(self, message):
        payload = canonical(message)
        m = (len(payload) + 8) * 8
        diagonal, pad = secrets.randbits(m + 127), secrets.randbits(128)
        key_id = secrets.token_hex(16)
        with self._lock:
            self._keys[key_id] = (diagonal, pad, len(payload))
            self.key_bits_consumed += m + 255
            self.messages_issued += 1
        return {"key_id": key_id, "tag": f"{toeplitz_tag(payload, diagonal, pad):032x}"}

    def verify(self, message, envelope):
        with self._lock:
            key = self._keys.pop(envelope.get("key_id", ""), None)
            self.attempts += 1
        if key is None:
            return False
        diagonal, pad, size = key
        payload = canonical(message)
        if len(payload) != size:
            return False
        expected = f"{toeplitz_tag(payload, diagonal, pad):032x}"
        return secrets.compare_digest(expected, str(envelope.get("tag", "")))

    def summary(self):
        return {"construction": "Fresh Toeplitz universal hash + fresh 128-bit one-time mask",
                "messages": self.messages_issued, "attempts": self.attempts,
                "key_bits_consumed": self.key_bits_consumed,
                "per_attempt_bound": 2. ** -128,
                "assumption": "Uniform pre-shared secret keys and uncompromised endpoints; OS RNG is a simulation stand-in."}
