# Corrected Version - Including open_book_link

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import requests
import json
import os
import webbrowser
import tkinter.font as tkFont
from tkinter import scrolledtext
import traceback # For detailed error logging

# --- Dark Theme Colors ---
COLOR_BACKGROUND = "#2E2E2E"
COLOR_FOREGROUND = "#EAEAEA"
COLOR_WIDGET_BG = "#3C3C3C"
COLOR_WIDGET_FG = "#EAEAEA"
COLOR_ACCENT_FG = "#569CD6"  # A blue accent for links and highlights
COLOR_LABEL_FG = "#CCCCCC"  # Slightly dimmer for labels
COLOR_HEADER_FG = "#4EC9B0" # A teal/cyan accent for headers
COLOR_ERROR_FG = "#F44747" # Red for errors
COLOR_SEPARATOR_FG = "#6A6A6A" # Dimmer color for separators

# --- Global List for Clickable Regions ---
# Stores {'start': index, 'end': index, 'url': url} dictionaries
clickable_regions = []

# --- Configuration File Handling ---
CONFIG_DIR_NAME = "HardcoverFetcher"
CONFIG_FILE_NAME = "config.json"

def get_config_path():
    """Gets the platform-specific path for the configuration file."""
    app_data_path = os.getenv('APPDATA') # Windows
    if not app_data_path:
        app_data_path = os.path.expanduser("~/.config") # Linux XDG standard
        if not os.path.isdir(app_data_path): # Check if ~/.config exists
             app_data_path = os.path.expanduser("~/.local/share") # Alternative Linux
             if not os.path.isdir(app_data_path):
                  app_data_path = os.path.expanduser("~/Library/Application Support") # macOS
                  if not os.path.isdir(app_data_path):
                       app_data_path = os.path.expanduser("~") # Fallback to home
    config_dir = os.path.join(app_data_path, CONFIG_DIR_NAME)
    try:
        os.makedirs(config_dir, exist_ok=True)
    except OSError as e:
        print(f"Warning: Could not create config directory {config_dir}: {e}")
        return os.path.abspath(CONFIG_FILE_NAME) # Fallback to current dir
    return os.path.join(config_dir, CONFIG_FILE_NAME)

def save_config(config_data):
    """Saves configuration data to the config file."""
    config_file = get_config_path()
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
    except IOError as e:
        print(f"Error saving config file to {config_file}: {e}")
        messagebox.showwarning("Config Error", f"Could not save configuration file:\n{e}")

def load_config():
    """Loads configuration data from the config file."""
    config_file = get_config_path()
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config file from {config_file}: {e}")
            return {}
    else:
        print(f"Config file not found at {config_file}. Using defaults.")
        return {}

# --- >>> ADDED MISSING FUNCTION HERE <<< ---
# --- Link Handling ---
def open_book_link(book_slug):
    """Opens the Hardcover book page in a web browser."""
    if book_slug:
        url = f"https://hardcover.app/books/{book_slug}"
        print(f"Opening URL: {url}")
        try:
            webbrowser.open_new_tab(url)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open link:\n{e}")
    else:
        # This case should ideally not happen if the link label is only shown when slug exists
        print("Error: No slug provided to open_book_link.")
        messagebox.showwarning("Link Error", "Could not create link (missing book slug).")
# --- >>> END OF ADDED FUNCTION <<< ---


# --- URL Generation Helper ---
def get_platform_url(platform_name, external_id):
    """Constructs a URL for a given platform and external ID."""
    if not platform_name or not external_id:
        return None

    name = platform_name.lower()
    if isinstance(external_id, str) and external_id.startswith(('http://', 'https://')):
        if '.' in external_id:
             return external_id
        else:
             return None

    ext_id_str = str(external_id)

    if name == 'goodreads':
        return f"https://www.goodreads.com/book/show/{ext_id_str}"
    elif name == 'google':
        return f"https://books.google.com/books?id={ext_id_str}"
    elif name == 'openlibrary':
        if ext_id_str.startswith(('/books/', '/works/')):
            return f"https://openlibrary.org{ext_id_str}"
        else:
             return f"https://openlibrary.org/search?q={ext_id_str}"
    else:
        return None

# --- Link Handling Callbacks for Output Widget ---
def on_link_enter(event):
    """Changes cursor to hand when hovering over link tag."""
    event.widget.config(cursor="hand2")

def on_link_leave(event):
    """Changes cursor back to default when leaving link tag."""
    event.widget.config(cursor="")

def on_link_click(event):
    """Opens the URL associated with the clicked text region."""
    widget = event.widget
    index = widget.index(f"@{event.x},{event.y}")

    global clickable_regions
    found_link = False
    for region in clickable_regions:
        if widget.compare(index, '>=', region['start']) and widget.compare(index, '<', region['end']):
            url_to_open = region['url']
            print(f"Opening link: {url_to_open}")
            try:
                webbrowser.open_new_tab(url_to_open)
                found_link = True
            except Exception as e:
                 messagebox.showerror("Link Error", f"Could not open URL:\n{url_to_open}\nError: {e}")
            break
    # if not found_link:
    #     print(f"Click at index {index} was not on a registered link region.")


# --- Function to Display Formatted Data with Links ---
def display_formatted_data(widget, book_data):
    """Formats book data and inserts it into the text widget with clickable links."""
    global clickable_regions
    clickable_regions = [] # Clear links from previous fetch

    # Define Text Tags
    widget.tag_configure("header", foreground=COLOR_HEADER_FG, font=tkFont.Font(weight='bold'))
    widget.tag_configure("label", foreground=COLOR_LABEL_FG)
    widget.tag_configure("value", foreground=COLOR_FOREGROUND)
    widget.tag_configure("hyperlink", foreground=COLOR_ACCENT_FG, underline=True)
    widget.tag_configure("separator", foreground=COLOR_SEPARATOR_FG)
    widget.tag_configure("error", foreground=COLOR_ERROR_FG)

    # Nested Helper Function
    def insert_pair(label_text, value_text, is_link=False, url=None, value_tag="value"):
        widget.insert(tk.END, label_text, ("label",))
        value_str = str(value_text or 'N/A')
        if is_link and url and value_str != 'N/A':
            start_index = widget.index(f"{tk.END}-1c")
            widget.insert(tk.END, value_str, ("hyperlink",))
            end_index = widget.index(f"{tk.END}-1c")
            clickable_regions.append({'start': start_index, 'end': end_index, 'url': url})
            widget.insert(tk.END, "\n")
        else:
            widget.insert(tk.END, value_str + "\n", (value_tag,))

    # Enable widget, clear
    widget.config(state=tk.NORMAL)
    widget.delete('1.0', tk.END)

    # --- Book Details ---
    widget.insert(tk.END, "Book Details:\n", ("header",))
    widget.insert(tk.END, "-" * 50 + "\n", ("separator",))
    insert_pair("Title: ", book_data.get('title', 'N/A'))

    author_name = "N/A"
    contributions = book_data.get('contributions', [])
    if contributions and isinstance(contributions, list) and len(contributions) > 0:
        author_info = contributions[0].get('author')
        if author_info and isinstance(author_info, dict):
            author_name = author_info.get('name', 'N/A')
    insert_pair("Author: ", author_name)

    book_slug = book_data.get('slug')
    slug_url = f"https://hardcover.app/books/{book_slug}" if book_slug else None
    insert_pair("Slug: ", book_slug, is_link=bool(slug_url), url=slug_url)

    insert_pair("Editions Count: ", str(book_data.get('editions_count', 'N/A')))
    insert_pair("Users Count: ", str(book_data.get('users_count', 'N/A')))
    insert_pair("Users Read Count: ", str(book_data.get('users_read_count', 'N/A')))
    widget.insert(tk.END, "\n" + "=" * 50 + "\n\n", ("separator",))

    # --- Editions Details ---
    editions = book_data.get('editions', [])
    if editions:
        try:
            editions.sort(key=lambda e: e.get('score') if isinstance(e, dict) and e.get('score') is not None else -float('inf'))
        except Exception as sort_e:
            print(f"Error sorting editions: {sort_e}")
            widget.insert(tk.END, f"(Could not sort editions: {sort_e})\n", ("error",))

    if not editions:
        widget.insert(tk.END,"No editions found in the data.\n", ("value",))
    else:
        widget.insert(tk.END, f"Editions Found ({len(editions)}) - Sorted by Score (Lowest First):\n", ("header",))
        widget.insert(tk.END, "-" * 50 + "\n", ("separator",))

        for i, edition in enumerate(editions):
            if not isinstance(edition, dict): continue

            widget.insert(tk.END, f"\n--- Edition {i+1} --- \n", ("header",))

            edition_id = edition.get('id')
            edit_url = None
            if book_slug and edition_id:
                 edit_url = f"https://hardcover.app/books/{book_slug}/editions/{edition_id}/edit"
            insert_pair("  ID: ", edition_id, is_link=bool(edit_url), url=edit_url)

            insert_pair("  Score: ", str(edition.get('score', 'N/A')))
            insert_pair("  Format: ", edition.get('edition_format', 'N/A'))
            insert_pair("  ASIN: ", edition.get('asin') or 'N/A')
            insert_pair("  ISBN-10: ", edition.get('isbn_10') or 'N/A')
            insert_pair("  ISBN-13: ", edition.get('isbn_13') or 'N/A')

            widget.insert(tk.END, "  Image: ", ("label",))
            image_info = edition.get('image')
            image_url = image_info.get('url') if image_info and isinstance(image_info, dict) else None
            insert_pair("", image_url, is_link=bool(image_url), url=image_url)

            widget.insert(tk.END, "  Platform Mappings:\n", ("label",))
            mappings = edition.get('book_mappings', [])
            if not mappings:
                widget.insert(tk.END, "    - None found for this edition.\n", ("value",))
            else:
                platform_counts = {}
                for mapping in mappings:
                     if not isinstance(mapping, dict): continue
                     platform = mapping.get('platform')
                     platform_name = "N/A"
                     if platform and isinstance(platform, dict):
                         platform_name = platform.get('name', 'N/A')
                     external_id = mapping.get('external_id', 'N/A')

                     widget.insert(tk.END, "    - Platform: ", ("label",))
                     widget.insert(tk.END, f"{platform_name}\n", ("value",))

                     platform_url = get_platform_url(platform_name, external_id)
                     insert_pair("      External ID: ", external_id, is_link=bool(platform_url), url=platform_url)

                     if platform_name != "N/A":
                         platform_counts[platform_name] = platform_counts.get(platform_name, 0) + 1

                if any(count > 1 for platform, count in platform_counts.items()):
                     widget.insert(tk.END, "    (Note: Duplicate platform names found for this edition)\n", ("label",))

    # --- Make widget read-only again ---
    widget.config(state=tk.DISABLED)

# --- Function to Display Error Message ---
def display_error_message(widget, error_message):
    """Displays an error message in the output widget."""
    try:
        widget.config(state=tk.NORMAL)
        widget.delete('1.0', tk.END)
        widget.tag_configure("error", foreground=COLOR_ERROR_FG) # Ensure tag exists
        widget.insert(tk.END, "Error:\n", ("error",))
        widget.insert(tk.END, str(error_message), ("error",))
        widget.config(state=tk.DISABLED)
    except tk.TclError as e:
        print(f"Error displaying error message in widget: {e}")


# --- Core Logic to Fetch Data ---
def fetch_and_process_data():
    """Gets data from GUI, calls API, displays cleaned data and link."""

    # Reset UI
    link_label.grid_remove()
    status_var.set("Processing...")
    output_viewer.config(state=tk.NORMAL)
    output_viewer.delete('1.0', tk.END)
    output_viewer.config(state=tk.DISABLED)
    window.update_idletasks()

    # Get Inputs & Validate
    bearer_token = token_entry.get().strip()
    book_id_str = book_id_entry.get().strip()

    if not bearer_token:
        msg = "Bearer Token cannot be empty."
        messagebox.showerror("Error", msg)
        status_var.set("Error: Missing Bearer Token.")
        display_error_message(output_viewer, msg)
        return
    if not book_id_str:
        msg = "Book ID cannot be empty."
        messagebox.showerror("Input Error", msg)
        status_var.set("Error: Missing Book ID.")
        display_error_message(output_viewer, msg)
        return
    if not book_id_str.isdigit():
        msg = "Book ID must be a number."
        messagebox.showerror("Input Error", msg)
        status_var.set("Error: Invalid Book ID.")
        display_error_message(output_viewer, msg)
        return
    try:
        book_id_int = int(book_id_str)
    except ValueError:
        msg = "Book ID is not a valid integer."
        messagebox.showerror("Input Error", msg)
        status_var.set("Error: Invalid Book ID format.")
        display_error_message(output_viewer, msg)
        return

    # Save Config
    current_config = load_config()
    current_config['bearer_token'] = bearer_token
    save_config(current_config)

    status_var.set(f"Fetching data for ID: {book_id_int}...")
    window.update_idletasks()

    # API Setup
    api_url = "https://api.hardcover.app/v1/graphql"
    graphql_query = """
    query MyQuery($bookId: Int!) {
      books(where: {id: {_eq: $bookId}}) {
        title
        slug
        editions_count
        users_count
        users_read_count
        contributions {
          author {
            name
          }
        }
        editions {
          id
          score
          edition_format
          asin
          isbn_10
          isbn_13
          image {
            url
          }
          book_mappings {
            external_id
            platform {
              name
            }
          }
        }
      }
    }
    """
    payload = { "query": graphql_query, "variables": { "bookId": book_id_int }, "operationName": "MyQuery" }
    headers = { "accept": "application/json", "authorization": f"Bearer {bearer_token}", "content-type": "application/json", "user-agent": "Python Hardcover GUI Client V7.1" } # Minor version bump

    # API Request
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        raw_data = response.json()

        status_var.set("Data received. Formatting output...")
        window.update_idletasks()

        # Process API Response
        if 'errors' in raw_data:
             error_message = raw_data['errors'][0]['message'] if raw_data['errors'] else "Unknown API error"
             status_var.set(f"API Error: {error_message}")
             messagebox.showerror("API Error", f"The API returned an error:\n{error_message}")
             display_error_message(output_viewer, f"API Error:\n{error_message}")
             return

        books_data = raw_data.get('data', {}).get('books', [])

        if not books_data:
             no_book_message = f"No book found for ID {book_id_int}."
             status_var.set(no_book_message)
             messagebox.showinfo("Info", no_book_message)
             display_error_message(output_viewer, no_book_message)
             return

        book = books_data[0]
        book_title = book.get('title', 'N/A')
        actual_book_slug = book.get('slug')

        # --- Generate and Display Readable Output ---
        display_formatted_data(output_viewer, book) # Call the display function

        status_var.set(f"Success! Displaying data for '{book_title}'.")

        # Show Link to main book page (using open_book_link)
        if actual_book_slug:
            link_text = f"View '{book_title}' on Hardcover"
            link_label.config(text=link_text, foreground=COLOR_ACCENT_FG)
            link_label.unbind("<Button-1>")
            link_label.bind("<Button-1>", lambda e, s=actual_book_slug: open_book_link(s)) # Use lambda
            link_label.grid()
        else:
            link_label.grid_remove()


    # Exception Handling
    except requests.exceptions.Timeout:
        error_msg = "Network Error: The request timed out."
        status_var.set("Network Error: Timeout.")
        link_label.grid_remove()
        messagebox.showerror("Network Error", error_msg)
        display_error_message(output_viewer, error_msg)
    except requests.exceptions.RequestException as e:
        error_msg = f"Network/API Error:\n{e}"
        status_var.set("Network/API Error.")
        link_label.grid_remove()
        messagebox.showerror("API Error", f"Failed to connect or get data from the API.\nCheck connection and token.\nError: {e}")
        display_error_message(output_viewer, error_msg)
    except json.JSONDecodeError:
        error_msg = "Invalid JSON received from API."
        status_var.set("Error: Invalid JSON received.")
        link_label.grid_remove()
        try:
            error_msg += f"\n\nResponse Text:\n{response.text[:500]}..."
        except Exception: pass
        messagebox.showerror("Data Error", "The response from the API was not valid JSON.")
        display_error_message(output_viewer, error_msg)
    except Exception as e:
        error_msg = f"An unexpected error occurred:\n{type(e).__name__}: {e}"
        status_var.set("An unexpected error occurred.")
        link_label.grid_remove()
        messagebox.showerror("Error", error_msg)
        print(f"Traceback for unexpected error:\n", flush=True)
        traceback.print_exc()
        display_error_message(output_viewer, error_msg)


# --- GUI Setup ---
if __name__ == "__main__": # Run only if script executed directly
    window = tk.Tk()
    window.title("Hardcover Book Data Fetcher (ID Only)")
    window.geometry("800x650")
    window.config(bg=COLOR_BACKGROUND)

    # --- Themed Style Configuration ---
    style = ttk.Style()
    default_themes = ['clam', 'alt', 'default']
    selected_theme = None
    for theme in default_themes:
        if theme in style.theme_names():
            try:
                style.theme_use(theme)
                selected_theme = theme
                print(f"Using ttk theme: {theme}")
                break
            except tk.TclError:
                continue
    if not selected_theme:
        print("No suitable ttk theme found, using system default.")

    style.configure('.', background=COLOR_BACKGROUND, foreground=COLOR_FOREGROUND)
    style.configure('TFrame', background=COLOR_BACKGROUND)
    style.configure('TLabel', background=COLOR_BACKGROUND, foreground=COLOR_LABEL_FG, anchor=tk.W)
    style.configure('TNotebook', background=COLOR_BACKGROUND, borderwidth=0, tabposition='nw')
    style.configure('TNotebook.Tab', background=COLOR_WIDGET_BG, foreground=COLOR_LABEL_FG, padding=[10, 5], borderwidth=1)
    style.map('TNotebook.Tab',
              background=[('selected', COLOR_BACKGROUND), ('!selected', COLOR_WIDGET_BG)],
              foreground=[('selected', COLOR_HEADER_FG), ('!selected', COLOR_LABEL_FG)],
              expand=[('selected', [1, 1, 1, 0])])
    style.configure('TButton', background=COLOR_WIDGET_BG, foreground=COLOR_FOREGROUND, padding=8, font=tkFont.Font(weight='bold'))
    style.map('TButton',
              background=[('active', COLOR_ACCENT_FG), ('pressed', COLOR_ACCENT_FG)],
              foreground=[('active', COLOR_BACKGROUND), ('pressed', COLOR_BACKGROUND)])
    style.configure('TEntry',
                    foreground=COLOR_WIDGET_FG,
                    fieldbackground=COLOR_WIDGET_BG,
                    insertcolor=COLOR_FOREGROUND,
                    borderwidth=1,
                    relief=tk.FLAT)
    style.map('TEntry', relief=[('focus', tk.SOLID)])

    # --- Main Notebook (Tabs) ---
    notebook = ttk.Notebook(window, style='TNotebook')
    notebook.pack(pady=10, padx=10, fill="both", expand=True)

    # --- Tab 1: Input & Controls ---
    input_frame = ttk.Frame(notebook, padding="20", style='TFrame')
    notebook.add(input_frame, text='Fetch Data')
    input_frame.columnconfigure(1, weight=1)

    token_label = ttk.Label(input_frame, text="Bearer Token:")
    token_label.grid(row=0, column=0, sticky=tk.W, pady=5, padx=(0, 10))
    token_entry = ttk.Entry(input_frame, width=60, show="*", style='TEntry')
    token_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)

    book_id_label = ttk.Label(input_frame, text="Book ID:")
    book_id_label.grid(row=1, column=0, sticky=tk.W, pady=5, padx=(0, 10))
    book_id_entry = ttk.Entry(input_frame, width=20, style='TEntry')
    book_id_entry.grid(row=1, column=1, sticky=tk.W, pady=5)

    fetch_button = ttk.Button(input_frame, text="Fetch Data", command=fetch_and_process_data, style='TButton', width=15)
    fetch_button.grid(row=2, column=0, columnspan=2, pady=(25, 15))

    status_var = tk.StringVar()
    status_label = ttk.Label(input_frame, textvariable=status_var, wraplength=700)
    status_label.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

    link_font = tkFont.Font(family="Segoe UI", size=10, underline=True) # Or system default font
    link_label = ttk.Label(input_frame, text="", style='TLabel', cursor="hand2", font=link_font)
    link_label.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(5, 10))
    link_label.grid_remove()

    # --- Tab 2: Output Viewer ---
    output_frame = ttk.Frame(notebook, padding="5", style='TFrame')
    notebook.add(output_frame, text='Output')
    output_frame.rowconfigure(0, weight=1)
    output_frame.columnconfigure(0, weight=1)

    output_viewer = scrolledtext.ScrolledText(
        output_frame,
        wrap=tk.WORD,
        state=tk.DISABLED,
        bg=COLOR_WIDGET_BG,
        fg=COLOR_FOREGROUND,
        insertbackground=COLOR_FOREGROUND,
        selectbackground=COLOR_ACCENT_FG,
        selectforeground=COLOR_BACKGROUND,
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=COLOR_BACKGROUND,
        highlightcolor=COLOR_ACCENT_FG,
        padx=8,
        pady=8,
        font=("Consolas", 10) # Monospace font
    )
    output_viewer.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

    # Bind link events to the output viewer
    output_viewer.tag_bind("hyperlink", "<Enter>", on_link_enter)
    output_viewer.tag_bind("hyperlink", "<Leave>", on_link_leave)
    output_viewer.bind("<Button-1>", on_link_click)

    # --- Load Configuration on Startup ---
    config = load_config()
    saved_token = config.get('bearer_token', '')
    if saved_token:
        token_entry.insert(0, saved_token)
        status_var.set("Loaded saved token. Enter Book ID.")
    else:
         status_var.set("Enter token and Book ID, then press 'Fetch Data'.")

    # --- Run the GUI ---
    window.mainloop()