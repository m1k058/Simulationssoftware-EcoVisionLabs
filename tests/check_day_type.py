
import pandas as pd
import holidays

def check_day_type():
    simu_jahr = 2030
    de_holidays = holidays.Germany(years=simu_jahr, language='de')
    feiertage = [pd.Timestamp(date) for date in de_holidays.keys()]
    
    date = pd.Timestamp("2030-08-07")
    is_holiday = date in feiertage
    weekday = date.weekday() # 0=Mon, 2=Wed
    
    print(f"Date: {date}")
    print(f"Is Holiday: {is_holiday}")
    print(f"Weekday: {weekday}")
    
    if is_holiday or weekday == 6:
        dtype = 'FT'
    elif weekday == 5:
        dtype = 'SA'
    else:
        dtype = 'WT'
        
    print(f"Day Type: {dtype}")

if __name__ == "__main__":
    check_day_type()
