import os
import pandas as pd
import folium
from folium import Popup, FeatureGroup
from folium.plugins import MousePosition
from shapely.geometry import LineString
from geopy.distance import geodesic
from flask import Flask, render_template_string
from datetime import datetime

app = Flask(__name__)

def create_species_map(df, species_name):
    df = df[df['species_scientific_name_banding'] == species_name]

    if df.empty or df[['lat_dd_banding', 'lon_dd_banding', 'lat_dd_recap_enc', 'lon_dd_recap_enc']].isnull().any().any():
        return "<p>No valid location data available for this species.</p>"

    mean_lat = df[['lat_dd_banding', 'lat_dd_recap_enc']].stack().mean()
    mean_lon = df[['lon_dd_banding', 'lon_dd_recap_enc']].stack().mean()

    fmap = folium.Map(location=[mean_lat, mean_lon], zoom_start=4, tiles=None)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
        name="Esri Satellite",
        overlay=False,
        control=False
    ).add_to(fmap)

    for _, row in df.iterrows():
        if pd.isna(row['lat_dd_banding']) or pd.isna(row['lon_dd_banding']) or pd.isna(row['lat_dd_recap_enc']) or pd.isna(row['lon_dd_recap_enc']):
            continue  # Skip incomplete rows

        banding_coords = [row['lat_dd_banding'], row['lon_dd_banding']]
        recap_coords = [row['lat_dd_recap_enc'], row['lon_dd_recap_enc']]
        distance_km = geodesic(banding_coords, recap_coords).km

        try:
            band_date = datetime.strptime(row['event_date_banding'], "%Y-%m-%d")
            recap_date = datetime.strptime(row['event_date_recap_enc'], "%Y-%m-%d")
            duration_days = (recap_date - band_date).days
        except:
            duration_days = "NA"

        popup_html = (
            f"<b>Track Summary</b><br>"
            f"<b>Tag ID:</b> {row['original_band']}<br><br>"
            f"<b>Banding:</b><br>"
            f"Date: {row['event_date_banding']}<br>"
            f"Country: {row['iso_country_banding']}<br>"
            f"State: {row['iso_subdivision_banding']}<br><br>"
            f"<b>Encounter:</b><br>"
            f"Date: {row['event_date_recap_enc']}<br>"
            f"Country: {row['iso_country_recap_enc']}<br>"
            f"State: {row['iso_subdivision_recap_enc']}<br><br>"
            f"<b>Distance:</b> {distance_km:.1f} km<br>"
            f"<b>Duration:</b> {duration_days} days"
        )
        popup = folium.Popup(popup_html, max_width=400)

        feature_group = FeatureGroup(name=f"Track: {row['original_band']}")

        folium.PolyLine(
            locations=[banding_coords, recap_coords],
            color='white', weight=2, opacity=0.6,
            tooltip="Hover to highlight"
        ).add_to(feature_group)

        for coords in [banding_coords, recap_coords]:
            folium.CircleMarker(
                location=coords,
                radius=4,
                color='lightblue' if coords == banding_coords else 'pink',
                fill=True,
                fill_color='lightblue' if coords == banding_coords else 'pink',
                fill_opacity=0.8,
                popup=popup
            ).add_to(feature_group)

        feature_group.add_to(fmap)

    MousePosition().add_to(fmap)
    return fmap._repr_html_()

@app.route("/<species>")
def map_view(species):
    try:
        df = pd.read_csv("filtered_hummingbird_recap_encounters_updated.csv")
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
    except Exception as e:
        return f"<h2>Internal Server Error</h2><pre>{e}</pre>", 500

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
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
