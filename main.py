import requests
from bs4 import BeautifulSoup
import hashlib
import json
import os
import curses
from datetime import datetime
import feedparser

# File paths for data storage
LINKS_FILE = 'saved_links.json'
ARTICLES_FILE = 'saved_articles.json'

# Load data from JSON files
def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return [] if 'articles' in file_path else {}

# Save data to JSON files
def save_data(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

# Function to add and save a website link
def add_link(stdscr, link):
    links = load_data(LINKS_FILE)
    if link not in links:
        links[link] = {'hash': '', 'updates': [], 'last_updated': 'Never'}
        save_data(LINKS_FILE, links)
        stdscr.addstr(f"Link '{link}' added successfully.\n")
    else:
        stdscr.addstr(f"Link '{link}' is already saved.\n")

# Function to fetch and detect changes
def fetch_updates(stdscr):
    links = load_data(LINKS_FILE)
    for link in links:
        try:
            response = requests.get(link)
            response.raise_for_status()
            content_hash = hashlib.md5(response.text.encode()).hexdigest()

            if links[link]['hash'] != content_hash:
                stdscr.addstr(f"Update found for {link}\n")
                links[link]['hash'] = content_hash
                links[link]['updates'].append(response.text[:500])
                links[link]['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                stdscr.addstr(f"No updates for {link}\n")
        except requests.RequestException as e:
            stdscr.addstr(f"Failed to fetch {link}: {e}\n")

    save_data(LINKS_FILE, links)

# Function to parse RSS feed with pagination support
def fetch_rss_articles(feed_url):
    articles = []
    next_page = feed_url

    while next_page:
        feed = feedparser.parse(next_page)
        if feed.entries:
            for entry in feed.entries:
                articles.append({
                    'title': entry.get('title', 'No Title'),
                    'link': entry.get('link', ''),
                    'content': entry.get('summary', '')[:200]
                })

        next_page = feed.feed.get('next') if 'next' in feed.feed else None

    return articles

# Fallback web scraping if no RSS feed is available
def scrape_website(link):
    articles = []
    try:
        response = requests.get(link)
        soup = BeautifulSoup(response.content, 'html.parser')
        headlines = soup.find_all(['h1', 'h2', 'h3', 'p'], limit=50)  # Increased limit

        for tag in headlines:
            articles.append({
                'title': tag.get_text(strip=True),
                'link': link,
                'content': tag.get_text(strip=True)[:200]
            })
    except requests.RequestException as e:
        print(f"Failed to scrape website {link}: {e}")
    return articles

# Function to display articles with pagination
def display_articles(stdscr, articles, saved_articles=None):
    current_idx = 0
    if saved_articles is None:
        saved_articles = load_data(ARTICLES_FILE)
    page_size = 5  # Number of articles per page

    while True:
        stdscr.clear()
        stdscr.addstr("Articles:\n", curses.A_BOLD | curses.A_UNDERLINE)

        max_y, max_x = stdscr.getmaxyx()
        max_width = max_x - 4

        start_idx = (current_idx // page_size) * page_size
        end_idx = min(start_idx + page_size, len(articles))

        for idx in range(start_idx, end_idx):
            article = articles[idx]
            title = article.get('title', 'No Title')[:max_width]
            content = article.get('content', '')[:max_width]
            is_saved = "✔️" if article in saved_articles else "❌"

            try:
                if idx == current_idx:
                    stdscr.addstr(f"{is_saved} {title}\n", curses.A_REVERSE)
                    stdscr.addstr(f"{content}\n", curses.A_REVERSE)
                    stdscr.addstr("─" * min(40, max_width) + "\n", curses.A_REVERSE)
                else:
                    stdscr.addstr(f"{is_saved} {title}\n")
                    stdscr.addstr(f"{content}\n")
                    stdscr.addstr("─" * min(40, max_width) + "\n")
            except curses.error:
                pass

        stdscr.addstr("(Arrow keys to navigate, Enter to save, PgUp/PgDn for pages, ESC to exit)\n")

        key = stdscr.getch()

        if key == curses.KEY_UP and current_idx > 0:
            current_idx -= 1
        elif key == curses.KEY_DOWN and current_idx < len(articles) - 1:
            current_idx += 1
        elif key in [curses.KEY_ENTER, ord('\n')]:
            if articles[current_idx] in saved_articles:
                saved_articles.remove(articles[current_idx])
            else:
                saved_articles.append(articles[current_idx])
        elif key == curses.KEY_NPAGE and current_idx + page_size < len(articles):  # Page Down
            current_idx += page_size
        elif key == curses.KEY_PPAGE and current_idx - page_size >= 0:  # Page Up
            current_idx -= page_size
        elif key == 27:  # ESC key to exit
            break

    save_data(ARTICLES_FILE, saved_articles)
    stdscr.addstr("Saved selected articles!\n")
    stdscr.addstr("Press any key to return...")
    stdscr.getch()

# Function to view saved articles
def view_saved_articles(stdscr):
    saved_articles = load_data(ARTICLES_FILE)
    if saved_articles:
        display_articles(stdscr, saved_articles, saved_articles)
    else:
        stdscr.addstr("No saved articles found.\n")
        stdscr.addstr("Press any key to return...")
        stdscr.getch()

# Function to view saved links and select one
def view_saved_links(stdscr):
    links = load_data(LINKS_FILE)
    if not links:
        stdscr.addstr("No saved links found.\n")
        stdscr.addstr("Press any key to return to the menu...")
        stdscr.getch()
        return

    current_idx = 0
    link_list = list(links.keys())

    while True:
        stdscr.clear()
        stdscr.addstr("Select a link to view articles:\n", curses.A_BOLD)

        for idx, link in enumerate(link_list):
            last_updated = links[link].get('last_updated', 'Never')
            if idx == current_idx:
                stdscr.addstr(f"> {link} (Last updated: {last_updated})\n", curses.A_REVERSE)
            else:
                stdscr.addstr(f"  {link} (Last updated: {last_updated})\n")

        stdscr.addstr("(Arrow keys to navigate, Enter to select, ESC to go back)\n")
        key = stdscr.getch()

        if key == curses.KEY_UP and current_idx > 0:
            current_idx -= 1
        elif key == curses.KEY_DOWN and current_idx < len(link_list) - 1:
            current_idx += 1
        elif key in [curses.KEY_ENTER, ord('\n')]:
            link = link_list[current_idx]
            articles = fetch_rss_articles(link) if 'rss' in link else scrape_website(link)
            display_articles(stdscr, articles)
        elif key == 27:  # ESC key to exit
            break

# Interactive CLI using curses
def main(stdscr):
    curses.curs_set(0)
    current_option = 0
    options = [
        "Add a website link",
        "Check for updates",
        "View saved links",
        "View saved articles",
        "Exit"
    ]

    while True:
        stdscr.clear()
        stdscr.addstr("RSS Feed Aggregator\n", curses.A_BOLD | curses.A_UNDERLINE)

        for idx, option in enumerate(options):
            if idx == current_option:
                stdscr.addstr(f"> {option}\n", curses.A_REVERSE)
            else:
                stdscr.addstr(f"  {option}\n")

        key = stdscr.getch()

        if key == curses.KEY_UP and current_option > 0:
            current_option -= 1
        elif key == curses.KEY_DOWN and current_option < len(options) - 1:
            current_option += 1
        elif key in [curses.KEY_ENTER, ord('\n')]:
            stdscr.clear()

            if current_option == 0:  # Add link
                stdscr.addstr("Enter website link: ")
                curses.echo()
                link = stdscr.getstr().decode()
                curses.noecho()
                add_link(stdscr, link)
            elif current_option == 1:  # Check updates
                fetch_updates(stdscr)
            elif current_option == 2:  # View saved links
                view_saved_links(stdscr)
            elif current_option == 3:  # View saved articles
                view_saved_articles(stdscr)
            elif current_option == 4:  # Exit
                break

            stdscr.addstr("\nPress any key to return to the menu...")
            stdscr.getch()

        stdscr.refresh()

if __name__ == "__main__":
    curses.wrapper(main)
