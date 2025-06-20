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
st.title("📅 Kodaikanal Astronomy Calendar")
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, Planetary Rise/Set & Zenith Times (IST)")

# --- Live IST Clock ---
# Refresh every second to display live time
count = st_autorefresh(interval=1000, limit=None, key="live_clock")
now_ist = datetime.now(IST)
st.markdown(f"#### Current IST Date: {now_ist.strftime('%d-%m-%Y')}")
st.markdown(f"#### Current IST Time: {now_ist.strftime('%I:%M:%S %p')}")

# --- Year/Month Selector ---
year = st.number_input("Select Year", min_value=1900, max_value=2100, value=date.today().year)
months = ["January","February","March","April","May","June","July","August","September","October","November","December"]
month_name = st.selectbox("Select Month", months, index=date.today().month-1)
month_num = months.index(month_name) + 1
cal = monthcalendar(year, month_num)

# --- Selected Date State ---
if "selected_date" not in st.session_state:
    today = date.today()
    if today.year == year and today.month == month_num:
        st.session_state.selected_date = today
    else:
        st.session_state.selected_date = date(year, month_num, 1)

# --- Mobile-Friendly Grid Calendar ---
st.markdown("### Select Day")
cols = st.columns(7)
for idx, d in enumerate(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]):
    cols[idx].markdown(f"**{d}**")

for week in cal:
    cols = st.columns(7)
    for idx, day in enumerate(week):
        if day == 0:
            cols[idx].markdown(" ")
        else:
            dt = date(year, month_num, day)
            label = str(day)
            if dt == st.session_state.selected_date:
                label = f"🟢 {day}"
            elif dt == date.today():
                label = f"🔴 {day}"
            if cols[idx].button(label, key=f"{year}-{month_num}-{day}"):
                st.session_state.selected_date = dt

# --- Astronomy Calculations for Selected Date ---
sel = st.session_state.selected_date
st.markdown("---")
st.header(f"Astronomy Data for {sel.strftime('%A, %d %B %Y')}")

def to_ist(dt):
    return dt.astimezone(IST).strftime("%I:%M %p") if dt else "N/A"

observer = ephem.Observer()
observer.lat, observer.lon = str(location.latitude), str(location.longitude)
observer.date = datetime(sel.year, sel.month, sel.day, 0, 0, tzinfo=IST).astimezone(pytz.utc)

# Sun
sun_times = sun(location.observer, date=sel, tzinfo=IST)
sunrise, sunset, solar_noon = [sun_times[k].strftime("%I:%M %p") for k in ("sunrise","sunset","noon")]

# Moon and planets
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

moon = ephem.Moon(observer); moon.phase_txt = f"{moon.phase:.1f}%"

# Gather planetary data
coords = {name: get_times(body) for name, body in
          [("Moon", moon),
           ("Mercury", ephem.Mercury()),
           ("Venus", ephem.Venus()),
           ("Mars", ephem.Mars()),
           ("Jupiter", ephem.Jupiter()),
           ("Saturn", ephem.Saturn())]}

# Display
with st.expander("🌅 Sun"):
    st.write(f"**Sunrise:** {sunrise}")
    st.write(f"**Solar Noon:** {solar_noon}")
    st.write(f"**Sunset:** {sunset}")

with st.expander("🌕 Moon"):
    r,s,z = coords["Moon"]
    st.write(f"Illumination: **{moon.phase_txt}**")
    st.write(f"Moonrise: {r}")
    st.write(f"Moonset: {s}")
    st.write(f"Moon Zenith: {z}")

plan_df = pd.DataFrame.from_dict(
    {k:v for k,v in coords.items() if k != "Moon"},
    orient='index',
    columns=["Rise (IST)","Set (IST)","Zenith (IST)"]
)
with st.expander("🪐 Planets"):
    st.dataframe(plan_df, use_container_width=True)
