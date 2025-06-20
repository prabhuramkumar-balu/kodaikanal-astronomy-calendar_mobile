import streamlit as st
from datetime import datetime, date
from calendar import monthcalendar, setfirstweekday, MONDAY
import pytz
from astral.sun import sun
from astral.location import LocationInfo
import ephem
import pandas as pd

# --- Setup ---
setfirstweekday(MONDAY)
IST = pytz.timezone("Asia/Kolkata")
location = LocationInfo("Kodaikanal", "India", "Asia/Kolkata", 10.2306, 77.4686)

st.set_page_config(page_title="Kodaikanal Astronomy Calendar", layout="centered")
st.title("📅 Kodaikanal Astronomy Calendar")
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, Planetary Rise/Set & Zenith Times (IST, 12-hour format)")

# --- Display Current IST Time ---
now_ist = datetime.now(IST)
st.markdown(f"### 📅 Current IST Date: `{now_ist.strftime('%d-%m-%Y')}`")
st.markdown(f"### ⏰ Current IST Time: `{now_ist.strftime('%I:%M:%S %p')}`")

# --- Location Info ---
st.markdown("#### 📍 Location: Kodaikanal, India")
st.markdown("**🗺 Latitude:** 10.2306° N &nbsp;&nbsp;&nbsp; **🗺 Longitude:** 77.4686° E")
st.markdown("**🏔 Altitude:** 2343 m")

# --- Inject JavaScript for Device Detection ---
st.markdown("""
<script>
const screenWidth = window.innerWidth;
const isMobile = screenWidth < 768;
window.parent.postMessage({type: 'streamlit:setComponentValue', key: 'mobile_view', value: isMobile}, '*');
</script>
""", unsafe_allow_html=True)

# --- Session State Defaults ---
if "selected_date" not in st.session_state:
    st.session_state.selected_date = now_ist.date()
if "mobile_view" not in st.session_state:
    st.session_state.mobile_view = False  # Default

# --- JavaScript Sync Handler ---
from streamlit.components.v1 import html

def update_mobile_flag():
    html("""
    <script>
    const screenWidth = window.innerWidth;
    const isMobile = screenWidth < 768;
    window.parent.postMessage({type: 'streamlit:setComponentValue', key: 'mobile_view', value: isMobile}, '*');
    </script>
    """, height=0)

update_mobile_flag()

# --- Year/Month Selection ---
year = st.number_input("Select Year", min_value=1900, max_value=2100, value=now_ist.year)
months = ["January","February","March","April","May","June","July","August","September","October","November","December"]
month_name = st.selectbox("Select Month", months, index=now_ist.month-1)
month_num = months.index(month_name) + 1
cal = monthcalendar(year, month_num)

# --- Responsive Calendar Display ---
st.markdown("### 📆 Click a Day")
weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

is_mobile = st.session_state.mobile_view

# Headers
if not is_mobile:
    cols = st.columns(7)
    for idx, d in enumerate(weekday_labels):
        cols[idx].markdown(f"**{d}**")
else:
    st.markdown("**Weekdays:**")
    st.markdown(", ".join(weekday_labels))

# Day Buttons
for week in cal:
    if not is_mobile:
        cols = st.columns(7)
        for idx, day in enumerate(week):
            if day == 0:
                cols[idx].markdown(" ")
            else:
                dt = date(year, month_num, day)
                if cols[idx].button(str(day), key=f"{year}-{month_num}-{day}"):
                    st.session_state.selected_date = dt
    else:
        for idx, day in enumerate(week):
            if day != 0:
                dt = date(year, month_num, day)
                label = f"{weekday_labels[idx]} {day}"
                if st.button(label, key=f"mob-{year}-{month_num}-{day}"):
                    st.session_state.selected_date = dt

# --- Astronomy Calculations ---
sel = st.session_state.selected_date
st.markdown("---")
st.header(f"🌠 Astronomy Data for {sel.strftime('%A, %d %B %Y')}")

def to_ist(dt):
    return dt.astimezone(IST).strftime("%I:%M %p") if dt else "N/A"

observer = ephem.Observer()
observer.lat, observer.lon = str(location.latitude), str(location.longitude)

# Important: Set observer date as naive UTC for ephem
observer.date = datetime(sel.year, sel.month, sel.day).strftime('%Y/%m/%d')

# Sun Times
sun_times = sun(location.observer, date=sel, tzinfo=IST)
sunrise, sunset, solar_noon = [sun_times[k].strftime("%I:%M %p") for k in ("sunrise", "sunset", "noon")]

# Moon & Planet Data
def get_times(body):
    observer.date = datetime(sel.year, sel.month, sel.day).strftime('%Y/%m/%d')  # reset each time
    try:
        rise = observer.next_rising(body).datetime()
    except:
        rise = None
    try:
        set_ = observer.next_setting(body).datetime()
    except:
        set_ = None
    try:
        zen = observer.next_transit(body).datetime()
    except:
        zen = None
    return to_ist(rise), to_ist(set_), to_ist(zen)

# Moon
moon = ephem.Moon(observer)
moon_phase_txt = f"{moon.phase:.1f}%"
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

# --- Display Sections ---
with st.expander("🌅 Sun"):
    st.write(f"**Sunrise:** {sunrise}")
    st.write(f"**Solar Noon (Zenith):** {solar_noon}")
    st.write(f"**Sunset:** {sunset}")

with st.expander("🌕 Moon"):
    st.write(f"**Illumination:** {moon_phase_txt}")
    st.write(f"**Moonrise:** {moon_rise}")
    st.write(f"**Moonset:** {moon_set}")
    st.write(f"**Moon Zenith:** {moon_zen}")

# Planet Table
planet_df = pd.DataFrame.from_dict(
    planet_times,
    orient="index",
    columns=["Rise (IST)", "Set (IST)", "Zenith (IST)"]
)
with st.expander("🪐 Planetary Rise/Set & Zenith Times"):
    st.dataframe(planet_df, use_container_width=True)
