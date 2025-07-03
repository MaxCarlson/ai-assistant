```python
def is_prime(number):
    """Checks if a number is prime."""
    if number <= 1:
        return False
    for i in range(2, int(number**0.5) + 1):
        if number % i == 0:
            return False
    return True

# Example usage:
print(is_prime(2))  # Output: True
print(is_prime(3))  # Output: True
print(is_prime(4))  # Output: False
print(is_prime(5))  # Output: True
print(is_prime(10)) # Output: False
```