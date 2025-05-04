import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import requests
import json
import os
import webbrowser
import tkinter.font as tkFont
from tkinter import scrolledtext
import traceback
import base64 # Added for token obfuscation

# --- Dark Theme Colors ---
COLOR_BACKGROUND = "#2E2E2E"
COLOR_FOREGROUND = "#EAEAEA"
COLOR_WIDGET_BG = "#3C3C3C"
COLOR_WIDGET_FG = "#EAEAEA"
COLOR_ACCENT_FG = "#569CD6"  # Blue accent for links
COLOR_LABEL_FG = "#CCCCCC"
COLOR_HEADER_FG = "#4EC9B0" # Teal/cyan accent for headers
COLOR_ERROR_FG = "#F44747" # Red for errors
COLOR_SEPARATOR_FG = "#6A6A6A"
COLOR_WARNING_FG = "#FF8C00" # DarkOrange for warnings (Missing critical data)
COLOR_INFO_FG = "#FFCC66"   # Lighter Orange/Gold for info flags (Missing less critical data)

# --- Global List for Clickable Regions ---
clickable_regions = []

# --- Configuration File Handling (No changes needed here) ---
CONFIG_DIR_NAME = "HardcoverFetcher"
CONFIG_FILE_NAME = "config.json"
# ... (get_config_path, save_config, load_config remain the same) ...
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
                # Handle potential empty file
                content = f.read()
                if not content:
                    return {}
                return json.loads(content)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading/parsing config file from {config_file}: {e}")
            return {}
    else:
        print(f"Config file not found at {config_file}. Using defaults.")
        return {}

# --- Link Handling (No changes needed here) ---
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
        print("Error: No slug provided to open_book_link.")
        messagebox.showwarning("Link Error", "Could not create link (missing book slug).")

# --- URL Generation Helper (No changes needed here) ---
def get_platform_url(platform_name, external_id):
    """Constructs a URL for a given platform and external ID."""
    if not platform_name or not external_id: return None
    name = platform_name.lower()
    if isinstance(external_id, str) and external_id.startswith(('http://', 'https://')):
        if '.' in external_id: return external_id
        else: return None
    ext_id_str = str(external_id)
    if name == 'goodreads': return f"https://www.goodreads.com/book/show/{ext_id_str}"
    if name == 'google': return f"https://books.google.com/books?id={ext_id_str}"
    if name == 'openlibrary':
        if ext_id_str.startswith(('/books/', '/works/')): return f"https://openlibrary.org{ext_id_str}"
        else: return f"https://openlibrary.org/search?q={ext_id_str}"
    return None

# --- Link Handling Callbacks for Output Widget (No changes needed here) ---
def on_link_enter(event): event.widget.config(cursor="hand2")
def on_link_leave(event): event.widget.config(cursor="")
def on_link_click(event):
    widget = event.widget
    index = widget.index(f"@{event.x},{event.y}")
    global clickable_regions
    for region in clickable_regions:
        if widget.compare(index, '>=', region['start']) and widget.compare(index, '<', region['end']):
            url_to_open = region['url']
            print(f"Opening link: {url_to_open}")
            try: webbrowser.open_new_tab(url_to_open)
            except Exception as e: messagebox.showerror("Link Error", f"Could not open URL:\n{url_to_open}\nError: {e}")
            break

# --- MODIFIED: Function to Display Formatted Data with Flags ---
def display_formatted_data(widget, book_data):
    """Formats book data and inserts it into the text widget with colors and flags."""
    global clickable_regions
    clickable_regions = []

    # Define Text Tags (Update colors here)
    widget.tag_configure("header", foreground=COLOR_HEADER_FG, font=tkFont.Font(weight='bold'))
    widget.tag_configure("label", foreground=COLOR_LABEL_FG)
    widget.tag_configure("value", foreground=COLOR_FOREGROUND)
    widget.tag_configure("hyperlink", foreground=COLOR_ACCENT_FG, underline=True)
    widget.tag_configure("separator", foreground=COLOR_SEPARATOR_FG)
    widget.tag_configure("error", foreground=COLOR_ERROR_FG)
    widget.tag_configure("warning_flag", foreground=COLOR_WARNING_FG, font=tkFont.Font(weight='bold')) # Red/Orange
    widget.tag_configure("info_flag", foreground=COLOR_INFO_FG, font=tkFont.Font(weight='bold'))    # Yellow/Orange

    # Nested Helper Function (remains the same)
    def insert_pair(label_text, value_text, is_link=False, url=None, value_tag="value"):
        # NOTE: This function no longer handles inserting flags directly for book details.
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

    # --- Gather Book-Level Flags ---
    book_flags = []
    if not book_data.get('description'):
        book_flags.append(("[NO DESCRIPTION]", "warning_flag")) # Warning
    if not book_data.get('default_cover_edition'): book_flags.append(("[NO DEFAULT COVER]", "info_flag")) # Info
    if not book_data.get('default_ebook_edition'): book_flags.append(("[NO DEFAULT EBOOK]", "info_flag")) # Info
    if not book_data.get('default_audio_edition'): book_flags.append(("[NO DEFAULT AUDIO]", "info_flag")) # Info
    if not book_data.get('default_physical_edition'): book_flags.append(("[NO DEFAULT PHYSICAL]", "info_flag")) # Info
    # --- End Book-Level Flag Gathering ---

    # Insert Book Details (without flags attached here)
    insert_pair("Title: ", book_data.get('title', 'N/A')) # Flags removed from here

    author_name = "N/A" # Default
    contributions = book_data.get('contributions', [])
    if contributions and isinstance(contributions, list) and len(contributions) > 0:
    # Check if the first contribution is a dict before getting 'author'
        first_contribution = contributions[0]
    if isinstance(first_contribution, dict):
        author_info = first_contribution.get('author') # Get author, could be None or dict
        # Check if author_info is a dict before getting 'name'
        if author_info and isinstance(author_info, dict):
             author_name = author_info.get('name', 'N/A')
    insert_pair("Author: ", author_name)

    book_slug = book_data.get('slug')
    slug_url = f"https://hardcover.app/books/{book_slug}" if book_slug else None
    insert_pair("Slug: ", book_slug, is_link=bool(slug_url), url=slug_url)

    insert_pair("Book ID: ", str(book_data.get('id', 'N/A')))
    insert_pair("Editions Count: ", str(book_data.get('editions_count', 'N/A')))
    insert_pair("Users Count: ", str(book_data.get('users_count', 'N/A')))
    insert_pair("Users Read Count: ", str(book_data.get('users_read_count', 'N/A')))

    # --- Display Book Flags Separately ---
    if book_flags:
        widget.insert(tk.END, "Book Flags: ", ("label",)) # Label for the flags
        for flag_text, flag_tag in book_flags:
            widget.insert(tk.END, flag_text + " ", (flag_tag,)) # Insert flags inline
        widget.insert(tk.END, "\n") # Newline after flags
    # --- End Book Flag Display ---

    # Display Description if present
    description = book_data.get('description')
    if description:
         widget.insert(tk.END, "Description:\n", ("label",)) # Label on own line
         widget.insert(tk.END, description[:500] + ("..." if len(description) > 500 else "") + "\n", ("value",))


    widget.insert(tk.END, "\n" + "=" * 50 + "\n\n", ("separator",))

    # --- Editions Details (Logic remains similar, using new flag colors) ---
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

        LOW_SCORE_THRESHOLD = 500

        for i, edition in enumerate(editions):
            if not isinstance(edition, dict): continue

            widget.insert(tk.END, f"\n--- Edition {i+1} --- \n", ("header",))

            # --- Gather Edition Flags ---
            edition_flags = []
            edition_score = edition.get('score')
            if edition_score is not None and edition_score < LOW_SCORE_THRESHOLD:
                edition_flags.append((f"[LOW SCORE:{edition_score}]", "warning_flag")) # Warning
            if not edition.get('isbn_10') and not edition.get('isbn_13'):
                edition_flags.append(("[MISSING ISBN]", "warning_flag")) # Warning
            image_info = edition.get('image')
            image_url = image_info.get('url') if image_info and isinstance(image_info, dict) else None
            if not image_url:
                edition_flags.append(("[NO IMAGE]", "warning_flag")) # Warning
            if not edition.get('pages'): edition_flags.append(("[NO PAGES]", "info_flag")) # Info
            if not edition.get('release_date'): edition_flags.append(("[NO RELEASE DATE]", "info_flag")) # Info
            if not edition.get('publisher'): edition_flags.append(("[NO PUBLISHER]", "info_flag")) # Info
            if not edition.get('language'): edition_flags.append(("[NO LANGUAGE]", "info_flag")) # Info
            if not edition.get('edition_format'): edition_flags.append(("[NO FORMAT]", "info_flag")) # Info

            # Check for duplicate platforms within this edition's mappings
            mappings = edition.get('book_mappings', [])
            platform_counts = {}
            if mappings:
                 for mapping in mappings:
                      if not isinstance(mapping, dict): continue
                      platform = mapping.get('platform')
                      platform_name = platform.get('name', 'N/A') if platform and isinstance(platform, dict) else "N/A"
                      if platform_name != "N/A":
                          platform_counts[platform_name] = platform_counts.get(platform_name, 0) + 1
            dupe_platforms = [p for p, c in platform_counts.items() if c > 1]
            if dupe_platforms:
                 edition_flags.append((f"[DUPE PLATFORMS: {', '.join(dupe_platforms)}]", "info_flag")) # Info
            # --- End Edition Flag Gathering ---


            # Insert edition flags near the top
            if edition_flags:
                widget.insert(tk.END, "  Flags: ", ("label",))
                for flag_text, flag_tag in edition_flags:
                     widget.insert(tk.END, flag_text + " ", (flag_tag,))
                widget.insert(tk.END, "\n")

            # Insert Edition Details
            edition_id = edition.get('id')
            edit_url = f"https://hardcover.app/books/{book_slug}/editions/{edition_id}/edit" if book_slug and edition_id else None
            insert_pair("  ID: ", edition_id, is_link=bool(edit_url), url=edit_url)

            insert_pair("  Score: ", str(edition_score or 'N/A'))
            insert_pair("  Format: ", edition.get('edition_format', 'N/A'))
            insert_pair("  ASIN: ", edition.get('asin') or 'N/A')
            insert_pair("  ISBN-10: ", edition.get('isbn_10') or 'N/A')
            insert_pair("  ISBN-13: ", edition.get('isbn_13') or 'N/A')
            insert_pair("  Pages: ", str(edition.get('pages', 'N/A')))
            insert_pair("  Release Date: ", edition.get('release_date', 'N/A'))

            publisher_name = "N/A" # Default
            publisher_info = edition.get('publisher') # Get value, could be None or dict
            if publisher_info and isinstance(publisher_info, dict): # Check it's a valid dict
                publisher_name = publisher_info.get('name', 'N/A')
            insert_pair("  Publisher: ", publisher_name)
            language_name = "N/A" # Default
            language_info = edition.get('language') # Get value
            if language_info and isinstance(language_info, dict): # Check it's valid
                language_name = language_info.get('language', 'N/A')
            insert_pair("  Language: ", language_name)
            reading_fmt = "N/A" # Default
            reading_fmt_info = edition.get('reading_format') # Get value
            if reading_fmt_info and isinstance(reading_fmt_info, dict): # Check it's valid
                reading_fmt = reading_fmt_info.get('format', 'N/A')
            insert_pair("  Reading Format: ", reading_fmt)

            widget.insert(tk.END, "  Image: ", ("label",))
            insert_pair("", image_url, is_link=bool(image_url), url=image_url)

            widget.insert(tk.END, "  Platform Mappings:\n", ("label",))
            if not mappings:
                widget.insert(tk.END, "    - None found for this edition.\n", ("value",))
            else:
                for mapping in mappings:
                     if not isinstance(mapping, dict): continue
                     platform = mapping.get('platform')
                     platform_name = platform.get('name', 'N/A') if platform and isinstance(platform, dict) else "N/A"
                     external_id = mapping.get('external_id', 'N/A')

                     widget.insert(tk.END, "    - Platform: ", ("label",))
                     widget.insert(tk.END, f"{platform_name}\n", ("value",))

                     platform_url = get_platform_url(platform_name, external_id)
                     insert_pair("      External ID: ", external_id, is_link=bool(platform_url), url=platform_url)

                # Removed duplicate platform note from here as it's included in flags above


    # Make widget read-only again
    widget.config(state=tk.DISABLED)


# --- Function to Display Error Message (No changes needed here) ---
def display_error_message(widget, error_message):
    """Displays an error message in the output widget."""
    # ... (function remains the same) ...
    try:
        widget.config(state=tk.NORMAL)
        widget.delete('1.0', tk.END)
        widget.tag_configure("error", foreground=COLOR_ERROR_FG) # Ensure tag exists
        widget.insert(tk.END, "Error:\n", ("error",))
        widget.insert(tk.END, str(error_message), ("error",)) # Ensure message is string
        widget.config(state=tk.DISABLED)
    except tk.TclError as e:
        print(f"Error displaying error message in widget: {e}")


# --- Core Logic to Fetch Data ---
def fetch_and_process_data():
    """Gets data from GUI, calls API, displays cleaned data and link."""

    # Reset UI (Same)
    link_label.grid_remove()
    status_var.set("Processing...")
    output_viewer.config(state=tk.NORMAL)
    output_viewer.delete('1.0', tk.END)
    output_viewer.config(state=tk.DISABLED)
    window.update_idletasks()

    # Get Inputs & Validate (Same)
    bearer_token = token_entry.get().strip()
    book_id_str = book_id_entry.get().strip()
    # ... (validation logic remains the same) ...
    if not bearer_token: msg = "Bearer Token cannot be empty."; messagebox.showerror("Error", msg); status_var.set("Error: Missing Bearer Token."); display_error_message(output_viewer, msg); return
    if not book_id_str: msg = "Book ID cannot be empty."; messagebox.showerror("Input Error", msg); status_var.set("Error: Missing Book ID."); display_error_message(output_viewer, msg); return
    if not book_id_str.isdigit(): msg = "Book ID must be a number."; messagebox.showerror("Input Error", msg); status_var.set("Error: Invalid Book ID."); display_error_message(output_viewer, msg); return
    try: book_id_int = int(book_id_str)
    except ValueError: msg = "Book ID is not a valid integer."; messagebox.showerror("Input Error", msg); status_var.set("Error: Invalid Book ID format."); display_error_message(output_viewer, msg); return


    # --- Encode Token Before Saving Config ---
    try:
        # Only encode if the token is not empty
        encoded_token = base64.b64encode(bearer_token.encode()).decode() if bearer_token else ""
    except Exception as e:
        print(f"Error encoding token: {e}")
        messagebox.showerror("Token Error", f"Could not encode token for saving:\n{e}")
        encoded_token = "" # Save empty if encoding fails

    current_config = load_config()
    current_config['bearer_token_b64'] = encoded_token # Save encoded token under new key
    # Optionally remove old plain text key if it exists
    current_config.pop('bearer_token', None)
    save_config(current_config)
    # --- End Token Encoding ---


    status_var.set(f"Fetching data for ID: {book_id_int}...")
    window.update_idletasks()

    # API Setup
    api_url = "https://api.hardcover.app/v1/graphql"
    # --- <<< USE THE NEW COMPREHENSIVE QUERY >>> ---
    graphql_query = """
    query MyQuery($bookId: Int!) {
      books(where: {id: {_eq: $bookId}}) {
        id
        title
        slug
        editions_count
        description
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
          pages
          release_date
          image {
            url
          }
          book_mappings {
            external_id
            platform {
              name
            }
          }
          publisher {
            name
          }
          reading_format {
            format
          }
          language {
            language
          }
        }
        default_audio_edition {
          id
          edition_format
        }
        default_cover_edition {
          id
          edition_format
        }
        default_ebook_edition {
          id
          edition_format
        }
        default_physical_edition {
          id
          edition_format
        }
      }
    }
    """
    # --- <<< END NEW QUERY >>> ---

    payload = { "query": graphql_query, "variables": { "bookId": book_id_int }, "operationName": "MyQuery" }
    headers = { "accept": "application/json", "authorization": f"Bearer {bearer_token}", "content-type": "application/json", "user-agent": "Python Hardcover Librarian Tool V1.0" } # Updated UA

    # --- API Request & Processing (largely same, but uses new display function) ---
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

        # --- Generate and Display Using New Function ---
        display_formatted_data(output_viewer, book) # Call the updated display function

        status_var.set(f"Success! Displaying data for '{book_title}'.")

        # Show Link to main book page (Same)
        if actual_book_slug:
            link_text = f"View '{book_title}' on Hardcover"
            link_label.config(text=link_text, foreground=COLOR_ACCENT_FG)
            link_label.unbind("<Button-1>")
            link_label.bind("<Button-1>", lambda e, s=actual_book_slug: open_book_link(s))
            link_label.grid()
        else:
            link_label.grid_remove()


    # Exception Handling (Same)
    except requests.exceptions.Timeout: error_msg = "Network Error: The request timed out."; status_var.set("Network Error: Timeout."); link_label.grid_remove(); messagebox.showerror("Network Error", error_msg); display_error_message(output_viewer, error_msg)
    except requests.exceptions.RequestException as e: error_msg = f"Network/API Error:\n{e}"; status_var.set("Network/API Error."); link_label.grid_remove(); messagebox.showerror("API Error", f"Failed to connect or get data from the API.\nCheck connection and token.\nError: {e}"); display_error_message(output_viewer, error_msg)
    except json.JSONDecodeError:
        error_msg = "Invalid JSON received from API."
        status_var.set("Error: Invalid JSON received.")
        link_label.grid_remove()
        try: error_msg += f"\n\nResponse Text:\n{response.text[:500]}..."
        except Exception: pass
        messagebox.showerror("Data Error", "The response from the API was not valid JSON.")
        display_error_message(output_viewer, error_msg)
    except Exception as e:
        error_msg = f"An unexpected error occurred:\n{type(e).__name__}: {e}"
        status_var.set("An unexpected error occurred.")
        link_label.grid_remove()
        messagebox.showerror("Error", error_msg)
        print(f"Traceback for unexpected error:\n", flush=True); traceback.print_exc()
        display_error_message(output_viewer, error_msg)


# --- GUI Setup ---
if __name__ == "__main__":
    window = tk.Tk()
    window.title("Hardcover Librarian Tool") # New Title
    window.geometry("850x700") # Adjusted size
    window.config(bg=COLOR_BACKGROUND)

    # Style Configuration (Same)
    style = ttk.Style()
    default_themes = ['clam', 'alt', 'default']
    selected_theme = None
    for theme in default_themes:
        if theme in style.theme_names():
            try: style.theme_use(theme); selected_theme = theme; print(f"Using ttk theme: {theme}"); break
            except tk.TclError: continue
    if not selected_theme: print("No suitable ttk theme found, using system default.")
    style.configure('.', background=COLOR_BACKGROUND, foreground=COLOR_FOREGROUND)
    style.configure('TFrame', background=COLOR_BACKGROUND)
    style.configure('TLabel', background=COLOR_BACKGROUND, foreground=COLOR_LABEL_FG, anchor=tk.W)
    style.configure('TNotebook', background=COLOR_BACKGROUND, borderwidth=0, tabposition='nw')
    style.configure('TNotebook.Tab', background=COLOR_WIDGET_BG, foreground=COLOR_LABEL_FG, padding=[10, 5], borderwidth=1)
    style.map('TNotebook.Tab', background=[('selected', COLOR_BACKGROUND), ('!selected', COLOR_WIDGET_BG)], foreground=[('selected', COLOR_HEADER_FG), ('!selected', COLOR_LABEL_FG)], expand=[('selected', [1, 1, 1, 0])])
    style.configure('TButton', background=COLOR_WIDGET_BG, foreground=COLOR_FOREGROUND, padding=8, font=tkFont.Font(weight='bold'))
    style.map('TButton', background=[('active', COLOR_ACCENT_FG), ('pressed', COLOR_ACCENT_FG)], foreground=[('active', COLOR_BACKGROUND), ('pressed', COLOR_BACKGROUND)])
    style.configure('TEntry', foreground=COLOR_WIDGET_FG, fieldbackground=COLOR_WIDGET_BG, insertcolor=COLOR_FOREGROUND, borderwidth=1, relief=tk.FLAT)
    style.map('TEntry', relief=[('focus', tk.SOLID)])

    # Main Notebook (Same)
    notebook = ttk.Notebook(window, style='TNotebook')
    notebook.pack(pady=10, padx=10, fill="both", expand=True)

    # Tab 1: Input & Controls (Same layout)
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
    status_label = ttk.Label(input_frame, textvariable=status_var, wraplength=750) # Wider wrap
    status_label.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
    link_font = tkFont.Font(family="Segoe UI", size=10, underline=True) # Consider generic font families later
    link_label = ttk.Label(input_frame, text="", style='TLabel', cursor="hand2", font=link_font)
    link_label.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(5, 10))
    link_label.grid_remove()

    # Tab 2: Output Viewer (Same layout)
    output_frame = ttk.Frame(notebook, padding="5", style='TFrame')
    notebook.add(output_frame, text='Output')
    output_frame.rowconfigure(0, weight=1)
    output_frame.columnconfigure(0, weight=1)
    output_viewer = scrolledtext.ScrolledText(
        output_frame, wrap=tk.WORD, state=tk.DISABLED, bg=COLOR_WIDGET_BG, fg=COLOR_FOREGROUND,
        insertbackground=COLOR_FOREGROUND, selectbackground=COLOR_ACCENT_FG, selectforeground=COLOR_BACKGROUND,
        borderwidth=0, highlightthickness=1, highlightbackground=COLOR_BACKGROUND, highlightcolor=COLOR_ACCENT_FG,
        padx=8, pady=8, font=("Consolas", 10) # Monospace preferred for alignment
    )
    output_viewer.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
    output_viewer.tag_bind("hyperlink", "<Enter>", on_link_enter)
    output_viewer.tag_bind("hyperlink", "<Leave>", on_link_leave)
    output_viewer.bind("<Button-1>", on_link_click)

    # --- Load Configuration on Startup ---
    # --- MODIFIED TO HANDLE BASE64 ---
    config = load_config()
    saved_token_b64 = config.get('bearer_token_b64', '')
    saved_token_plain = config.get('bearer_token', '') # Check for old plain text token
    final_token = ""

    if saved_token_b64:
        try:
            final_token = base64.b64decode(saved_token_b64).decode()
            print("Decoded token from bearer_token_b64.")
        except Exception as e:
            print(f"Error decoding saved token: {e}. Please re-enter token.")
            # Optionally clear the bad token from config here
    elif saved_token_plain: # If b64 fails or not present, check for old plain one
        print("Using plain text token from config (will be encoded on next save).")
        final_token = saved_token_plain

    if final_token:
        token_entry.insert(0, final_token)
        status_var.set("Loaded saved token. Enter Book ID.")
    else:
         status_var.set("Enter token and Book ID, then press 'Fetch Data'.")
    # --- End Base64 Load ---

    # --- Run the GUI ---
    window.mainloop()