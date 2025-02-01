import streamlit as st
from streamlit_geolocation import streamlit_geolocation

st.title("User Geolocation App")

# Prompt user to press the button to get their location
location = streamlit_geolocation()

if location:
    st.write(f"Latitude: {location['latitude']}")
    st.write(f"Longitude: {location['longitude']}")
else:
    st.write("Press the button to get your location.")
