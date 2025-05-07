import logging
import pandas as pd
import folium
from folium import FeatureGroup
from folium.plugins import MousePosition
from geopy.distance import geodesic
from flask import Flask, render_template_string

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(_name__)

def create_combined_species_map(df):
    # Parse dates
    df['event_date_banding'] = pd.to_datetime(df['event_date_banding'], errors='coerce')
    df['event_date_recap_enc'] = pd.to_datetime(df['event_date_recap_enc'], errors='coerce')

    # Drop records with missing coordinates
    df = df.dropna(subset=['lat_dd_banding', 'lon_dd_banding', 'lat_dd_recap_enc', 'lon_dd_recap_enc'])

    # Set map center
    mean_lat = df[['lat_dd_banding', 'lat_dd_recap_enc']].stack().mean()
    mean_lon = df[['lon_dd_banding', 'lon_dd_recap_enc']].stack().mean()

    fmap = folium.Map(
        location=[mean_lat, mean_lon],
        zoom_start=4,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri"  # No layer name = won't appear in LayerControl
    )

    # Color settings
    species_styles = {
        "Selasphorus rufus": {
            "banding_color": "#b35806",
            "recap_color": "#f1a340",
            "track_color": "#fee0b6"
        },
        "Archilochus colubris": {
            "banding_color": "#542788",
            "recap_color": "#998ec3",
            "track_color": "#d8daeb"
        }
    }

    for species, styles in species_styles.items():
        group = FeatureGroup(name=species)
        species_df = df[df['species_scientific_name_banding'].str.lower() == species.lower()]

        for _, row in species_df.iterrows():
            banding_coords = (row['lat_dd_banding'], row['lon_dd_banding'])
            recap_coords = (row['lat_dd_recap_enc'], row['lon_dd_recap_enc'])
            distance_km = geodesic(banding_coords, recap_coords).km

            duration_days = (
                (row['event_date_recap_enc'] - row['event_date_banding']).days
                if pd.notnull(row['event_date_banding']) and pd.notnull(row['event_date_recap_enc'])
                else "NA"
            )

            popup_html = f"""
            <b>Tag ID:</b> {row['original_band']}<br>
            <b>Banding:</b> {row['event_date_banding']} ({row['iso_country_banding']}, {row['iso_subdivision_banding']})<br>
            <b>Encounter:</b> {row['event_date_recap_enc']} ({row['iso_country_recap_enc']}, {row['iso_subdivision_recap_enc']})<br>
            <b>Distance:</b> {distance_km:.1f} km<br>
            <b>Duration:</b> {duration_days} days
            """

            folium.CircleMarker(
                location=banding_coords,
                radius=4,
                color=styles["banding_color"],
                fill=True,
                fill_color=styles["banding_color"],
                fill_opacity=0.8,
                popup=folium.Popup(popup_html, max_width=400)
            ).add_to(group)

            folium.CircleMarker(
                location=recap_coords,
                radius=4,
                color=styles["recap_color"],
                fill=True,
                fill_color=styles["recap_color"],
                fill_opacity=0.8,
                popup=folium.Popup(popup_html, max_width=400)
            ).add_to(group)

            track_geojson = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [banding_coords[1], banding_coords[0]],
                        [recap_coords[1], recap_coords[0]]
                    ]
                },
                "properties": {
                    "popupContent": popup_html
                }
            }

            folium.GeoJson(
                data=track_geojson,
                style_function=lambda feature, color=styles["track_color"]: {
                    "color": color,
                    "weight": 2,
                    "opacity": 0.6
                },
                highlight_function=lambda feature: {
                    "color": "yellow",
                    "weight": 4,
                    "opacity": 1.0
                },
                tooltip=folium.Tooltip("Click for details"),
                popup=folium.Popup(popup_html, max_width=400)
            ).add_to(group)

        group.add_to(fmap)

    MousePosition().add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)

    return fmap.get_root().render()

@app.route("/")
def index():
    df = pd.read_csv("filtered_hummingbird_recap_encounters_updated.csv")
    html_map = create_combined_species_map(df)
    return render_template_string("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
            <title>Hummingbird Recapture Map</title>
            <style>
                html, body {
                    margin: 0;
                    padding: 0;
                    height: 100%;
                    width: 100%;
                    font-family: sans-serif;
                }
                #map {
                    height: 100vh;
                    width: 100%;
                }
                h2 {
                    padding: 10px;
                    text-align: center;
                }
            </style>
        </head>
        <body>
            <h2>Hummingbird Banding and Encounter Map</h2>
            <div id="map">{{ html_map|safe }}</div>
        </body>
        </html>
    """, html_map=html_map)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
