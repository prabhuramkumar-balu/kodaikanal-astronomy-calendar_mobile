import streamlit as st
from datetime import datetime, date, timedelta
from calendar import monthcalendar, setfirstweekday, MONDAY
from astral.sun import sun
from astral.location import LocationInfo
import pytz
import ephem
import pandas as pd

setfirstweekday(MONDAY)
IST = pytz.timezone("Asia/Kolkata")

# Location for Kodaikanal
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
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, Planet Rise/Set & Zenith Times (IST, 12-hour format)")

# Inputs
today = date.today()

year = st.number_input("Select Year", min_value=1900, max_value=2100, value=today.year)
months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
month_index = st.selectbox("Select Month", options=range(12), format_func=lambda i: months[i], index=today.month - 1) + 1

calendar_data = monthcalendar(year, month_index)
days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Initialize selected_day in session state
if "selected_day" not in st.session_state:
    if (year, month_index) == (today.year, today.month):
        st.session_state.selected_day = today.day
    else:
        st.session_state.selected_day = 1

def select_day(day):
    st.session_state.selected_day = day

st.write("### Select Day")

# Show days of week header
cols = st.columns(7)
for col_idx, d in enumerate(days_of_week):
    cols[col_idx].markdown(f"**{d}**")

# Show calendar grid with clickable colored days
for week in calendar_data:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].write(" ")
        else:
            is_selected = (day == st.session_state.selected_day)
            is_today = (day == today.day and month_index == today.month and year == today.year)

            bg_color = ""
            text_color = "black"
            if is_selected:
                bg_color = "#a3d3a2"  # green
            elif is_today:
                bg_color = "#e57373"  # red
                text_color = "white"

            day_html = f"""
                <div style="
                    background-color: {bg_color};
                    color: {text_color};
                    padding: 8px 12px;
                    border-radius: 6px;
                    text-align: center;
                    cursor: pointer;
                    user-select: none;
                    font-weight: {'bold' if is_selected or is_today else 'normal'};
                    ">
                    {day}
                </div>
            """

            # Invisible button for clicking the day
            if cols[i].button(label="", key=f"select_{day}"):
                select_day(day)
            cols[i].markdown(day_html, unsafe_allow_html=True)

# Astronomy calculations functions

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

def get_zenith_time(observer, body):
    try:
        # next_transit is when the body crosses the local meridian (highest point = zenith)
        zenith = observer.next_transit(body)
        return zenith.datetime()
    except Exception:
        return "N/A"

def describe_moon_phase(illum):
    # illum is percentage illumination (0-100)
    if illum == 0:
        return "New Moon"
    elif 0 < illum < 50:
        return "Waxing Crescent"
    elif illum == 50:
        return "First Quarter"
    elif 50 < illum < 100:
        return "Waxing Gibbous"
    elif illum == 100:
        return "Full Moon"
    elif 50 < illum < 100:
        return "Waning Gibbous"
    elif illum == 50:
        return "Last Quarter"
    elif 0 < illum < 50:
        return "Waning Crescent"
    else:
        return "Unknown"

# Prepare datetime for selected day at noon IST (to avoid date boundary issues)
try:
    selected_date = date(year, month_index, st.session_state.selected_day)
except Exception:
    st.error("Invalid selected date.")
    st.stop()

dt_local = datetime(selected_date.year, selected_date.month, selected_date.day, 12, 0, 0)
dt_utc = pytz.timezone(timezone).localize(dt_local).astimezone(pytz.utc)

# Sun times using astral
try:
    sun_times = sun(astral_city.observer, date=dt_local.date(), tzinfo=pytz.timezone(timezone))
    sunrise_ist = sun_times['sunrise'].strftime('%I:%M %p')
    sunset_ist = sun_times['sunset'].strftime('%I:%M %p')
    solar_noon_ist = sun_times['noon'].strftime('%I:%M %p')
except Exception:
    sunrise_ist = sunset_ist = solar_noon_ist = "N/A"

# Setup observer for ephem
observer = ephem.Observer()
observer.lat = str(latitude)
observer.lon = str(longitude)
observer.elevation = 2133
observer.date = dt_utc

# Moon calculations
moon = ephem.Moon(observer)
moon_phase = moon.phase
moon_phase_desc = describe_moon_phase(moon_phase)
moonrise_utc, moonset_utc = get_rise_set(observer, moon)
moonrise_ist = to_ist_12h(moonrise_utc)
moonset_ist = to_ist_12h(moonset_utc)
moon_zenith_utc = get_zenith_time(observer, moon)
moon_zenith_ist = to_ist_12h(moon_zenith_utc)

# Planets calculations
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
    zenith_dt = get_zenith_time(observer, pbody)
    planet_times[pname] = (
        to_ist_12h(rise_dt),
        to_ist_12h(set_dt),
        to_ist_12h(zenith_dt)
    )

# Display astronomy data
st.markdown("---")
st.header(f"Astronomy Data for {selected_date.strftime('%A, %d %B %Y')}")

with st.expander("🌅 Sun"):
    st.write(f"**Sunrise:** {sunrise_ist} IST")
    st.write(f"**Sunset:** {sunset_ist} IST")
    st.write(f"**Solar Noon (Zenith):** {solar_noon_ist} IST")

with st.expander("🌕 Moon"):
    st.write(f"Illumination: **{moon_phase:.1f}%** ({moon_phase_desc})")
    st.write(f"**Moonrise:** {moonrise_ist} IST")
    st.write(f"**Moonset:** {moonset_ist} IST")
    st.write(f"**Moon Zenith (Transit):** {moon_zenith_ist} IST")

planet_df = pd.DataFrame.from_dict(
    planet_times,
    orient='index',
    columns=["Rise (IST)", "Set (IST)", "Zenith (IST)"]
)
with st.expander("🪐 Planet Rise/Set/Zenith Times"):
    st.dataframe(planet_df, use_container_width=True)
