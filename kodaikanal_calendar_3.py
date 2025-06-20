import streamlit as st
from datetime import datetime, date
from calendar import monthcalendar, setfirstweekday, MONDAY
from astral.sun import sun
from astral.location import LocationInfo
import pytz
import ephem
import pandas as pd

# Setup
setfirstweekday(MONDAY)
IST = pytz.timezone("Asia/Kolkata")
today = date.today()

# Kodaikanal Location
latitude = 10 + 13 / 60 + 50 / 3600
longitude = 77 + 28 / 60 + 7 / 3600
timezone = "Asia/Kolkata"
astral_city = LocationInfo("Kodaikanal", "India", timezone, latitude, longitude)

# Page Config
st.set_page_config("Kodaikanal Astronomy Calendar", layout="centered")

st.title("📅 Kodaikanal Astronomy Calendar")
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, Planetary Rise/Set & Zenith Times (IST, 12-hour format)")

# Year and Month Select
year = st.number_input("Select Year", 1900, 2100, value=today.year)
months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
month_index = st.selectbox("Select Month", range(12), format_func=lambda i: months[i]) + 1

calendar_data = monthcalendar(year, month_index)
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Session state for selected day
if "selected_day" not in st.session_state:
    if year == today.year and month_index == today.month:
        st.session_state.selected_day = today.day
    else:
        st.session_state.selected_day = 1

# Handle query param on first load
query_day = st.query_params.get("day", [None])[0]
if query_day:
    try:
        st.session_state.selected_day = int(query_day)
    except:
        pass

# HTML Calendar Grid
def render_calendar_html():
    html = """
    <style>
        .calendar { width: 100%; border-collapse: collapse; font-size: 16px; }
        .calendar th, .calendar td {
            border: 1px solid #ccc;
            padding: 0.6em;
            text-align: center;
        }
        .calendar th {
            background: #f0f0f0;
        }
        .calendar td a {
            display: block;
            text-decoration: none;
            color: black;
        }
        .calendar .today {
            background-color: #e57373;
            color: white;
            font-weight: bold;
        }
        .calendar .selected {
            background-color: #a3d3a2;
            font-weight: bold;
        }
    </style>
    <table class="calendar">
        <tr>""" + "".join(f"<th>{d}</th>" for d in days) + "</tr>"
    
    for week in calendar_data:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td></td>"
            else:
                css_class = ""
                if (day == today.day and year == today.year and month_index == today.month):
                    css_class = "today"
                if day == st.session_state.selected_day:
                    css_class = "selected"
                html += f"""<td class="{css_class}">
                    <a href="?day={day}">{day}</a>
                </td>"""
        html += "</tr>"
    html += "</table>"
    return html

st.markdown(render_calendar_html(), unsafe_allow_html=True)

# Astronomy calculations
try:
    selected_date = date(year, month_index, st.session_state.selected_day)
except Exception:
    st.error("Invalid date selected.")
    st.stop()

dt_local = datetime(selected_date.year, selected_date.month, selected_date.day, 12, 0, 0)
dt_utc = pytz.timezone(timezone).localize(dt_local).astimezone(pytz.utc)

def to_ist_12h(dt_utc):
    if dt_utc in ["N/A", None]: return "N/A"
    dt_utc = pytz.utc.localize(dt_utc)
    dt_ist = dt_utc.astimezone(IST)
    return dt_ist.strftime("%I:%M %p")

def get_rise_set(observer, body):
    try: rise = observer.next_rising(body)
    except: rise = None
    try: set_ = observer.next_setting(body)
    except: set_ = None
    return rise.datetime() if rise else "N/A", set_.datetime() if set_ else "N/A"

def get_zenith(observer, body):
    try: zenith = observer.next_transit(body)
    except: zenith = None
    return zenith.datetime() if zenith else "N/A"

def describe_moon_phase(illum):
    if illum == 0: return "New Moon"
    elif illum < 50: return "Waxing Crescent"
    elif illum == 50: return "First Quarter"
    elif illum < 100: return "Waxing Gibbous"
    elif illum == 100: return "Full Moon"
    elif illum > 50: return "Waning Gibbous"
    elif illum == 50: return "Last Quarter"
    else: return "Waning Crescent"

# Astral sun times
try:
    sun_times = sun(astral_city.observer, date=selected_date, tzinfo=IST)
    sunrise = sun_times['sunrise'].strftime('%I:%M %p')
    sunset = sun_times['sunset'].strftime('%I:%M %p')
    solar_noon = sun_times['noon'].strftime('%I:%M %p')
except:
    sunrise = sunset = solar_noon = "N/A"

# Ephem observer
observer = ephem.Observer()
observer.lat = str(latitude)
observer.lon = str(longitude)
observer.elevation = 2133
observer.date = dt_utc

# Moon data
moon = ephem.Moon(observer)
moon_phase = moon.phase
moon_phase_desc = describe_moon_phase(moon_phase)
moonrise, moonset = get_rise_set(observer, moon)
moonzen = get_zenith(observer, moon)
moonrise_ist = to_ist_12h(moonrise)
moonset_ist = to_ist_12h(moonset)
moonzen_ist = to_ist_12h(moonzen)

# Planets
planets = {
    "Mercury": ephem.Mercury(),
    "Venus": ephem.Venus(),
    "Mars": ephem.Mars(),
    "Jupiter": ephem.Jupiter(),
    "Saturn": ephem.Saturn()
}
planet_data = {}
for name, body in planets.items():
    rise, set_ = get_rise_set(observer, body)
    zen = get_zenith(observer, body)
    planet_data[name] = (
        to_ist_12h(rise),
        to_ist_12h(set_),
        to_ist_12h(zen)
    )

# Display Data
st.markdown("---")
st.header(f"Astronomy Data for {selected_date.strftime('%A, %d %B %Y')}")

with st.expander("🌅 Sun"):
    st.write(f"**Sunrise:** {sunrise} IST")
    st.write(f"**Sunset:** {sunset} IST")
    st.write(f"**Solar Noon (Zenith):** {solar_noon} IST")

with st.expander("🌕 Moon"):
    st.write(f"**Phase:** {moon_phase:.1f}% ({moon_phase_desc})")
    st.write(f"**Moonrise:** {moonrise_ist} IST")
    st.write(f"**Moonset:** {moonset_ist} IST")
    st.write(f"**Moon Zenith:** {moonzen_ist} IST")

planet_df = pd.DataFrame.from_dict(
    planet_data,
    orient="index",
    columns=["Rise (IST)", "Set (IST)", "Zenith (IST)"]
)
with st.expander("🪐 Planetary Times"):
    st.dataframe(planet_df, use_container_width=True)
