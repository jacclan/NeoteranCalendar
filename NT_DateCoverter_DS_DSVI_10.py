from skyfield.api import load
from skyfield.almanac import moon_phases
from skyfield import almanac
from datetime import datetime, timedelta, timezone

# === Load ephemeris and timescale ===
eph = load('D:/Downloads/Software and Fixes/JPL Ephemeris/de440s.bsp')
ts = load.timescale()

# === Print header ===
print("==== GREGORIAN TO NEOTERAN CALENDAR DATE CONVERTER ====\n")

# === SECTION I (a): Input and Epoch Determination ===
year = int(input("Enter Gregorian year (4 digits): "))
month = int(input("Enter Gregorian month (1–12): "))
day = int(input("Enter Gregorian date (1–31): "))
hour = int(input("Enter UTC hour (0–23): "))
minute = int(input("Enter UTC minutes (0–59): "))

input_GTime_dt = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
input_GTime = ts.utc(input_GTime_dt)

# Updated epoch cutoff date
neoteran_epoch_start = datetime(2020, 9, 18, 15, 0, 0, tzinfo=timezone.utc)
epoch = "ER" if input_GTime.utc_datetime() >= neoteran_epoch_start else "AR"


# === SECTION I(b): General Conjunction Finder Function ===
def get_true_conjunction(query_GTime):
    """Find the correct lunisolar conjunction for a given query time"""
    # Convert to datetime for easier manipulation
    query_dt = query_GTime.utc_datetime()
    
    # Find conjunctions within 60 days before and 40 days after query time
    end_time = ts.utc(query_dt + timedelta(days=40))
    start_time = ts.utc(query_dt - timedelta(days=60))
    
    # Get all moon phase events in range
    t_events, event_types = almanac.find_discrete(start_time, end_time, moon_phases(eph))
    
    # Filter for conjunctions (phase=0) before query time
    conjunctions = [t.utc_datetime() for t, phase in zip(t_events, event_types) 
                   if phase == 0 and t.utc_datetime() < query_dt]
    
    if len(conjunctions) < 2:
        raise ValueError(f"Not enough conjunctions found near {query_dt}")
    
    # Get two most recent conjunctions
    prob_ConjGTime_1 = conjunctions[-1]  # Most recent
    prob_ConjGTime_2 = conjunctions[-2]  # Second most recent
    
    # Calculate midnight boundaries
    query_GDate = query_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    prob_ConjGDate_1 = prob_ConjGTime_1.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate time differences
    time_since_conjunction = (query_GDate - prob_ConjGTime_1).total_seconds()
    time_since_midnight = (query_dt - query_GDate).total_seconds()
    
    # Apply corrected condition
    condition = (
        (prob_ConjGDate_1 < query_GDate and 
         time_since_conjunction <= 15 * 3600 and
         time_since_midnight <= 15 * 3600)
    ) or (
        prob_ConjGDate_1 == query_GDate and
        time_since_midnight >= 9 * 3600
    )
    
    # Return appropriate conjunction based on condition
    return prob_ConjGTime_2 if condition else prob_ConjGTime_1

# === SECTION II: Find Conjunction for Input Time ===
trueInput_ConjGTime = get_true_conjunction(input_GTime)
print(f"\nTrue conjunction for input time: {trueInput_ConjGTime}")

# === SECTION III: Compute Neoteran Month Start ===
print("\n=== SECTION III: Neoteran Month Start ===")

# Convert the trueInput_ConjGTime to datetime
trueInput_ConjGTime_dt = trueInput_ConjGTime  # This is already a datetime object from Section II

# Compute midnight GMT of the conjunction day
trueInput_ConjGDate = trueInput_ConjGTime_dt.replace(hour=0, minute=0, second=0, microsecond=0)

# Calculate time difference since midnight
time_diff = (trueInput_ConjGTime_dt - trueInput_ConjGDate).total_seconds()
print(f"Conjunction time: {trueInput_ConjGTime_dt}")
print(f"Time difference from midnight: {time_diff/3600:.2f} hours")

# Determine Neoteran month start based on conjunction time
if time_diff <= 9 * 3600:  # Conjunction at or before 09:00 UTC
    NMonth_Start = trueInput_ConjGDate + timedelta(hours=15)
    print("Case: Conjunction before 09:00 UTC → Start same day at 15:00 UTC")
else:
    NMonth_Start = trueInput_ConjGDate + timedelta(hours=39)  # Next day 15:00 UTC
    print("Case: Conjunction after 09:00 UTC → Start next day at 15:00 UTC")

print(f"Neoteran month starts on: {NMonth_Start}")

# === SECTION IV: Compute Neoteran Day of Month ===
NMonth_Date = (input_GTime.utc_datetime() - NMonth_Start).days + 1

# === SECTION V: Compute Neoteran Month End ===
next_start_time = ts.utc(NMonth_Start + timedelta(days=1))
end_search_limit = ts.utc(NMonth_Start + timedelta(days=35))

t_events, event_types = almanac.find_discrete(next_start_time, end_search_limit, moon_phases(eph))
endMonth_conjunctions = [t.utc_datetime() for t, phase in zip(t_events, event_types) if phase == 0]

if not endMonth_conjunctions:
    raise ValueError("No next conjunction found after start of month.")

endMonth_ConjGTime = endMonth_conjunctions[0]
endMonth_ConjGDate = endMonth_ConjGTime.replace(hour=0, minute=0, second=0, microsecond=0)

if (endMonth_ConjGTime - endMonth_ConjGDate).total_seconds() < 9 * 3600:
    NMonth_End = endMonth_ConjGDate + timedelta(hours=14, minutes=59, seconds=59)
else:
    NMonth_End = endMonth_ConjGDate + timedelta(hours=38, minutes=59, seconds=59)






# === SECTION VI: Determining Base Descendant Equinox and Neoteran Year Number ===
print("\n=== SECTION VI: Determining Base Descendant Equinox and Neoteran Year Number ===")

# 1. Get September equinoxes surrounding NMonth_Start
def find_nearest_september_equinoxes(reference_time):
    start = ts.utc(reference_time.utc_datetime() - timedelta(days=370))
    end = ts.utc(reference_time.utc_datetime() + timedelta(days=370))
    f = almanac.seasons(eph)
    times, events = almanac.find_discrete(start, end, f)
    sept_equinoxes = [t for t, e in zip(times, events) if e == 2]

    eq_before = max([t for t in sept_equinoxes if t.utc_datetime() < NMonth_Start], default=None)
    eq_after  = min([t for t in sept_equinoxes if t.utc_datetime() > NMonth_Start], default=None)

    if eq_before is None or eq_after is None:
        raise ValueError("Could not find both equinoxes.")

    return eq_before, eq_after

prob_baseDcEquinox_1, prob_baseDcEquinox_2 = find_nearest_september_equinoxes(ts.utc(NMonth_Start))
true_baseDcEquinox = prob_baseDcEquinox_2 if prob_baseDcEquinox_2.utc_datetime() < NMonth_End else prob_baseDcEquinox_1

print(f"\nFirst probable September equinox: {prob_baseDcEquinox_1.utc_datetime()}")
print(f"Second probable September equinox: {prob_baseDcEquinox_2.utc_datetime()}")
print(f"True base descendant equinox for this year: {true_baseDcEquinox.utc_datetime()}")

# 2. Count equinoxes between true_baseDcEquinox and epochal base (2020-09-22)
epochal_baseDcEquinox = ts.utc(2020, 9, 22)

def count_sept_equinoxes_inclusive(start_time, end_time, required_time):
    start = ts.utc(min(start_time.utc_datetime(), end_time.utc_datetime()) - timedelta(days=10))
    end   = ts.utc(max(start_time.utc_datetime(), end_time.utc_datetime()) + timedelta(days=10))

    f = almanac.seasons(eph)
    times, events = almanac.find_discrete(start, end, f)

    counted_equinoxes = [t for t, e in zip(times, events) if e == 2 and
                         min(start_time.utc_datetime(), end_time.utc_datetime()) <= t.utc_datetime() <= max(start_time.utc_datetime(), end_time.utc_datetime())]

    # Force include true_baseDcEquinox if not present
    if not any(abs((t.utc_datetime() - required_time.utc_datetime()).total_seconds()) < 1 for t in counted_equinoxes):
        counted_equinoxes.append(required_time)

    # Sort to maintain chronological order
    counted_equinoxes.sort(key=lambda t: t.utc_datetime())

    print("\nList of counted September equinoxes:")
    for t in counted_equinoxes:
        print(f" - {t.utc_datetime()}")

    print(f"Total number of counted equinoxes: {len(counted_equinoxes)}")

    return len(counted_equinoxes)

count = count_sept_equinoxes_inclusive(epochal_baseDcEquinox, true_baseDcEquinox, true_baseDcEquinox)
NYearNo = count

if true_baseDcEquinox.utc_datetime() < epochal_baseDcEquinox.utc_datetime():
    NYearNo = abs(count)

print(f"Neoteran Year Number: {str(NYearNo).zfill(4)} {epoch}")







# === SECTION VII: Start of Neoteran Month 01C (Refactored) ===
print("\n=== SECTION VII: Start of Neoteran Month 01C ===")

# VII(a): Use general function to find 01C conjunction
print("VII(a): Finding correct conjunction for Month 01C")
true01C_ConjGTime = get_true_conjunction(true_baseDcEquinox)
print(f"True conjunction for 01C: {true01C_ConjGTime}")

# VII(b): Calculate exact start time of Month 01C
print("\nVII(b): Calculate start of Month 01C")
true01C_ConjGDate = true01C_ConjGTime.replace(hour=0, minute=0, second=0, microsecond=0)
time_diff = (true01C_ConjGTime - true01C_ConjGDate).total_seconds()

print(f"Conjunction time difference: {time_diff/3600:.2f} hours")
if time_diff <= 9 * 3600:  # <= 09:00 UTC
    NMonth01C_Start = true01C_ConjGDate + timedelta(hours=15)
    print("Case: Conjunction before 09:00 UTC → Start same day at 15:00 UTC")
else:
    NMonth01C_Start = true01C_ConjGDate + timedelta(hours=39)  # Next day 15:00 UTC
    print("Case: Conjunction after 09:00 UTC → Start next day at 15:00 UTC")

print(f"Start of Neoteran Month 01C: {NMonth01C_Start}")

# === SECTION VIII: Year Conjunctions Identification ===
print("\n=== SECTION VIII: Year Conjunctions Identification ===")

# Define solar event function (if not already defined earlier)
def get_solar_event(year, event_type):
    """Get equinox/solstice datetime for given year and event type"""
    start = ts.utc(year, 1, 1)
    end = ts.utc(year, 12, 31)
    f = almanac.seasons(eph)
    times, events = almanac.find_discrete(start, end, f)
    for t, event in zip(times, events):
        if event == {'autumnal': 2, 'vernal': 0, 'summer': 1, 'winter': 3}[event_type]:
            return t.utc_datetime()
    raise ValueError(f"{event_type} event not found in {year}")

# 1. Start with the verified 01C conjunction from Section VII
year_conjunctions = [true01C_ConjGTime]  # This is conj_C01

# 2. Calculate next descendant equinox
next_year = true_baseDcEquinox.utc_datetime().year + 1
nxtYr_DcEquinox = get_solar_event(next_year, 'autumnal')
print(f"Next descendant equinox: {nxtYr_DcEquinox}")

# 3. Find ALL conjunctions AFTER 01C until next descendant equinox
search_start = ts.utc(true01C_ConjGTime + timedelta(minutes=1))
search_end = ts.utc(nxtYr_DcEquinox)  # Search up to the equinox

t_events, event_types = almanac.find_discrete(search_start, search_end, moon_phases(eph))
all_future_conjunctions = [t.utc_datetime() for t, phase in zip(t_events, event_types) if phase == 0]

# 4. Add all conjunctions to the list
year_conjunctions.extend(all_future_conjunctions)

# 5. Assign identifiers
conjunction_dict = {}
total_conjunctions = len(year_conjunctions)

print(f"\nFound {total_conjunctions} conjunctions in the year:")
for i, conj in enumerate(year_conjunctions):
    if i == 0:
        identifier = "conj_C01"
        status = "(Current Year Start)"
    elif i < total_conjunctions - 1:
        identifier = f"conj_C{str(i+1).zfill(2)}"
        status = f"(Month {i+1})"
    else:
        identifier = "conj_N01"
        status = "(Next Year Start)"
    
    conjunction_dict[identifier] = conj
    print(f"  {identifier}: {conj} {status}")

# 6. Find current month's conjunction using Section II's result
current_conjunction = trueInput_ConjGTime  # From Section II
ordinal_NMonth = None
for identifier, conj_time in conjunction_dict.items():
    if abs((conj_time - current_conjunction).total_seconds()) < 3600:  # 1-hour tolerance
        print(f"\nCurrent month's lunisolar conjunction identified as: {identifier}")
        if identifier.startswith("conj_C"):
            ordinal_NMonth = int(identifier[6:])
        else:  # For next year's months
            ordinal_NMonth = 1
        break

# Fallback if not found
if ordinal_NMonth is None:
    days_since_01C = (current_conjunction - true01C_ConjGTime).days
    ordinal_NMonth = min(max(1, days_since_01C // 28 + 1), 13)
    print(f"\nFallback: Estimated ordinal month as {ordinal_NMonth}")

# 7. Store ordinal month for Section IX
ordinal_NMonth_str = str(ordinal_NMonth).zfill(2)
print(f"Ordinal month number: {ordinal_NMonth_str}")



# === SECTION IX: Leap Year Date Formatting ===
print("\n=== SECTION IX: Leap Year Date Formatting ===")

# Define leap year status (13 conjunctions = ordinary year, 14 = leap year)
is_leap_year = total_conjunctions == 14  # This was missing in the previous version

if not is_leap_year:
    # Ordinary year (13 conjunctions) - always use C suffix
    month_id = f"{ordinal_NMonth_str}C"
    print(f"Ordinary year (13 conjunctions): Using standard month format")
elif ordinal_NMonth <= 3:
    # First three months in leap year - use C suffix
    month_id = f"{ordinal_NMonth_str}C"
    print(f"Leap year: First three months use standard format")
else:
    # Month 04+ in leap year - calculate solar events
    print(f"Leap year detected: Calculating solar events for month {ordinal_NMonth}")
    
    # Get base year from descendant equinox
    base_year = true_baseDcEquinox.utc_datetime().year  # This was missing in the previous version
    
    # Calculate solar events
    sth_solstice = get_solar_event(base_year, 'winter')
    ac_equinox = get_solar_event(base_year + 1, 'vernal')
    nth_solstice = get_solar_event(base_year + 1, 'summer')
    
    print(f"Southern Solstice (Dec {base_year}): {sth_solstice}")
    print(f"Ascendant Equinox (Mar {base_year+1}): {ac_equinox}")
    print(f"Northern Solstice (Jun {base_year+1}): {nth_solstice}")
    
    # Find associated conjunctions
    conj_sth_solstice = get_true_conjunction(ts.utc(sth_solstice))
    conj_ac_equinox = get_true_conjunction(ts.utc(ac_equinox))
    conj_nth_solstice = get_true_conjunction(ts.utc(nth_solstice))
    
    # Find matching conjunction identifiers
    def find_conj_id(target_conj):
        for id, conj_time in conjunction_dict.items():
            if id.startswith("conj_C") and abs((conj_time - target_conj).total_seconds()) < 3600:
                return id.split("_")[1]  # Returns "C04", "C07", etc.
        return None
    
    id_sth = find_conj_id(conj_sth_solstice)
    id_ac = find_conj_id(conj_ac_equinox)
    id_nth = find_conj_id(conj_nth_solstice)
    
    print(f"Conjunction IDs: Southern={id_sth}, Ascendant={id_ac}, Northern={id_nth}")
    
    # Determine pattern
    pattern = None
    if id_sth == "C04" and id_ac == "C07" and id_nth == "C10":
        pattern = 1
    elif id_sth == "C04" and id_ac == "C07" and id_nth == "C11":
        pattern = 2
    elif id_sth == "C04" and id_ac == "C08":
        pattern = 3
    elif id_sth == "C05":
        pattern = 4
    
    # Apply pattern mapping
    if pattern == 1:
        month_map = {
            4: "04C", 5: "05C", 6: "06C", 7: "07C", 8: "08C", 
            9: "09C", 10: "10C", 11: "11C", 12: "12C", 13: "12S"
        }
    elif pattern == 2:
        month_map = {
            4: "04C", 5: "05C", 6: "06C", 7: "07C", 8: "08C", 
            9: "09C", 10: "09S", 11: "10C", 12: "11C", 13: "12C"
        }
    elif pattern == 3:
        month_map = {
            4: "04C", 5: "05C", 6: "06C", 7: "06S", 8: "07C", 
            9: "08C", 10: "09C", 11: "10C", 12: "11C", 13: "12C"
        }
    elif pattern == 4:
        month_map = {
            4: "03S", 5: "04C", 6: "05C", 7: "06C", 8: "07C", 
            9: "08C", 10: "09C", 11: "10C", 12: "11C", 13: "12C"
        }
    
    month_id = month_map.get(ordinal_NMonth)

# Final date assembly
Neoteran_Date = f"{str(NMonth_Date).zfill(2)}|{month_id}|{str(NYearNo).zfill(4)} {epoch}"
print(f"\nStandard Neoteran Date: {Neoteran_Date}")