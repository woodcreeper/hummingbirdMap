import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import pandas as pd
import folium
from folium import Popup
from folium.plugins import MousePosition
from shapely.geometry import LineString
from geopy.distance import geodesic
from flask import Flask, render_template_string
from datetime import datetime

app = Flask(__name__)

def create_species_map(df, species_name):
    logger.info(f"Requested species: {species_name}")
    logger.info(f"Available species in dataset: {df['species_scientific_name_banding'].unique()}")

    # Normalize and filter by species name
    species_name = species_name.strip().lower()
    df['species_scientific_name_banding'] = df['species_scientific_name_banding'].str.lower()
    df = df[df['species_scientific_name_banding'] == species_name]
    logger.info(f"Filtered dataset has {len(df)} rows.")

    # Convert date columns to datetime
    df['event_date_banding'] = pd.to_datetime(df['event_date_banding'], errors='coerce')
    df['event_date_recap_enc'] = pd.to_datetime(df['event_date_recap_enc'], errors='coerce')

    # Drop rows with missing coordinates
    df = df.dropna(subset=['lat_dd_banding', 'lon_dd_banding', 'lat_dd_recap_enc', 'lon_dd_recap_enc'])

    if df.empty:
        logger.warning("No data available after filtering. Returning blank map.")
        return "<p>No data available for the selected species.</p>"

    # Create map centered on mean location
    mean_lat = df[['lat_dd_banding', 'lat_dd_recap_enc']].stack().mean()
    mean_lon = df[['lon_dd_banding', 'lon_dd_recap_enc']].stack().mean()

    fmap = folium.Map(
        location=[mean_lat, mean_lon],
        zoom_start=4,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
    )

    for _, row in df.iterrows():
        banding_coords = (row['lat_dd_banding'], row['lon_dd_banding'])
        recap_coords = (row['lat_dd_recap_enc'], row['lon_dd_recap_enc'])
        distance_km = geodesic(banding_coords, recap_coords).km

        # Safely calculate duration
        if pd.notnull(row['event_date_banding']) and pd.notnull(row['event_date_recap_enc']):
            duration_days = (row['event_date_recap_enc'] - row['event_date_banding']).days
        else:
            duration_days = "NA"

        popup_html = f"""
        <b>Tag ID:</b> {row['original_band']}<br>
        <b>Banding:</b> {row['event_date_banding']} ({row['iso_country_banding']}, {row['iso_subdivision_banding']})<br>
        <b>Encounter:</b> {row['event_date_recap_enc']} ({row['iso_country_recap_enc']}, {row['iso_subdivision_recap_enc']})<br>
        <b>Distance:</b> {distance_km:.1f} km<br>
        <b>Duration:</b> {duration_days} days
        """

        # Add banding marker
        folium.CircleMarker(
            location=banding_coords,
            radius=4,
            color='lightblue',
            fill=True,
            fill_color='lightblue',
            fill_opacity=0.8,
            popup=folium.Popup(popup_html, max_width=400)
        ).add_to(fmap)

        # Add encounter marker
        folium.CircleMarker(
            location=recap_coords,
            radius=4,
            color='pink',
            fill=True,
            fill_color='pink',
            fill_opacity=0.8,
            popup=folium.Popup(popup_html, max_width=400)
        ).add_to(fmap)

        # Add interactive line (GeoJson) with highlight on hover
        folium.GeoJson(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [banding_coords[1], banding_coords[0]],
                        [recap_coords[1], recap_coords[0]]
                    ],
                },
                "properties": {
                    "popupContent": popup_html
                }
            },
            style_function=lambda feature: {
                "color": "white",
                "weight": 2,
                "opacity": 0.6,
            },
            highlight_function=lambda feature: {
                "color": "yellow",
                "weight": 4,
                "opacity": 1.0,
            },
            tooltip=folium.Tooltip("Click for details"),
            popup=folium.Popup(popup_html, max_width=400)
        ).add_to(fmap)

    MousePosition().add_to(fmap)
    return fmap.get_root().render()

@app.route("/<species>")
def map_view(species):
    df = pd.read_csv("filtered_hummingbird_recap_encounters_updated.csv", parse_dates=["event_date_banding", "event_date_recap_enc"])
    html_map = create_species_map(df, species)
    return render_template_string("""
        <html>
        <head><title>{{ species }} Map</title></head>
        <body>
            <h2>{{ species }} Banding and Encounter Map</h2>
            {{ html_map|safe }}
        </body>
        </html>
    """, species=species, html_map=html_map)

@app.route("/")
def index():
    return """
    <h2>Choose a species to view:</h2>
    <ul>
        <li><a href='/Selasphorus rufus'>Rufous Hummingbird</a></li>
        <li><a href='/Archilochus colubris'>Ruby-throated Hummingbird</a></li>
    </ul>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
