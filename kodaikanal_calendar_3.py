import streamlit as st
from datetime import datetime, date
from calendar import monthcalendar, setfirstweekday, MONDAY
import pytz
from astral.sun import sun
from astral import LocationInfo
import ephem
import pandas as pd
from urllib.parse import urlencode

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

# --- Session State Defaults ---
if "selected_date" not in st.session_state:
    st.session_state.selected_date = now_ist.date()

# --- Year/Month Selection ---
year = st.number_input("Select Year", min_value=1900, max_value=2100, value=now_ist.year)
months = ["January","February","March","April","May","June","July","August","September","October","November","December"]
month_name = st.selectbox("Select Month", months, index=now_ist.month-1)
month_num = months.index(month_name) + 1
cal = monthcalendar(year, month_num)

# --- Responsive Calendar Grid using HTML ---
st.markdown("### 📆 Click a Day")

weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
params = st.experimental_get_query_params()

if "d" in params:
    try:
        clicked_day = int(params["d"][0])
        st.session_state.selected_date = date(year, month_num, clicked_day)
    except:
        pass

# Generate calendar grid HTML
calendar_html = f"""
<style>
.calendar {{
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 5px;
  text-align: center;
}}
.calendar-day {{
  padding: 10px;
  border-radius: 5px;
  background-color: #f0f2f6;
  cursor: pointer;
  font-weight: bold;
}}
.calendar-day.today {{
  background-color: #ffdca9;
}}
.calendar-day.selected {{
  background-color: #add8e6;
}}
.calendar-header {{
  font-weight: bold;
  padding: 5px;
  background-color: #dbeafe;
  border-radius: 5px;
}}
a {{
  text-decoration: none;
  color: inherit;
}}
</style>

<div class="calendar">
"""

# Weekday Headers
for wd in weekday_labels:
    calendar_html += f'<div class="calendar-header">{wd}</div>'

# Calendar Days
for week in cal:
    for day in week:
        if day == 0:
            calendar_html += '<div></div>'
        else:
            classes = "calendar-day"
            if date(year, month_num, day) == now_ist.date():
                classes += " today"
            if date(year, month_num, day) == st.session_state.selected_date:
                classes += " selected"
            query = urlencode({"d": day})
            calendar_html += f'<div class="{classes}"><a href="?{query}">{day}</a></div>'

calendar_html += "</div>"

st.markdown(calendar_html, unsafe_allow_html=True)

# --- Astronomy Calculations ---
sel = st.session_state.selected_date
st.markdown("---")
st.header(f"🌠 Astronomy Data for {sel.strftime('%A, %d %B %Y')}")

def to_ist(dt):
    return dt.astimezone(IST).strftime("%I:%M %p") if dt else "N/A"

# Sun Times
sun_times = sun(location.observer, date=sel, tzinfo=IST)
sunrise, sunset, solar_noon = [sun_times[k].strftime("%I:%M %p") for k in ("sunrise", "sunset", "noon")]

# Observer Setup
observer = ephem.Observer()
observer.lat, observer.lon = str(location.latitude), str(location.longitude)
observer.date = datetime(sel.year, sel.month, sel.day).strftime('%Y/%m/%d')

# Moon Phase Name Helper
def moon_phase_name(phase):
    if phase < 1:
        return "New Moon"
    elif phase < 49:
        return "Waxing Crescent"
    elif phase < 51:
        return "First Quarter"
    elif phase < 99:
        return "Waxing Gibbous"
    elif phase <= 100:
        return "Full Moon"
    elif phase > 99:
        return "Waning Gibbous"
    elif phase > 51:
        return "Last Quarter"
    else:
        return "Waning Crescent"

# Moon & Planet Data
def get_times(body):
    observer.date = datetime(sel.year, sel.month, sel.day)
    try:
        rise = observer.next_rising(body).datetime().astimezone(IST)
    except:
        rise = None
    try:
        set_ = observer.next_setting(body).datetime().astimezone(IST)
    except:
        set_ = None
    try:
        zen = observer.next_transit(body).datetime().astimezone(IST)
    except:
        zen = None
    return to_ist(rise), to_ist(set_), to_ist(zen)

# Moon
moon = ephem.Moon(observer)
moon_phase_txt = f"{moon.phase:.1f}% ({moon_phase_name(moon.phase)})"
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
