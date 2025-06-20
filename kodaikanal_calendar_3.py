import streamlit as st
from datetime import datetime, date
from calendar import monthcalendar, setfirstweekday, MONDAY
from astral.sun import sun
from astral.location import LocationInfo
import pytz
import ephem
import pandas as pd

# Setup calendar week to start on Monday
setfirstweekday(MONDAY)
IST = pytz.timezone("Asia/Kolkata")

# Location details for Kodaikanal
latitude = 10 + 13 / 60 + 50 / 3600
longitude = 77 + 28 / 60 + 7 / 3600
timezone = "Asia/Kolkata"
astral_city = LocationInfo("Kodaikanal", "India", timezone, latitude, longitude)

st.set_page_config(page_title="Kodaikanal Astronomy Calendar", layout="centered")

st.title("📅 Kodaikanal Astronomy Calendar")
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, and Planetary Rise/Set Times (IST, 12-hour format)")

# Inputs
year = st.number_input("Select Year", min_value=1900, max_value=2100, value=date.today().year)
months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
month_index = st.selectbox("Select Month", options=range(12), format_func=lambda i: months[i], index=date.today().month - 1) + 1

# Generate the month calendar (weeks with days)
calendar_data = monthcalendar(year, month_index)
days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Initialize selected day in session state if not present
if "selected_day" not in st.session_state:
    # Default to today's date if in current month/year, else 1st
    if (year, month_index) == (date.today().year, date.today().month):
        st.session_state.selected_day = date.today().day
    else:
        st.session_state.selected_day = 1

# When user clicks on a day button, update selected_day in session_state
def select_day(day):
    st.session_state.selected_day = day

# Display calendar grid with clickable buttons for days
st.write("### Select Day")

calendar_html = """
<style>
.calendar { border-collapse: collapse; width: 100%; max-width: 400px; margin-bottom: 1em; }
.calendar th, .calendar td { border: 1px solid #ccc; text-align: center; padding: 0.5em; font-size: 1em; }
.calendar th { background-color: #f0f0f0; }
.selected { background-color: #a3d3a2; font-weight: bold; }
.button-day { background: none; border: none; cursor: pointer; font-size: 1em; width: 100%; height: 100%; }
</style>
"""

calendar_html += "<table class='calendar'><thead><tr>"
for d in days_of_week:
    calendar_html += f"<th>{d}</th>"
calendar_html += "</tr></thead><tbody>"

for week in calendar_data:
    calendar_html += "<tr>"
    for day in week:
        if day == 0:
            calendar_html += "<td></td>"
        else:
            # Highlight selected day
            selected_class = "selected" if day == st.session_state.selected_day else ""
            # Use a form button for each day
            # We'll create a form for each day so clicking submits and updates session state
            calendar_html += f"""
            <td class="{selected_class}">
                <form action="" method="post">
                    <input type="hidden" name="day" value="{day}">
                    <button class="button-day" type="submit">{day}</button>
                </form>
            </td>
            """
    calendar_html += "</tr>"
calendar_html += "</tbody></table>"

# Streamlit can't process raw html forms natively with callback, so we'll handle clicks differently:
# Instead, use st.button for each day arranged in columns to mimic grid:

st.write("")

cols = st.columns(7)
for col_idx, d in enumerate(days_of_week):
    cols[col_idx].markdown(f"**{d}**")

for week in calendar_data:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].write(" ")
        else:
            is_selected = (day == st.session_state.selected_day)
            button_label = f"**{day}**" if is_selected else str(day)
            if cols[i].button(button_label, key=f"day_{day}", help=f"Select day {day}"):
                select_day(day)

# Now get the selected date
selected_date = date(year, month_index, st.session_state.selected_day)

# Astronomy calculations

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

try:
    dt_local = datetime(selected_date.year, selected_date.month, selected_date.day, 12, 0, 0)
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
    st.header(f"Astronomy Data for {selected_date.strftime('%A, %d %B %Y')}")

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
