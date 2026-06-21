import random


def main():
    print("Welcome to Guess the Number!")
    print("I'm thinking of a number between 1 and 100.")

    secret_number = random.randint(1, 100)
    attempts = 0

    while True:
        guess_input = input("Enter your guess: ").strip()

        if not guess_input.isdigit():
            print("Please enter a valid whole number.")
            continue

        guess = int(guess_input)
        attempts += 1

        if guess < secret_number:
            print("Too low!")
        elif guess > secret_number:
            print("Too high!")
        else:
            print(f"Correct! You guessed the number in {attempts} attempts.")
            break


if __name__ == "__main__":
    main()
