# This program checks if a number is prime.
def is_prime(num):
    if num <= 1:
        return False
    for i in range(2, int(num**0.5) + 1):
        if num % i == 0:
            return False
    return True

# Get input from the user
import sys

if len(sys.argv) != 2:
    print("Usage: python prime_solver.py <number>")
    sys.exit(1)
    num_str = sys.argv[1]
        print(f"{num} is not a prime number.")
    print("Invalid input. Please enter a valid integer.")