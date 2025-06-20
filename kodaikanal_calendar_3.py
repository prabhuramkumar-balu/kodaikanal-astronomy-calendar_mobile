import streamlit as st
from datetime import datetime, date
from calendar import monthrange
from astral.sun import sun
from astral.location import LocationInfo
import pytz
import ephem
import pandas as pd

# Setup
IST = pytz.timezone("Asia/Kolkata")

latitude = 10 + 13 / 60 + 50 / 3600
longitude = 77 + 28 / 60 + 7 / 3600
timezone = "Asia/Kolkata"
astral_city = LocationInfo("Kodaikanal", "India", timezone, latitude, longitude)

st.set_page_config(page_title="Kodaikanal Astronomy Calendar", layout="centered")

st.title("📅 Kodaikanal Astronomy Calendar")
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, and Planetary Rise/Set Times (IST, 12-hour format)")

# Inputs
year = st.number_input("Select Year", min_value=1900, max_value=2100, value=date.today().year)
months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
month_index = st.selectbox("Select Month", options=range(12), format_func=lambda i: months[i], index=date.today().month - 1) + 1

# Get number of days in the selected month/year
num_days = monthrange(year, month_index)[1]

# List days vertically
st.write("### Select Day")
day = st.radio(
    label="",
    options=list(range(1, num_days + 1)),
    index=date.today().day - 1 if (year, month_index) == (date.today().year, date.today().month) else 0
)

selected_date = date(year, month_index, day)

def to_ist_12h(dt_utc):
    if dt_utc == "N/A" or dt_utc is None:
        return "N/A"
    dt_utc = pytz.utc.localize(dt_utc)
    dt_ist = dt_utc.astimezone(IST)
    return dt_ist.strftime("%I:%M %p")

def get_rise_set(observer, body):
    try:
        rise = observer.next_rising(body)
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        rise = None
    try:
        set_ = observer.next_setting(body)
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        set_ = None
    return rise.datetime() if rise else "N/A", set_.datetime() if set_ else "N/A"

def describe_moon_phase(illum):
    if illum < 1:
        return "New Moon"
    elif illum < 50:
        return "Waxing Crescent"
    elif illum == 50:
        return "First Quarter"
    elif illum < 99:
        return "Waxing Gibbous"
    elif illum >= 99:
        return "Full Moon"
    elif illum > 50:
        return "Waning Gibbous"
    elif illum == 50:
        return "Last Quarter"
    else:
        return "Waning Crescent"

try:
    dt_local = datetime(selected_date.year, selected_date.month, selected_date.day, 12, 0, 0)
    dt_utc = pytz.timezone(timezone).localize(dt_local).astimezone(pytz.utc)

    sun_times = sun(astral_city.observer, date=dt_local, tzinfo=pytz.timezone(timezone))
    sunrise_ist = sun_times['sunrise'].strftime('%I:%M %p')
    sunset_ist = sun_times['sunset'].strftime('%I:%M %p')

    observer = ephem.Observer()
    observer.lat = str(latitude)
    observer.lon = str(longitude)
    observer.elevation = 2133
    observer.date = dt_utc

    moon = ephem.Moon(observer)
    moon_phase = moon.phase
    moon_phase_desc = describe_moon_phase(moon_phase)
    moonrise_utc, moonset_utc = get_rise_set(observer, moon)
    moonrise_ist = to_ist_12h(moonrise_utc)
    moonset_ist = to_ist_12h(moonset_utc)

    planets = {
        "Mercury": ephem.Mercury(),
        "Venus": ephem.Venus(),
        "Mars": ephem.Mars(),
        "Jupiter": ephem.Jupiter(),
        "Saturn": ephem.Saturn(),
    }

    planet_times = {}
    for pname, pbody in planets.items():
        rise_dt, set_dt = get_rise_set(observer, pbody)
        planet_times[pname] = (to_ist_12h(rise_dt), to_ist_12h(set_dt))

    st.markdown("---")
    st.header(f"Astronomy Data for {selected_date.strftime('%A, %d %B %Y')}")

    with st.expander("🌅 Sunrise & Sunset"):
        st.write(f"**Sunrise:** {sunrise_ist} IST")
        st.write(f"**Sunset:** {sunset_ist} IST")

    with st.expander("🌕 Moon Phase and Moonrise/Moonset"):
        st.write(f"Illumination: **{moon_phase:.1f}%** ({moon_phase_desc})")
        st.write(f"**Moonrise:** {moonrise_ist} IST")
        st.write(f"**Moonset:** {moonset_ist} IST")

    planet_df = pd.DataFrame.from_dict(
        planet_times,
        orient='index',
        columns=["Rise (IST)", "Set (IST)"]
    )
    with st.expander("🪐 Planet Rise/Set Times"):
        st.dataframe(planet_df, use_container_width=True)

except Exception as e:
    st.error(f"Error retrieving data: {e}")
