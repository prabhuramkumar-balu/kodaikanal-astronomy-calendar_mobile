import streamlit as st
from datetime import datetime, date, timedelta
from calendar import monthcalendar, setfirstweekday, MONDAY
from astral.sun import sun
from astral.location import LocationInfo
import pytz
import ephem
import pandas as pd
import time

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
st.caption("Sunrise, Sunset, Moon Phase, Moonrise/Set, Planetary Rise/Set & Zenith Times (IST, 12-hour format)")

# Live IST time display (updates every second)
time_placeholder = st.empty()

def show_time():
    while True:
        now_ist = datetime.now(IST)
        time_placeholder.markdown(f"**Current IST Date:** {now_ist.strftime('%d-%m-%Y')}")
        time_placeholder.markdown(f"**Current IST Time:** {now_ist.strftime('%I:%M:%S %p')}")
        time.sleep(1)

# Run the live clock asynchronously so UI can still interact
import threading
if "clock_thread_started" not in st.session_state:
    threading.Thread(target=show_time, daemon=True).start()
    st.session_state.clock_thread_started = True

# Inputs
year = st.number_input("Select Year", min_value=1900, max_value=2100, value=date.today().year, key="year_input")

months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

# Use st.selectbox with index to handle setting and getting selected month
# Default month is current month
default_month_index = date.today().month - 1
month_index = st.selectbox("Select Month", options=months, index=default_month_index, key="month_select")
month_num = months.index(month_index) + 1

calendar_data = monthcalendar(year, month_num)

days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Handle query params for selected day (persistent across reloads)
query_params = st.query_params
selected_day_str = query_params.get("selected_day", [None])[0]

if selected_day_str:
    try:
        selected_day = datetime.strptime(selected_day_str, "%Y-%m-%d").date()
        # Validate selected_day is in the current year/month shown
        if not (selected_day.year == year and selected_day.month == month_num):
            selected_day = None
    except:
        selected_day = None
else:
    selected_day = None

# Default to today if no selection & current month/year
if selected_day is None and year == date.today().year and month_num == date.today().month:
    selected_day = date.today()

# Calendar rendering as grid with clickable days (no buttons, just clickable text)
st.write("### Select Day")
cols = st.columns(7)

for week in calendar_data:
    for i, day in enumerate(week):
        with cols[i]:
            if day == 0:
                st.write(" ")
            else:
                this_date = date(year, month_num, day)
                style = ""
                if this_date == selected_day:
                    style = "background-color: #a3d3a2; font-weight: bold; border-radius: 5px;"  # green highlight
                elif this_date == date.today():
                    style = "background-color: #d46a6a; font-weight: bold; border-radius: 5px;"  # red highlight

                # Make date clickable: when clicked, update query params without reloading a new page
                date_str = this_date.strftime("%Y-%m-%d")
                link = f"?selected_day={date_str}&year={year}&month={month_num}"
                # Use markdown link with style
                st.markdown(f'<a href="{link}" style="display:block; padding:6px; {style} text-decoration:none; color:black;">{day}</a>', unsafe_allow_html=True)

# Update st.query_params if user selects a different date from URL manually
# and re-run without infinite loop
def update_query_params():
    params = st.query_params
    # If selected_day in URL and different from session selected_day, update
    if "selected_day" in params:
        url_date = params["selected_day"][0]
        try:
            dt_url = datetime.strptime(url_date, "%Y-%m-%d").date()
            if dt_url != selected_day:
                st.session_state.selected_day = dt_url
                st.experimental_rerun()
        except:
            pass

# No infinite rerun needed because we read from query_params directly

# Astronomy info display
if selected_day:
    try:
        dt_local = datetime(selected_day.year, selected_day.month, selected_day.day, 12, 0, 0)
        dt_utc = pytz.timezone(timezone).localize(dt_local).astimezone(pytz.utc)

        sun_times = sun(astral_city.observer, date=dt_local, tzinfo=pytz.timezone(timezone))
        sunrise_ist = sun_times['sunrise'].strftime('%I:%M %p')
        sunset_ist = sun_times['sunset'].strftime('%I:%M %p')
        solar_noon_ist = sun_times['noon'].strftime('%I:%M %p')

        observer = ephem.Observer()
        observer.lat = str(latitude)
        observer.lon = str(longitude)
        observer.elevation = 2133
        observer.date = dt_utc

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
            if dt_utc == "N/A" or dt_utc is None:
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
                rise.datetime() if rise else "N/A",
                set_.datetime() if set_ else "N/A",
                zenith.datetime() if zenith else "N/A",
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

        st.markdown("---")
        st.header(f"Astronomy Data for {selected_day.strftime('%A, %d %B %Y')}")

        with st.expander("🌅 Sun Times"):
            st.write(f"**Sunrise:** {sunrise_ist} IST")
            st.write(f"**Sunset:** {sunset_ist} IST")
            st.write(f"**Solar Noon (Zenith):** {solar_noon_ist} IST")

        with st.expander("🌕 Moon Phase and Moonrise/Moonset/Zenith"):
            st.write(f"Illumination: **{moon_phase:.1f}%** ({moon_phase_desc})")
            st.write(f"**Moonrise:** {moonrise_ist} IST")
            st.write(f"**Moonset:** {moonset_ist} IST")
            st.write(f"**Moon Zenith (Transit):** {moon_zenith_ist} IST")

        planet_df = pd.DataFrame.from_dict(
            planet_times,
            orient='index',
            columns=["Rise (IST)", "Set (IST)", "Zenith (IST)"]
        )
        with st.expander("🪐 Planet Rise/Set/Zenith Times"):
            st.dataframe(planet_df, use_container_width=True)

    except Exception as e:
        st.error(f"Error retrieving astronomy data: {e}")
