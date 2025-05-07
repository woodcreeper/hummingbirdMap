import logging
import pandas as pd
import folium
from folium import FeatureGroup
from folium.plugins import MousePosition
from geopy.distance import geodesic
from flask import Flask, render_template_string
 @@ -20,19 +20,20 @@ def create_combined_species_map(df):
    mean_lat = df[['lat_dd_banding', 'lat_dd_recap_enc']].stack().mean()
    mean_lon = df[['lon_dd_banding', 'lon_dd_recap_enc']].stack().mean()

    fmap = folium.Map(
        location=[mean_lat, mean_lon],
        zoom_start=4,
        tiles=None  # Prevent default base layer from showing in LayerControl
    )

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri",
        name=None,
        control=False  # Don't include in LayerControl
    ).add_to(fmap)

    species_styles = {
        "Selasphorus rufus": {
            "banding_color": "#b35806",
 @@ -49,24 +50,19 @@ def create_combined_species_map(df):
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
 @@ -89,41 +85,88 @@ def create_combined_species_map(df):
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