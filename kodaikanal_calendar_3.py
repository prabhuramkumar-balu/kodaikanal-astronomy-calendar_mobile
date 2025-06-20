import streamlit as st
from datetime import datetime, date
from calendar import monthcalendar, setfirstweekday, MONDAY
import pytz
from astral.sun import sun
from astral.location import LocationInfo
import ephem
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# --- Setup ---
setfirstweekday(MONDAY)
IST = pytz.timezone("Asia/Kolkata")
location = LocationInfo("Kodaikanal", "India", "Asia/Kolkata", 10.2306, 77.4686)

st.set_page_config(page_title="Kodaikanal Astronomy Calendar", layout="centered")

# 🔁 Auto-refresh every second (only for live clock display)
st_autorefresh(interval=1000, limit=None, key="live_time_refresh")

st.title("📅 Kodaikanal Astronomy Calendar")
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, Planetary Rise/Set & Zenith Times (IST, 12-hour format)")

# --- Live IST Time (display only) ---
now_ist = datetime.now(IST)
st.markdown(f"### 📅 Current IST Date: `{now_ist.strftime('%d-%m-%Y')}`")
st.markdown(f"### ⏰ Current IST Time: `{now_ist.strftime('%I:%M:%S %p')}`")

# --- Date Selection ---
year = st.number_input("Select Year", min_value=1900, max_value=2100, value=now_ist.year)
months = ["January","February","March","April","May","June","July","August","September","October","November","December"]
month_name = st.selectbox("Select Month", months, index=now_ist.month-1)
month_num = months.index(month_name) + 1
cal = monthcalendar(year, month_num)

if "selected_date" not in st.session_state:
    st.session_state.selected_date = now_ist.date()

# --- Calendar Grid ---
st.markdown("### 📆 Click a Day")
cols = st.columns(7)
for idx, d in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
    cols[idx].markdown(f"**{d}**")

for week in cal:
    cols = st.columns(7)
    for idx, day in enumerate(week):
        if day == 0:
            cols[idx].markdown(" ")
        else:
            dt = date(year, month_num, day)
            if cols[idx].button(f"{day}", key=f"{year}-{month_num}-{day}"):
                st.session_state.selected_date = dt

# --- Astronomy Calculations ---
sel = st.session_state.selected_date
st.markdown("---")
st.header(f"🌠 Astronomy Data for {sel.strftime('%A, %d %B %Y')}")

def to_ist(dt):
    return dt.astimezone(IST).strftime("%I:%M %p") if dt else "N/A"

observer = ephem.Observer()
observer.lat, observer.lon = str(location.latitude), str(location.longitude)
observer.date = datetime(sel.year, sel.month, sel.day, 0, 0, tzinfo=IST).astimezone(pytz.utc)

# Sun
sun_times = sun(location.observer, date=sel, tzinfo=IST)
sunrise = sun_times['sunrise'].strftime("%I:%M %p")
sunset = sun_times['sunset'].strftime("%I:%M %p")
solar_noon = sun_times['noon'].strftime("%I:%M %p")

# Moon
moon = ephem.Moon(observer)
moon_phase_txt = f"{moon.phase:.1f}%"

def get_times(body):
    try: rise = observer.next_rising(body).datetime()
    except: rise = None
    try: set_ = observer.next_setting(body).datetime()
    except: set_ = None
    try: zen = observer.next_transit(body).datetime()
    except: zen = None
    return to_ist(rise), to_ist(set_), to_ist(zen)

moon_rise, moon_set, moon_zen = get_times(moon)

# Planets
planets = {
    "Mercury": ephem.Mercury(),
    "Venus": ephem.Venus(),
    "Mars": ephem.Mars(),
    "Jupiter": ephem.Jupiter(),
    "Saturn": ephem.Saturn()
}
planet_times = {}
for name, body in planets.items():
    planet_times[name] = get_times(body)

# --- Display Results ---
with st.expander("🌅 Sun"):
    st.write(f"**Sunrise:** {sunrise}")
    st.write(f"**Solar Noon (Zenith):** {solar_noon}")
    st.write(f"**Sunset:** {sunset}")

with st.expander("🌕 Moon"):
    st.write(f"**Illumination:** {moon_phase_txt}")
    st.write(f"**Moonrise:** {moon_rise}")
    st.write(f"**Moonset:** {moon_set}")
    st.write(f"**Moon Zenith:** {moon_zen}")

df = pd.DataFrame.from_dict(
    planet_times,
    orient="index",
    columns=["Rise (IST)", "Set (IST)", "Zenith (IST)"]
)

with st.expander("🪐 Planetary Rise/Set & Zenith Times"):
    st.dataframe(df, use_container_width=True)
