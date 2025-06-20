import streamlit as st
from datetime import datetime, date
from calendar import monthcalendar, setfirstweekday, MONDAY
import pytz
from astral.sun import sun
from astral.location import LocationInfo
import ephem
import pandas as pd

setfirstweekday(MONDAY)

# Location for Kodaikanal
latitude = 10 + 13 / 60 + 50 / 3600
longitude = 77 + 28 / 60 + 7 / 3600
timezone = "Asia/Kolkata"
location = LocationInfo("Kodaikanal", "India", timezone, latitude, longitude)
IST = pytz.timezone("Asia/Kolkata")

# Autorefresh to update clock every 1 second (1000 ms)
count = st.experimental_get_query_params().get("refresh_count", [0])[0]
count = int(count) if count else 0
count += 1
st.experimental_set_query_params(refresh_count=count)
if count > 100000:  # reset after a while to prevent overflow
    count = 0

# --- LIVE IST CLOCK DISPLAY ---
now_ist = datetime.now(IST)
st.markdown(f"### Current IST Date: {now_ist.strftime('%d-%m-%Y')}")
st.markdown(f"### Current IST Time: {now_ist.strftime('%I:%M:%S %p')}")
st.experimental_rerun() if st.experimental_get_query_params().get("refresh_count")[0] != str(count) else None


# Title
st.title("📅 Kodaikanal Astronomy Calendar")

# Select Year and Month
year = st.number_input("Select Year", min_value=1900, max_value=2100, value=date.today().year, key="year")
months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
month_idx = st.selectbox("Select Month", months, index=date.today().month - 1, key="month")
month_num = months.index(month_idx) + 1

# Calendar for month/year
cal = monthcalendar(year, month_num)

# Initialize selected_date in session state
if "selected_date" not in st.session_state:
    today = date.today()
    if today.year == year and today.month == month_num:
        st.session_state.selected_date = today
    else:
        st.session_state.selected_date = date(year, month_num, 1)

# Show calendar grid as buttons, update selected_date on click
st.write("### Select Day")

cols = st.columns(7)
days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
for idx, d in enumerate(days_of_week):
    cols[idx].write(f"**{d}**")

for week in cal:
    cols = st.columns(7)
    for idx, day in enumerate(week):
        if day == 0:
            cols[idx].write(" ")
        else:
            current_day = date(year, month_num, day)
            button_label = str(day)
            # Highlight selected day
            if current_day == st.session_state.selected_date:
                button_label = f"**🟢 {day}**"
            elif current_day == date.today():
                button_label = f"**🔴 {day}**"

            if cols[idx].button(button_label, key=f"day_{year}_{month_num}_{day}"):
                st.session_state.selected_date = current_day

# Astronomy calculations for selected date
selected_date = st.session_state.selected_date
st.markdown("---")
st.header(f"Astronomy Data for {selected_date.strftime('%A, %d %B %Y')}")

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

    with st.expander("🌅 Sun Times"):
        st.write(f"Sunrise: {sunrise_ist} IST")
        st.write(f"Sunset: {sunset_ist} IST")
        st.write(f"Solar Noon (Zenith): {solar_noon_ist} IST")

    with st.expander("🌕 Moon Phase and Moonrise/Moonset/Zenith"):
        st.write(f"Illumination: {moon_phase:.1f}% ({moon_phase_desc})")
        st.write(f"Moonrise: {moonrise_ist} IST")
        st.write(f"Moonset: {moonset_ist} IST")
        st.write(f"Moon Zenith (Transit): {moon_zenith_ist} IST")

    planet_df = pd.DataFrame.from_dict(
        planet_times,
        orient="index",
        columns=["Rise (IST)", "Set (IST)", "Zenith (IST)"],
    )
    with st.expander("🪐 Planet Rise/Set/Zenith Times"):
        st.dataframe(planet_df, use_container_width=True)

except Exception as e:
    st.error(f"Error calculating astronomy data: {e}")
