import os
import glob
import csv
import threading
from datetime import datetime
from collections import defaultdict, Counter

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

import pandas as pd
import numpy as np

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext

from ttkthemes import ThemedTk

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for image saving
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from wordcloud import WordCloud

# Global variable to store uploaded Excel file paths (if any)
uploaded_files = []

# ----------------------- METADATA APP FUNCTIONS ----------------------- #
CLIENT_ID = "206d3b06da384ae480d33a632e22a2a8" ## 'your-client-id'
CLIENT_SECRET = ##'Your client secret'

def authenticate_spotify():
    client_credentials_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    return spotipy.Spotify(client_credentials_manager=client_credentials_manager)

METADATA_FIELDS = [
    "track_name", "album_name", "release_date", "duration_ms",
    "track_spotify_url", "artist_name", "genres", "popularity",
    "followers", "artist_spotify_url"
]

def get_playlist_tracks(sp, playlist_id, progress_callback):
    tracks = []
    try:
        results = sp.playlist_tracks(playlist_id)
    except spotipy.exceptions.SpotifyException as e:
        messagebox.showerror("Spotify API Error", f"An error occurred: {e}")
        return []
    total = results.get('total', 0)
    count = 0
    while results:
        for item in results['items']:
            track = item.get('track')
            if track:
                track_data = {
                    "track_name": track.get("name", "N/A"),
                    "album_name": track.get("album", {}).get("name", "N/A"),
                    "release_date": track.get("album", {}).get("release_date", "N/A"),
                    "duration_ms": track.get("duration_ms", "N/A"),
                    "track_spotify_url": track.get("external_urls", {}).get("spotify", "N/A"),
                    "artists": [artist["id"] for artist in track.get("artists", [])]
                }
                tracks.append(track_data)
            count += 1
            progress_callback(count, total)
        results = sp.next(results) if results.get('next') else None
    return tracks

def get_artist_metadata(sp, artist_ids):
    artists_data = {}
    batch_size = 50
    for i in range(0, len(artist_ids), batch_size):
        batch = artist_ids[i:i + batch_size]
        try:
            response = sp.artists(batch).get("artists", [])
            for artist in response:
                artists_data[artist["id"]] = {
                    "artist_name": artist.get("name", "N/A"),
                    "genres": ", ".join(artist.get("genres", [])),
                    "popularity": artist.get("popularity", "N/A"),
                    "followers": artist.get("followers", {}).get("total", 0),
                    "artist_spotify_url": artist.get("external_urls", {}).get("spotify", "N/A")
                }
        except Exception as e:
            print(f"Error fetching artist data: {e}")
    return artists_data

def collect_metadata(sp, playlist_id, progress_callback):
    tracks = get_playlist_tracks(sp, playlist_id, progress_callback)
    unique_artist_ids = {artist_id for track in tracks for artist_id in track["artists"]}
    artist_metadata = get_artist_metadata(sp, list(unique_artist_ids))
    final_data = []
    for track in tracks:
        for artist_id in track["artists"]:
            if artist_id in artist_metadata:
                final_data.append({
                    "track_name": track["track_name"],
                    "album_name": track["album_name"],
                    "release_date": track["release_date"],
                    "duration_ms": track["duration_ms"],
                    "track_spotify_url": track["track_spotify_url"],
                    "artist_name": artist_metadata[artist_id]["artist_name"],
                    "genres": artist_metadata[artist_id]["genres"],
                    "popularity": artist_metadata[artist_id]["popularity"],
                    "followers": artist_metadata[artist_id]["followers"],
                    "artist_spotify_url": artist_metadata[artist_id]["artist_spotify_url"]
                })
    return final_data

def export_to_csv(data, filename, playlist_name, playlist_owner):
    if not data:
        messagebox.showerror("Error", "No data to export.")
        return
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Playlist Name", playlist_name])
        writer.writerow(["Playlist Owner", playlist_owner])
        writer.writerow(["Exported On", datetime.now().strftime("%Y-%m-%d")])
        writer.writerow([])
        writer.writerow(METADATA_FIELDS)
        for row in data:
            writer.writerow([row[field] for field in METADATA_FIELDS])
    messagebox.showinfo("Export Complete", f"Data successfully exported to:\n{filename}")

# ----------------------- DATA ANALYSIS FUNCTIONS ----------------------- #
def log_message(text_widget, message):
    text_widget.insert(tk.END, message + "\n")
    text_widget.see(tk.END)
    text_widget.update_idletasks()

def get_column_case_insensitive(df, col_name):
    for col in df.columns:
        if col.strip().lower() == col_name.strip().lower():
            return col
    return None

def load_data(folder_path, log_widget):
    global uploaded_files
    dfs = []
    if uploaded_files:
        log_message(log_widget, f"Loading {len(uploaded_files)} uploaded Excel file(s).")
        files_to_load = uploaded_files
    else:
        log_message(log_widget, f"Loading Excel files from folder: {folder_path}")
        files_to_load = glob.glob(os.path.join(folder_path, "*.xlsx"))
    
    if not files_to_load:
        log_message(log_widget, "No Excel files found.")
        return pd.DataFrame()
    
    for file in files_to_load:
        try:
            df = pd.read_excel(file, header=4, usecols="A:J")
            playlist_name = os.path.splitext(os.path.basename(file))[0]
            df["playlist"] = playlist_name
            dfs.append(df)
            log_message(log_widget, f"Loaded file: {os.path.basename(file)} (header row 5, columns A:J)")
        except Exception as e:
            log_message(log_widget, f"Error reading {file}: {e}")
    
    if dfs:
        combined_df = pd.concat(dfs, ignore_index=True)
        log_message(log_widget, f"Combined {len(dfs)} files into one DataFrame with {len(combined_df)} records.")
    else:
        combined_df = pd.DataFrame()
    return combined_df

def create_word_cloud(df, output_dir, log_widget, genre_col_name, exported_filename):
    log_message(log_widget, f"Creating word cloud using column: '{genre_col_name}'...")
    log_message(log_widget, "Available columns: " + str(list(df.columns)))
    selected_col = get_column_case_insensitive(df, genre_col_name)
    if selected_col is None:
        log_message(log_widget, f"No column matching '{genre_col_name}' found.")
        messagebox.showerror("Error", f"No column matching '{genre_col_name}' found.")
        return
    word_counts = Counter()
    word_playlist = defaultdict(Counter)
    for _, row in df.iterrows():
        playlist = row.get("playlist", "Unknown")
        cell = row[selected_col]
        if pd.isnull(cell):
            continue
        words = [w.strip() for w in str(cell).split(",") if w.strip()]
        for word in words:
            word_counts[word] += 1
            word_playlist[word][playlist] += 1
    if not word_counts:
        log_message(log_widget, f"The column '{selected_col}' is empty after processing.")
        messagebox.showerror("Error", f"The column '{selected_col}' is empty.")
        return
    word_to_playlist = {}
    for word, counts in word_playlist.items():
        most_common_playlist, _ = counts.most_common(1)[0]
        word_to_playlist[word] = most_common_playlist
    all_playlists = sorted(df["playlist"].dropna().unique())
    cmap = plt.get_cmap("tab10")
    playlist_colors = {pl: cmap(i % 10) for i, pl in enumerate(all_playlists)}
    def custom_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        pl = word_to_playlist.get(word, None)
        if pl and pl in playlist_colors:
            return matplotlib.colors.rgb2hex(playlist_colors[pl])
        return "black"
    wordcloud = WordCloud(regexp=r"[\w-]+", width=800, height=400, background_color="white")\
                    .generate_from_frequencies(word_counts)
    wordcloud.recolor(color_func=custom_color_func)
    plt.figure(figsize=(12, 6))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.title("Word Cloud (colored by Playlist)")
    handles = [Patch(color=matplotlib.colors.rgb2hex(playlist_colors[pl]), label=pl) for pl in all_playlists]
    plt.legend(handles=handles, title="Playlist", loc="center left", bbox_to_anchor=(1, 0.5))
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    exported_path = os.path.join(output_dir, exported_filename)
    plt.savefig(exported_path)
    plt.close()
    log_message(log_widget, f"Word cloud saved to: {exported_path}")

def count_tags(val):
    if pd.isnull(val) or str(val).strip() == "":
        return 0
    return len([tag.strip() for tag in str(val).split(",") if tag.strip()])

def transform_series(series, col_name):
    if "genre" in col_name.lower() or "tag" in col_name.lower():
        return series.apply(count_tags)
    numeric_series = pd.to_numeric(series, errors="coerce")
    if not numeric_series.isnull().all():
        return numeric_series
    datetime_series = pd.to_datetime(series, errors="coerce", format="%Y-%m-%d")  # <-- updated line
    return datetime_series


def create_scatter_chart(df, output_dir, log_widget, x_col_name, y_col_name, exported_filename, group_col="playlist"):
    log_message(log_widget, f"Creating scatter graph using X='{x_col_name}' and Y='{y_col_name}'...")
    log_message(log_widget, "Available columns: " + str(list(df.columns)))

    x_raw = df[get_column_case_insensitive(df, x_col_name)]
    y_raw = df[get_column_case_insensitive(df, y_col_name)]

    if x_raw is None:
        messagebox.showerror("Error", f"No column matching '{x_col_name}' found.")
        return
    if y_raw is None:
        messagebox.showerror("Error", f"No column matching '{y_col_name}' found.")
        return
    if group_col not in df.columns:
        messagebox.showerror("Error", f"No '{group_col}' column found in the data.")
        return

    # Transform data
    df["x_value"] = transform_series(x_raw, x_col_name)
    df["y_value"] = transform_series(y_raw, y_col_name)

    # Setup for plotting
    groups = df[group_col].dropna().unique()
    cmap = plt.get_cmap("tab10")
    group_colors = {pl: cmap(i % 10) for i, pl in enumerate(sorted(groups))}
    marker_styles = ['o', 's', '^', 'D', 'P', 'X', '*', 'v', '<', '>', 'H']

    plt.figure(figsize=(12, 8))

    for i, grp in enumerate(sorted(groups)):
        subset = df[df[group_col] == grp]
        marker = marker_styles[i % len(marker_styles)]
        plt.scatter(
            subset["x_value"], subset["y_value"],
            color=group_colors[grp],
            alpha=0.75,
            s=50,
            label=grp,
            edgecolors='w',
            linewidth=0.5,
            marker=marker
        )

    # Label formatting
    plt.xlabel(x_col_name)
    plt.ylabel(y_col_name)
    plt.title(f"Scatter Graph: {y_col_name} vs. {x_col_name}")
    plt.grid(True, linestyle='--', alpha=0.5)

    # Optional: fix x-axis ticks if it's number of tags or genres
    if "tag" in x_col_name.lower() or "genre" in x_col_name.lower():
        unique_vals = sorted(df["x_value"].dropna().unique())
        plt.xticks(unique_vals)

    # Add legend with colored patch markers
    handles = [Patch(color=matplotlib.colors.rgb2hex(group_colors[grp]), label=grp) for grp in sorted(groups)]
    plt.legend(handles=handles, title=group_col, bbox_to_anchor=(1.05, 1), loc="upper left")

    # Save graph
    plt.tight_layout()
    exported_path = os.path.join(output_dir, exported_filename)
    plt.savefig(exported_path, dpi=300)
    plt.close()

    log_message(log_widget, f"Scatter graph saved to: {exported_path}")


def process_and_visualize_word_cloud(folder_path, genre_col_name, wc_filename, log_widget):
    try:
        df = load_data(folder_path, log_widget)
        if df.empty:
            log_message(log_widget, "No data loaded. Exiting word cloud process.")
            return
        # Determine output directory based on file location.
        output_dir = os.path.join(os.path.dirname(folder_path), "output") if not uploaded_files else os.path.join(os.path.dirname(uploaded_files[0]), "output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            log_message(log_widget, f"Created output directory at: {output_dir}")
        create_word_cloud(df, output_dir, log_widget, genre_col_name, wc_filename)
        log_message(log_widget, "Word cloud processing complete. Check the output directory for the image.")
        messagebox.showinfo("Process Complete", "The word cloud image has been saved.")
    except Exception as e:
        log_message(log_widget, f"An error occurred (word cloud): {e}")
        messagebox.showerror("Error", str(e))

def process_and_visualize_scatter(folder_path, x_col_name, y_col_name, sg_filename, log_widget):
    try:
        df = load_data(folder_path, log_widget)
        if df.empty:
            log_message(log_widget, "No data loaded. Exiting scatter graph process.")
            return
        output_dir = os.path.join(os.path.dirname(folder_path), "output") if not uploaded_files else os.path.join(os.path.dirname(uploaded_files[0]), "output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            log_message(log_widget, f"Created output directory at: {output_dir}")
        create_scatter_chart(df, output_dir, log_widget, x_col_name, y_col_name, sg_filename)
        log_message(log_widget, "Scatter graph processing complete. Check the output directory for the image.")
        messagebox.showinfo("Process Complete", "The scatter graph image has been saved.")
    except Exception as e:
        log_message(log_widget, f"An error occurred (scatter graph): {e}")
        messagebox.showerror("Error", str(e))

def clear_log(log_widget):
    log_widget.delete(1.0, tk.END)

# ----------------------- UI LAUNCH FUNCTIONS ----------------------- #
def run_metadata_app():
    #Toplevel window for the metadata scraper using a themed window.
    meta_window = tk.Toplevel(root)
    meta_window.title("Spotify Playlist Metadata Scraper")
    meta_window.geometry("800x400")
    meta_window.resizable(False, False)
    meta_window.configure(bg="#121212")
    
    title_label = tk.Label(meta_window, text="Spotify Playlist Metadata Scraper", font=("Arial", 18, "bold"), fg="white", bg="#121212")
    title_label.pack(pady=10)
    
    frame = tk.Frame(meta_window, bg="#121212")
    frame.pack(pady=20)
    
    playlist_label = tk.Label(frame, text="Enter Playlist ID/URL:", font=("Arial", 12), bg="#121212", fg="white")
    playlist_label.pack(side="left", padx=5)
    
    playlist_entry = tk.Entry(frame, width=45, font=("Arial", 12), bg="#1E1E1E", fg="white", insertbackground="white")
    playlist_entry.pack(side="left", padx=10)
    
    progress_var = tk.IntVar(meta_window)
    progress_bar = ttk.Progressbar(meta_window, variable=progress_var, maximum=100, length=400, mode="determinate")
    progress_bar.pack(pady=(10, 0))
    
    status_label = tk.Label(meta_window, text="Ready", font=("Arial", 12), fg="white", bg="#121212")
    status_label.pack(pady=5)
    
    def update_progress(current, total):
        if total > 0:
            percentage = int((current / total) * 100)
            if 0 <= percentage <= 100:
                progress_var.set(percentage)
                progress_bar.update_idletasks()
    
    def run_scraper():
        playlist_id = playlist_entry.get().strip()
        if not playlist_id:
            messagebox.showerror("Error", "Please enter a playlist ID")
            return
        
        def scrape():
            try:
                status_label.config(text="Fetching data...", fg="#FFC107")
                scrape_button.config(state="disabled")
                progress_bar.start(10)
                
                sp = authenticate_spotify()
                playlist_info = sp.playlist(playlist_id)
                playlist_name = playlist_info["name"]
                playlist_owner = playlist_info["owner"]["display_name"]
                
                metadata = collect_metadata(sp, playlist_id, update_progress)
                
                progress_bar.stop()
                status_label.config(text="Ready", fg="#4CAF50")
                scrape_button.config(state="normal")
                
                timestamp = datetime.now().strftime("%Y-%m-%d")
                auto_filename = f"{playlist_name} - {playlist_owner} - {timestamp}.csv".replace("/", "_")
                
                save_folder = filedialog.askdirectory(title="Select folder to save CSV")
                if save_folder:
                    export_path = os.path.join(save_folder, auto_filename)
                    export_to_csv(metadata, export_path, playlist_name, playlist_owner)
            except Exception as e:
                progress_bar.stop()
                status_label.config(text="Error", fg="#F44336")
                scrape_button.config(state="normal")
                messagebox.showerror("Error", f"An error occurred: {e}")
        
        threading.Thread(target=scrape, daemon=True).start()
    
    scrape_button = tk.Button(frame, text="Scrape Metadata", command=run_scraper, font=("Arial", 12, "bold"), bg="#1DB954", fg="white", padx=10, pady=5)
    scrape_button.pack(side="right", padx=5)

def run_data_analysis_app():
    analysis_window = tk.Toplevel(root)
    analysis_window.title("Metadata Visualizer")
    analysis_window.geometry("800x700")
    
    # Create a menu bar for the analysis tool.
    menu_bar = tk.Menu(analysis_window)
    file_menu = tk.Menu(menu_bar, tearoff=0)
    
    def upload_files():
        global uploaded_files
        files = filedialog.askopenfilenames(title="Select Excel Files", filetypes=[("Excel files", "*.xlsx")])
        if files:
            uploaded_files = list(files)
            folder_entry.delete(0, tk.END)
            folder_entry.insert(0, "Uploaded Excel Files")
            log_message(log_text, f"Uploaded {len(uploaded_files)} file(s).")
    
    def browse_folder():
        global uploaded_files
        uploaded_files = []
        folder = filedialog.askdirectory(title="Select Folder Containing Excel Files")
        if folder:
            folder_entry.delete(0, tk.END)
            folder_entry.insert(0, folder)
            log_message(log_text, f"Selected folder: {folder}")
    
    file_menu.add_command(label="Upload Excel Files", command=upload_files)
    file_menu.add_command(label="Browse Folder", command=browse_folder)
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=analysis_window.destroy)
    menu_bar.add_cascade(label="File", menu=file_menu)
    analysis_window.config(menu=menu_bar)
    
    # Create a Notebook widget with two tabs.
    notebook = ttk.Notebook(analysis_window)
    notebook.pack(pady=10, fill="both", expand=True)
    
    # --- Word Cloud Tab ---
    word_cloud_frame = tk.Frame(notebook)
    notebook.add(word_cloud_frame, text="Word Cloud")
    
    folder_frame = tk.Frame(word_cloud_frame)
    folder_frame.pack(pady=10)
    tk.Label(folder_frame, text="Folder / Uploaded Files:", font=("Arial", 10)).pack(side="left", padx=5)
    folder_entry = tk.Entry(folder_frame, width=50, font=("Arial", 10))
    folder_entry.pack(side="left", padx=5)
    tk.Button(folder_frame, text="Browse", command=browse_folder).pack(side="left", padx=5)
    
    wc_config_frame = tk.Frame(word_cloud_frame)
    wc_config_frame.pack(pady=5)
    tk.Label(wc_config_frame, text="Genre Column:", font=("Arial", 10)).grid(row=0, column=0, padx=5, pady=2, sticky="e")
    wc_entry = tk.Entry(wc_config_frame, width=15, font=("Arial", 10))
    wc_entry.grid(row=0, column=1, padx=5, pady=2)
    wc_entry.insert(0, "genres")
    tk.Label(wc_config_frame, text="Export Filename:", font=("Arial", 10)).grid(row=0, column=2, padx=5, pady=2, sticky="e")
    wc_filename_entry = tk.Entry(wc_config_frame, width=15, font=("Arial", 10))
    wc_filename_entry.grid(row=0, column=3, padx=5, pady=2)
    wc_filename_entry.insert(0, "word_cloud.png")
    tk.Button(word_cloud_frame, text="Generate Word Cloud", font=("Arial", 10), 
              command=lambda: process_and_visualize_word_cloud(folder_entry.get(), wc_entry.get(), wc_filename_entry.get(), log_text)).pack(pady=10)
    
    # --- Scatter Graph Tab ---
    scatter_frame = tk.Frame(notebook)
    notebook.add(scatter_frame, text="Scatter Graph")
    
    folder_frame2 = tk.Frame(scatter_frame)
    folder_frame2.pack(pady=10)
    tk.Label(folder_frame2, text="Folder / Uploaded Files:", font=("Arial", 10)).pack(side="left", padx=5)
    folder_entry2 = tk.Entry(folder_frame2, width=50, font=("Arial", 10))
    folder_entry2.pack(side="left", padx=5)
    tk.Button(folder_frame2, text="Browse", command=browse_folder).pack(side="left", padx=5)
    
    sg_config_frame = tk.Frame(scatter_frame)
    sg_config_frame.pack(pady=5)
    tk.Label(sg_config_frame, text="X Axis Column:", font=("Arial", 10)).grid(row=0, column=0, padx=5, pady=2, sticky="e")
    x_entry = tk.Entry(sg_config_frame, width=15, font=("Arial", 10))
    x_entry.grid(row=0, column=1, padx=5, pady=2)
    x_entry.insert(0, "tags")
    tk.Label(sg_config_frame, text="Y Axis Column:", font=("Arial", 10)).grid(row=1, column=0, padx=5, pady=2, sticky="e")
    y_entry = tk.Entry(sg_config_frame, width=15, font=("Arial", 10))
    y_entry.grid(row=1, column=1, padx=5, pady=2)
    y_entry.insert(0, "followers")
    tk.Label(sg_config_frame, text="Export Filename:", font=("Arial", 10)).grid(row=2, column=0, padx=5, pady=2, sticky="e")
    sg_filename_entry = tk.Entry(sg_config_frame, width=15, font=("Arial", 10))
    sg_filename_entry.grid(row=2, column=1, padx=5, pady=2)
    sg_filename_entry.insert(0, "scatter_graph.png")
    tk.Button(scatter_frame, text="Generate Scatter Graph", font=("Arial", 10), 
              command=lambda: process_and_visualize_scatter(folder_entry2.get(), x_entry.get(), y_entry.get(), sg_filename_entry.get(), log_text)).pack(pady=10)
    
    # --- Log Area ---
    global log_text
    log_text = scrolledtext.ScrolledText(analysis_window, width=90, height=10, font=("Arial", 10), state="normal")
    log_text.pack(pady=10)
    tk.Button(analysis_window, text="Clear Log", font=("Arial", 10), command=lambda: clear_log(log_text)).pack(pady=5)

# ----------------------- HOME PAGE ----------------------- #
# A simple home page to launch each tool.
root = tk.Tk()
root.title("Spotify MIR Home")
root.geometry("700x200")
root.configure(bg="#1ED760")
root.resizable(False, False)
root.protocol("WM_DELETE_WINDOW", root.destroy)

home_label = tk.Label(root, text="Select a Tool to Launch", background="#1DB954",
                foreground="white",
                font=("Helvetica", 18, "bold"))
home_label.pack(pady=20)

button_frame = tk.Frame(root, bg="#1DB954")
button_frame.pack(pady=10)

meta_button = tk.Button(button_frame, text="Metadata Collector", font=("Arial", 12), width=20, command=run_metadata_app)
meta_button.grid(row=0, column=0, padx=10, pady=10)

analysis_button = tk.Button(button_frame, text="Data Analysis Tool", font=("Arial", 12), width=20, command=run_data_analysis_app)
analysis_button.grid(row=0, column=1, padx=10, pady=10)

root.mainloop()

