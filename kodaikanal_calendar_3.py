import streamlit as st
from datetime import datetime, date
from calendar import monthcalendar, setfirstweekday, MONDAY
from astral.sun import sun
from astral.location import LocationInfo
import pytz
import ephem
import pandas as pd
import time

# Refresh every second for live clock update
if 'last_refresh' not in st.session_state:
    st.session_state['last_refresh'] = time.time()

if time.time() - st.session_state['last_refresh'] > 1:
    st.session_state['last_refresh'] = time.time()
    st.experimental_rerun()

# Calendar setup
setfirstweekday(MONDAY)
IST = pytz.timezone("Asia/Kolkata")

# Location for Kodaikanal
latitude = 10 + 13 / 60 + 50 / 3600
longitude = 77 + 28 / 60 + 7 / 3600
timezone = "Asia/Kolkata"
astral_city = LocationInfo("Kodaikanal", "India", timezone, latitude, longitude)

# UI setup
st.set_page_config(
    page_title="Kodaikanal Astronomy Calendar",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("📅 Kodaikanal Astronomy Calendar")
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, Planetary Rise/Set & Zenith Times (IST, 12-hour format)")

# Display current IST date and time, live updating
now_ist = datetime.now(IST)
st.write(f"**Current IST Date:** {now_ist.strftime('%d-%m-%Y')}")
st.write(f"**Current IST Time:** {now_ist.strftime('%H:%M:%S')}")

# Inputs
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

# Selected day state
if 'selected_day' not in st.session_state:
    # Default to today if in selected month and year, else first day of month
    if year == date.today().year and month_index == date.today().month:
        st.session_state.selected_day = date.today()
    else:
        # First valid day in month calendar
        first_day = next((d for week in calendar_data for d in week if d != 0), 1)
        st.session_state.selected_day = date(year, month_index, first_day)

# Function to render calendar grid without buttons, highlight current and selected date
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
        cursor: pointer;
    }
    .calendar th {
        background: #f0f0f0;
    }
    .selected {
        background-color: #a3d3a2;
        font-weight: bold;
    }
    .today {
        background-color: #f28b82;
        font-weight: bold;
    }
    </style>
    <table class='calendar'>
        <tr>""" + "".join(f"<th>{d}</th>" for d in days) + "</tr>"

    for week in calendar_data:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td></td>"
            else:
                cell_date = date(year, month_index, day)
                classes = []
                if cell_date == st.session_state.selected_day:
                    classes.append("selected")
                if cell_date == today:
                    classes.append("today")
                class_attr = " ".join(classes)
                # Use a link with query param to select date
                html += f"""<td class="{class_attr}">
                    <a href="?selected_day={day}&year={year}&month={month_index}" style="text-decoration:none;color:inherit;">{day}</a>
                </td>"""
        html += "</tr>"
    html += "</table>"
    return html

# Render calendar grid
st.markdown(render_calendar_html(), unsafe_allow_html=True)

# Read date selection from query params
query_params = st.experimental_get_query_params()
try:
    q_year = int(query_params.get("year", [year])[0])
    q_month = int(query_params.get("month", [month_index])[0])
    q_day = int(query_params.get("selected_day", [st.session_state.selected_day.day])[0])
    st.session_state.selected_day = date(q_year, q_month, q_day)
except Exception:
    pass

# Astronomy info
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
        # Compute the time when body is at highest altitude (transit)
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

# Show astronomy data for selected day
if st.session_state.selected_day:
    try:
        dt_local = datetime(st.session_state.selected_day.year, st.session_state.selected_day.month, st.session_state.selected_day.day, 12, 0, 0)
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

        with st.expander("🌕 Moon: Phase, Moonrise, Moonset & Zenith"):
            st.write(f"Illumination: **{moon_phase:.1f}%** ({moon_phase_desc})")
            st.write(f"**Moonrise:** {moonrise_ist} IST")
            st.write(f"**Moonset:** {moonset_ist} IST")
            st.write(f"**Zenith:** {moon_zenith_ist} IST")

        planet_df = pd.DataFrame.from_dict(
            planet_times,
            orient='index',
            columns=["Rise (IST)", "Set (IST)"]
        )
        planet_df["Zenith (IST)"] = pd.Series(planet_zenith_times)

        with st.expander("🪐 Planet Rise/Set & Zenith Times"):
            st.dataframe(planet_df, use_container_width=True)

    except Exception as e:
        st.error(f"Error retrieving data: {e}")
