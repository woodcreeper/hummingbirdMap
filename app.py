import pandas as pd
import folium
import os
from folium import Popup
from folium.plugins import MousePosition
from shapely.geometry import LineString
from geopy.distance import geodesic
from flask import Flask, render_template_string

app = Flask(__name__)

def create_species_map(df, species_name):
    df = df[df['species_scientific_name_banding'] == species_name]

    # Handle case where no data exists for the species
    if df.empty or df[['lat_dd_banding', 'lon_dd_banding', 'lat_dd_recap_enc', 'lon_dd_recap_enc']].isnull().any().any():
        return "<p>No valid location data available for this species.</p>"

    mean_lat = df[['lat_dd_banding', 'lat_dd_recap_enc']].stack().mean()
    mean_lon = df[['lon_dd_banding', 'lon_dd_recap_enc']].stack().mean()

    fmap = folium.Map(location=[mean_lat, mean_lon], zoom_start=4, tiles='Esri.WorldImagery')
  

    for _, row in df.iterrows():
        banding_coords = (row['lat_dd_banding'], row['lon_dd_banding'])
        recap_coords = (row['lat_dd_recap_enc'], row['lon_dd_recap_enc'])

        # Calculate distance
        distance_km = geodesic(banding_coords, recap_coords).km

        # Add banding marker
        folium.Marker(
            location=banding_coords,
            icon=folium.Icon(color='lightblue', icon='info-sign'),
            tooltip=f"Banding\nID: {row['original_band']}\nDate: {row['event_date_banding']}"
        ).add_to(fmap)

        # Add encounter marker
        folium.Marker(
            location=recap_coords,
            icon=folium.Icon(color='pink', icon='flag'),
            tooltip=f"Encounter\nID: {row['original_band']}\nDate: {row['event_date_recap_enc']}"
        ).add_to(fmap)

        # Add line with distance popup
        line = folium.PolyLine(
            locations=[banding_coords, recap_coords],
            color='white', weight=2, opacity=0.6,
            tooltip=f"{distance_km:.1f} km"
        )
        line.add_to(fmap)

    # Add mouse position for reference
    MousePosition().add_to(fmap)
    return fmap._repr_html_()

@app.route("/<species>")
def map_view(species):
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
