import streamlit as st
from datetime import datetime, date
from calendar import monthcalendar, setfirstweekday, MONDAY
from astral.sun import sun
from astral.location import LocationInfo
import pytz
import ephem
import pandas as pd
import time

# Setup calendar starting Monday
setfirstweekday(MONDAY)
IST = pytz.timezone("Asia/Kolkata")

latitude = 10 + 13 / 60 + 50 / 3600
longitude = 77 + 28 / 60 + 7 / 3600
timezone = "Asia/Kolkata"
astral_city = LocationInfo("Kodaikanal", "India", timezone, latitude, longitude)

# Page config
st.set_page_config(
    page_title="Kodaikanal Astronomy Calendar",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("📅 Kodaikanal Astronomy Calendar")
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, Planetary Rise/Set & Zenith Times (IST, 12-hour format)")

# Display live IST date and time without full rerun:
time_container = st.empty()

def display_time():
    now_ist = datetime.now(IST)
    time_container.markdown(f"**Current IST Date:** {now_ist.strftime('%d-%m-%Y')}  \n**Current IST Time:** {now_ist.strftime('%H:%M:%S')}")

display_time()

if 'last_time_update' not in st.session_state:
    st.session_state['last_time_update'] = time.time()

if time.time() - st.session_state['last_time_update'] > 1:
    st.session_state['last_time_update'] = time.time()
    display_time()

# Input widgets
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

# Manage selected day with session state and query params
query_params = st.query_params
def parse_selected_day():
    try:
        y = int(query_params.get("year", [str(year)])[0])
        m = int(query_params.get("month", [str(month_index)])[0])
        d = int(query_params.get("selected_day", [str(date.today().day)])[0])
        return date(y, m, d)
    except Exception:
        return date(year, month_index, 1)

if 'selected_day' not in st.session_state:
    st.session_state.selected_day = parse_selected_day()
else:
    # if user changed month/year, reset selected_day accordingly:
    if st.session_state.selected_day.year != year or st.session_state.selected_day.month != month_index:
        if year == date.today().year and month_index == date.today().month:
            st.session_state.selected_day = date.today()
        else:
            first_day = next((d for w in calendar_data for d in w if d != 0), 1)
            st.session_state.selected_day = date(year, month_index, first_day)

selected_day = st.session_state.selected_day

# Generate calendar grid HTML with clickable dates (no buttons)
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
    a {
        text-decoration: none;
        color: inherit;
        display: block;
        width: 100%;
        height: 100%;
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
                if cell_date == selected_day:
                    classes.append("selected")
                if cell_date == today:
                    classes.append("today")
                class_attr = " ".join(classes)
                html += f"""<td class="{class_attr}">
                    <a href="?selected_day={day}&year={year}&month={month_index}">{day}</a>
                </td>"""
        html += "</tr>"
    html += "</table>"
    return html

st.markdown(render_calendar_html(), unsafe_allow_html=True)

# Update selected_day if query params changed (via click)
new_selected_day = parse_selected_day()
if new_selected_day != st.session_state.selected_day:
    st.session_state.selected_day = new_selected_day
    selected_day = new_selected_day

# Astronomy calculations and display
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

if selected_day:
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
