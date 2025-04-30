# Spotify Metadata Scraper and Visualisation Tool (Lo-fi Genre Study)

This Python-based tool was developed as part of a university dissertation exploring how metadata influences the visibility and discoverability of lo-fi artists on Spotify. It automates the collection, organisation, and visualisation of track- and artist-level metadata using Spotify’s Web API.

## API Access Notes
This tool uses Spotify's Client Credentials Flow and may be limited by API restrictions on playlist type or audio feature access. See /limitations.md for a breakdown of known issues and suggested workarounds.

## Features

- Extracts metadata from public Spotify playlists using playlist ID input
- Captures track-level information (title, release date, popularity score)
- Captures artist-level metadata (genre tags, follower count)
- Exports structured data to CSV for further analysis
- Generates scatter plots and word clouds from selected fields

## Example Use Case

This tool was used to analyse over 1,000 tracks from curated playlists by both Lo-fi Girl and Spotify. The visual outputs supported research into:
- Genre tag frequency and distribution
- Artist popularity vs metadata richness
- Platform-based differences in tagging structure

## Requirements

- Python 3.8+
- spotipy
- pandas
- matplotlib
- seaborn
- wordcloud
- openpyxl (if working with Excel files)

Install dependencies with:

```bash
pip install -r requirements.txt
