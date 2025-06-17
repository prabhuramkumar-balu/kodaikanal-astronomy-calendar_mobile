import streamlit as st
from datetime import datetime, date
from calendar import monthcalendar, setfirstweekday, MONDAY
from astral.sun import sun
from astral.location import LocationInfo
import pytz
import ephem
import pandas as pd

# Calendar setup
setfirstweekday(MONDAY)
IST = pytz.timezone("Asia/Kolkata")

# Location for Kodaikanal
latitude = 10 + 13 / 60 + 50 / 3600
longitude = 77 + 28 / 60 + 7 / 3600
timezone = "Asia/Kolkata"
astral_city = LocationInfo("Kodaikanal", "India", timezone, latitude, longitude)

# UI setup
st.set_page_config(
    page_title="Kodaikanal Astronomy Calendar",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("📅 Kodaikanal Astronomy Calendar")
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, and Planetary Rise/Set Times (IST, 12-hour format)")

# Inputs
year = st.number_input("Select Year", min_value=1900, max_value=2100, value=date.today().year)
months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
month_name = st.selectbox("Select Month", months)
month_index = months.index(month_name) + 1
calendar_data = monthcalendar(year, month_index)

days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Toggle
use_list_view = st.checkbox("📱 Use mobile-friendly list view", value=False)

# Calendar rendering
selected_day = None

def render_calendar_html():
    today = date.today()
    html = """
    <style>
    .calendar { width: 100%; border-collapse: collapse; }
    .calendar th, .calendar td {
        border: 1px solid #ccc;
        text-align: center;
        padding: 0.6em;
        font-size: 0.95em;
    }
    .calendar th {
        background: #f0f0f0;
    }
    .today {
        background-color: #a3d3a2;
        font-weight: bold;
    }
    .calendar-btn {
        width: 100%;
        border: none;
        background: none;
        font-size: 1em;
        padding: 0.4em;
    }
    </style>
    <form method="GET">
    <table class='calendar'>
        <tr>""" + "".join(f"<th>{d}</th>" for d in days) + "</tr>"

    for week in calendar_data:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td></td>"
            else:
                is_today = (year, month_index, day) == (today.year, today.month, today.day)
                cell_class = "today" if is_today else ""
                html += f"""<td class="{cell_class}">
                    <button class="calendar-btn" name="selected_day" value="{day}">{day}</button>
                </td>"""
        html += "</tr>"
    html += "</table></form>"
    return html

# List or grid UI
if use_list_view:
    st.write("### Select Day")
    for week in calendar_data:
        for day in week:
            if day != 0:
                label = f"{day}"
                if date.today() == date(year, month_index, day):
                    label = f"🟢 {day}"
                if st.button(label, key=f"{year}-{month_index}-{day}"):
                    selected_day = date(year, month_index, day)
else:
    st.markdown(render_calendar_html(), unsafe_allow_html=True)
    selected_day_param = st.query_params.get("selected_day", None)
    if selected_day_param:
        try:
            selected_day = date(year, month_index, int(selected_day_param))
        except:
            pass

# Astronomy info
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

# Data display
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

    except Exception as e:
        st.error(f"Error retrieving data: {e}")
