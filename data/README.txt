# DriverID Data README

## Overview
The Driver Identification Dataset was created to collect and analyze driving behavior data from 50 different drivers. Each driver operated a **2014 Kenworth T270 Class 6** truck around **Fort Collins, Colorado** while various data sources recorded their driving behavior and vehicle performance. The dataset includes **CANbus (Controller Area Network) data**, **GPS data**, **inertial measurement data**, and **biometric data from a heart rate monitor**.

A **cyberattack** was executed during each drive, which caused multiple dashboard warning lights to illuminate and set the tachometer and speedometer to zero, regardless of actual speed. The attack was stopped either **after one minute or if the driver pulled over**.

### Participant Groups
Drivers were divided into three groups based on their awareness of the cyberattack:
- **Group 1** (N=17): No prior knowledge of the cyberattack.
- **Group 2** (N=16): Informed that a cyberattack **may or may not** occur.
- **Group 3** (N=17): Informed that a cyberattack **may or may not** occur and given instructions to pull over if it happens.

### Errors in Data
- **VBOX Data Missing**: G1S15, G1S16, G2S13, G3S13
- The VBOX reset towards the end of the drive for G1S09. The driver was pulled over, so the drive was stopped until it finished reseting and resumed data collection. The only data that was lost was of the vehicle being stationary.
- **CANbus Data Collected at Low Frequency**: G1S04
- The remaining participants have **complete** VBOX and CANbus data.

## Data Structure
The dataset consists of three primary folders:

### 1. **DriverIDDataDownsampled**
- Contains a **downsampled** version of the data.
- Each timestamp corresponds to all recorded data types.
- Additional calculated variables:
  - **Distance traveled** (calculated using the **haversine formula** based on GPS coordinates).
  - **Cyberattack status** (indicating whether the attack is active).
  - **Qualtrics Survey Data** (Participant answers to MMDBQ (Modified Manchester Driver Behavior Questionnaire)
- A **data dictionary** is included to explain all variables.

### 2. **DriverIDDataHighResolution**
- Contains **high-resolution data**, where each data type has its **own** timestamp.
- Most variables have a recorded data point every hundredth of a second
- Data is available in **both SQLite and CSV formats**.
- A **data dictionary** is included.

### 3. **DriverIDDataRaw**
- Contains the **original, unprocessed** data collected from each device.
- Includes:
  - **Binary file** from **CANLogger3**.
  - **.log file** from **TruckCape Beaglebone**.
  - **.vbo file** from **VBOX 3i**.
  - **Three CSV files** from the **Empatica E4 wristband heart rate monitor**.
  - **A KML file that is generated using a python script that grabs all longitude/latitude values from the Sparkfun NEO GPS antenna. This can be inputted into Google Maps, Google Earth, etc.

## Data Collection Devices & Standards

### **CANbus Data**
- Collected from **CANLogger3** and **TruckCape Beaglebone Black**.
- Follows **SAE J1939 Standard**.
- [Sources:](https://www.engr.colostate.edu/~jdaily/truck/index.html)
  - https://www.sae.org/standards/content/j1939da_202301/
  - https://github.com/SystemsCyber/TruckCapeProjects
  - https://github.com/SystemsCyber/CAN-Logger-3

### **VBOX Data**
- Collected using **VBOX 3i**.
- [Source:](https://www.vboxautomotive.co.uk/index.php/en/products/data-loggers/vb3i)
  - https://www.vboxautomotive.co.uk/index.php/en/products/data-loggers/vb3i

### **GPS Data**
- Collected using **Teensy 4 and NEO-M9N from SparkFun**.
- [Source:](https://github.com/SystemsCyber/TruckGPS)
  - https://github.com/SystemsCyber/TruckGPS

### **Heart Rate Monitor Data**
- Collected from **Empatica E4 Wristband**.
- [Source:](https://support.empatica.com/hc/en-us/articles/202581999-E4-wristband-technical-specifications)
  - https://support.empatica.com/hc/en-us/articles/202581999-E4-wristband-technical-specifications

## Purpose of the Dataset
This dataset is used for:
- **Analyzing driver responses to a cyberattack**.
- **Developing machine learning models to identify drivers** based on their driving behavior.
- **Understanding how different levels of attack awareness influence driving behavior**.

## Data Processing
- The **downsampled dataset** aggregates data into **1-second intervals** using the mean value of each interval. To show the loss of data, standard deviation, min, and max of each **1-second interval** are included.
- The **cyberattack status** variable indicates when the attack was active.
- Additional **survey data** is available from each participant.
- The code to parse the data is shown and described in [Source:](https://github.com/SystemsCyber/DriverIDCode)

## Calculated Correlations of VBOX GPS Speed and CANbus Wheel-Based Vehicle Speed After VBOX Timestamps Shifted:

### Group 1
- **S01:** Correlation: 0.99987, VBOX Data Shift: 10.21 s
- **S02:** Correlation: 0.99983, VBOX Data Shift: 3.34 s
- **S03:** Correlation: 0.99987, VBOX Data Shift: 2.44 s
- **S04:** Correlation: 0.83595, VBOX Data Shift: -23.68 s (Lower Correlation Due to Sampling rate of the CANbus data being significantly lower than other drives)
- **S05:** Correlation: 0.99989, VBOX Data Shift: 8.69 s
- **S06:** Correlation: 0.99984, VBOX Data Shift: -0.37 s
- **S07:** Correlation: 0.99975, VBOX Data Shift: -0.13 s
- **S08:** Correlation: 0.99987, VBOX Data Shift: 42.76 s
- **S09:** Correlation: 0.74942, VBOX Data Shift: -10.58 s (Lower Correlation due to VBOX Resetting itself towards the end of the drive)
- **S10:** Correlation: 0.99965, VBOX Data Shift: -3.16 s
- **S11:** Correlation: 0.99972, VBOX Data Shift: -4.85 s
- **S12:** Correlation: 0.99959, VBOX Data Shift: -2.19 s
- **S13:** Correlation: 0.99984, VBOX Data Shift: -5.55 s
- **S14:** Correlation: 0.99964, VBOX Data Shift: 1.85 s
- **S15:** *NO USABLE VBOX Data*
- **S16:** *NO USABLE VBOX Data*
- **S17:** Correlation: 0.99979, VBOX Data Shift: -7.62 s

### Group 2
- **S01:** Correlation: 0.99987, VBOX Data Shift: 5.58 s
- **S02:** Correlation: 0.99980, VBOX Data Shift: 2.07 s
- **S03:** Correlation: 0.99986, VBOX Data Shift: 3.19 s
- **S04:** Correlation: 0.99989, VBOX Data Shift: 7.07 s
- **S05:** Correlation: 0.99978, VBOX Data Shift: 4.57 s
- **S06:** Correlation: 0.99989, VBOX Data Shift: 3.14 s
- **S07:** Correlation: 0.99992, VBOX Data Shift: 5.32 s
- **S08:** Correlation: 0.99985, VBOX Data Shift: 3.58 s
- **S09:** Correlation: 0.99976, VBOX Data Shift: 2.35 s
- **S10:** Correlation: 0.99988, VBOX Data Shift: 2.38 s
- **S11:** Correlation: 0.99977, VBOX Data Shift: 1.19 s
- **S12:** Correlation: 0.99982, VBOX Data Shift: 2.08 s
- **S13:** *NO USABLE VBOX Data*
- **S14:** Correlation: 0.99972, VBOX Data Shift: -1.89 s
- **S15:** Correlation: 0.99982, VBOX Data Shift: -5.48 s
- **S16:** Correlation: 0.99984, VBOX Data Shift: 3.48 s

### Group 3
- **S01:** Correlation: 0.99983, VBOX Data Shift: 1.89 s
- **S02:** Correlation: 0.99990, VBOX Data Shift: 3.46 s
- **S03:** Correlation: 0.99976, VBOX Data Shift: 2.43 s
- **S04:** Correlation: 0.99985, VBOX Data Shift: -22.07 s
- **S05:** Correlation: 0.99986, VBOX Data Shift: 2.40 s
- **S06:** Correlation: 0.99980, VBOX Data Shift: 3.22 s
- **S07:** Correlation: 0.99981, VBOX Data Shift: 2.92 s
- **S08:** Correlation: 0.99989, VBOX Data Shift: 3.41 s
- **S09**: Correlation: 0.9998,  VBOX Data Shift: 2.81s
- **S10**: Correlation: 0.9997,  VBOX Data Shift: -8.21s
- **S11**: Correlation: 0.9998,  VBOX Data Shift: 4.21s
- **S12**: Correlation: 0.9998,  VBOX Data Shift: 2.69s
- **S13**: *NO USABLE VBOX Data*
- **S14**: Correlation: 0.9978,  VBOX Data Shift: 3.73s
- **S15**: Correlation: 0.9998,  VBOX Data Shift: 2.44s
- **S16**: Correlation: 0.9998,  VBOX Data Shift: -24.30s
- **S17**: Correlation: 0.9999,  VBOX Data Shift: -6.93s
