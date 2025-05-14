def get_response(question, reverse=False):
    prompt = f"{question}\nOn a scale from 0 (strongly oppose) to 100 (strongly support): "
    while True:
        try:
            val = int(input(prompt))
            if 0 <= val <= 100:
                return 100 - val if reverse else val
        except ValueError:
            pass
        print(" Please enter a whole number between 0 and 100.\n")

def main():
    print("\n=== 12-Item Social & Economic Conservatism Scale ===\n")
    items = [
        ("Do you support abortion rights?", True),
        ("Do you support limited government intervention?", False),
        ("Do you support strong military spending and national security?", False),
        ("Do you support religion having a role in public life?", False),
        ("Do you support welfare benefits for the needy?", True),
        ("Do you support individuals' right to own guns?", False),
        ("Do you support defining marriage as between a man and a woman?", False),
        ("Do you support maintaining traditional values in society?", False),
        ("Do you support fiscal responsibility and balanced budgets?", False),
        ("Do you support free enterprise and business?", False),
        ("Do you support the importance of the family unit?", False),
        ("Do you feel strong patriotism toward your country?", False),
    ]

    scores = [get_response(q, rev) for q, rev in items]

    mean_raw = sum(scores) / len(scores)
    conservatism_score = mean_raw / 10

    print(f"\nRaw mean (0–100): {mean_raw:.1f}")
    print(f"Conservatism score (0–10): {conservatism_score:.2f}")

    if conservatism_score > 5:
        print("Classification: Right / Conservative")
    elif conservatism_score < 5:
        print("Classification: Left / Liberal")
    else:
        print("Classification: Neutral / Mixed")

if __name__ == "__main__":
    main()
