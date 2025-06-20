import streamlit as st
from datetime import datetime, date
from calendar import monthcalendar, setfirstweekday, MONDAY
from astral.sun import sun
from astral.location import LocationInfo
import pytz
import ephem
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# Auto-refresh every second (1000 ms) for live clock update
st_autorefresh(interval=1000, key="refresh")

# Timezone
IST = pytz.timezone("Asia/Kolkata")

# Location for Kodaikanal
latitude = 10 + 13 / 60 + 50 / 3600
longitude = 77 + 28 / 60 + 7 / 3600
timezone = "Asia/Kolkata"
astral_city = LocationInfo("Kodaikanal", "India", timezone, latitude, longitude)

# Calendar setup
setfirstweekday(MONDAY)

# Streamlit page config
st.set_page_config(
    page_title="Kodaikanal Astronomy Calendar",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Title and Caption
st.title("📅 Kodaikanal Astronomy Calendar")
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, and Planetary Rise/Set Times (IST, 12-hour format)")

# Display live current date and time IST
now = datetime.now(IST)
st.markdown("### 🕒 Current Date and Time (IST)")
st.markdown(f"**{now.strftime('%d-%m-%Y')}**")
st.markdown(f"**{now.strftime('%I:%M:%S %p')}**")

# Inputs
year = st.number_input("Select Year", min_value=1900, max_value=2100, value=date.today().year, key="selected_year")

months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
month_name = st.selectbox("Select Month", months, index=date.today().month - 1, key="selected_month")

month_index = months.index(month_name) + 1

# Generate month calendar matrix
calendar_data = monthcalendar(year, month_index)
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Select a date (defaults to today if in the same month and year)
default_day = date.today().day if (date.today().year == year and date.today().month == month_index) else 1
selected_day = st.selectbox("Select Day", [d for week in calendar_data for d in week if d != 0], index=default_day - 1, key="selected_day")

# Function to convert UTC datetime to IST 12-hour format string
def to_ist_12h(dt_utc):
    if dt_utc == "N/A" or dt_utc is None:
        return "N/A"
    dt_utc = pytz.utc.localize(dt_utc)
    dt_ist = dt_utc.astimezone(IST)
    return dt_ist.strftime("%I:%M %p")

# Function to get rise and set times of a celestial body using ephem
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

# Function to get culmination (zenith) time of a celestial body using ephem
def get_culmination(observer, body):
    try:
        culmination = observer.next_transit(body)
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        culmination = None
    return culmination.datetime() if culmination else "N/A"

# Function to describe moon phase from illumination percentage
def describe_moon_phase(illum):
    if illum == 0:
        return "New Moon"
    elif illum < 50:
        return "Waxing Crescent"
    elif illum == 50:
        return "First Quarter"
    elif illum < 100:
        return "Waxing Gibbous"
    elif illum == 100:
        return "Full Moon"
    elif illum > 50:
        return "Waning Gibbous"
    elif illum == 50:
        return "Last Quarter"
    else:
        return "Waning Crescent"

# Prepare datetime for selected day
dt_local = datetime(year, month_index, selected_day, 12, 0, 0)
dt_utc = pytz.timezone(timezone).localize(dt_local).astimezone(pytz.utc)

# Display the calendar grid without buttons, just plain table with date numbers
def render_calendar_table():
    html = """
    <style>
    table.calendar {
        width: 100%;
        border-collapse: collapse;
        font-family: Arial, sans-serif;
        font-size: 0.95em;
    }
    table.calendar th, table.calendar td {
        border: 1px solid #ccc;
        text-align: center;
        padding: 0.6em;
        vertical-align: middle;
        user-select: none;
    }
    table.calendar th {
        background-color: #f0f0f0;
        font-weight: bold;
    }
    </style>
    <table class="calendar">
        <thead>
            <tr>""" + "".join(f"<th>{d}</th>" for d in days) + "</tr></thead><tbody>"
    for week in calendar_data:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td></td>"
            else:
                html += f"<td>{day}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html

# Show calendar grid
st.markdown("### Calendar")
st.markdown(render_calendar_table(), unsafe_allow_html=True)

# Astronomy data calculation

try:
    # Astral sun times
    sun_times = sun(astral_city.observer, date=dt_local, tzinfo=pytz.timezone(timezone))
    sunrise_ist = sun_times['sunrise'].strftime('%I:%M %p')
    sunset_ist = sun_times['sunset'].strftime('%I:%M %p')
    solar_noon_ist = sun_times['noon'].strftime('%I:%M %p')

    # Ephem observer
    observer = ephem.Observer()
    observer.lat = str(latitude)
    observer.lon = str(longitude)
    observer.elevation = 2133
    observer.date = dt_utc

    # Moon info
    moon = ephem.Moon(observer)
    moon_phase = moon.phase
    moon_phase_desc = describe_moon_phase(moon_phase)
    moonrise_utc, moonset_utc = get_rise_set(observer, moon)
    moonculmination_utc = get_culmination(observer, moon)
    moonrise_ist = to_ist_12h(moonrise_utc)
    moonset_ist = to_ist_12h(moonset_utc)
    moonculmination_ist = to_ist_12h(moonculmination_utc)

    # Planets info
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
        culminate_dt = get_culmination(observer, pbody)
        planet_times[pname] = {
            "Rise (IST)": to_ist_12h(rise_dt),
            "Set (IST)": to_ist_12h(set_dt),
            "Zenith (IST)": to_ist_12h(culminate_dt),
        }

    # Sun zenith time is solar noon from astral
except Exception as e:
    st.error(f"Error retrieving data: {e}")
    st.stop()

# Display Astronomy Data
st.markdown("---")
st.header(f"Astronomy Data for {dt_local.strftime('%A, %d %B %Y')}")

with st.expander("🌅 Sunrise, Solar Noon & Sunset"):
    st.write(f"**Sunrise:** {sunrise_ist} IST")
    st.write(f"**Solar Noon (Zenith):** {solar_noon_ist} IST")
    st.write(f"**Sunset:** {sunset_ist} IST")

with st.expander("🌕 Moon Phase and Moonrise/Moonset/Zenith"):
    st.write(f"Illumination: **{moon_phase:.1f}%** ({moon_phase_desc})")
    st.write(f"**Moonrise:** {moonrise_ist} IST")
    st.write(f"**Moonset:** {moonset_ist} IST")
    st.write(f"**Moon Zenith (Culmination):** {moonculmination_ist} IST")

planet_df = pd.DataFrame.from_dict(
    planet_times,
    orient='index',
    columns=["Rise (IST)", "Set (IST)", "Zenith (IST)"]
)

with st.expander("🪐 Planet Rise/Set/Zenith Times"):
    st.dataframe(planet_df, use_container_width=True)
