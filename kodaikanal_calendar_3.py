import streamlit as st
from datetime import datetime, date
from calendar import monthcalendar, setfirstweekday, MONDAY
from astral.sun import sun
from astral.location import LocationInfo
import pytz
import ephem
import pandas as pd
import time

# --- Config ---
setfirstweekday(MONDAY)
IST = pytz.timezone("Asia/Kolkata")

# --- Location Setup ---
latitude = 10 + 13 / 60 + 50 / 3600
longitude = 77 + 28 / 60 + 7 / 3600
location = LocationInfo("Kodaikanal", "India", "Asia/Kolkata", latitude, longitude)

# --- Page Setup ---
st.set_page_config(page_title="Kodaikanal Astronomy Calendar", layout="centered")

st.title("📅 Kodaikanal Astronomy Calendar")
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, Planetary Rise/Set & Zenith Times (IST, 12-hour format)")

# --- Live Clock Display ---
time_placeholder = st.empty()
date_placeholder = st.empty()

def update_clock():
    now = datetime.now(IST)
    date_placeholder.markdown(f"**Current IST Date:** {now.strftime('%d-%m-%Y')}")
    time_placeholder.markdown(f"**Current IST Time:** {now.strftime('%I:%M:%S %p')}")

update_clock()
# Delay and re-render the live time every second
st_autorefresh = st.empty()
st_autorefresh.empty()

# --- Inputs ---
year = st.number_input("Select Year", min_value=1900, max_value=2100, value=date.today().year)
months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
month_idx = st.selectbox("Select Month", months, index=date.today().month - 1)
month_num = months.index(month_idx) + 1

# Calendar Setup
calendar_data = monthcalendar(year, month_num)

# Session state to store selected date
if "selected_date" not in st.session_state:
    today = date.today()
    st.session_state.selected_date = today if today.month == month_num and today.year == year else date(year, month_num, 1)

st.write("### Select Day")

cols = st.columns(7)
for idx, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
    cols[idx].write(f"**{name}**")

for week in calendar_data:
    cols = st.columns(7)
    for idx, day in enumerate(week):
        if day == 0:
            cols[idx].markdown(" ")
        else:
            day_date = date(year, month_num, day)
            label = f"**{day}**"
            if st.session_state.selected_date == day_date:
                label = f"🟢 **{day}**"
            elif day_date == date.today():
                label = f"🔴 **{day}**"

            if cols[idx].button(str(day), key=f"btn_{year}_{month_num}_{day}"):
                st.session_state.selected_date = day_date

# --- Astronomy Data ---
selected_date = st.session_state.selected_date
st.markdown("---")
st.header(f"Astronomy Data for {selected_date.strftime('%A, %d %B %Y')}")

def to_ist_12h(dt_utc):
    if dt_utc is None:
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
        rise.datetime() if rise else None,
        set_.datetime() if set_ else None,
        zenith.datetime() if zenith else None,
    )

try:
    dt_local = datetime(selected_date.year, selected_date.month, selected_date.day, 12, 0, 0)
    sun_times = sun(location.observer, date=dt_local, tzinfo=IST)
    sunrise = sun_times["sunrise"].strftime("%I:%M %p")
    sunset = sun_times["sunset"].strftime("%I:%M %p")
    solar_noon = sun_times["noon"].strftime("%I:%M %p")

    observer = ephem.Observer()
    observer.lat = str(latitude)
    observer.lon = str(longitude)
    observer.elevation = 2343
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

    moonrise, moonset, moon_zenith = get_rise_set_zenith(observer, moon)
    moonrise_ist = to_ist_12h(moonrise)
    moonset_ist = to_ist_12h(moonset)
    moon_zenith_ist = to_ist_12h(moon_zenith)

    planets = {
        "Mercury": ephem.Mercury(),
        "Venus": ephem.Venus(),
        "Mars": ephem.Mars(),
        "Jupiter": ephem.Jupiter(),
        "Saturn": ephem.Saturn(),
    }

    planet_data = {}
    for name, body in planets.items():
        rise, set_, zenith = get_rise_set_zenith(observer, body)
        planet_data[name] = [to_ist_12h(rise), to_ist_12h(set_), to_ist_12h(zenith)]

    # Display Data
    with st.expander("🌅 Sun"):
        st.write(f"Sunrise: {sunrise}")
        st.write(f"Sunset: {sunset}")
        st.write(f"Solar Noon (Zenith): {solar_noon}")

    with st.expander("🌕 Moon"):
        st.write(f"Illumination: {moon_phase:.1f}% ({describe_moon_phase(moon_phase)})")
        st.write(f"Moonrise: {moonrise_ist}")
        st.write(f"Moonset: {moonset_ist}")
        st.write(f"Moon Zenith (Transit): {moon_zenith_ist}")

    with st.expander("🪐 Planet Rise/Set/Zenith Times"):
        df = pd.DataFrame.from_dict(planet_data, orient="index", columns=["Rise (IST)", "Set (IST)", "Zenith (IST)"])
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Error loading data: {e}")
