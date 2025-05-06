import pandas as pd
import folium
from folium import Popup
from folium.plugins import MousePosition
from shapely.geometry import LineString
from geopy.distance import geodesic
from flask import Flask, render_template_string

app = Flask(__name__)

def create_species_map(df, species_name):
    df = df[df['species_scientific_name_banding'] == species_name]

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

        # Calculate distance
        distance_km = geodesic(banding_coords, recap_coords).km

        # Add banding marker with smaller CircleMarker
        folium.CircleMarker(
            location=banding_coords,
            radius=4,
            color='lightblue',
            fill=True,
            fill_color='lightblue',
            fill_opacity=0.8,
            tooltip=f"Banding\nID: {row['original_band']}\nDate: {row['event_date_banding']}"
        ).add_to(fmap)

        # Add encounter marker with smaller CircleMarker
        folium.CircleMarker(
            location=recap_coords,
            radius=4,
            color='pink',
            fill=True,
            fill_color='pink',
            fill_opacity=0.8,
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
    app.run(host='0.0.0.0', port=5000, debug=True)
