import difflib
import json
import os
import random
import statistics
import sys
import time


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
CHARS_PER_WORD = 5

SENTENCE_POOL = [
    "The advancement of artificial intelligence has revolutionized how we interact with technology. From automated natural language processing to complex data analytics, machine learning algorithms continue to shape the modern digital landscape in unprecedented ways.",
    
    "Python is widely regarded as one of the most accessible yet powerful programming languages in the world. Its clean syntax and extensive ecosystem of libraries make it an ideal choice for web development, data science, automation, and software engineering.",
    
    "Consistency and deliberate practice are the true cornerstones of mastery. Whether you are learning to play a musical instrument, writing code, or improving your typing speed, daily dedication compounds over time to produce remarkable results.",
    
    "Clean code always looks like it was written by someone who cares. Writing maintainable software requires attention to detail, proper documentation, and a willingness to refactor your solutions as requirements evolve over time.",
    
    "Open source software relies on global collaboration, transparent code review, and shared knowledge. Developers from diverse backgrounds contribute to projects that power everything from personal computing devices to global enterprise infrastructure.",
    
    "Deep in the heart of the ancient forest, sunlight filters through the dense canopy, casting intricate patterns of shadow and light on the mossy floor. The quiet rustle of leaves in the gentle breeze provides a sense of profound peace.",
    
    "Time management is not just about fitting as many tasks as possible into a single day; it is about prioritizing meaningful work, establishing clear boundaries, and maintaining sharp focus amidst endless modern distractions."
]


def calculate_metrics(start_time, end_time, target_sentence, user_input):
    """Calculate elapsed time, typing speed, and character accuracy."""
    elapsed_seconds = max(0, end_time - start_time)
    elapsed_minutes = max(elapsed_seconds / 60, 0.001)
    wpm = (len(user_input) / CHARS_PER_WORD) / elapsed_minutes

    mistakes, weak_keys = analyze_mistakes(target_sentence, user_input)
    compared_length = max(len(target_sentence), len(user_input))
    accuracy = (
        (compared_length - mistakes) / compared_length * 100
        if compared_length
        else 0
    )
    net_wpm = max(0, len(user_input) - mistakes) / CHARS_PER_WORD / elapsed_minutes

    return {
        "elapsed_seconds": round(elapsed_seconds, 2),
        "wpm": round(wpm, 2),
        "net_wpm": round(net_wpm, 2),
        "accuracy": round(max(0, min(100, accuracy)), 2),
        "mistakes": mistakes,
        "error_rate": round(mistakes / compared_length * 100, 2) if compared_length else 0,
        "weak_keys": weak_keys,
    }


def analyze_mistakes(target_text, typed_text):
    """Count typing errors and attribute them to the intended keys."""
    weak_keys = {}
    matcher = difflib.SequenceMatcher(None, target_text, typed_text, autojunk=False)

    for operation, target_start, target_end, typed_start, typed_end in matcher.get_opcodes():
        if operation == "equal":
            continue

        expected = target_text[target_start:target_end]
        for character in expected:
            if character.isalpha():
                key = character.lower()
                weak_keys[key] = weak_keys.get(key, 0) + 1

    edit_row = list(range(len(typed_text) + 1))
    for target_char in target_text:
        next_row = [edit_row[0] + 1]
        for index, typed_char in enumerate(typed_text, start=1):
            next_row.append(
                min(
                    next_row[-1] + 1,
                    edit_row[index] + 1,
                    edit_row[index - 1] + (target_char != typed_char),
                )
            )
        edit_row = next_row

    sorted_weak_keys = dict(sorted(weak_keys.items(), key=lambda item: (-item[1], item[0])))
    return edit_row[-1], sorted_weak_keys


def read_timed_input(duration_seconds):
    """Read and echo characters until the sprint timer expires."""
    if not sys.stdin.isatty():
        raise RuntimeError("Timed sprints require an interactive terminal.")

    typed_characters = []
    start_time = time.perf_counter()
    deadline = start_time + duration_seconds

    if os.name == "nt":
        import msvcrt

        while time.perf_counter() < deadline:
            if not msvcrt.kbhit():
                time.sleep(min(0.01, max(0, deadline - time.perf_counter())))
                continue
            character = msvcrt.getwch()
            if character in ("\x00", "\xe0"):
                msvcrt.getwch()
            elif character in ("\b", "\x7f"):
                if typed_characters:
                    typed_characters.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif character in ("\r", "\n"):
                continue
            elif character.isprintable():
                typed_characters.append(character)
                sys.stdout.write(character)
                sys.stdout.flush()
    else:
        import select
        import termios
        import tty

        terminal_fd = sys.stdin.fileno()
        previous_settings = termios.tcgetattr(terminal_fd)
        try:
            tty.setcbreak(terminal_fd)
            while time.perf_counter() < deadline:
                remaining = deadline - time.perf_counter()
                ready, _, _ = select.select([sys.stdin], [], [], remaining)
                if not ready:
                    break
                character = os.read(terminal_fd, 1).decode(errors="replace")
                if character in ("\x7f", "\b"):
                    if typed_characters:
                        typed_characters.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                elif character in ("\r", "\n"):
                    continue
                elif character.isprintable():
                    typed_characters.append(character)
                    sys.stdout.write(character)
                    sys.stdout.flush()
        finally:
            termios.tcsetattr(terminal_fd, termios.TCSADRAIN, previous_settings)

    elapsed_seconds = time.perf_counter() - start_time
    print()
    return "".join(typed_characters), elapsed_seconds


def display_results(metrics, is_personal_best=False):
    print("\n" + "=" * 40)
    print("              TEST RESULTS")
    print("=" * 40)
    print(f"Time Taken: {metrics['elapsed_seconds']} seconds")
    print(f"Raw Speed:  {metrics['wpm']} WPM")
    print(f"Net Speed (after mistakes): {metrics['net_wpm']} WPM")
    print(f"Accuracy:   {metrics['accuracy']}%")
    print(f"Mistakes:   {metrics.get('mistakes', 0)} ({metrics.get('error_rate', 0)}% error rate)")
    weak_keys = metrics.get("weak_keys", {})
    if weak_keys:
        print("Weak keys:  " + ", ".join(f"{key} ({count})" for key, count in list(weak_keys.items())[:5]))
    if is_personal_best:
        print("New personal best!")
    print("=" * 40)


def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as history_file:
            history = json.load(history_file)
        return history if isinstance(history, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def save_result_to_history(result_data):
    history = load_history()
    history.append(result_data)
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as history_file:
            json.dump(history, history_file, indent=4)
    except OSError:
        print("Error: Could not save score to history file.")
        return False
    return True


def display_history():
    history = load_history()
    if not history:
        print("\nNo history found yet. Play a game to record stats!")
        return

    print("\n" + "=" * 50)
    print("                 PAST SCORES")
    print("=" * 50)
    speeds = [entry.get("wpm", 0) for entry in history]
    accuracies = [entry.get("accuracy", 0) for entry in history]
    print(f"Tests: {len(history)}  |  Best: {max(speeds):.2f} WPM  |  Average: {sum(speeds) / len(speeds):.2f} WPM")
    print(f"Average accuracy: {sum(accuracies) / len(accuracies):.2f}%")
    print("-" * 65)
    print(f"{'Test #':<8} {'WPM':<9} {'Net WPM':<10} {'Accuracy':<12} {'Time (s)':<10}")
    print("-" * 65)
    for index, entry in enumerate(history[-10:], start=1):
        print(
            f"{index:<8} {entry.get('wpm', 0):<9} "
            f"{entry.get('net_wpm', entry.get('wpm', 0)):<10} "
            f"{entry.get('accuracy', 0):<12}% "
            f"{entry.get('elapsed_seconds', 0):<10}"
        )
    print("=" * 65)


def display_dashboard():
    history = load_history()
    if not history:
        print("\nNo results yet. Complete a test to populate your dashboard.")
        return

    speeds = [entry.get("wpm", 0) for entry in history]
    net_speeds = [entry.get("net_wpm", entry.get("wpm", 0)) for entry in history]
    accuracies = [entry.get("accuracy", 0) for entry in history]
    elapsed = sum(entry.get("elapsed_seconds", 0) for entry in history)
    recent_speeds = speeds[-10:]
    trend = "improving" if len(recent_speeds) > 1 and recent_speeds[-1] > recent_speeds[0] else "declining"
    if len(recent_speeds) < 2 or recent_speeds[-1] == recent_speeds[0]:
        trend = "steady"

    print("\n" + "=" * 58)
    print("                 ADVANCED STATISTICS")
    print("=" * 58)
    print(f"Tests completed: {len(history)}  |  Practice time: {elapsed / 60:.1f} minutes")
    print(f"Best speed: {max(speeds):.2f} WPM  |  Average speed: {statistics.mean(speeds):.2f} WPM")
    print(f"Average net speed: {statistics.mean(net_speeds):.2f} WPM  |  Average accuracy: {statistics.mean(accuracies):.2f}%")
    print(f"Speed consistency (standard deviation): {statistics.pstdev(speeds):.2f} WPM")
    print(f"Recent trend (last {len(recent_speeds)} tests): {trend}")
    print("Recent speeds: " + " -> ".join(f"{speed:.1f}" for speed in recent_speeds))

    sprint_counts = {}
    for entry in history:
        mode = entry.get("mode", "standard")
        sprint_counts[mode] = sprint_counts.get(mode, 0) + 1
    print("Modes: " + "  |  ".join(f"{mode}: {count}" for mode, count in sorted(sprint_counts.items())))
    print("=" * 58)


def display_mistake_analysis():
    history = load_history()
    if not history:
        print("\nNo results yet. Complete a test to see your weak keys and mistakes.")
        return

    weak_keys = {}
    total_mistakes = 0
    analyzed_tests = 0
    for entry in history:
        total_mistakes += entry.get("mistakes", 0)
        for key, count in entry.get("weak_keys", {}).items():
            weak_keys[key] = weak_keys.get(key, 0) + count
        if "weak_keys" in entry:
            analyzed_tests += 1

    print("\n" + "=" * 50)
    print("             WEAK KEYS / MISTAKE ANALYSIS")
    print("=" * 50)
    print(f"Analyzed tests: {analyzed_tests} of {len(history)}  |  Total mistakes: {total_mistakes}")
    if not weak_keys:
        print("No per-key data yet. New test results will build this analysis.")
    else:
        print("Most-missed intended keys:")
        for key, count in sorted(weak_keys.items(), key=lambda item: (-item[1], item[0]))[:10]:
            print(f"  {key}: {count}")
    print("=" * 50)


def build_sprint_passage():
    sentences = SENTENCE_POOL[:]
    random.shuffle(sentences)
    passage = " ".join(sentences)
    while len(passage) < 1200:
        passage += " " + " ".join(random.sample(SENTENCE_POOL, len(SENTENCE_POOL)))
    return passage


def play_game():
    print("\n" + "=" * 40)
    print("       STARTING TYPING TEST")
    print("=" * 40)

    target_sentence = random.choice(SENTENCE_POOL)
    print("\nTarget Sentence:")
    print("-" * 40)
    print(f'"{target_sentence}"')
    print("-" * 40)

    input("\nPress Enter when you are ready to start typing...")
    print("Type the sentence above and press Enter:")
    start_time = time.perf_counter()
    user_input = input(">> ")
    end_time = time.perf_counter()

    metrics = calculate_metrics(start_time, end_time, target_sentence, user_input)
    metrics["mode"] = "standard"
    previous_best = max(
        (entry.get("wpm", 0) for entry in load_history() if entry.get("mode", "standard") == "standard"),
        default=0,
    )
    saved = save_result_to_history(metrics)
    display_results(metrics, saved and metrics["wpm"] > previous_best)


def play_sprint(duration_seconds):
    print("\n" + "=" * 40)
    print(f"       {duration_seconds}-SECOND TYPING SPRINT")
    print("=" * 40)
    target_text = build_sprint_passage()
    print("\nType the passage below. The sprint ends when time runs out:")
    print("-" * 40)
    print(target_text)
    print("-" * 40)
    input("Press Enter when you are ready...")
    print(f"Go! Type for {duration_seconds} seconds:")
    typed_text, elapsed_seconds = read_timed_input(duration_seconds)

    metrics = calculate_metrics(0, elapsed_seconds, target_text[:len(typed_text)], typed_text)
    metrics["elapsed_seconds"] = round(elapsed_seconds, 2)
    metrics["mode"] = f"{duration_seconds}-second sprint"
    metrics["target_seconds"] = duration_seconds
    previous_best = max(
        (entry.get("wpm", 0) for entry in load_history() if entry.get("mode") == metrics["mode"]),
        default=0,
    )
    saved = save_result_to_history(metrics)
    display_results(metrics, saved and metrics["wpm"] > previous_best)


def choose_sprint():
    print("\n1. 30-second sprint")
    print("2. 60-second sprint")
    choice = input("Choose a sprint (1-2): ").strip()
    if choice == "1":
        play_sprint(30)
    elif choice == "2":
        play_sprint(60)
    else:
        print("Invalid choice. Choose 1 or 2.")


def main():
    while True:
        print("\n" + "=" * 40)
        print("       PYTHON TYPING SPEED TEST")
        print("=" * 40)
        print("1. Start Standard Test")
        print("2. Timed Sprint (30/60 seconds)")
        print("3. Advanced Statistics Dashboard")
        print("4. Weak Keys / Mistake Analysis")
        print("5. View History")
        print("6. Exit")
        
        choice = input("\nChoose an option (1-6): ").strip()
        
        if choice == "1":
            play_game()
        elif choice == "2":
            choose_sprint()
        elif choice == "3":
            display_dashboard()
        elif choice == "4":
            display_mistake_analysis()
        elif choice == "5":
            display_history()
        elif choice == "6":
            print("\nThank you for using Python Typing Speed Test. Goodbye!")
            break
        else:
            print("\nInvalid choice. Please enter a number from 1 to 6.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye!")