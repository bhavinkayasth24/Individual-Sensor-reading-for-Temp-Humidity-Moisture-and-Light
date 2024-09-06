import time
import threading
import csv
import os
import Adafruit_DHT
import RPi.GPIO as GPIO
from datetime import datetime

# Sensor Pins for 3 Pots
DHT11_PIN_POT1 = 4
DHT22_PIN_POT1 = 17
DHT11_PIN_POT2 = 27
DHT22_PIN_POT2 = 22
DHT11_PIN_POT3 = 10
DHT22_PIN_POT3 = 9

SOIL_PIN_POT1 = 5
SOIL_PIN_POT2 = 6
SOIL_PIN_POT3 = 13

LIGHT_PIN_POT1 = 19
LIGHT_PIN_POT2 = 26
LIGHT_PIN_POT3 = 21

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(SOIL_PIN_POT1, GPIO.IN)
GPIO.setup(SOIL_PIN_POT2, GPIO.IN)
GPIO.setup(SOIL_PIN_POT3, GPIO.IN)

GPIO.setup(LIGHT_PIN_POT1, GPIO.IN)
GPIO.setup(LIGHT_PIN_POT2, GPIO.IN)
GPIO.setup(LIGHT_PIN_POT3, GPIO.IN)

# Thresholds for dynamic duty cycling
TEMP_THRESHOLD = 0.5  # Temperature change threshold (degrees Celsius)
HUMIDITY_THRESHOLD = 1.0  # Humidity change threshold (%)
SOIL_THRESHOLD = 1  # Digital soil sensor (binary change)
LIGHT_THRESHOLD = 1  # Digital light sensor (binary change)

# Global variables for storing the previous readings for dynamic duty cycling
prev_dht11 = [(None, None)] * 3
prev_dht22 = [(None, None)] * 3
prev_soil = [None] * 3
prev_light = [None] * 3

# Function to read DHT sensor (DHT11 or DHT22)
def read_dht(sensor_type, pin):
    humidity, temperature = Adafruit_DHT.read_retry(sensor_type, pin)
    return temperature, humidity

# Function to read digital capacitive soil moisture sensor
def read_soil_moisture(pin):
    return GPIO.input(pin)

# Function to read digital light sensor
def read_light_intensity(pin):
    return GPIO.input(pin)

# Function to calculate averages of sensor readings from 3 pots
def average_readings(readings):
    return sum(readings) / len(readings)

# Function to dynamically adjust the duty cycle based on threshold comparison
def calculate_duty_cycle(curr_readings, prev_readings, threshold):
    if any(abs(curr - prev) > threshold for curr, prev in zip(curr_readings, prev_readings) if prev is not None):
        return 60  # More frequent updates if significant change, e.g., every 1 minute
    return 300  # Default to 5 minutes if no significant change

# Function to log data into CSV file
def log_data_to_csv(file_path, data):
    file_exists = os.path.isfile(file_path)
    with open(file_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            # Write header if file is new
            writer.writerow(['Timestamp', 'DHT11 Avg Temp', 'DHT11 Avg Humidity', 'DHT22 Avg Temp', 'DHT22 Avg Humidity', 'Avg Soil Moisture', 'Avg Light Intensity'])
        writer.writerow(data)

# Function to perform duty cycling and gather sensor data
def gather_sensor_data():
    global prev_dht11, prev_dht22, prev_soil, prev_light
    
    while True:
        current_time = datetime.now()

        # Reading from all 3 pots
        dht11_readings = [read_dht(Adafruit_DHT.DHT11, DHT11_PIN_POT1),
                          read_dht(Adafruit_DHT.DHT11, DHT11_PIN_POT2),
                          read_dht(Adafruit_DHT.DHT11, DHT11_PIN_POT3)]
        
        dht22_readings = [read_dht(Adafruit_DHT.DHT22, DHT22_PIN_POT1),
                          read_dht(Adafruit_DHT.DHT22, DHT22_PIN_POT2),
                          read_dht(Adafruit_DHT.DHT22, DHT22_PIN_POT3)]
        
        soil_readings = [read_soil_moisture(SOIL_PIN_POT1), 
                         read_soil_moisture(SOIL_PIN_POT2), 
                         read_soil_moisture(SOIL_PIN_POT3)]
        
        light_readings = [read_light_intensity(LIGHT_PIN_POT1), 
                          read_light_intensity(LIGHT_PIN_POT2), 
                          read_light_intensity(LIGHT_PIN_POT3)]

        # Averaging the readings from all 3 pots
        avg_dht11_temp = average_readings([r[0] for r in dht11_readings])
        avg_dht11_humidity = average_readings([r[1] for r in dht11_readings])
        avg_dht22_temp = average_readings([r[0] for r in dht22_readings])
        avg_dht22_humidity = average_readings([r[1] for r in dht22_readings])
        avg_soil = average_readings(soil_readings)
        avg_light = average_readings(light_readings)

        # Log the data into CSV file
        log_data = [current_time.strftime("%Y-%m-%d %H:%M:%S"), 
                    avg_dht11_temp, avg_dht11_humidity, 
                    avg_dht22_temp, avg_dht22_humidity, 
                    avg_soil, avg_light]
        
        log_data_to_csv(f"sensor_log_{current_time.strftime('%Y-%m-%d')}.csv", log_data)

        # Calculate the dynamic duty cycle based on changes in sensor data
        dht11_duty_cycle = calculate_duty_cycle(dht11_readings, prev_dht11, TEMP_THRESHOLD)
        dht22_duty_cycle = calculate_duty_cycle(dht22_readings, prev_dht22, TEMP_THRESHOLD)
        soil_duty_cycle = calculate_duty_cycle(soil_readings, prev_soil, SOIL_THRESHOLD)
        light_duty_cycle = calculate_duty_cycle(light_readings, prev_light, LIGHT_THRESHOLD)

        # Use the smallest duty cycle (most frequent)
        duty_cycle = min(dht11_duty_cycle, dht22_duty_cycle, soil_duty_cycle, light_duty_cycle)

        # Update previous readings
        prev_dht11 = dht11_readings
        prev_dht22 = dht22_readings
        prev_soil = soil_readings
        prev_light = light_readings

        # Wait for the next cycle based on the duty cycle
        time.sleep(duty_cycle)

# Main function to manage daily log rotation and start sensor reading thread
def main():
    sensor_thread = threading.Thread(target=gather_sensor_data)
    sensor_thread.start()

    # Check and rotate logs at 00:00 every day
    while True:
        current_time = datetime.now()
        if current_time.hour == 0 and current_time.minute == 0:
            time.sleep(60)  # Wait 1 minute to avoid repeated log creation
        time.sleep(1)

if __name__ == "__main__":
    main()
