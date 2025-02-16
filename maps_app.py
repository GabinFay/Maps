import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
from dotenv import load_dotenv
import os
import time
from streamlit_geolocation import streamlit_geolocation
import math

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variables
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
if not API_KEY:
    st.error("GOOGLE_MAPS_API_KEY environment variable is not set.")
    st.stop()

st.title("Most Reviewed Places Finder")

# Initialize session state for place_query
if "previous_query" not in st.session_state:
    st.session_state.previous_query = ""

# Add a text input for the search box
place_query = st.text_input("Search for a city:", "")

# Function to fetch place details using Google Places API
def fetch_place_details(query):
    search_url = (
        f"https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        f"?input={query}&inputtype=textquery&fields=geometry,name&key={API_KEY}"
    )
    response = requests.get(search_url)
    if response.status_code == 200:
        candidates = response.json().get('candidates', [])
        if candidates:
            return candidates[0]  # Return the first matching place
    return None

# Initialize session state
if "marker_location" not in st.session_state:
    st.session_state.marker_location = [48.8566, 2.3522]  # Default to Paris
    st.session_state.zoom = 12

# Add to session state initialization at the top
if "search_results_map" not in st.session_state:
    st.session_state.search_results_map = None
if "search_results" not in st.session_state:
    st.session_state.search_results = []

# Handle the search query only when it changes
if place_query and place_query != st.session_state.previous_query:
    print("place query", place_query)
    place_details = fetch_place_details(place_query)
    if place_details:
        location = place_details['geometry']['location']
        st.session_state.marker_location = [location['lat'], location['lng']]
        st.session_state.zoom = 15  # Zoom in closer to the selected place
        st.success(f"Found: {place_details['name']}")
    else:
        st.error("Place not found. Please try a different query.")
    # Update the previous query
    st.session_state.previous_query = place_query

# Search settings
st.subheader("Search Settings")

PLACE_TYPES = [
    'restaurant', 'bar', 'cafe', 'tourist_attraction', 'historical_landmark',
    'museum', 'night_club', 'bakery', 'library', 'art_gallery', 'lodging',
    'church', 'park', 'supermarket', 'atm', 'tourism', 'pharmacy',
    'clothing_store', 'electronics_store', 'parking', 'movie_theater',
    'post_office', 'shoe_store', 'shopping_mall', 'stadium', 'store'
]
selected_place_type = st.selectbox("Place Type", options=PLACE_TYPES, index=0)

# Replace the columns and slider with just the number input
search_radius = st.number_input("Search Radius (meters)", min_value=100, value=500, help="Enter a radius in meters")

# Add grid search option after the search radius input
grid_search_enabled = st.checkbox("Enable Grid Search", value=False, help="Enable this to search in a grid pattern for better coverage")

# Add this after the grid search checkbox
fetch_all_pages = st.checkbox("Fetch all available results", value=False, help="When enabled, fetches up to 60 results (3 pages). When disabled, fetches only 20 results (1 page).")

# Calculate appropriate zoom level based on radius
# These values are approximate and can be adjusted
if search_radius <= 200:
    st.session_state.zoom = 15
elif search_radius <= 500:
    st.session_state.zoom = 14
elif search_radius <= 1000:
    st.session_state.zoom = 12
elif search_radius <= 7500:
    st.session_state.zoom = 11
elif search_radius <= 50000:
    st.session_state.zoom = 10
else:
    st.session_state.zoom = 9

# Add geolocation button
col1, col2 = st.columns([1, 3])
with col1:
    location = streamlit_geolocation()
with col2:
    st.markdown("👈 Click to use your current location")

if location and location['latitude'] is not None and location['longitude'] is not None:
    st.session_state.marker_location = [location['latitude'], location['longitude']]
    st.session_state.zoom = 15

# Add this function before the fetch_nearby_places function
def calculate_grid_points(center, radius):
    lat, lng = center
    # Calculate offsets for a 3x3 grid
    # Adjust spacing to 0.4 (up from 0.33) for slightly larger coverage
    lat_offset = (radius * 0.00001) * 0.5  # Increased spacing
    lng_offset = (radius * 0.00001 / math.cos(math.radians(lat))) * 0.5  # Adjusted for longitude distortion
    
    grid_points = []
    for i in range(-1, 2):  # -1, 0, 1
        for j in range(-1, 2):  # -1, 0, 1
            grid_points.append([
                lat + (i * lat_offset),
                lng + (j * lng_offset)
            ])
    return grid_points

# Update the create_base_map function
def create_base_map():
    m = folium.Map(location=st.session_state.marker_location, zoom_start=st.session_state.zoom)
    
    # Add center marker
    folium.Marker(
        location=st.session_state.marker_location,
        draggable=False,
        icon=folium.Icon(color="red", icon="info-sign"),
    ).add_to(m)
    
    if grid_search_enabled:
        # Display 3x3 grid
        grid_points = calculate_grid_points(st.session_state.marker_location, search_radius)
        
        # Create grid cells with slightly larger radius
        for point in grid_points:
            folium.Circle(
                location=point,
                radius=search_radius * 0.5,  # Increased from 0.33 to 0.4
                color="blue",
                fill=True,
                fillColor="blue",
                fillOpacity=0.1
            ).add_to(m)
    else:
        # Display single circle
        folium.Circle(
            location=st.session_state.marker_location,
            radius=search_radius,
            color="blue",
            fill=True,
            fillColor="blue",
            fillOpacity=0.1
        ).add_to(m)
    
    return m

# Function to add place markers to the map
def add_place_markers(places, map_obj, limit=None):
    # Sort places by review count to identify top 3
    sorted_places = sorted(places, key=lambda x: x.get('user_ratings_total', 0), reverse=True)
    
    for i, place in enumerate(sorted_places):
        if 'geometry' in place and 'location' in place['geometry']:
            location = place['geometry']['location']
            
            # Create the popup HTML with the place name, reviews, and Google Maps link
            google_maps_link = (
                f"https://www.google.com/maps/search/?api=1&"
                f"query={place['name'].replace(' ', '+')}&"
                f"query_place_id={place['place_id']}"
            )
            
            popup_html = f"""
                <div style='font-family: Arial, sans-serif;'>
                    <h4><a href='{google_maps_link}' target='_blank'>{place.get('name', 'N/A')}</a></h4>
                    <p>Reviews: {place.get('user_ratings_total', 0)}</p>
                </div>
            """
            
            # Create a Popup object with the HTML content
            popup = folium.Popup(folium.Html(popup_html, script=True), max_width=300)
            
            # Set color based on ranking
            if i == 0:
                color = 'yellow'  # First place
            elif i == 1:
                color = 'green'   # Second place
            elif i == 2:
                color = 'orange'  # Third place
            else:
                color = 'blue'    # All other places
            
            # Create a marker with both the popup and a tooltip (visible on hover)
            tooltip = f"{place.get('name', 'N/A')} - {place.get('user_ratings_total', 0)} reviews"
            folium.Marker(
                location=[location['lat'], location['lng']],
                popup=popup,
                tooltip=tooltip,
                icon=folium.Icon(color=color)
            ).add_to(map_obj)

# Initialize the map
m = create_base_map()

# Display coordinates
st.write(f"Selected Coordinates: {st.session_state.marker_location}")

# Render the map
map_data = st_folium(m, width=300, height=300)

# Initialize session state for map clicks
if "map_clicked" not in st.session_state:
    st.session_state.map_clicked = False

# Map click handling
if map_data.get("last_clicked") and not st.session_state.map_clicked:
    print("last clicked", map_data["last_clicked"])
    lat, lng = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
    if [lat, lng] != st.session_state.marker_location:  # Only rerun if location actually changed
        st.session_state.marker_location = [lat, lng]
        st.session_state.zoom = map_data["zoom"]
        st.session_state.map_clicked = True
        print('rerunning')
        st.rerun()

# Reset map_clicked state after the rerun
if st.session_state.map_clicked:
    st.session_state.map_clicked = False

def fetch_nearby_places(location, radius=2500, place_type='restaurant'):
    all_results = []
    search_url = (
        f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        f"?location={location}&radius={radius}&type={place_type}&key={API_KEY}"
    )
    
    # Fetch first page
    response = requests.get(search_url)
    if response.status_code != 200:
        st.error("Error fetching data from Google Places API.")
        return []
    
    first_page = response.json()
    all_results.extend(first_page.get('results', []))
    
    # Only fetch additional pages if the option is enabled
    if fetch_all_pages:
        # Fetch up to 2 more pages using pagetoken
        for _ in range(2):  # Try to get 2 more pages
            next_page_token = first_page.get('next_page_token')
            if not next_page_token:
                break
                
            # Wait for token to become valid (Google requires a delay)
            time.sleep(2)
            
            next_page_url = f"{search_url}&pagetoken={next_page_token}"
            response = requests.get(next_page_url)
            if response.status_code == 200:
                first_page = response.json()
                all_results.extend(first_page.get('results', []))
    
    # Debugging: Print the latitude and longitude of each fetched place
    for place in all_results:
        if 'geometry' in place and 'location' in place['geometry']:
            location = place['geometry']['location']
            print(f"Fetched place: {place.get('name', 'N/A')} at "
                  f"Latitude: {location.get('lat', 'N/A')}, "
                  f"Longitude: {location.get('lng', 'N/A')}")
    
    return all_results


# Add this after the existing place types list
MAIN_PLACE_TYPES = [
    'restaurant', 'bar', 'cafe', 'tourist_attraction', 'museum'
]

PLACE_TYPE_COLORS = {
    'restaurant': '#FF0000',     # Red
    'bar': '#FFA500',           # Orange
    'cafe': '#8B4513',          # Brown
    'tourist_attraction': '#4169E1',  # Royal Blue
    'museum': '#800080',        # Purple
    'shopping_mall': '#FFD700',  # Gold
    'park': '#228B22',          # Forest Green
    'night_club': '#FF1493',    # Deep Pink
    'art_gallery': '#4B0082',   # Indigo
    'other': '#808080'          # Gray for uncategorized places
}

# Update the Typeless Search button section
if st.button("Typeless Search"):
    location_str = f"{st.session_state.marker_location[0]},{st.session_state.marker_location[1]}"
    all_results = []
    seen_place_ids = set()
    
    with st.spinner('Searching across main categories... This may take a few seconds...'):
        if grid_search_enabled:
            grid_points = calculate_grid_points(st.session_state.marker_location, search_radius)
            for point in grid_points:
                loc_str = f"{point[0]},{point[1]}"
                for place_type in MAIN_PLACE_TYPES:
                    results = fetch_nearby_places(loc_str, radius=search_radius, place_type=place_type)
                    for result in results:
                        if result.get('place_id') not in seen_place_ids:
                            seen_place_ids.add(result.get('place_id'))
                            result['category'] = place_type
                            all_results.append(result)
        else:
            for place_type in MAIN_PLACE_TYPES:
                results = fetch_nearby_places(location_str, radius=search_radius, place_type=place_type)
                for result in results:
                    if result.get('place_id') not in seen_place_ids:
                        seen_place_ids.add(result.get('place_id'))
                        result['category'] = place_type
                        all_results.append(result)

        if all_results:
            # Sort results by review count
            sorted_results = sorted(all_results, key=lambda x: x.get('user_ratings_total', 0), reverse=True)
            
            # Store results in session state
            st.session_state.search_results = sorted_results
            
            # Create results map
            results_map = create_base_map()
            add_place_markers(sorted_results, results_map)
            st.session_state.search_results_map = results_map

# Move the single place type search here, right after typeless search
if st.button(f"Search {selected_place_type.replace('_', ' ').title()}s"):
    location_str = f"{st.session_state.marker_location[0]},{st.session_state.marker_location[1]}"
    
    with st.spinner(f'Searching for {selected_place_type}s...'):
        results = fetch_nearby_places(location_str, radius=search_radius, place_type=selected_place_type)
        
        if results:
            sorted_results = sorted(results, key=lambda x: x.get('user_ratings_total', 0), reverse=True)
            st.session_state.search_results = sorted_results
            results_map = create_base_map()
            add_place_markers(sorted_results, results_map)
            st.session_state.search_results_map = results_map

# Display the results map right after the search buttons
if st.session_state.search_results_map:
    st.subheader("Results Map")
    st_folium(st.session_state.search_results_map, width=700, height=500)

# Display results list last
if st.session_state.search_results:
    st.subheader("Places Found:")
    for place in st.session_state.search_results:
        st.markdown(f"### {place.get('name')}")
        st.write(f"**Rating:** {place.get('rating', 'N/A')} stars")
        st.write(f"**Reviews:** {place.get('user_ratings_total', 0)}")
        if 'place_id' in place:
            google_maps_link = (
                f"https://www.google.com/maps/search/?api=1&"
                f"query={place['name'].replace(' ', '+')}&"
                f"query_place_id={place['place_id']}"
            )
            st.markdown(f"[View on Google Maps]({google_maps_link})")
        st.write("---")
