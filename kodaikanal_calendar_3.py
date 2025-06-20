import streamlit as st
from datetime import datetime, date, time as dt_time, timedelta
from calendar import monthcalendar, setfirstweekday, MONDAY
import pytz
from astral.sun import sun
from astral.location import LocationInfo
import ephem
import threading
import time as time_module
import pandas as pd

# Constants
setfirstweekday(MONDAY)
IST = pytz.timezone("Asia/Kolkata")
latitude = 10 + 13/60 + 50/3600
longitude = 77 + 28/60 + 7/3600
timezone = "Asia/Kolkata"
location = LocationInfo("Kodaikanal", "India", timezone, latitude, longitude)

# UI
st.title("📅 Kodaikanal Astronomy Calendar")
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, Planetary Rise/Set & Zenith Times (IST, 12-hour format)")

# --- Live IST time (update every second) ---

time_placeholder_date = st.empty()
time_placeholder_time = st.empty()

def live_ist_clock():
    while True:
        now_ist = datetime.now(IST)
        time_placeholder_date.markdown(f"**Current IST Date:** {now_ist.strftime('%d-%m-%Y')}")
        time_placeholder_time.markdown(f"**Current IST Time:** {now_ist.strftime('%I:%M:%S %p')}")
        time_module.sleep(1)

if "clock_thread_started" not in st.session_state:
    threading.Thread(target=live_ist_clock, daemon=True).start()
    st.session_state.clock_thread_started = True

# --- Select Year and Month ---
year = st.number_input("Select Year", min_value=1900, max_value=2100, value=date.today().year, key="year_input")
months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
default_month_index = date.today().month - 1
month_name = st.selectbox("Select Month", months, index=default_month_index)
month_num = months.index(month_name) + 1

# --- Calendar grid ---
cal = monthcalendar(year, month_num)
days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Get selected date from query params or default to today if in same month/year
query_params = st.experimental_get_query_params()
selected_date_str = query_params.get("selected_day", [None])[0]

if selected_date_str:
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    except:
        selected_date = None
else:
    selected_date = None

if not selected_date or selected_date.year != year or selected_date.month != month_num:
    # Default selection to today if in current displayed month/year
    if year == date.today().year and month_num == date.today().month:
        selected_date = date.today()
    else:
        selected_date = date(year, month_num, 1)

# Display calendar grid with clickable days
st.write("### Select Day")

cols = st.columns(7)
for day_name, col in zip(days_of_week, cols):
    col.markdown(f"**{day_name}**")

for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day == 0:
                st.write(" ")
            else:
                day_date = date(year, month_num, day)
                style = ""
                # Highlight selected day in green, today in red
                if day_date == selected_date:
                    style = "background-color:#a3d3a2; font-weight:bold; border-radius:5px;"
                elif day_date == date.today():
                    style = "background-color:#d46a6a; font-weight:bold; border-radius:5px;"

                # Create clickable link that updates the query params to selected day
                link = f"?selected_day={day_date.isoformat()}&year={year}&month={month_num}"
                st.markdown(
                    f'<a href="{link}" style="display:block; padding:6px; {style} text-decoration:none; color:black;">{day}</a>',
                    unsafe_allow_html=True,
                )

# --- Astronomy calculations for the selected date ---

def to_ist_12h(dt_utc):
    if dt_utc == "N/A" or dt_utc is None:
        return "N/A"
    dt_utc = pytz.utc.localize(dt_utc)
    dt_ist = dt_utc.astimezone(IST)
    return dt_ist.strftime("%I:%M %p")

def get_rise_set_zenith(observer, body):
    try:
        rise = observer.next_rising(body)
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        rise = None
    try:
        set_ = observer.next_setting(body)
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        set_ = None
    try:
        zenith = observer.next_transit(body)
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        zenith = None
    return (
        rise.datetime() if rise else "N/A",
        set_.datetime() if set_ else "N/A",
        zenith.datetime() if zenith else "N/A",
    )

try:
    dt_local = datetime(selected_date.year, selected_date.month, selected_date.day, 12, 0, 0)
    sun_times = sun(location.observer, date=dt_local, tzinfo=IST)
    sunrise_ist = sun_times["sunrise"].strftime("%I:%M %p")
    sunset_ist = sun_times["sunset"].strftime("%I:%M %p")
    solar_noon_ist = sun_times["noon"].strftime("%I:%M %p")

    observer = ephem.Observer()
    observer.lat = str(latitude)
    observer.lon = str(longitude)
    observer.elevation = 2133
    # ephem dates are in UTC, so convert local noon to UTC
    observer.date = dt_local.astimezone(pytz.utc)

    moon = ephem.Moon(observer)
    moon_phase = moon.phase

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

    moon_phase_desc = describe_moon_phase(moon_phase)

    moonrise_utc, moonset_utc, moon_zenith_utc = get_rise_set_zenith(observer, moon)
    moonrise_ist = to_ist_12h(moonrise_utc)
    moonset_ist = to_ist_12h(moonset_utc)
    moon_zenith_ist = to_ist_12h(moon_zenith_utc)

    planets = {
        "Mercury": ephem.Mercury(),
        "Venus": ephem.Venus(),
        "Mars": ephem.Mars(),
        "Jupiter": ephem.Jupiter(),
        "Saturn": ephem.Saturn(),
    }

    planet_times = {}
    for pname, pbody in planets.items():
        rise_dt, set_dt, zenith_dt = get_rise_set_zenith(observer, pbody)
        planet_times[pname] = (
            to_ist_12h(rise_dt),
            to_ist_12h(set_dt),
            to_ist_12h(zenith_dt),
        )

    st.markdown("---")
    st.header(f"Astronomy Data for {selected_date.strftime('%A, %d %B %Y')}")

    with st.expander("🌅 Sun Times"):
        st.write(f"**Sunrise:** {sunrise_ist} IST")
        st.write(f"**Sunset:** {sunset_ist} IST")
        st.write(f"**Solar Noon (Zenith):** {solar_noon_ist} IST")

    with st.expander("🌕 Moon Phase and Moonrise/Moonset/Zenith"):
        st.write(f"Illumination: **{moon_phase:.1f}%** ({moon_phase_desc})")
        st.write(f"**Moonrise:** {moonrise_ist} IST")
        st.write(f"**Moonset:** {moonset_ist} IST")
        st.write(f"**Moon Zenith (Transit):** {moon_zenith_ist} IST")

    planet_df = pd.DataFrame.from_dict(
        planet_times,
        orient="index",
        columns=["Rise (IST)", "Set (IST)", "Zenith (IST)"],
    )
    with st.expander("🪐 Planet Rise/Set/Zenith Times"):
        st.dataframe(planet_df, use_container_width=True)

except Exception as e:
    st.error(f"Error calculating astronomy data: {e}")
