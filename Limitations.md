Metadata Tool Limitations and Future Improvements

Known Limitations
1. Restricted Access to Audio Features
Spotify’s public API now limits access to advanced audio features (e.g. tempo, valence, energy) without elevated permissions. This means the tool cannot retrieve deeper musical descriptors unless connected to a paid developer account or using user-authenticated OAuth scopes.

Workaround:
Use external Music Information Retrieval (MIR) libraries such as librosa or Essentia to analyse local audio files, especially for royalty-free or public domain content.

2. Limited Access to Algorithmic and Editorial Playlists
Some Spotify-curated playlists (e.g. "Lo-Fi Beats", "Peaceful Piano") are classified as algorithmic or editorial, and cannot be accessed via the public API’s client credentials flow.

Known Workaround:
Create a public clone of the playlist (manually or via a user token) to generate a usable playlist ID. The tool will treat it as any other playlist input.

3. Artist-Level Genre Tags Only
Spotify assigns genre tags at the artist level, not track level. This can flatten genre diversity in cases where artists release music across multiple styles.

4. No OAuth Flow (User-Level Data Access)
The current version uses Spotify’s Client Credentials Flow, which limits access to user-specific data like saved tracks or listening history.

5. No Duplicate/Conflict Detection
The tool does not currently check for:

Duplicate tracks across playlists
Conflicting metadata entries
