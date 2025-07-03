from prime_solver import is_prime, find_primes
import pytest

@pytest.mark.parametrize("num, expected", [
    (2, True),
    (3, True),
    (4, False),
    (5, True),
    (7, True),
    (9, False),
    (11, True),
    (13, True),
    (17, True),
    (19, True),
    (23, True),
    (29, True),
    (1, False),
    (-5, False),
    (0, False),
])
def test_is_prime(num, expected):
    assert is_prime(num) == expected

@pytest.mark.parametrize("limit, expected", [
    (10, [2, 3, 5, 7]),
    (20, [2, 3, 5, 7, 11, 13, 17, 19]),
    (30, [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]),
    (1, []),
    (0, []),
    (-5, [])
])
def test_find_primes(limit, expected):
    assert find_primes(limit) == expected