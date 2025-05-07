import logging
import pandas as pd
import folium
from folium import FeatureGroup, Marker
from folium.plugins import MousePosition
from geopy.distance import geodesic
from flask import Flask, render_template_string

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def create_combined_species_map(df):
    df['event_date_banding'] = pd.to_datetime(df['event_date_banding'], errors='coerce')
    df['event_date_recap_enc'] = pd.to_datetime(df['event_date_recap_enc'], errors='coerce')

    df = df.dropna(subset=['lat_dd_banding', 'lon_dd_banding', 'lat_dd_recap_enc', 'lon_dd_recap_enc'])

    mean_lat = df[['lat_dd_banding', 'lat_dd_recap_enc']].stack().mean()
    mean_lon = df[['lon_dd_banding', 'lon_dd_recap_enc']].stack().mean()

    fmap = folium.Map(location=[mean_lat, mean_lon], zoom_start=4, tiles=None)

    # Add Esri base tiles without putting it in LayerControl
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri",
        name=None,
        control=False
    ).add_to(fmap)

    # Identify multi-encounter tag IDs
    tag_counts = df['original_band'].value_counts()
    multi_encounter_tags = tag_counts[tag_counts > 1].index

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
        multi_df = species_df[species_df['original_band'].isin(multi_encounter_tags)]
        single_df = species_df[~species_df['original_band'].isin(multi_encounter_tags)]

        # --- SINGLE-ENCOUNTER ENTRIES ---
        for _, row in single_df.iterrows():
            banding_coords = (row['lat_dd_banding'], row['lon_dd_banding'])
            recap_coords = (row['lat_dd_recap_enc'], row['lon_dd_recap_enc'])

            popup_html = f"""
            <b>Tag ID:</b> {row['original_band']}<br>
            <b>Banding:</b> {row['event_date_banding']} ({row['iso_country_banding']}, {row['iso_subdivision_banding']})<br>
            <b>Encounter:</b> {row['event_date_recap_enc']} ({row['iso_country_recap_enc']}, {row['iso_subdivision_recap_enc']})<br>
            <b>Distance:</b> {geodesic(banding_coords, recap_coords).km:.1f} km
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

            folium.PolyLine(
                [banding_coords, recap_coords],
                color=styles["track_color"],
                weight=2,
                opacity=0.6,
                popup=folium.Popup(popup_html, max_width=400)
            ).add_to(group)

        # --- MULTI-ENCOUNTER ENTRIES ---
        for tag, group_df in multi_df.groupby("original_band"):
            points = []
            popup_lines = []
            group_df = group_df.sort_values("event_date_recap_enc")

            for _, row in group_df.iterrows():
                banding_coords = (row['lat_dd_banding'], row['lon_dd_banding'])
                recap_coords = (row['lat_dd_recap_enc'], row['lon_dd_recap_enc'])

                # Add banding and recap points (as stars)
                Marker(
                    location=banding_coords,
                    icon=folium.Icon(color='white', icon='star', prefix='fa'),
                    popup=folium.Popup(f"Multi-encounter tag: {tag}<br>Banding at {row['iso_subdivision_banding']}", max_width=400)
                ).add_to(group)

                Marker(
                    location=recap_coords,
                    icon=folium.Icon(color='white', icon='star', prefix='fa'),
                    popup=folium.Popup(f"Multi-encounter tag: {tag}<br>Recap at {row['iso_subdivision_recap_enc']}", max_width=400)
                ).add_to(group)

                # Collect sequential points
                points.append(banding_coords)
                points.append(recap_coords)

                popup_lines.append(
                    f"{row['event_date_banding'].date() if pd.notnull(row['event_date_banding']) else ''} → "
                    f"{row['event_date_recap_enc'].date() if pd.notnull(row['event_date_recap_enc']) else ''}: "
                    f"{row['iso_subdivision_banding']} → {row['iso_subdivision_recap_enc']}"
                )

            # Remove duplicates in point list
            unique_points = []
            [unique_points.append(p) for p in points if p not in unique_points]

            # Line and summary popup
            folium.PolyLine(
                locations=unique_points,
                color=styles["track_color"],
                weight=3,
                opacity=0.9,
                popup=folium.Popup("<br>".join(popup_lines), max_width=400)
            ).add_to(group)

        group.add_to(fmap)

    MousePosition().add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)

    # Add floating legend
    legend_html = """
    <div style="
        position: fixed;
        bottom: 20px;
        left: 20px;
        z-index: 1000;
        background-color: white;
        border:2px solid #ccc;
        padding: 10px;
        font-size: 13px;
        box-shadow: 0 0 15px rgba(0,0,0,0.2);
    ">
    <b>Legend</b><br>
    <span style="color:#b35806;">●</span> RUHU Banding<br>
    <span style="color:#f1a340;">●</span> RUHU Encounter<br>
    <span style="color:#542788;">●</span> RTHU Banding<br>
    <span style="color:#998ec3;">●</span> RTHU Encounter<br>
    <span style="color:black;">★</span> Multi-encounter Tag<br>
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(legend_html))

    return fmap.get_root().render()

@app.route("/")
def index():
    df = pd.read_csv("filtered_hummingbird_recap_encounters_updated.csv")
    html_map = create_combined_species_map(df)
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Hummingbird Map</title>
            <style>
                html, body { margin:0; padding:0; height:100%; width:100%; font-family:sans-serif; }
                #map { height: 100vh; width: 100%; }
                h2 { padding: 10px; text-align: center; }
                .leaflet-control-layers {
                    max-width: 150px;
                    overflow-x: auto;
                    font-size: 14px;
                }
                .leaflet-control-layers-expanded {
                    width: auto !important;
                    max-width: 90vw !important;
                    white-space: nowrap;
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
