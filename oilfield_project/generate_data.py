import random
import datetime
import pandas as pd

random.seed(42)

wells = [f'WELL-0{i}' for i in range(1, 6)]
start_date = datetime.date(2026, 4, 1)
rows = []

for well in wells:
    for day in range(30):
        is_failure = random.random() < 0.15
        pressure = random.uniform(1200, 2800)

        if is_failure:
            pressure *= 0.6
            oil_rate = random.uniform(50, 120)
            vibration = random.uniform(4.0, 9.0)      
            motor_current = random.uniform(80, 140)   
        else:
            oil_rate = random.uniform(200, 500)
            vibration = random.uniform(0.5, 3.0)      
            motor_current = random.uniform(30, 60)    

        gas_rate = oil_rate * random.uniform(0.8, 1.5)      
        gor = round((gas_rate * 1000) / oil_rate, 2) if oil_rate > 0 else 0  
        choke_position = round(random.uniform(20, 100), 1) 

        rows.append((
            well,
            (start_date + datetime.timedelta(days=day)).isoformat(),
            round(oil_rate, 2),
            round(gas_rate, 2),
            gor,
            round(random.uniform(5, 60), 2),
            round(pressure, 2),
            round(random.uniform(60, 120), 2),
            choke_position,
            round(vibration, 2),
            round(motor_current, 2),
            1 if is_failure else 0
        ))

df = pd.DataFrame(rows, columns=[
    'Well_ID', 'Date', 'Oil_Rate', 'Gas_Rate', 'GOR', 'Water_Cut',
    'Pressure', 'Temperature', 'Choke_Position', 'Vibration',
    'Motor_Current', 'Pump_Status'
])
df.to_csv('production_data.csv', index=False)
