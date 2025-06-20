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
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, Planetary Rise/Set & Zenith Times (IST)")

# --- Display Current IST Time (Updates on interaction or manual refresh) ---
now_ist = datetime.now(IST)
st.markdown(f"#### Current IST Date: {now_ist.strftime('%d-%m-%Y')}")
st.markdown(f"#### Current IST Time: {now_ist.strftime('%I:%M:%S %p')}")

# --- Year/Month Selection ---
year = st.number_input("Select Year", min_value=1900, max_value=2100, value=now_ist.year)
months = ["January","February","March","April","May","June","July","August","September","October","November","December"]
month_name = st.selectbox("Select Month", months, index=now_ist.month-1)
month_num = months.index(month_name) + 1
cal = monthcalendar(year, month_num)

# --- Selected Date Management ---
if "selected_date" not in st.session_state:
    st.session_state.selected_date = now_ist.date()

# --- Calendar Display (Grid) ---
st.markdown("### Select Day")
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
            label = str(day)
            if cols[idx].button(label, key=f"{year}-{month_num}-{day}"):
                st.session_state.selected_date = dt

# --- Astronomy Calculations ---
sel = st.session_state.selected_date
st.markdown("---")
st.header(f"Astronomy Data for {sel.strftime('%A, %d %B %Y')}")

def to_ist(dt):
    return dt.astimezone(IST).strftime("%I:%M %p") if dt else "N/A"

observer = ephem.Observer()
observer.lat, observer.lon = str(location.latitude), str(location.longitude)
observer.date = datetime(sel.year, sel.month, sel.day, 0, 0, tzinfo=IST).astimezone(pytz.utc)

# Sun Times
sun_times = sun(location.observer, date=sel, tzinfo=IST)
sunrise, sunset, solar_noon = [sun_times[k].strftime("%I:%M %p") for k in ("sunrise", "sunset", "noon")]

# Moon and Planets
def get_times(body):
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

moon = ephem.Moon(observer)
moon.phase_txt = f"{moon.phase:.1f}%"

# Planetary Times
coords = {
    "Moon": get_times(moon),
    "Mercury": get_times(ephem.Mercury()),
    "Venus": get_times(ephem.Venus()),
    "Mars": get_times(ephem.Mars()),
    "Jupiter": get_times(ephem.Jupiter()),
    "Saturn": get_times(ephem.Saturn())
}

# --- Display Sections ---
with st.expander("🌅 Sun"):
    st.write(f"**Sunrise:** {sunrise}")
    st.write(f"**Solar Noon (Zenith):** {solar_noon}")
    st.write(f"**Sunset:** {sunset}")

with st.expander("🌕 Moon"):
    r, s, z = coords["Moon"]
    st.write(f"Illumination: **{moon.phase_txt}**")
    st.write(f"Moonrise: {r}")
    st.write(f"Moonset: {s}")
    st.write(f"Moon Zenith: {z}")

# Planetary Table
planet_df = pd.DataFrame.from_dict(
    {k: v for k, v in coords.items() if k != "Moon"},
    orient='index',
    columns=["Rise (IST)", "Set (IST)", "Zenith (IST)"]
)
with st.expander("🪐 Planets"):
    st.dataframe(planet_df, use_container_width=True)
