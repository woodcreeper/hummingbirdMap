import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from shapely.geometry import Point, LineString
import pandas as pd

def plot_species_map(csv_path, species_name):
    # Load the filtered dataset
    df = pd.read_csv(csv_path)

    # Filter to selected species
    df = df[df['species_scientific_name_banding'] == species_name]

    # Create GeoDataFrames for banding and encounter locations
    geometry_banding = [Point(xy) for xy in zip(df['lon_dd_banding'], df['lat_dd_banding'])]
    geometry_encounter = [Point(xy) for xy in zip(df['lon_dd_recap_enc'], df['lat_dd_recap_enc'])]

    gdf_banding = gpd.GeoDataFrame(df, geometry=geometry_banding, crs='EPSG:4326')
    gdf_encounter = gpd.GeoDataFrame(df, geometry=geometry_encounter, crs='EPSG:4326')

    # Convert to Web Mercator for basemap compatibility
    gdf_banding = gdf_banding.to_crs(epsg=3857)
    gdf_encounter = gdf_encounter.to_crs(epsg=3857)

    # Define visual properties
    banding_color = 'yellow' if 'rufus' in species_name.lower() else 'cyan'
    encounter_color = 'magenta' if 'rufus' in species_name.lower() else 'lightblue'

    # Create the map
    fig, ax = plt.subplots(figsize=(14, 12))

    # Plot points
    gdf_banding.plot(ax=ax, marker='o', color=banding_color, markersize=50,
                     label=f'{species_name} - Banding', alpha=0.9, edgecolor='black')
    gdf_encounter.plot(ax=ax, marker='X', color=encounter_color, markersize=70,
                       label=f'{species_name} - Encounter', alpha=0.9, edgecolor='black')

    # Plot connecting lines
    for idx, row in gdf_banding.iterrows():
        banding_point = row.geometry
        encounter_point = gdf_encounter.geometry.iloc[idx]
        line = LineString([banding_point, encounter_point])
        ax.plot(*line.xy, color='white', linestyle='--', linewidth=1, alpha=0.6)

    # Add satellite basemap
    ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery)

    # Finalize plot
    ax.set_axis_off()
    ax.set_title(f'{species_name} Banding and Encounter Map')
    ax.legend()

    plt.show()

# Example usage:
# plot_species_map('filtered_hummingbird_recap_encounters_updated.csv', 'Selasphorus rufus')
# plot_species_map('filtered_hummingbird_recap_encounters_updated.csv', 'Archilochus colubris')
