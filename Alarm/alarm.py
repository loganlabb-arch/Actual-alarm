import json
import sys
import time
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

try:
    import msvcrt  # Windows-only keyboard support
except ImportError:
    msvcrt = None

CONFIG_PATH = Path(__file__).with_name("alarm_config.json")

DEFAULT_CONFIG = {
    "enabled": False,
    "alarm_time": "07:00",
    "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "confirmation_phrase": "I am awake and ready.",
    "initial_wait_minutes": 5,
    "confirmation_timeout_seconds": 60,
}


def load_config():
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    merged = DEFAULT_CONFIG.copy()
    merged.update(data)
    return merged


def save_config(config):
    with CONFIG_PATH.open("w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)


def parse_time_string(value):
    value = value.strip()
    formats = ["%H:%M", "%I:%M %p", "%I:%M%p"]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    raise ValueError("Could not understand time. Try formats like 07:30 or 7:30 AM.")


def next_alarm_datetime(alarm_time):
    now = datetime.now()
    candidate = datetime.combine(now.date(), alarm_time)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def wait_until(target):
    while True:
        now = datetime.now()
        if now >= target:
            return
        remaining = (target - now).total_seconds()
        sleep_for = max(1, min(remaining, 60))
        time.sleep(sleep_for)


def countdown_timer(seconds, label):
    end_ts = time.time() + seconds
    print(label)
    while True:
        remaining = int(end_ts - time.time())
        if remaining <= 0:
            break
        mins, secs = divmod(remaining, 60)
        print(f"  Time remaining: {mins:02d}:{secs:02d}", end="\r", flush=True)
        time.sleep(1)
    print(" " * 40, end="\r", flush=True)


def timed_input(prompt, timeout_seconds):
    if timeout_seconds <= 0:
        return input(prompt)
    if msvcrt is None:
        print("Timed input not supported on this platform. Falling back to standard input.")
        return input(prompt)

    print(prompt, end="", flush=True)
    start = time.time()
    buffer = []
    while True:
        if msvcrt.kbhit():
            char = msvcrt.getwche()
            if char in ("\r", "\n"):
                print()
                return "".join(buffer)
            if char == "\b":
                if buffer:
                    buffer.pop()
                    print("\b \b", end="", flush=True)
            else:
                buffer.append(char)
        if (time.time() - start) >= timeout_seconds:
            print()
            return None
        time.sleep(0.05)


def wait_for_initial_input():
    input("Press Enter once you are up and ready (or type anything then Enter): ")


def perform_alarm_cycle(config):
    confirmation_phrase = config["confirmation_phrase"].strip()
    wait_minutes = max(0, int(config.get("initial_wait_minutes", 5)))
    confirm_timeout = max(1, int(config.get("confirmation_timeout_seconds", 60)))

    while True:
        print("\nOpening YouTube alarm...")
        webbrowser.open(config["youtube_url"], new=2)
        wait_for_initial_input()

        if wait_minutes:
            countdown_timer(wait_minutes * 60, f"Waiting {wait_minutes} minute(s) before confirmation...")

        print("\nType this phrase exactly within the time limit to silence the alarm:")
        print(f"  >>> {confirmation_phrase}")
        response = timed_input("Your input: ", confirm_timeout)

        if response is not None and response.strip() == confirmation_phrase:
            print("Alarm dismissed. Have a great day!\n")
            return

        print("Confirmation failed or timed out. Replaying alarm.\n")


def run_alarm_service(config):
    if not config["enabled"]:
        print("Alarm is currently disabled. Enable it from the menu before starting the service.")
        return

    alarm_time = parse_time_string(config["alarm_time"])
    print(f"Alarm set for {alarm_time.strftime('%I:%M %p')}. Waiting...")

    while True:
        target = next_alarm_datetime(alarm_time)
        print(f"Next alarm: {target.strftime('%Y-%m-%d %I:%M %p')}")
        wait_until(target)

        fresh_config = load_config()
        if not fresh_config.get("enabled", False):
            print("Alarm disabled while waiting. Exiting service loop.")
            return

        perform_alarm_cycle(fresh_config)

        fresh_config = load_config()
        if not fresh_config.get("enabled", False):
            print("Alarm disabled after completion. Exiting service loop.")
            return
        print("Alarm cycle complete. Scheduling the next occurrence...\n")


def show_config(config):
    print("\nCurrent alarm settings:")
    print(f"  Enabled:              {config['enabled']}")
    print(f"  Alarm time:           {config['alarm_time']}")
    print(f"  YouTube URL:          {config['youtube_url']}")
    print(f"  Confirmation phrase:  {config['confirmation_phrase']}")
    print(f"  Initial wait minutes: {config['initial_wait_minutes']}")
    print(f"  Confirmation timeout: {config['confirmation_timeout_seconds']} seconds\n")


def prompt_update(config):
    while True:
        print("Alarm Menu:")
        print("  1) View alarm settings")
        print("  2) Set alarm time")
        print("  3) Set YouTube URL")
        print("  4) Set confirmation phrase")
        print("  5) Set minutes to wait before phrase")
        print("  6) Set phrase timeout seconds")
        print("  7) Toggle enabled/disabled")
        print("  8) Start alarm service")
        print("  9) Exit")

        choice = input("Choose an option: ").strip()
        if choice == "1":
            show_config(config)
        elif choice == "2":
            new_time = input("Enter alarm time (e.g. 07:30 or 7:30 AM): ").strip()
            try:
                parse_time_string(new_time)
            except ValueError as exc:
                print(exc)
            else:
                config["alarm_time"] = new_time
                save_config(config)
                print("Alarm time updated.\n")
        elif choice == "3":
            url = input("Enter the YouTube URL to play: ").strip()
            if url:
                config["youtube_url"] = url
                save_config(config)
                print("YouTube URL updated.\n")
            else:
                print("URL cannot be empty.\n")
        elif choice == "4":
            phrase = input("Enter the confirmation phrase: ").strip()
            if phrase:
                config["confirmation_phrase"] = phrase
                save_config(config)
                print("Confirmation phrase updated.\n")
            else:
                print("Phrase cannot be empty.\n")
        elif choice == "5":
            minutes = input("Minutes to wait before showing the phrase: ").strip()
            if minutes.isdigit():
                config["initial_wait_minutes"] = int(minutes)
                save_config(config)
                print("Wait minutes updated.\n")
            else:
                print("Please enter a whole number.\n")
        elif choice == "6":
            seconds = input("Seconds allowed to type the phrase: ").strip()
            if seconds.isdigit() and int(seconds) > 0:
                config["confirmation_timeout_seconds"] = int(seconds)
                save_config(config)
                print("Timeout updated.\n")
            else:
                print("Please enter a positive number of seconds.\n")
        elif choice == "7":
            config["enabled"] = not config.get("enabled", False)
            save_config(config)
            state = "enabled" if config["enabled"] else "disabled"
            print(f"Alarm {state}.\n")
        elif choice == "8":
            print()
            run_alarm_service(load_config())
        elif choice == "9":
            print("Goodbye!")
            return
        else:
            print("Unknown choice, please try again.\n")


def main():
    config = load_config()
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        run_alarm_service(config)
        return
    prompt_update(config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted. See you next time!")
