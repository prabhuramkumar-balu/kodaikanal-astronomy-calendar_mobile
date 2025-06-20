import streamlit as st
from datetime import datetime, date
from calendar import monthcalendar, setfirstweekday, MONDAY
from astral.sun import sun
from astral.location import LocationInfo
import pytz
import ephem
import pandas as pd
import time

# Setup calendar start on Monday
setfirstweekday(MONDAY)
IST = pytz.timezone("Asia/Kolkata")

latitude = 10 + 13 / 60 + 50 / 3600
longitude = 77 + 28 / 60 + 7 / 3600
timezone = "Asia/Kolkata"
astral_city = LocationInfo("Kodaikanal", "India", timezone, latitude, longitude)

st.set_page_config(
    page_title="Kodaikanal Astronomy Calendar",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("📅 Kodaikanal Astronomy Calendar")
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, Planetary Rise/Set & Zenith Times (IST, 12-hour format)")

# Live IST date/time display container
time_display = st.empty()

# Function to display live time (updates every second)
def display_live_time():
    while True:
        now_ist = datetime.now(IST)
        time_display.markdown(f"**Current IST Date:** {now_ist.strftime('%d-%m-%Y')}  \n**Current IST Time:** {now_ist.strftime('%H:%M:%S')}")
        time.sleep(1)

# Run live time in background thread or use st_autorefresh below:
# Streamlit doesn't support while True loops directly in main thread,
# so instead we'll use st_autorefresh (built-in) for simple periodic rerun

count = st.experimental_get_query_params().get("refresh_count", [0])
refresh_count = int(count[0]) if count else 0

if refresh_count < 100000:  # limit refresh count to avoid infinite refresh forever
    st.experimental_set_query_params(refresh_count=refresh_count + 1)
    time_display.markdown(f"**Current IST Date:** {datetime.now(IST).strftime('%d-%m-%Y')}")
    time_display.markdown(f"**Current IST Time:** {datetime.now(IST).strftime('%H:%M:%S')}")
    st.experimental_rerun()

# === Calendar Input Widgets ===

year = st.number_input("Select Year", min_value=1900, max_value=2100, value=date.today().year)
months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
month_index_default = date.today().month - 1
month_name = st.selectbox("Select Month", months, index=month_index_default)
month_index = months.index(month_name) + 1
calendar_data = monthcalendar(year, month_index)

days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Handle selected day via session state or default to today if matching month/year
if 'selected_day' not in st.session_state:
    if year == date.today().year and month_index == date.today().month:
        st.session_state.selected_day = date.today()
    else:
        # First day in the month (non-zero)
        first_day = next((d for w in calendar_data for d in w if d != 0), 1)
        st.session_state.selected_day = date(year, month_index, first_day)

selected_day = st.session_state.selected_day

# Parse date from query params (when user clicks date links)
query_params = st.experimental_get_query_params()
q_year = query_params.get("year", [str(year)])[0]
q_month = query_params.get("month", [str(month_index)])[0]
q_day = query_params.get("selected_day", [str(selected_day.day)])[0]

try:
    q_year, q_month, q_day = int(q_year), int(q_month), int(q_day)
    if (q_year, q_month, q_day) != (selected_day.year, selected_day.month, selected_day.day):
        # Update selected day on session state and rerun to reflect changes
        st.session_state.selected_day = date(q_year, q_month, q_day)
        selected_day = st.session_state.selected_day
        st.experimental_rerun()
except Exception:
    pass  # ignore invalid query params

# === Render calendar as HTML table with clickable links ===
def render_calendar_html():
    today = date.today()
    html = """
    <style>
    .calendar { width: 100%; border-collapse: collapse; }
    .calendar th, .calendar td {
        border: 1px solid #ccc;
        text-align: center;
        padding: 0.6em;
        font-size: 0.95em;
        user-select: none;
    }
    .calendar th {
        background: #f0f0f0;
    }
    .selected {
        background-color: #a3d3a2;  /* green for selected date */
        font-weight: bold;
    }
    .today {
        background-color: #f28b82; /* red for today */
        font-weight: bold;
    }
    a {
        text-decoration: none;
        color: inherit;
        display: block;
        width: 100%;
        height: 100%;
    }
    </style>
    <table class='calendar'>
        <thead>
        <tr>""" + "".join(f"<th>{d}</th>" for d in days) + "</tr></thead><tbody>"

    for week in calendar_data:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td></td>"
            else:
                cell_date = date(year, month_index, day)
                classes = []
                if cell_date == selected_day:
                    classes.append("selected")
                if cell_date == today:
                    classes.append("today")
                class_attr = " ".join(classes)
                # Build query param links that update selected day, year and month (refresh page)
                html += f"""<td class="{class_attr}">
                    <a href="?selected_day={day}&year={year}&month={month_index}">{day}</a>
                </td>"""
        html += "</tr>"
    html += "</tbody></table>"
    return html

st.markdown(render_calendar_html(), unsafe_allow_html=True)

# === Astronomy Data Calculation & Display ===

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

def get_zenith(observer, body):
    try:
        transit = observer.next_transit(body)
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        transit = None
    return transit.datetime() if transit else "N/A"

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
    dt_local = datetime(selected_day.year, selected_day.month, selected_day.day, 12, 0, 0)
    dt_utc = pytz.timezone(timezone).localize(dt_local).astimezone(pytz.utc)

    sun_times = sun(astral_city.observer, date=dt_local, tzinfo=pytz.timezone(timezone))
    sunrise_ist = sun_times['sunrise'].strftime('%I:%M %p')
    sunset_ist = sun_times['sunset'].strftime('%I:%M %p')
    solar_noon_ist = sun_times['noon'].strftime('%I:%M %p')

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
    moon_zenith_utc = get_zenith(observer, moon)
    moon_zenith_ist = to_ist_12h(moon_zenith_utc)

    planets = {
        "Mercury": ephem.Mercury(),
        "Venus": ephem.Venus(),
        "Mars": ephem.Mars(),
        "Jupiter": ephem.Jupiter(),
        "Saturn": ephem.Saturn(),
    }

    planet_times = {}
    planet_zenith_times = {}
    for pname, pbody in planets.items():
        rise_dt, set_dt = get_rise_set(observer, pbody)
        zenith_dt = get_zenith(observer, pbody)
        planet_times[pname] = (to_ist_12h(rise_dt), to_ist_12h(set_dt))
        planet_zenith_times[pname] = to_ist_12h(zenith_dt)

    st.markdown("---")
    st.header(f"Astronomy Data for {dt_local.strftime('%A, %d %B %Y')}")

    with st.expander("🌅 Sun: Sunrise, Sunset & Zenith (Solar Noon)"):
        st.write(f"**Sunrise:** {sunrise_ist} IST")
        st.write(f"**Sunset:** {sunset_ist} IST")
        st.write(f"**Zenith (Solar Noon):** {solar_noon_ist} IST")

    with st.expander("🌙 Moon: Rise, Set, Zenith & Phase"):
        st.write(f"**Moonrise:** {moonrise_ist} IST")
        st.write(f"**Moonset:** {moonset_ist} IST")
        st.write(f"**Zenith (Transit):** {moon_zenith_ist} IST")
        st.write(f"**Moon Phase:** {moon_phase_desc} ({moon_phase:.1f}%)")

    with st.expander("🪐 Planets: Rise, Set & Zenith Times"):
        for pname in planets:
            rise_time, set_time = planet_times[pname]
            zenith_time = planet_zenith_times[pname]
            st.write(f"**{pname}:** Rise - {rise_time}, Set - {set_time}, Zenith - {zenith_time}")

except Exception as e:
    st.error(f"Error calculating astronomy data: {e}")
