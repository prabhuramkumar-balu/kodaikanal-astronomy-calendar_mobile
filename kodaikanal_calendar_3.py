import streamlit as st
from datetime import datetime, date
from calendar import monthcalendar, setfirstweekday, MONDAY
from astral.sun import sun
from astral.location import LocationInfo
import pytz
import ephem
import pandas as pd

# Set IST timezone
IST = pytz.timezone("Asia/Kolkata")

# Location for Kodaikanal
latitude = 10 + 13 / 60 + 50 / 3600
longitude = 77 + 28 / 60 + 7 / 3600
timezone = "Asia/Kolkata"
astral_city = LocationInfo("Kodaikanal", "India", timezone, latitude, longitude)

# Set Monday as first day of week
setfirstweekday(MONDAY)

# Streamlit page config
st.set_page_config(page_title="Kodaikanal Astronomy Calendar", layout="centered")

st.title("📅 Kodaikanal Astronomy Calendar")
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, Planetary Rise/Set & Zenith Times (IST, 12-hour format)")

# 🔴 Live Current IST Clock (JS-Based)
current_date = datetime.now(IST).strftime("%d-%m-%Y")
st.markdown(f"#### 📅 Current IST Date: `{current_date}`")

live_clock_code = """
<script>
function updateClock() {
    const options = { timeZone: 'Asia/Kolkata', hour12: true, hour: '2-digit', minute: '2-digit', second: '2-digit' };
    const timeString = new Intl.DateTimeFormat([], options).format(new Date());
    document.getElementById("ist-clock").innerHTML = timeString;
}
setInterval(updateClock, 1000);
</script>
<span style='font-size:18px;'>⏰ Current IST Time: <span id="ist-clock">Loading...</span></span>
"""
st.markdown(live_clock_code, unsafe_allow_html=True)

# Year and Month selection
year = st.number_input("Select Year", min_value=1900, max_value=2100, value=date.today().year)

months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
month_name = st.selectbox("Select Month", months)
month_index = months.index(month_name) + 1

# Get calendar for selected month
calendar_data = monthcalendar(year, month_index)
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Use session state for selected day
if "selected_day" not in st.session_state:
    st.session_state.selected_day = None

# Render calendar grid
def render_calendar():
    today = date.today()
    html = """
    <style>
    .calendar { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .calendar th, .calendar td {
        border: 1px solid #ddd;
        text-align: center;
        padding: 0.5em;
        font-size: 16px;
    }
    .calendar th { background: #f0f0f0; }
    .calendar td { cursor: pointer; }
    .calendar .today { background-color: #ffcccc; }
    .calendar .selected { background-color: #c2f0c2; font-weight: bold; }
    </style>
    <table class='calendar'>
        <tr>""" + "".join(f"<th>{d}</th>" for d in days) + "</tr>"

    for week in calendar_data:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td></td>"
            else:
                d = date(year, month_index, day)
                classes = []
                if d == today:
                    classes.append("today")
                if st.session_state.selected_day == d:
                    classes.append("selected")
                class_str = " ".join(classes)
                html += f"<td class='{class_str}'><a href='?selected_day={day}'>{day}</a></td>"
        html += "</tr>"
    html += "</table>"
    return html

st.markdown(render_calendar(), unsafe_allow_html=True)

# Handle selected date from query param
params = st.query_params
selected_day_param = params.get("selected_day")

try:
    if selected_day_param:
        st.session_state.selected_day = date(year, month_index, int(selected_day_param))
except:
    pass

selected_day = st.session_state.selected_day

# Helper functions
def to_ist_12h(dt_utc):
    if dt_utc in ["N/A", None]:
        return "N/A"
    dt_utc = pytz.utc.localize(dt_utc)
    dt_ist = dt_utc.astimezone(IST)
    return dt_ist.strftime("%I:%M:%S %p")

def get_rise_set(observer, body):
    try:
        rise = observer.next_rising(body)
    except:
        rise = None
    try:
        set_ = observer.next_setting(body)
    except:
        set_ = None
    try:
        transit = observer.next_transit(body)
    except:
        transit = None
    return (
        rise.datetime() if rise else "N/A",
        set_.datetime() if set_ else "N/A",
        transit.datetime() if transit else "N/A"
    )

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

# Display data for selected day
if selected_day:
    try:
        dt_local = datetime(selected_day.year, selected_day.month, selected_day.day, 12, 0, 0)
        dt_utc = IST.localize(dt_local).astimezone(pytz.utc)

        sun_times = sun(astral_city.observer, date=dt_local.date(), tzinfo=IST)
        sunrise = sun_times['sunrise']
        sunset = sun_times['sunset']
        solar_noon = sun_times['noon']

        observer = ephem.Observer()
        observer.lat = str(latitude)
        observer.lon = str(longitude)
        observer.elevation = 2343
        observer.date = dt_utc

        # Moon
        moon = ephem.Moon(observer)
        moon_phase = moon.phase
        moon_phase_desc = describe_moon_phase(moon_phase)
        moonrise, moonset, moon_transit = get_rise_set(observer, moon)

        # Planets
        planets = {
            "Mercury": ephem.Mercury(),
            "Venus": ephem.Venus(),
            "Mars": ephem.Mars(),
            "Jupiter": ephem.Jupiter(),
            "Saturn": ephem.Saturn(),
        }

        planet_times = {}
        for pname, pbody in planets.items():
            rise, set_, transit = get_rise_set(observer, pbody)
            planet_times[pname] = (
                to_ist_12h(rise),
                to_ist_12h(set_),
                to_ist_12h(transit)
            )

        st.markdown("---")
        st.header(f"Astronomy Data for {dt_local.strftime('%A, %d %B %Y')}")

        with st.expander("🌅 Sunrise, Sunset, Solar Noon"):
            st.write(f"**Sunrise:** {sunrise.strftime('%I:%M:%S %p')} IST")
            st.write(f"**Sunset:** {sunset.strftime('%I:%M:%S %p')} IST")
            st.write(f"**Zenith (Solar Noon):** {solar_noon.strftime('%I:%M:%S %p')} IST")

        with st.expander("🌕 Moon Phase and Moonrise/Moonset"):
            st.write(f"Illumination: **{moon_phase:.1f}%** ({moon_phase_desc})")
            st.write(f"**Moonrise:** {to_ist_12h(moonrise)} IST")
            st.write(f"**Moonset:** {to_ist_12h(moonset)} IST")
            st.write(f"**Zenith (Transit):** {to_ist_12h(moon_transit)} IST")

        planet_df = pd.DataFrame.from_dict(
            planet_times,
            orient='index',
            columns=["Rise (IST)", "Set (IST)", "Zenith (Transit)"]
        )

        with st.expander("🪐 Planet Rise/Set/Zenith Times"):
            st.dataframe(planet_df)

    except Exception as e:
        st.error(f"Error computing astronomy data: {e}")
