import streamlit as st
from datetime import datetime, date
from calendar import monthcalendar, setfirstweekday, MONDAY
from astral.sun import sun
from astral.location import LocationInfo
import pytz
import ephem
import pandas as pd

# Set week start
setfirstweekday(MONDAY)
IST = pytz.timezone("Asia/Kolkata")

# Kodaikanal location info
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
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, and Planetary Rise/Set Times (IST, 12-hour format)")

# -------------------- Year & Month Selection --------------------
year = st.number_input("Select Year", min_value=1900, max_value=2100, value=date.today().year)

months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

if "selected_month_index" not in st.session_state:
    st.session_state.selected_month_index = date.today().month - 1

month_name = st.selectbox("Select Month", months, key="selected_month_index")
month_index = months.index(month_name) + 1

calendar_data = monthcalendar(year, month_index)
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# -------------------- Track Selected Day --------------------
if "selected_day" not in st.session_state:
    st.session_state.selected_day = None

# -------------------- Helper Functions --------------------
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
    elif 49.5 <= illum <= 50.5:
        return "First Quarter"
    elif illum < 99:
        return "Waxing Gibbous"
    elif illum >= 99:
        return "Full Moon"
    elif illum > 50:
        return "Waning Gibbous"
    elif 49.5 <= illum <= 50.5:
        return "Last Quarter"
    else:
        return "Waning Crescent"

# -------------------- Calendar UI (Grid) --------------------
today = date.today()
st.markdown("### Select a Day")

# Header row
cols = st.columns(7)
for i, day_name in enumerate(days):
    cols[i].markdown(f"**{day_name}**")

# Calendar weeks
for week in calendar_data:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].markdown(" ")
        else:
            label = f"🟢 {day}" if today == date(year, month_index, day) else str(day)
            if cols[i].button(label, key=f"grid-{year}-{month_index}-{day}"):
                st.session_state.selected_day = date(year, month_index, day)

# -------------------- Astronomy Data --------------------
selected_day = st.session_state.selected_day

if selected_day:
    try:
        dt_local = datetime(selected_day.year, selected_day.month, selected_day.day, 12, 0, 0)
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
        st.header(f"Astronomy Data for {dt_local.strftime('%A, %d %B %Y')}")

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

        if st.button("🔙 Back to Calendar"):
            st.session_state.selected_day = None
            st.experimental_rerun()

    except Exception as e:
        st.error(f"Error retrieving data: {e}")
